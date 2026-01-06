"""Dashboard API endpoints."""

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request

import app.core.dependencies as dependencies
from app.core.config import config
from app.core.dependencies import get_dashboard_plan_detail_cache, get_dashboard_plans_cache, get_dashboard_stats_cache
from app.models.responses import DashboardPlanDetail, DashboardPlansResponse, DashboardRunsResponse
from app.services.cache import cache_meta
from app.services.testrail_client import testrail_service


def _resolve_testrail_client(request: Request):
    """
    Resolve TestRail client with support for FastAPI dependency overrides and runtime patching.

    Tests can override app.core.dependencies.get_testrail_client via dependency_overrides
    or monkeypatching; this resolver checks overrides first and otherwise calls the
    dependency module directly.
    """
    override = request.app.dependency_overrides.get(dependencies.get_testrail_client)
    if override:
        return override()
    return dependencies.get_testrail_client()


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/plans", response_model=DashboardPlansResponse)
def get_dashboard_plans(
    project: int = 1,
    is_completed: int | None = None,
    limit: int | None = None,
    offset: int = 0,
    created_after: int | None = None,
    created_before: int | None = None,
    search: str | None = None,
    plans_cache=Depends(get_dashboard_plans_cache),
    client=Depends(_resolve_testrail_client),
):
    """
    Get paginated list of test plans with aggregated statistics for the dashboard.

    This endpoint fetches test plans from TestRail and calculates comprehensive statistics
    for each plan, including pass rates, completion rates, and status distributions.
    Results are cached for performance (default: 5 minutes).
    """
    # Validate parameters
    if project < 1:
        raise HTTPException(status_code=400, detail="Project ID must be positive")

    if offset < 0:
        raise HTTPException(status_code=400, detail="Offset must be non-negative")

    if is_completed is not None and is_completed not in (0, 1):
        raise HTTPException(status_code=400, detail="is_completed must be 0 or 1")

    # Validate date range
    if created_after is not None and created_after < 0:
        raise HTTPException(status_code=400, detail="created_after must be non-negative timestamp")

    if created_before is not None and created_before < 0:
        raise HTTPException(status_code=400, detail="created_before must be non-negative timestamp")

    if created_after is not None and created_before is not None and created_after > created_before:
        raise HTTPException(status_code=400, detail="created_after must be less than or equal to created_before")

    # Validate and normalize limit using configured defaults
    if limit is None:
        limit = config.DASHBOARD_DEFAULT_PAGE_SIZE
    limit = max(1, min(limit, config.DASHBOARD_MAX_PAGE_SIZE))

    # Check cache
    cache_key = ("dashboard_plans", project, is_completed, offset, limit, created_after, created_before, search)
    cached = plans_cache.get(cache_key)
    if cached:
        payload, expires_at = cached
        data = payload.copy()
        estimated_flag = data.pop("_estimated_total", False)
        data["meta"] = cache_meta(True, expires_at)
        data["meta"]["estimated_total"] = estimated_flag
        return data

    try:
        base_client = client or testrail_service.get_client()

        def _apply_search_and_date(plans: list[dict]) -> list[dict]:
            filtered = []
            search_term = search.strip().lower() if search else None
            for plan in plans:
                if not isinstance(plan, dict):
                    continue
                if created_after is not None or created_before is not None:
                    created_on = plan.get("created_on")
                    if created_on is None:
                        created_on = 0
                    elif not isinstance(created_on, (int, float)):
                        try:
                            created_on = int(created_on)
                        except (ValueError, TypeError):
                            created_on = 0
                    if created_after is not None and created_on < created_after:
                        continue
                    if created_before is not None and created_on > created_before:
                        continue
                if search_term:
                    plan_name = plan.get("name", "")
                    if not isinstance(plan_name, str):
                        plan_name = str(plan_name) if plan_name is not None else ""
                    if search_term not in plan_name.lower():
                        continue
                filtered.append(plan)
            return filtered

        # Fetch only the window we need (plus one extra to detect has_more)
        # Use smaller batch size for incomplete plans to avoid timeouts
        if is_completed == 0:
            page_batch_size = min(limit * 2, 25)  # Smaller batch for incomplete plans
        else:
            page_batch_size = max(limit * 2, 50)
        needed = limit + 1
        cursor = offset
        collected: list[dict] = []
        source_exhausted = False

        while len(collected) < needed:
            try:
                batch = base_client.get_plans_for_project(
                    project,
                    is_completed=is_completed,
                    created_after=created_after,
                    created_before=created_before,
                    start_offset=cursor,
                    max_plans=page_batch_size,
                    page_limit=page_batch_size,
                )
            except Exception as e:
                print(f"Error: TestRail API error for project {project}: {e}", flush=True)
                raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {str(e)}")

            if not batch:
                source_exhausted = True
                break

            if not isinstance(batch, list):
                print(f"Error: Invalid plans data type: {type(batch)}", flush=True)
                raise HTTPException(status_code=500, detail="Invalid response from TestRail API")

            cursor += len(batch)
            filtered_batch = _apply_search_and_date(batch)
            collected.extend(filtered_batch)

            if len(batch) < page_batch_size:
                source_exhausted = True
                break

        total_count = offset + len(collected)
        if not source_exhausted or len(collected) > limit:
            # Indicate at least one more plan may be available
            total_count += 1

        paginated_plans = collected[:limit]

        # Calculate statistics for each plan using parallel processing
        try:
            from app.dashboard_stats import calculate_plan_statistics
        except ImportError:
            # Fallback if dashboard_stats module not available
            def calculate_plan_statistics(plan_id: int, client: Any) -> Any:
                class MockStats:
                    def __init__(self, plan_id: int, plan_name: str = "Unknown Plan"):
                        self.plan_id = plan_id
                        self.plan_name = plan_name
                        self.created_on = 0
                        self.is_completed = False
                        self.updated_on = None
                        self.total_runs = 0
                        self.total_tests = 0
                        self.status_distribution: Dict[str, int] = {}
                        self.pass_rate = 0.0
                        self.completion_rate = 0.0
                        self.failed_count = 0
                        self.blocked_count = 0
                        self.untested_count = 0

                return MockStats(plan_id)

        def calculate_stats_for_plan(plan):
            """Helper function to calculate stats for a single plan."""
            if not isinstance(plan, dict):
                print(f"Warning: Skipping invalid plan data: {plan}", flush=True)
                return None

            plan_id = plan.get("id")
            if not plan_id:
                print(f"Warning: Skipping plan with missing ID: {plan}", flush=True)
                return None

            try:
                # Create a new client for this thread
                stats = calculate_plan_statistics(plan_id, base_client)

                # Convert to dict format
                return {
                    "plan_id": stats.plan_id,
                    "plan_name": stats.plan_name,
                    "created_on": stats.created_on,
                    "is_completed": stats.is_completed,
                    "updated_on": stats.updated_on,
                    "total_runs": stats.total_runs,
                    "total_tests": stats.total_tests,
                    "status_distribution": stats.status_distribution,
                    "pass_rate": stats.pass_rate,
                    "completion_rate": stats.completion_rate,
                    "failed_count": stats.failed_count,
                    "blocked_count": stats.blocked_count,
                    "untested_count": stats.untested_count,
                }
            except Exception as e:
                print(f"Warning: Failed to calculate stats for plan {plan_id}: {e}", flush=True)
                # Include plan with minimal info if stats calculation fails
                return {
                    "plan_id": plan_id,
                    "plan_name": plan.get("name", f"Plan {plan_id}"),
                    "created_on": plan.get("created_on", 0),
                    "is_completed": plan.get("is_completed", False),
                    "updated_on": plan.get("updated_on"),
                    "total_runs": 0,
                    "total_tests": 0,
                    "status_distribution": {},
                    "pass_rate": 0.0,
                    "completion_rate": 0.0,
                    "failed_count": 0,
                    "blocked_count": 0,
                    "untested_count": 0,
                }

        # Use ThreadPoolExecutor to calculate stats in parallel
        # Limit to 2 workers to avoid TestRail API rate limits
        max_workers = min(2, len(paginated_plans))
        plans_with_stats = []

        if paginated_plans:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_plan = {executor.submit(calculate_stats_for_plan, plan): plan for plan in paginated_plans}

                # Collect results as they complete
                for future in future_to_plan:
                    try:
                        result = future.result(timeout=15)  # 15 second timeout per plan
                        if result is not None:
                            plans_with_stats.append(result)
                    except Exception as e:
                        plan = future_to_plan[future]
                        plan_id = plan.get("id") if isinstance(plan, dict) else "unknown"
                        print(f"Warning: Failed to get stats for plan {plan_id}: {e}", flush=True)
                        # Add plan with minimal stats if calculation fails
                        if isinstance(plan, dict) and plan.get("id"):
                            plans_with_stats.append(
                                {
                                    "plan_id": plan["id"],
                                    "plan_name": plan.get("name", f"Plan {plan['id']}"),
                                    "created_on": plan.get("created_on", 0),
                                    "is_completed": plan.get("is_completed", False),
                                    "updated_on": plan.get("updated_on"),
                                    "total_runs": 0,
                                    "total_tests": 0,
                                    "status_distribution": {},
                                    "pass_rate": 0.0,
                                    "completion_rate": 0.0,
                                    "failed_count": 0,
                                    "blocked_count": 0,
                                    "untested_count": 0,
                                }
                            )

        has_more = (len(collected) > limit) or (not source_exhausted)
        estimated_total = not source_exhausted or len(collected) > limit

        response_data = {
            "plans": plans_with_stats,
            "total_count": total_count,
            "offset": offset,
            "limit": limit,
            "has_more": has_more,
            "meta": {},
            "_estimated_total": estimated_total,
        }

        # Cache the response
        expires_at = plans_cache.set(cache_key, response_data, ttl_seconds=config.DASHBOARD_PLANS_CACHE_TTL)
        meta_dict = cache_meta(False, expires_at)
        meta_dict["estimated_total"] = estimated_total
        response_data["meta"] = meta_dict

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: Unexpected error in dashboard plans: {e}", flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard plans: {str(e)}")


