"""FastAPI dependency injection setup."""

from functools import lru_cache
from fastapi import HTTPException

from testrail_client import (
    DEFAULT_HTTP_BACKOFF,
    DEFAULT_HTTP_RETRIES,
    DEFAULT_HTTP_TIMEOUT,
    TestRailClient,
)
from testrail_daily_report import env_or_die
from app.services.cache import TTLCache
from app.core.config import config


# Cache instances
@lru_cache()
def get_plans_cache() -> TTLCache:
    """Get plans cache instance."""
    return TTLCache(
        ttl_seconds=config.PLANS_CACHE_TTL,
        maxsize=config.PLANS_CACHE_MAXSIZE
    )


@lru_cache()
def get_runs_cache() -> TTLCache:
    """Get runs cache instance."""
    return TTLCache(
        ttl_seconds=config.RUNS_CACHE_TTL,
        maxsize=config.RUNS_CACHE_MAXSIZE
    )


@lru_cache()
def get_dashboard_plans_cache() -> TTLCache:
    """Get dashboard plans cache instance."""
    return TTLCache(
        ttl_seconds=config.DASHBOARD_PLANS_CACHE_TTL,
        maxsize=128
    )


@lru_cache()
def get_dashboard_plan_detail_cache() -> TTLCache:
    """Get dashboard plan detail cache instance."""
    return TTLCache(
        ttl_seconds=config.DASHBOARD_PLAN_DETAIL_CACHE_TTL,
        maxsize=64
    )


@lru_cache()
def get_dashboard_stats_cache() -> TTLCache:
    """Get dashboard stats cache instance."""
    return TTLCache(
        ttl_seconds=config.DASHBOARD_STATS_CACHE_TTL,
        maxsize=128
    )


@lru_cache()
def get_dashboard_run_stats_cache() -> TTLCache:
    """Get dashboard run stats cache instance."""
    return TTLCache(
        ttl_seconds=config.DASHBOARD_RUN_STATS_CACHE_TTL,
        maxsize=256
    )


def get_testrail_client() -> TestRailClient:
    """Get TestRail client instance."""
    try:
        base_url = env_or_die("TESTRAIL_BASE_URL").rstrip("/")
        user = env_or_die("TESTRAIL_USER")
        api_key = env_or_die("TESTRAIL_API_KEY")
    except SystemExit:
        raise HTTPException(status_code=500, detail="Server missing TestRail credentials")
    
    return TestRailClient(
        base_url=base_url,
        auth=(user, api_key),
        timeout=DEFAULT_HTTP_TIMEOUT,
        max_attempts=DEFAULT_HTTP_RETRIES,
        backoff=DEFAULT_HTTP_BACKOFF,
    )


def require_write_enabled():
    """Dependency to check if write operations are enabled."""
    # For now, always allow writes. This can be extended later
    # to check environment variables or user permissions
    return True