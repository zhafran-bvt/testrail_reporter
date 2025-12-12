"""General API endpoints for plans, runs, cases, and users."""

import json
from datetime import datetime
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.dependencies import get_testrail_client, get_plans_cache, get_runs_cache
from app.services.cache import cache_meta
from testrail_client import get_plan, get_plans_for_project
from testrail_daily_report import env_or_die

router = APIRouter(prefix="/api", tags=["general"])

# Default status mapping for test cases
DEFAULT_STATUS_MAP = {
    1: "Passed",
    2: "Blocked", 
    3: "Untested",
    4: "Retest",
    5: "Failed",
}


@router.get("/plans")
def get_plans(
    project: int = 1,
    is_completed: int | None = None,
    plans_cache=Depends(get_plans_cache)
):
    """List plans for a project, optionally filter by completion (0 or 1)."""
    cache_key = ("plans", project, is_completed)
    cached = plans_cache.get(cache_key)
    if cached:
        payload, expires_at = cached
        data = payload.copy()
        data["meta"] = cache_meta(True, expires_at)
        return data
    
    try:
        base_url = env_or_die("TESTRAIL_BASE_URL").rstrip("/")
        user = env_or_die("TESTRAIL_USER")
        api_key = env_or_die("TESTRAIL_API_KEY")
    except SystemExit:
        raise HTTPException(status_code=500, detail="Server missing TestRail credentials")
    
    import requests
    session = requests.Session()
    session.auth = (user, api_key)
    plans = get_plans_for_project(session, base_url, project_id=project, is_completed=is_completed)
    
    # return concise info
    slim = [
        {
            "id": p.get("id"),
            "name": p.get("name"),
            "is_completed": p.get("is_completed"),
            "created_on": p.get("created_on"),
        }
        for p in plans
    ]
    base_payload = {"count": len(slim), "plans": slim}
    expires_at = plans_cache.set(cache_key, base_payload)
    resp = base_payload.copy()
    resp["meta"] = cache_meta(False, expires_at)
    return resp


@router.get("/runs")
def get_runs(
    plan: int | None = None,
    project: int = 1,
    runs_cache=Depends(get_runs_cache)
):
    """Return runs for a plan. If no plan is provided, return an empty list instead of 422."""
    # Gracefully handle missing plan so client-side refreshes don't 422
    if plan is None:
        return {
            "count": 0,
            "runs": [],
            "meta": {
                "cache": {
                    "hit": False,
                    "expires_at": None,
                    "seconds_remaining": 0,
                }
            },
        }
    if plan < 1:
        raise HTTPException(status_code=400, detail="plan must be positive")

    cache_key = ("runs", project, plan)
    cached = runs_cache.get(cache_key)
    if cached:
        payload, expires_at = cached
        data = payload.copy()
        data["meta"] = cache_meta(True, expires_at)
        return data
    
    try:
        base_url = env_or_die("TESTRAIL_BASE_URL").rstrip("/")
        user = env_or_die("TESTRAIL_USER")
        api_key = env_or_die("TESTRAIL_API_KEY")
    except SystemExit:
        raise HTTPException(status_code=500, detail="Server missing TestRail credentials")
    
    import requests
    session = requests.Session()
    session.auth = (user, api_key)
    try:
        plan_obj = get_plan(session, base_url, plan)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error fetching plan runs: {e}")
    
    runs = []
    for entry in plan_obj.get("entries", []):
        suite_name = entry.get("name")
        for r in entry.get("runs", []):
            rid = r.get("id")
            if rid is None:
                continue
            runs.append(
                {
                    "id": rid,
                    "name": r.get("name") or f"Run {rid}",
                    "is_completed": r.get("is_completed"),
                    "suite_name": suite_name,
                }
            )
    runs.sort(key=lambda item: (item.get("is_completed", 0), item.get("name", "")))
    print(f"[api_runs] plan={plan} returned {len(runs)} runs", flush=True)
    base_payload = {"count": len(runs), "runs": runs}
    expires_at = runs_cache.set(cache_key, base_payload)
    data = base_payload.copy()
    data["meta"] = cache_meta(False, expires_at)
    return data