@router.get("/plan/{plan_id}", response_model=DashboardPlanDetail)
def get_dashboard_plan_detail(
    plan_id: int,
    plan_detail_cache=Depends(get_dashboard_plan_detail_cache),
    client=Depends(_resolve_testrail_client),
):
    """
    Get detailed information for a specific test plan including all runs and their statistics.
    """
    # Validate plan_id
    if plan_id < 1:
        raise HTTPException(status_code=400, detail="Plan ID must be positive")

    # Check cache
    cache_key = ("dashboard_plan_detail", plan_id)
    cached = plan_detail_cache.get(cache_key)
    if cached:
        payload, expires_at = cached
        data = payload.copy()
        data["meta"] = cache_meta(True, expires_at)
        return data

    try:
        base_client = client or testrail_service.get_client()

        # Calculate plan statistics
        try:
            from app.dashboard_stats import (
                calculate_plan_statistics,
                calculate_run_statistics,
            )
        except ImportError:
            # Fallback if dashboard_stats module not available
            def calculate_plan_statistics(plan_id: int, client: Any) -> Any:
                class MockStats:
                    def __init__(self, plan_id: int):
                        self.plan_id = plan_id
                        self.plan_name = f"Plan {plan_id}"
                        self.created_on = 0
                        self.is_completed = False
                        self.updated_on = None
                        self.total_runs = 0
                        self.total_tests = 0
                        self.status_distribution: Dict[str, int] = {}
                        self.pass_rate = 0.0
                        self.completion_rate = 0.0
                        self.failed_count = 0
                        self.blocked_count = 0
                        self.untested_count = 0

                return MockStats(plan_id)

            def calculate_run_statistics(run_id: int, client: Any) -> Any:
                class MockRunStats:
                    def __init__(self, run_id: int):
                        self.run_id = run_id
                        self.run_name = f"Run {run_id}"
                        self.suite_name = None
                        self.is_completed = False
                        self.total_tests = 0
                        self.status_distribution: Dict[str, int] = {}
                        self.pass_rate = 0.0
                        self.completion_rate = 0.0
                        self.updated_on = None

                return MockRunStats(run_id)

        try:
            plan_stats = calculate_plan_statistics(plan_id, base_client)
        except ValueError as e:
            print(f"Error: Invalid data for plan {plan_id}: {e}", flush=True)
            raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found or contains invalid data")

        # Convert plan stats to dict
        plan_dict = {
            "plan_id": plan_stats.plan_id,
            "plan_name": plan_stats.plan_name,
            "created_on": plan_stats.created_on,
            "is_completed": plan_stats.is_completed,
            "updated_on": plan_stats.updated_on,
            "total_runs": plan_stats.total_runs,
            "total_tests": plan_stats.total_tests,
            "status_distribution": plan_stats.status_distribution,
            "pass_rate": plan_stats.pass_rate,
            "completion_rate": plan_stats.completion_rate,
            "failed_count": plan_stats.failed_count,
            "blocked_count": plan_stats.blocked_count,
            "untested_count": plan_stats.untested_count,
        }

        # Get all runs for the plan
        try:
            plan_data = base_client.get_plan(plan_id)
        except Exception as e:
            print(f"Error: Failed to fetch plan data for {plan_id}: {e}", flush=True)
            raise HTTPException(status_code=502, detail=f"Error fetching plan data from TestRail API: {str(e)}")

        # Validate plan data
        if not isinstance(plan_data, dict):
            print(f"Error: Invalid plan data type for {plan_id}: {type(plan_data)}", flush=True)
            raise HTTPException(status_code=500, detail="Invalid response from TestRail API")

        run_ids: list[int] = []
        run_meta_map: dict[int, dict[str, Any]] = {}
        entries = plan_data.get("entries", [])
        if not isinstance(entries, list):
            print(f"Warning: Invalid entries type for plan {plan_id}: {type(entries)}", flush=True)
            entries = []

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            suite_name = entry.get("name")
            runs = entry.get("runs", [])
            if not isinstance(runs, list):
                continue
            for run in runs:
                if not isinstance(run, dict):
                    continue
                run_id = run.get("id")
                if run_id:
                    try:
                        run_id_int = int(run_id)
                    except (TypeError, ValueError):
                        continue
                    run_ids.append(run_id_int)
                    run_meta_map[run_id_int] = {
                        "run_name": run.get("name"),
                        "suite_name": run.get("suite_name") or suite_name,
                        "is_completed": run.get("is_completed"),
                        "updated_on": run.get("updated_on"),
                    }

        # Calculate statistics for each run
        runs_with_stats = []
        for run_id in run_ids:
            try:
                run_stats = calculate_run_statistics(run_id, base_client)

                # Convert to dict format
                meta = run_meta_map.get(run_id, {})
                run_name = meta.get("run_name") or run_stats.run_name or f"Run {run_id}"
                suite_name = meta.get("suite_name") or run_stats.suite_name
                is_completed = meta.get("is_completed")
                if is_completed is None:
                    is_completed = run_stats.is_completed
                updated_on = meta.get("updated_on")
                if updated_on is None:
                    updated_on = run_stats.updated_on
                run_dict = {
                    "run_id": run_stats.run_id,
                    "run_name": run_name,
                    "suite_name": suite_name,
                    "is_completed": is_completed,
                    "total_tests": run_stats.total_tests,
                    "status_distribution": run_stats.status_distribution,
                    "pass_rate": run_stats.pass_rate,
                    "completion_rate": run_stats.completion_rate,
                    "updated_on": updated_on,
                }
                runs_with_stats.append(run_dict)
            except Exception as e:
                print(f"Warning: Failed to calculate stats for run {run_id}: {e}", flush=True)

        response_data = {
            "plan": plan_dict,
            "runs": runs_with_stats,
            "meta": {},
        }

        # Cache the response
        expires_at = plan_detail_cache.set(cache_key, response_data, ttl_seconds=config.DASHBOARD_PLAN_DETAIL_CACHE_TTL)
        response_data["meta"] = cache_meta(False, expires_at)

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: Unexpected error in plan detail: {e}", flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch plan details: {str(e)}")


