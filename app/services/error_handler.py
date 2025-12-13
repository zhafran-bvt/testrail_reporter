"""Comprehensive error handling service."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError


class ErrorHandler:
    """Centralized error handling service."""

    @staticmethod
    def handle_exception(exc: Exception, request: Request) -> JSONResponse:
        """Handle any exception and return structured response."""
        correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Log the error with full context
        ErrorHandler.log_error(
            exc,
            {
                "correlation_id": correlation_id,
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host if request.client else "unknown",
            },
        )

        if isinstance(exc, HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "detail": exc.detail,
                    "error_code": f"HTTP_{exc.status_code}",
                    "timestamp": timestamp,
                    "correlation_id": correlation_id,
                },
                headers={"X-Correlation-ID": correlation_id},
            )

        elif isinstance(exc, ValidationError):
            return JSONResponse(
                status_code=400,
                content=ErrorHandler.format_validation_error(exc, correlation_id, timestamp),
                headers={"X-Correlation-ID": correlation_id},
            )

        elif isinstance(exc, requests.exceptions.RequestException):
            return JSONResponse(
                status_code=502,
                content={
                    "detail": f"External API error: {str(exc)}",
                    "error_code": "EXTERNAL_API_ERROR",
                    "timestamp": timestamp,
                    "correlation_id": correlation_id,
                },
                headers={"X-Correlation-ID": correlation_id},
            )

        else:
            # Generic server error
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "An unexpected error occurred",
                    "error_code": "INTERNAL_SERVER_ERROR",
                    "timestamp": timestamp,
                    "correlation_id": correlation_id,
                },
                headers={"X-Correlation-ID": correlation_id},
            )

    @staticmethod
    def log_error(exc: Exception, context: Dict[str, Any]) -> str:
        """Log error with context and return correlation ID."""
        correlation_id = context.get("correlation_id")
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())

        print(f"[ERROR] {correlation_id} - {type(exc).__name__}: {str(exc)} - " f"Context: {context}", flush=True)

        return correlation_id

    @staticmethod
    def format_validation_error(exc: ValidationError, correlation_id: str, timestamp: str) -> Dict[str, Any]:
        """Format Pydantic validation error into structured response."""
        field_errors: Dict[str, List[str]] = {}

        for error in exc.errors():
            field_path = ".".join(str(loc) for loc in error["loc"])
            message = error["msg"]

            if field_path not in field_errors:
                field_errors[field_path] = []
            field_errors[field_path].append(message)

        return {
            "detail": "Validation error",
            "error_code": "VALIDATION_ERROR",
            "timestamp": timestamp,
            "correlation_id": correlation_id,
            "field_errors": field_errors,
        }

    @staticmethod
    def create_http_exception(
        status_code: int, detail: str, error_code: Optional[str] = None, correlation_id: Optional[str] = None
    ) -> HTTPException:
        """Create HTTPException with structured detail."""
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        if not error_code:
            error_code = f"HTTP_{status_code}"

        structured_detail = {
            "detail": detail,
            "error_code": error_code,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "correlation_id": correlation_id,
        }

        return HTTPException(status_code=status_code, detail=structured_detail)