@router.get("/run/{run_id}")
def get_run(run_id: int, client=Depends(get_testrail_client)):
    """Fetch details for a specific run."""
    try:
        base_url = env_or_die("TESTRAIL_BASE_URL").rstrip("/")
        user = env_or_die("TESTRAIL_USER")
        api_key = env_or_die("TESTRAIL_API_KEY")
    except SystemExit:
        raise HTTPException(status_code=500, detail="Server missing TestRail credentials")

    import requests
    session = requests.Session()
    session.auth = (user, api_key)

    try:
        # Fetch run details from TestRail
        response = session.get(f"{base_url}/index.php?/api/v2/get_run/{run_id}")
        response.raise_for_status()
        run_data = response.json()

        return {
            "run": {
                "id": run_data.get("id"),
                "name": run_data.get("name"),
                "description": run_data.get("description"),
                "refs": run_data.get("refs"),
                "is_completed": run_data.get("is_completed"),
                "plan_id": run_data.get("plan_id"),
            }
        }
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error fetching run: {e}")


@router.get("/tests/{run_id}")
def get_tests_for_run(run_id: int, client=Depends(get_testrail_client)):
    """Fetch test cases for a specific run."""
    # Validate run_id
    if run_id < 1:
        raise HTTPException(status_code=400, detail="Run ID must be positive")

    try:
        # Fetch run details for the run name
        run_data = client.get_run(run_id)
        run_name = run_data.get("name") or f"Run {run_id}"

        # Fetch tests for the run
        tests = client.get_tests_for_run(run_id)

        # Get status mapping (use defaults if API fails)
        try:
            statuses = client.get_statuses_map(defaults=DEFAULT_STATUS_MAP)
        except Exception:
            statuses = DEFAULT_STATUS_MAP.copy()

        # Map tests to response format
        test_list = []
        for test in tests:
            test_id = test.get("id")
            if test_id is None:
                continue

            status_id = test.get("status_id")
            status_name = statuses.get(status_id, f"Status {status_id}") if status_id else "Unknown"

            test_list.append(
                {
                    "id": test_id,
                    "case_id": test.get("case_id"),
                    "title": test.get("title") or f"Test {test_id}",
                    "status_id": status_id,
                    "status_name": status_name,
                    "refs": test.get("refs"),
                }
            )

        return {
            "run_id": run_id,
            "run_name": run_name,
            "tests": test_list,
            "count": len(test_list),
        }

    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        raise HTTPException(status_code=502, detail=f"TestRail API error: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tests: {str(e)}")


@router.post("/cache/clear")
def clear_cache(
    plans_cache=Depends(get_plans_cache),
    runs_cache=Depends(get_runs_cache)
):
    """Clear the plans and runs cache for the reporter page."""
    plans_cache.clear()
    runs_cache.clear()

    return {
        "success": True,
        "message": "Cache cleared successfully",
        "cleared_at": datetime.now().isoformat()
    }


@router.get("/cases")
def get_cases(
    project: int = 1,
    suite_id: int | None = None,
    section_id: int | None = None,
    filters: str | None = None,
    client=Depends(get_testrail_client)
):
    """Get test cases for a project/suite/section."""
    try:
        filter_section_id = None
        if not section_id and filters:
            try:
                parsed = json.loads(filters)
                section_vals = parsed.get("filters", {}).get("cases:section_id", {}).get("values")
                if isinstance(section_vals, list) and section_vals:
                    try:
                        filter_section_id = int(str(section_vals[0]).strip())
                    except (TypeError, ValueError):
                        filter_section_id = None
            except Exception:
                filter_section_id = None
        effective_section = section_id or filter_section_id
        cases = client.get_cases(project, suite_id=suite_id, section_id=effective_section)
    except HTTPException:
        raise
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error fetching cases: {e}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load cases: {exc}")
    
    slim = []
    for c in cases:
        cid = c.get("id")
        if cid is None:
            continue
        slim.append(
            {
                "id": cid,
                "title": c.get("title") or f"Case {cid}",
                "refs": c.get("refs"),
                "updated_on": c.get("updated_on"),
                "priority_id": c.get("priority_id"),
                "section_id": c.get("section_id"),
            }
        )
    return {"count": len(slim), "cases": slim}


@router.get("/users")
def get_users(project: int = 1, client=Depends(get_testrail_client)):
    """Return list of users for dropdowns."""
    try:
        users = client.get_users_map()
        items = [{"id": uid, "name": name} for uid, name in sorted(users.items(), key=lambda kv: kv[1])]
        return {"count": len(items), "users": items}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load users: {exc}")