@router.get("/runs/{plan_id}", response_model=DashboardRunsResponse)
def get_dashboard_runs(
    plan_id: int,
    stats_cache=Depends(get_dashboard_stats_cache),
    client=Depends(_resolve_testrail_client),
):
    """
    Get list of runs for a specific plan with statistics.
    """
    # Validate plan_id
    if plan_id < 1:
        raise HTTPException(status_code=400, detail="Plan ID must be positive")

    # Check cache
    cache_key = ("dashboard_runs", plan_id)
    cached = stats_cache.get(cache_key)
    if cached:
        payload, expires_at = cached
        data = payload.copy()
        data["meta"] = cache_meta(True, expires_at)
        return data

    try:
        base_client = client or testrail_service.get_client()

        # Get all runs for the plan
        try:
            plan_data = base_client.get_plan(plan_id)
        except Exception as e:
            print(f"Error: Failed to fetch plan data for {plan_id}: {e}", flush=True)
            raise HTTPException(status_code=502, detail=f"Error fetching plan data from TestRail API: {str(e)}")

        # Validate plan data
        if not isinstance(plan_data, dict):
            print(f"Error: Invalid plan data type for {plan_id}: {type(plan_data)}", flush=True)
            raise HTTPException(status_code=500, detail="Invalid response from TestRail API")

        run_ids = []
        entries = plan_data.get("entries", [])
        if not isinstance(entries, list):
            print(f"Warning: Invalid entries type for plan {plan_id}: {type(entries)}", flush=True)
            entries = []

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            runs = entry.get("runs", [])
            if not isinstance(runs, list):
                continue
            for run in runs:
                if not isinstance(run, dict):
                    continue
                run_id = run.get("id")
                if run_id:
                    run_ids.append(run_id)

        # Calculate statistics for each run
        try:
            from app.dashboard_stats import calculate_run_statistics
        except ImportError:
            # Fallback if dashboard_stats module not available
            def calculate_run_statistics(run_id: int, client: Any) -> Any:
                class MockRunStats:
                    def __init__(self, run_id: int):
                        self.run_id = run_id
                        self.run_name = f"Run {run_id}"
                        self.suite_name = None
                        self.is_completed = False
                        self.total_tests = 0
                        self.status_distribution: Dict[str, int] = {}
                        self.pass_rate = 0.0
                        self.completion_rate = 0.0
                        self.updated_on = None

                return MockRunStats(run_id)

        runs_with_stats = []
        for run_id in run_ids:
            try:
                run_stats = calculate_run_statistics(run_id, base_client)

                # Convert to dict format
                run_dict = {
                    "run_id": run_stats.run_id,
                    "run_name": run_stats.run_name,
                    "suite_name": run_stats.suite_name,
                    "is_completed": run_stats.is_completed,
                    "total_tests": run_stats.total_tests,
                    "status_distribution": run_stats.status_distribution,
                    "pass_rate": run_stats.pass_rate,
                    "completion_rate": run_stats.completion_rate,
                    "updated_on": run_stats.updated_on,
                }
                runs_with_stats.append(run_dict)
            except Exception as e:
                print(f"Warning: Failed to calculate stats for run {run_id}: {e}", flush=True)

        response_data = {
            "plan_id": plan_id,
            "runs": runs_with_stats,
            "meta": {},
        }

        # Cache the response
        expires_at = stats_cache.set(cache_key, response_data, ttl_seconds=config.DASHBOARD_RUN_STATS_CACHE_TTL)
        response_data["meta"] = cache_meta(False, expires_at)

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: Unexpected error in dashboard runs: {e}", flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch runs: {str(e)}")


