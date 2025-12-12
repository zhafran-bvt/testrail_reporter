"""Application configuration management."""

import os
from typing import Optional


def _int_env(name: str, default: int) -> int:
    """Get integer environment variable with fallback."""
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _default_suite_id() -> Optional[int]:
    """Get default suite ID from environment."""
    val = os.getenv("DEFAULT_SUITE_ID", "1")
    try:
        parsed = int(str(val).strip())
        return parsed
    except ValueError:
        return None


def _default_section_id() -> Optional[int]:
    """Get default section ID from environment."""
    val = os.getenv("DEFAULT_SECTION_ID", "69")
    try:
        parsed = int(str(val).strip())
        return parsed
    except ValueError:
        return None


def _default_template_id() -> Optional[int]:
    """Get default template ID from environment."""
    val = os.getenv("DEFAULT_TEMPLATE_ID", "4")
    try:
        return int(str(val).strip())
    except ValueError:
        return None


def _default_type_id() -> Optional[int]:
    """Get default type ID from environment."""
    val = os.getenv("DEFAULT_TYPE_ID", "7")
    try:
        return int(str(val).strip())
    except ValueError:
        return None


def _default_priority_id() -> Optional[int]:
    """Get default priority ID from environment."""
    val = os.getenv("DEFAULT_PRIORITY_ID", "2")
    try:
        return int(str(val).strip())
    except ValueError:
        return None


class Config:
    """Application configuration."""
    
    # TestRail Configuration
    DEFAULT_SUITE_ID = _default_suite_id()
    DEFAULT_SECTION_ID = _default_section_id()
    DEFAULT_TEMPLATE_ID = _default_template_id()
    DEFAULT_TYPE_ID = _default_type_id()
    DEFAULT_PRIORITY_ID = _default_priority_id()
    
    # Cache Configuration
    PLANS_CACHE_TTL = _int_env("PLANS_CACHE_TTL", 180)
    PLANS_CACHE_MAXSIZE = max(1, _int_env("PLANS_CACHE_MAXSIZE", 128))
    RUNS_CACHE_TTL = _int_env("RUNS_CACHE_TTL", 60)
    RUNS_CACHE_MAXSIZE = max(1, _int_env("RUNS_CACHE_MAXSIZE", 128))
    
    # Dashboard Configuration
    DASHBOARD_PLANS_CACHE_TTL = _int_env("DASHBOARD_PLANS_CACHE_TTL", 300)
    DASHBOARD_PLAN_DETAIL_CACHE_TTL = _int_env("DASHBOARD_PLAN_DETAIL_CACHE_TTL", 180)
    DASHBOARD_STATS_CACHE_TTL = _int_env("DASHBOARD_STATS_CACHE_TTL", 120)
    DASHBOARD_RUN_STATS_CACHE_TTL = _int_env("DASHBOARD_RUN_STATS_CACHE_TTL", 120)
    DASHBOARD_DEFAULT_PAGE_SIZE = _int_env("DASHBOARD_DEFAULT_PAGE_SIZE", 25)
    DASHBOARD_MAX_PAGE_SIZE = _int_env("DASHBOARD_MAX_PAGE_SIZE", 25)
    
    # Visual Thresholds
    DASHBOARD_PASS_RATE_HIGH = _int_env("DASHBOARD_PASS_RATE_HIGH", 80)
    DASHBOARD_PASS_RATE_MEDIUM = _int_env("DASHBOARD_PASS_RATE_MEDIUM", 50)
    DASHBOARD_CRITICAL_FAIL_THRESHOLD = _int_env("DASHBOARD_CRITICAL_FAIL_THRESHOLD", 20)
    DASHBOARD_CRITICAL_BLOCK_THRESHOLD = _int_env("DASHBOARD_CRITICAL_BLOCK_THRESHOLD", 10)
    
    # Report Job Configuration
    REPORT_WORKERS = max(1, _int_env("REPORT_WORKERS", 1))
    REPORT_WORKERS_MAX = max(1, _int_env("REPORT_WORKERS_MAX", 4))
    REPORT_JOB_HISTORY = max(10, _int_env("REPORT_JOB_HISTORY", 60))
    
    # File Upload Configuration
    MAX_FILE_SIZE_MB = 25
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
    ALLOWED_FILE_TYPES = {
        "image/png": "PNG",
        "image/jpeg": "JPG", 
        "image/gif": "GIF",
        "video/mp4": "MP4",
        "video/mov": "MOV",
        "video/quicktime": "MOV",  # Alternative MIME type for MOV files
        "video/webm": "WebM",
        "application/pdf": "PDF",
    }
    
    # Keepalive Configuration
    KEEPALIVE_INTERVAL = max(60, _int_env("KEEPALIVE_INTERVAL", 240))
    MEM_LOG_INTERVAL = max(30, _int_env("MEM_LOG_INTERVAL", 60))


# Global configuration instance
config = Config()