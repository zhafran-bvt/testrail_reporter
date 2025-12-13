"""Health check API endpoints."""

import requests
from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_plans_cache, get_runs_cache, get_testrail_client
from testrail_client import DEFAULT_HTTP_BACKOFF, DEFAULT_HTTP_RETRIES, DEFAULT_HTTP_TIMEOUT

router = APIRouter(tags=["health"])


@router.get("/healthz")
def health_check(plans_cache=Depends(get_plans_cache), runs_cache=Depends(get_runs_cache)):
    """Basic health check endpoint."""
    # Import here to avoid circular imports
    try:
        from app.api.reports import job_manager

        queue_stats = job_manager.stats()
    except ImportError:
        # Fallback if reports module not available
        queue_stats = {"size": 0, "running": 0, "queued": 0}

    return {
        "ok": True,
        "queue": queue_stats,
        "cache": {
            "plans": plans_cache.stats(),
            "runs": runs_cache.stats(),
        },
        "http": {
            "timeout_seconds": DEFAULT_HTTP_TIMEOUT,
            "retries": DEFAULT_HTTP_RETRIES,
            "backoff_seconds": DEFAULT_HTTP_BACKOFF,
        },
    }


@router.get("/health/detailed")
def detailed_health_check(
    client=Depends(get_testrail_client), plans_cache=Depends(get_plans_cache), runs_cache=Depends(get_runs_cache)
):
    """Detailed health check including TestRail connectivity."""
    health_status = {"ok": True, "checks": {}, "timestamp": None}

    from datetime import datetime, timezone

    health_status["timestamp"] = datetime.now(timezone.utc).isoformat()

    # Check cache health
    try:
        plans_stats = plans_cache.stats()
        runs_stats = runs_cache.stats()
        health_status["checks"]["cache"] = {"status": "healthy", "plans": plans_stats, "runs": runs_stats}
    except Exception as e:
        health_status["ok"] = False
        health_status["checks"]["cache"] = {"status": "unhealthy", "error": str(e)}

    # Check TestRail connectivity
    try:
        # Try a simple API call to test connectivity
        # This is a lightweight call that should work if credentials are valid
        with client.make_session() as session:
            response = session.get(f"{client.base_url}/index.php?/api/v2/get_statuses")
            response.raise_for_status()

        health_status["checks"]["testrail"] = {"status": "healthy", "base_url": client.base_url}
    except requests.exceptions.ConnectionError as e:
        health_status["ok"] = False
        health_status["checks"]["testrail"] = {
            "status": "connection_error",
            "error": "Cannot connect to TestRail",
            "details": str(e),
        }
    except requests.exceptions.HTTPError as e:
        health_status["ok"] = False
        health_status["checks"]["testrail"] = {
            "status": "http_error",
            "error": f"TestRail API error: {e.response.status_code if e.response else 'unknown'}",
            "details": str(e),
        }
    except Exception as e:
        health_status["ok"] = False
        health_status["checks"]["testrail"] = {"status": "error", "error": "TestRail check failed", "details": str(e)}

    # Check report queue health
    try:
        from app.api.reports import job_manager

        queue_stats = job_manager.stats()
        health_status["checks"]["report_queue"] = {"status": "healthy", "stats": queue_stats}
    except ImportError:
        health_status["checks"]["report_queue"] = {"status": "unavailable", "error": "Report queue not available"}
    except Exception as e:
        health_status["ok"] = False
        health_status["checks"]["report_queue"] = {"status": "unhealthy", "error": str(e)}

    return health_status


@router.get("/health/cache")
def cache_health_check(plans_cache=Depends(get_plans_cache), runs_cache=Depends(get_runs_cache)):
    """Cache-specific health check."""
    return {
        "ok": True,
        "cache": {
            "plans": {"status": "healthy", **plans_cache.stats()},
            "runs": {"status": "healthy", **runs_cache.stats()},
        },
    }


@router.get("/health/testrail")
def testrail_health_check(client=Depends(get_testrail_client)):
    """TestRail connectivity health check."""
    try:
        # Test basic connectivity with a lightweight API call
        with client.make_session() as session:
            response = session.get(f"{client.base_url}/index.php?/api/v2/get_statuses")
            response.raise_for_status()
            statuses = response.json()

        return {
            "ok": True,
            "testrail": {
                "status": "healthy",
                "base_url": client.base_url,
                "api_version": "v2",
                "status_count": len(statuses) if isinstance(statuses, list) else 0,
            },
        }
    except requests.exceptions.ConnectionError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "ok": False,
                "testrail": {
                    "status": "connection_error",
                    "error": "Cannot connect to TestRail",
                    "base_url": client.base_url,
                    "details": str(e),
                },
            },
        )
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else 500
        raise HTTPException(
            status_code=status_code,
            detail={
                "ok": False,
                "testrail": {
                    "status": "http_error",
                    "error": f"TestRail API error: {status_code}",
                    "base_url": client.base_url,
                    "details": str(e),
                },
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "testrail": {
                    "status": "error",
                    "error": "TestRail check failed",
                    "base_url": client.base_url,
                    "details": str(e),
                },
            },
        )