@router.get("/config")
def get_dashboard_config():
    """
    Get dashboard configuration values for client-side use.
    """
    return {
        "cache": {
            "plans_ttl": config.DASHBOARD_PLANS_CACHE_TTL,
            "plan_detail_ttl": config.DASHBOARD_PLAN_DETAIL_CACHE_TTL,
            "stats_ttl": config.DASHBOARD_STATS_CACHE_TTL,
            "run_stats_ttl": config.DASHBOARD_RUN_STATS_CACHE_TTL,
        },
        "pagination": {
            "default_page_size": config.DASHBOARD_DEFAULT_PAGE_SIZE,
            "max_page_size": config.DASHBOARD_MAX_PAGE_SIZE,
        },
        "visual_thresholds": {
            "pass_rate_high": config.DASHBOARD_PASS_RATE_HIGH,
            "pass_rate_medium": config.DASHBOARD_PASS_RATE_MEDIUM,
            "critical_fail_threshold": config.DASHBOARD_CRITICAL_FAIL_THRESHOLD,
            "critical_block_threshold": config.DASHBOARD_CRITICAL_BLOCK_THRESHOLD,
        },
    }


@router.post("/cache/clear")
def clear_dashboard_cache(
    plans_cache=Depends(get_dashboard_plans_cache),
    plan_detail_cache=Depends(get_dashboard_plan_detail_cache),
    stats_cache=Depends(get_dashboard_stats_cache),
):
    """
    Clear all dashboard caches to force fresh data fetch from TestRail.
    """
    plans_cache.clear()
    plan_detail_cache.clear()
    stats_cache.clear()

    return {
        "status": "success",
        "message": "All dashboard caches cleared",
        "cleared_caches": ["dashboard_plans", "dashboard_plan_detail", "dashboard_stats"],
    }
