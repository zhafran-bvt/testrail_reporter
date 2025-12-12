"""FastAPI middleware configuration."""

import time
import uuid
from datetime import datetime
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for centralized error handling and logging."""
    
    async def dispatch(self, request: Request, call_next):
        # Generate correlation ID for request tracking
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            
            return response
            
        except Exception as exc:
            # Log the error with context
            duration = time.time() - start_time
            print(
                f"[ERROR] {correlation_id} - {request.method} {request.url} - "
                f"{type(exc).__name__}: {str(exc)} - Duration: {duration:.3f}s",
                flush=True
            )
            
            # Return structured error response
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "An unexpected error occurred",
                    "error_code": "INTERNAL_SERVER_ERROR",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "correlation_id": correlation_id,
                },
                headers={"X-Correlation-ID": correlation_id}
            )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        correlation_id = getattr(request.state, 'correlation_id', 'unknown')
        
        # Log request/response info
        print(
            f"[REQUEST] {correlation_id} - {request.method} {request.url} - "
            f"Status: {response.status_code} - Duration: {duration:.3f}s",
            flush=True
        )
        
        return response