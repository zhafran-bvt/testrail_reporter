"""
Dashboard statistics calculation module.

This module provides functions to calculate statistics for test plans and runs,
including pass rates, completion rates, and status distributions.

The module handles:
- Aggregating test results by status (Passed, Failed, Blocked, Retest, Untested)
- Calculating pass rates (percentage of passed tests out of executed tests)
- Calculating completion rates (percentage of executed tests out of total tests)
- Computing statistics for individual test runs
- Aggregating statistics across all runs in a test plan

Key Concepts:
- Pass Rate: (Passed / (Total - Untested)) * 100
  - Only counts executed tests in the denominator
  - Returns 0.0 if no tests have been executed
  
- Completion Rate: ((Total - Untested) / Total) * 100
  - Measures how many tests have been executed (any status except Untested)
  - Returns 0.0 if there are no tests

- Status Distribution: Dictionary mapping status names to counts
  - Uses TestRail status IDs: 1=Passed, 2=Blocked, 3=Untested, 4=Retest, 5=Failed
  - Unknown status IDs are mapped to "Unknown"

Error Handling:
- All functions validate input parameters
- Division by zero is handled gracefully (returns 0.0)
- Invalid data types are handled with appropriate error messages
- API errors are logged but don't crash the application

Performance Considerations:
- Functions make multiple API calls to TestRail
- Results should be cached at the API endpoint level
- Large plans with many runs may take several seconds to process
"""

from dataclasses import dataclass
from typing import Any

from testrail_client import TestRailClient


@dataclass
class RunStatistics:
    """Statistics for a single test run."""

    run_id: int
    run_name: str
    suite_name: str | None
    is_completed: bool
    total_tests: int
    status_distribution: dict[str, int]
    pass_rate: float
    completion_rate: float
    updated_on: int | None


@dataclass
class PlanStatistics:
    """Statistics for a test plan."""

    plan_id: int
    plan_name: str
    created_on: int
    is_completed: bool
    updated_on: int | None
    total_runs: int
    total_tests: int
    status_distribution: dict[str, int]
    pass_rate: float
    completion_rate: float
    failed_count: int
    blocked_count: int
    untested_count: int


def calculate_status_distribution(results: list[dict[str, Any]]) -> dict[str, int]:
    """
    Aggregate test results by status.

    Args:
        results: List of test result dictionaries with 'status_id' field

    Returns:
        Dictionary mapping status names to counts
    """
    # Validate input
    if not isinstance(results, list):
        raise ValueError(f"Results must be a list, got {type(results)}")
    
    # Common TestRail status IDs
    status_map = {
        1: "Passed",
        2: "Blocked",
        3: "Untested",
        4: "Retest",
        5: "Failed",
    }

    distribution: dict[str, int] = {}

    for result in results:
        # Handle non-dict results
        if not isinstance(result, dict):
            continue
        
        status_id = result.get("status_id")
        if status_id is None:
            status_name = "Untested"
        else:
            # Handle non-integer status IDs
            if not isinstance(status_id, int):
                try:
                    status_id = int(status_id)
                except (ValueError, TypeError):
                    status_name = "Unknown"
                else:
                    status_name = status_map.get(status_id, "Unknown")
            else:
                status_name = status_map.get(status_id, "Unknown")

        distribution[status_name] = distribution.get(status_name, 0) + 1

    return distribution


def calculate_pass_rate(status_distribution: dict[str, int]) -> float:
    """
    Calculate pass rate as percentage of passed tests out of executed tests.

    Args:
        status_distribution: Dictionary mapping status names to counts

    Returns:
        Pass rate as a percentage (0.0 to 100.0)
    """
    # Validate input
    if not isinstance(status_distribution, dict):
        raise ValueError(f"Status distribution must be a dict, got {type(status_distribution)}")
    
    # Handle empty distribution
    if not status_distribution:
        return 0.0
    
    # Calculate total, handling non-integer values
    total = 0
    for count in status_distribution.values():
        if isinstance(count, (int, float)):
            total += int(count)
        elif isinstance(count, str):
            try:
                total += int(count)
            except (ValueError, TypeError):
                pass  # Skip invalid string values
    
    # Handle division by zero - no tests at all
    if total == 0:
        return 0.0
    
    untested = status_distribution.get("Untested", 0)
    if isinstance(untested, (int, float)):
        untested = int(untested)
    elif isinstance(untested, str):
        try:
            untested = int(untested)
        except (ValueError, TypeError):
            untested = 0
    else:
        untested = 0
    
    executed = total - untested

    # Handle division by zero - no executed tests
    if executed <= 0:
        return 0.0

    passed = status_distribution.get("Passed", 0)
    if isinstance(passed, (int, float)):
        passed = int(passed)
    elif isinstance(passed, str):
        try:
            passed = int(passed)
        except (ValueError, TypeError):
            passed = 0
    else:
        passed = 0
    
    # Calculate pass rate with division by zero protection
    try:
        pass_rate = (passed / executed) * 100.0
        # Clamp to valid range
        return max(0.0, min(100.0, pass_rate))
    except ZeroDivisionError:
        return 0.0


