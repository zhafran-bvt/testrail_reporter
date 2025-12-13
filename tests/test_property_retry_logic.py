"""Property-based tests for retry logic implementation."""

import time
from unittest.mock import Mock, patch

import pytest
import requests
from hypothesis import given, settings
from hypothesis import strategies as st

from app.services.testrail_client import TestRailClientService, with_testrail_retry


class TestRetryLogicImplementation:
    """Property 5: Retry Logic Implementation - For any transient TestRail API failure,
    the system should implement exponential backoff retry logic with appropriate limits."""

    def test_retry_logic_handles_transient_failures(self):
        """Test that retry logic properly handles transient failures with exponential backoff."""
        service = TestRailClientService()

        # Mock function that fails twice then succeeds
        call_count = 0

        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise requests.exceptions.Timeout("Simulated timeout")
            return "success"

        # Should succeed after retries
        result = service.with_retry(failing_function)
        assert result == "success"
        assert call_count == 3  # Initial call + 2 retries

    def test_retry_logic_respects_max_attempts(self):
        """Test that retry logic respects maximum attempt limits."""
        service = TestRailClientService()

        # Mock function that always fails
        call_count = 0

        def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise requests.exceptions.ConnectionError("Simulated connection error")

        # Should fail after max attempts
        with pytest.raises(requests.exceptions.ConnectionError):
            service.with_retry(always_failing_function)

        assert call_count == 3  # Should try 3 times total

    @given(failure_count=st.integers(min_value=1, max_value=2))
    @settings(deadline=None)  # Disable deadline for timing tests
    def test_retry_logic_exponential_backoff_timing(self, failure_count):
        """Test that retry logic implements proper exponential backoff timing."""
        service = TestRailClientService()

        call_times = []
        call_count = 0
        sleep_calls = []

        def timing_test_function():
            nonlocal call_count
            call_times.append(time.time())
            call_count += 1

            if call_count <= failure_count:
                raise requests.exceptions.Timeout("Simulated timeout")
            return "success"

        # Mock time.sleep to capture delay values without actually sleeping
        with patch("time.sleep") as mock_sleep:

            def capture_sleep(delay):
                sleep_calls.append(delay)

            mock_sleep.side_effect = capture_sleep

            result = service.with_retry(timing_test_function)

        assert result == "success"
        assert len(call_times) == failure_count + 1

        # Check that delays increase (exponential backoff)
        if len(sleep_calls) >= 2:  # At least 2 retries to check delays
            delay1 = sleep_calls[0]
            delay2 = sleep_calls[1]

            # Second delay should be longer than first (exponential backoff)
            assert delay2 > delay1, "Second retry delay should be longer (exponential backoff)"

    def test_retry_logic_identifies_retryable_errors(self):
        """Test that retry logic correctly identifies which errors are retryable."""
        service = TestRailClientService()

        # Test retryable errors
        retryable_errors = [
            requests.exceptions.Timeout("Timeout"),
            requests.exceptions.ConnectionError("Connection failed"),
            requests.exceptions.HTTPError(response=Mock(status_code=429)),  # Rate limit
            requests.exceptions.HTTPError(response=Mock(status_code=500)),  # Server error
            requests.exceptions.HTTPError(response=Mock(status_code=502)),  # Bad gateway
            requests.exceptions.HTTPError(response=Mock(status_code=503)),  # Service unavailable
            requests.exceptions.HTTPError(response=Mock(status_code=504)),  # Gateway timeout
        ]

        for error in retryable_errors:
            call_count = 0

            def retryable_failing_function():
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise error
                return "success"

            # Should retry and eventually succeed
            result = service.with_retry(retryable_failing_function)
            assert result == "success", f"Should retry for error: {type(error).__name__}"
            assert call_count == 3, f"Should make 3 attempts for error: {type(error).__name__}"

    def test_retry_logic_skips_non_retryable_errors(self):
        """Test that retry logic does not retry non-retryable errors."""
        service = TestRailClientService()

        # Test non-retryable errors
        non_retryable_errors = [
            requests.exceptions.HTTPError(response=Mock(status_code=400)),  # Bad request
            requests.exceptions.HTTPError(response=Mock(status_code=401)),  # Unauthorized
            requests.exceptions.HTTPError(response=Mock(status_code=403)),  # Forbidden
            requests.exceptions.HTTPError(response=Mock(status_code=404)),  # Not found
            ValueError("Invalid input"),  # Non-HTTP error
        ]

        for error in non_retryable_errors:
            call_count = 0

            def non_retryable_failing_function():
                nonlocal call_count
                call_count += 1
                raise error

            # Should not retry and fail immediately
            with pytest.raises(type(error)):
                service.with_retry(non_retryable_failing_function)

            assert call_count == 1, f"Should not retry for error: {type(error).__name__}"

    def test_retry_decorator_functionality(self):
        """Test that the retry decorator works correctly."""
        call_count = 0

        @with_testrail_retry
        def decorated_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                raise requests.exceptions.Timeout("Simulated timeout")
            return "decorated_success"

        result = decorated_function()
        assert result == "decorated_success"
        assert call_count == 2  # Initial call + 1 retry

    @given(
        num_requests=st.integers(min_value=1, max_value=3)  # Reduce to avoid long test times
    )
    @settings(deadline=None)  # Disable deadline
    def test_batch_requests_with_retry_logic(self, num_requests):
        """Test that batch requests properly handle individual failures with retry logic."""
        service = TestRailClientService()

        # Mock client for batch operations
        mock_client = Mock()
        service._client = mock_client

        # Create test requests
        requests_data = []
        for i in range(num_requests):
            requests_data.append({"method": "GET", "endpoint": f"/test_endpoint_{i}", "params": {"id": i}})

        # Mock the client methods to simulate some failures
        call_counts = {}

        def mock_get(endpoint, params=None):
            if endpoint not in call_counts:
                call_counts[endpoint] = 0
            call_counts[endpoint] += 1

            # Simulate failure on first call for some endpoints
            if call_counts[endpoint] == 1 and "endpoint_1" in endpoint:
                raise requests.exceptions.Timeout("Simulated timeout")

            return {"endpoint": endpoint, "params": params}

        mock_client.get = mock_get

        # Mock time.sleep to avoid actual delays
        with patch("time.sleep"):
            # Execute batch requests
            results = service.batch_requests(requests_data)

        # Verify results
        assert len(results) == num_requests

        # Check that failed requests were retried and succeeded
        for i, result in enumerate(results):
            if result is not None:  # Successful requests
                assert result["endpoint"] == f"/test_endpoint_{i}"
                assert result["params"] == {"id": i}

    def test_connection_pooling_configuration(self):
        """Test that connection pooling is properly configured."""
        service = TestRailClientService()

        # Mock the TestRail client creation
        with patch("app.services.testrail_client.get_testrail_client") as mock_get_client:
            mock_client = Mock()
            mock_session = Mock()
            mock_client.session = mock_session
            mock_get_client.return_value = mock_client

            # Get client (should configure session)
            client = service.get_client()

            # Verify session configuration was attempted
            assert client == mock_client

            # Verify mount calls were made (for HTTP adapters)
            assert mock_session.mount.call_count >= 2  # Should mount http:// and https://

    def test_retry_with_jitter_reduces_thundering_herd(self):
        """Test that retry logic includes jitter to reduce thundering herd problems."""
        service = TestRailClientService()

        # Collect retry timings from multiple "concurrent" operations
        retry_delays = []

        for _ in range(5):  # Simulate 5 concurrent operations
            call_times = []
            call_count = 0

            def jitter_test_function():
                nonlocal call_count
                call_times.append(time.time())
                call_count += 1

                if call_count == 1:
                    raise requests.exceptions.Timeout("Simulated timeout")
                return "success"

            service.with_retry(jitter_test_function)

            if len(call_times) >= 2:
                delay = call_times[1] - call_times[0]
                retry_delays.append(delay)

        # Verify that delays are not identical (indicating jitter is present)
        if len(retry_delays) >= 2:
            unique_delays = set(round(delay, 2) for delay in retry_delays)
            # Should have some variation due to jitter (allow for some identical values)
            assert len(unique_delays) >= len(retry_delays) * 0.6, "Retry delays should include jitter for variation"
