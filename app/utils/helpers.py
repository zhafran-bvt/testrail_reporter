"""Utility helper functions."""

import os
import time
from datetime import datetime, timezone
from typing import Any, Dict


def int_env(name: str, default: int) -> int:
    """Get integer environment variable with fallback."""
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def cache_meta(hit: bool, expires_at: float) -> Dict[str, Any]:
    """Generate cache metadata for API responses."""
    return {
        "cache": {
            "hit": hit,
            "expires_at": datetime.fromtimestamp(expires_at, timezone.utc).isoformat(),
            "seconds_remaining": max(0, int(expires_at - time.time())),
        }
    }


def report_worker_config() -> tuple[int, int, int]:
    """Get report worker configuration."""
    try:
        requested = max(1, int(os.getenv("REPORT_WORKERS", "1")))
    except ValueError:
        requested = 1
    try:
        configured_max = max(1, int(os.getenv("REPORT_WORKERS_MAX", "4")))
    except ValueError:
        configured_max = 4
    resolved = max(1, min(requested, configured_max))
    if resolved != requested:
        print(
            f"INFO: REPORT_WORKERS limited to {resolved} " f"(requested {requested}, max {configured_max}).",
            flush=True,
        )
    return resolved, requested, configured_max


def web_worker_count() -> int:
    """Get web worker count from environment."""
    candidates = [
        os.getenv("WEB_CONCURRENCY"),
        os.getenv("UVICORN_WORKERS"),
        os.getenv("GUNICORN_WORKERS"),
    ]
    for value in candidates:
        if value is None:
            continue
        try:
            parsed = int(str(value).strip())
            if parsed > 0:
                return parsed
        except ValueError:
            continue
    return 1