def calculate_completion_rate(status_distribution: dict[str, int]) -> float:
    """
    Calculate completion rate as percentage of executed tests out of total tests.

    Args:
        status_distribution: Dictionary mapping status names to counts

    Returns:
        Completion rate as a percentage (0.0 to 100.0)
    """
    # Validate input
    if not isinstance(status_distribution, dict):
        raise ValueError(f"Status distribution must be a dict, got {type(status_distribution)}")
    
    # Handle empty distribution
    if not status_distribution:
        return 0.0
    
    # Calculate total, handling non-integer values
    total = 0
    for count in status_distribution.values():
        if isinstance(count, (int, float)):
            total += int(count)
        elif isinstance(count, str):
            try:
                total += int(count)
            except (ValueError, TypeError):
                pass  # Skip invalid string values

    # Handle division by zero - no tests at all
    if total == 0:
        return 0.0

    untested = status_distribution.get("Untested", 0)
    if isinstance(untested, (int, float)):
        untested = int(untested)
    elif isinstance(untested, str):
        try:
            untested = int(untested)
        except (ValueError, TypeError):
            untested = 0
    else:
        untested = 0
    
    executed = total - untested

    # Calculate completion rate with division by zero protection
    try:
        completion_rate = (executed / total) * 100.0
        # Clamp to valid range
        return max(0.0, min(100.0, completion_rate))
    except ZeroDivisionError:
        return 0.0


def calculate_run_statistics(
    run_id: int, client: TestRailClient
) -> RunStatistics:
    """
    Calculate statistics for a single test run.

    Args:
        run_id: TestRail run ID
        client: TestRail API client

    Returns:
        RunStatistics object with aggregated statistics
    
    Raises:
        ValueError: If run_id is invalid or tests data is malformed
    """
    # Validate input
    if not isinstance(run_id, int) or run_id < 1:
        raise ValueError(f"Invalid run_id: {run_id}")
    
    if client is None:
        raise ValueError("TestRail client cannot be None")
    
    # Fetch tests for the run
    try:
        tests = client.get_tests_for_run(run_id)
    except Exception as e:
        raise ValueError(f"Failed to fetch tests for run {run_id}: {e}")
    
    # Validate tests data
    if not isinstance(tests, list):
        raise ValueError(f"Invalid tests data type: {type(tests)}")

    # Build status distribution from tests
    try:
        status_distribution = calculate_status_distribution(tests)
    except Exception as e:
        raise ValueError(f"Failed to calculate status distribution for run {run_id}: {e}")

    # Calculate rates
    try:
        pass_rate = calculate_pass_rate(status_distribution)
        completion_rate = calculate_completion_rate(status_distribution)
    except Exception as e:
        raise ValueError(f"Failed to calculate rates for run {run_id}: {e}")

    # Extract run metadata (from first test if available)
    run_name = f"Run {run_id}"
    suite_name = None
    is_completed = False
    updated_on = None

    if tests:
        first_test = tests[0] if isinstance(tests[0], dict) else {}
        run_name = first_test.get("run_name") or run_name
        suite_name = first_test.get("suite_name")
        
        # Check if run is completed (all tests have status)
        try:
            is_completed = all(
                isinstance(t, dict) and t.get("status_id") is not None 
                for t in tests
            )
        except Exception:
            is_completed = False
        
        # Get most recent update timestamp
        try:
            timestamps = []
            for t in tests:
                if isinstance(t, dict):
                    ts = t.get("updated_on")
                    if ts is not None and isinstance(ts, (int, float)):
                        timestamps.append(ts)
            updated_on = max(timestamps) if timestamps else None
        except Exception:
            updated_on = None

    return RunStatistics(
        run_id=run_id,
        run_name=run_name,
        suite_name=suite_name,
        is_completed=is_completed,
        total_tests=len(tests),
        status_distribution=status_distribution,
        pass_rate=pass_rate,
        completion_rate=completion_rate,
        updated_on=updated_on,
    )


