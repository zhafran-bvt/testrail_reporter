"""Enhanced TestRail client service with retry logic and connection pooling."""

import time
from functools import wraps
from typing import Any, Callable, List, Optional

import requests
from urllib3.util.retry import Retry

from app.core.dependencies import get_testrail_client
from testrail_client import TestRailClient


class TestRailClientService:
    """Enhanced TestRail client with retry logic and connection pooling."""

    def __init__(self):
        self._client: Optional[TestRailClient] = None
        self._session: Optional[requests.Session] = None

    def get_client(self) -> TestRailClient:
        """Get TestRail client instance with connection pooling."""
        if self._client is None:
            self._client = get_testrail_client()

            # Configure session with connection pooling and retry strategy
            if hasattr(self._client, "session"):
                session = getattr(self._client, "session")
            else:
                session = requests.Session()
                # Try to add session to client, but don't fail if we can't
                try:
                    setattr(self._client, "session", session)
                except (AttributeError, TypeError):
                    # If we can't set the session on the client, store it separately
                    self._session = session

            # Configure retry strategy
            retry_strategy = Retry(
                total=3,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"],
                backoff_factor=1,
                raise_on_status=False,
            )

            # Configure HTTP adapter with connection pooling
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=10,
                pool_maxsize=20,
                max_retries=retry_strategy,
            )

            session.mount("http://", adapter)
            session.mount("https://", adapter)

            # Set reasonable timeouts
            session.timeout = (10, 30)  # (connect, read) timeout

            # Store session reference
            if self._session is None:
                self._session = session

        return self._client

    def with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with exponential backoff retry logic."""
        max_attempts = 3
        base_delay = 1.0

        for attempt in range(max_attempts):
            try:
                return func(*args, **kwargs)

            except (requests.exceptions.RequestException, ConnectionError) as e:
                if attempt == max_attempts - 1:
                    raise

                # Check if it's a retryable error
                if isinstance(e, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
                    retryable = True
                elif isinstance(e, ConnectionError):  # Built-in ConnectionError
                    retryable = True
                elif hasattr(e, "response") and e.response is not None:
                    retryable = e.response.status_code in [429, 500, 502, 503, 504]
                else:
                    retryable = False

                if not retryable:
                    raise

                # Calculate delay with exponential backoff and jitter
                delay = base_delay * (2**attempt) + (time.time() % 1)  # Add jitter
                print(f"Retrying TestRail request in {delay:.2f}s (attempt {attempt + 1}/{max_attempts})")
                time.sleep(delay)

            except Exception:
                # Non-retryable exceptions
                raise

    def batch_requests(self, requests_data: List[dict]) -> List[Any]:
        """Execute multiple requests efficiently with batching."""
        client = self.get_client()
        results = []

        # For now, execute requests sequentially with retry logic
        # In the future, this could be enhanced with actual batching if TestRail supports it
        for request_data in requests_data:
            method = request_data.get("method")
            endpoint = request_data.get("endpoint")
            params = request_data.get("params", {})

            try:
                if method == "GET":
                    result = self.with_retry(getattr(client, "get"), endpoint, params=params)
                elif method == "POST":
                    result = self.with_retry(getattr(client, "post"), endpoint, json=params)
                elif method == "PUT":
                    result = self.with_retry(getattr(client, "put"), endpoint, json=params)
                elif method == "DELETE":
                    result = self.with_retry(getattr(client, "delete"), endpoint)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                results.append(result)

            except Exception as e:
                # Log error but continue with other requests
                print(f"Batch request failed: {method} {endpoint} - {str(e)}")
                results.append(None)

        return results


# Global service instance
testrail_service = TestRailClientService()


def with_testrail_retry(func):
    """Decorator to add retry logic to TestRail API calls."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        return testrail_service.with_retry(func, *args, **kwargs)

    return wrapper
