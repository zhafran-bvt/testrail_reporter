"""Response models for API endpoints."""

from typing import Any
from pydantic import BaseModel


class DashboardPlansResponse(BaseModel):
    """Response model for paginated plan lists."""
    plans: list[dict[str, Any]]
    total_count: int
    offset: int
    limit: int
    has_more: bool
    meta: dict[str, Any]


class DashboardPlanDetail(BaseModel):
    """Response model for plan details with runs."""
    plan: dict[str, Any]
    runs: list[dict[str, Any]]
    meta: dict[str, Any]


class DashboardRunsResponse(BaseModel):
    """Response model for run lists."""
    plan_id: int
    runs: list[dict[str, Any]]
    meta: dict[str, Any]


class ErrorResponse(BaseModel):
    """Standard error response model."""
    detail: str
    error_code: str | None = None
    timestamp: str | None = None
    request_id: str | None = None


class SuccessResponse(BaseModel):
    """Standard success response model."""
    success: bool = True
    message: str | None = None
    data: dict[str, Any] | None = None