def calculate_plan_statistics(
    plan_id: int, client: TestRailClient
) -> PlanStatistics:
    """
    Calculate aggregated statistics across all runs in a plan.

    Args:
        plan_id: TestRail plan ID
        client: TestRail API client

    Returns:
        PlanStatistics object with aggregated statistics
    
    Raises:
        ValueError: If plan_id is invalid or plan data is malformed
    """
    # Validate input
    if not isinstance(plan_id, int) or plan_id < 1:
        raise ValueError(f"Invalid plan_id: {plan_id}")
    
    if client is None:
        raise ValueError("TestRail client cannot be None")
    
    # Fetch plan details
    try:
        plan = client.get_plan(plan_id)
    except Exception as e:
        raise ValueError(f"Failed to fetch plan {plan_id}: {e}")
    
    # Validate plan data
    if not isinstance(plan, dict):
        raise ValueError(f"Invalid plan data type: {type(plan)}")

    # Extract plan metadata with validation
    plan_name = plan.get("name")
    if not plan_name or not isinstance(plan_name, str):
        plan_name = f"Plan {plan_id}"
    
    created_on = plan.get("created_on")
    if not isinstance(created_on, (int, float)):
        created_on = 0
    else:
        created_on = int(created_on)
    
    is_completed = plan.get("is_completed")
    if not isinstance(is_completed, bool):
        is_completed = False
    
    updated_on = plan.get("updated_on")
    if updated_on is not None and not isinstance(updated_on, (int, float)):
        updated_on = None

    # Collect all runs from plan entries
    run_ids = []
    entries = plan.get("entries", [])
    if not isinstance(entries, list):
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
            if run_id and isinstance(run_id, int):
                run_ids.append(run_id)

    # Aggregate statistics across all runs
    total_tests = 0
    combined_distribution: dict[str, int] = {}

    for run_id in run_ids:
        try:
            tests = client.get_tests_for_run(run_id)
            if not isinstance(tests, list):
                continue
            
            total_tests += len(tests)

            # Aggregate status distribution
            try:
                run_distribution = calculate_status_distribution(tests)
                for status, count in run_distribution.items():
                    if isinstance(count, (int, float)):
                        combined_distribution[status] = combined_distribution.get(status, 0) + int(count)
            except Exception as e:
                # Log but continue with other runs
                print(f"Warning: Failed to calculate distribution for run {run_id}: {e}", flush=True)
                continue
        except Exception as e:
            # Log but continue with other runs
            print(f"Warning: Failed to fetch tests for run {run_id}: {e}", flush=True)
            continue

    # Calculate aggregated rates
    try:
        pass_rate = calculate_pass_rate(combined_distribution)
        completion_rate = calculate_completion_rate(combined_distribution)
    except Exception as e:
        print(f"Warning: Failed to calculate rates for plan {plan_id}: {e}", flush=True)
        pass_rate = 0.0
        completion_rate = 0.0

    # Extract specific counts with validation
    failed_count = combined_distribution.get("Failed", 0)
    if not isinstance(failed_count, (int, float)):
        failed_count = 0
    
    blocked_count = combined_distribution.get("Blocked", 0)
    if not isinstance(blocked_count, (int, float)):
        blocked_count = 0
    
    untested_count = combined_distribution.get("Untested", 0)
    if not isinstance(untested_count, (int, float)):
        untested_count = 0

    return PlanStatistics(
        plan_id=plan_id,
        plan_name=plan_name,
        created_on=created_on,
        is_completed=is_completed,
        updated_on=updated_on,
        total_runs=len(run_ids),
        total_tests=total_tests,
        status_distribution=combined_distribution,
        pass_rate=pass_rate,
        completion_rate=completion_rate,
        failed_count=int(failed_count),
        blocked_count=int(blocked_count),
        untested_count=int(untested_count),
    )
