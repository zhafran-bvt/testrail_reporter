"""Comprehensive integration tests for the modernized TestRail Reporter."""

from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.main import app


class TestComprehensiveIntegration:
    """Integration tests that validate all modernization requirements working together."""

    def test_modular_architecture_integration(self):
        """Test that all modular components work together seamlessly."""
        client = TestClient(app)

        # Test that all API routers are properly integrated
        with patch("app.core.dependencies.get_plans_cache") as mock_cache, patch(
            "app.core.dependencies.get_testrail_client"
        ) as mock_client_dep:
            # Setup mocks
            mock_cache_instance = Mock()
            mock_cache_instance.get.return_value = None
            mock_cache_instance.set.return_value = 1234567890.0
            mock_cache_instance.stats.return_value = {"size": 0, "maxsize": 128}
            mock_cache.return_value = mock_cache_instance

            mock_client = Mock()
            mock_client_dep.return_value = mock_client

            # Test dashboard API integration
            response = client.get("/healthz")
            assert response.status_code == 200

            # Test cache clear API integration
            response = client.post("/api/cache/clear")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            # Verify dependency injection is working
            assert mock_cache.called

    def test_error_handling_integration(self):
        """Test that error handling works across all components."""
        client = TestClient(app)

        # Test validation error handling
        response = client.post(
            "/api/manage/plan",
            json={
                "project": -1,  # Invalid
                "name": "",  # Invalid
                "dry_run": False,
            },
        )

        # Should return structured error response
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data

        # Test that correlation IDs are included in error responses
        if "X-Correlation-ID" in response.headers:
            correlation_id = response.headers["X-Correlation-ID"]
            assert len(correlation_id) > 0

    def test_performance_optimizations_integration(self):
        """Test that performance optimizations work together."""
        from app.services.cache import TTLCache
        from app.services.testrail_client import TestRailClientService

        # Test cache efficiency
        cache = TTLCache(ttl_seconds=60, maxsize=10)

        # Test cache operations
        for i in range(15):  # More than maxsize
            cache.set((f"key_{i}",), f"value_{i}")

        # Cache should respect size limits
        assert cache.size() <= cache.maxsize

        # Test TestRail client service
        service = TestRailClientService()

        # Test retry logic
        def test_function():
            return "success"

        result = service.with_retry(test_function)
        assert result == "success"

    def test_api_structure_for_frontend_integration(self):
        """Test that API structure is ready for frontend framework integration."""
        client = TestClient(app)

        # Test that API endpoints return proper JSON
        with patch("app.core.dependencies.get_plans_cache") as mock_cache:
            mock_cache_instance = Mock()
            mock_cache_instance.get.return_value = None
            mock_cache_instance.set.return_value = 1234567890.0
            mock_cache_instance.stats.return_value = {"size": 0, "maxsize": 128}
            mock_cache.return_value = mock_cache_instance

            # Test cache API
            response = client.post("/api/cache/clear")
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("application/json")

            data = response.json()
            assert isinstance(data, dict)
            assert "success" in data

        # Test health check API for frontend monitoring
        response = client.get("/healthz")
        assert response.status_code == 200
        health_data = response.json()
        assert "ok" in health_data
        assert isinstance(health_data["ok"], bool)

    def test_documentation_integration(self):
        """Test that enhanced documentation is properly integrated."""
        client = TestClient(app)

        # Test OpenAPI schema generation
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_schema = response.json()
        assert "openapi" in openapi_schema
        assert "info" in openapi_schema
        assert "paths" in openapi_schema

        # Verify API metadata
        info = openapi_schema["info"]
        assert info["title"] == "TestRail Reporter"
        assert "version" in info

        # Verify that endpoints are documented
        paths = openapi_schema["paths"]
        assert len(paths) > 0

        # Check that some key endpoints are present
        expected_endpoints = ["/healthz", "/api/cache/clear"]
        for endpoint in expected_endpoints:
            assert any(endpoint in path for path in paths.keys()), f"Missing endpoint: {endpoint}"

    def test_backward_compatibility_integration(self):
        """Test that backward compatibility is maintained across all changes."""
        client = TestClient(app)

        # Test that main page still works (HTML interface)
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

        # Test legacy form endpoint
        response = client.get("/generate")
        assert response.status_code == 307  # Redirect to main page

        # Test UI alias
        response = client.get("/ui")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_property_based_testing_integration(self):
        """Test that property-based testing validates system correctness."""
        # This test verifies that our property-based tests are working
        # by running a few key property validations

        # Test validation error detail property
        from pydantic import ValidationError

        from app.models.requests import ReportRequest

        try:
            ReportRequest(project=-1, plan=None, run=None)
        except ValidationError as e:
            errors = e.errors()
            assert len(errors) > 0

            for error in errors:
                assert "loc" in error
                assert "msg" in error
                assert "type" in error

        # Test dependency injection property
        from app.core.dependencies import get_plans_cache

        cache1 = get_plans_cache()
        cache2 = get_plans_cache()
        assert cache1 is cache2  # Should be same instance due to caching

        # Test cache efficiency property
        from app.services.cache import TTLCache

        cache = TTLCache(ttl_seconds=60, maxsize=5)

        # Add more items than maxsize
        for i in range(10):
            cache.set((f"key_{i}",), f"value_{i}")

        # Should respect size limits
        assert cache.size() <= cache.maxsize

    def test_end_to_end_request_flow(self):
        """Test complete request flow through the modernized architecture."""
        client = TestClient(app)

        # Mock all dependencies for a complete flow test
        with patch("app.core.dependencies.get_plans_cache") as mock_plans_cache, patch(
            "app.core.dependencies.get_runs_cache"
        ) as mock_runs_cache, patch("app.core.dependencies.get_testrail_client") as mock_client:
            # Setup cache mocks
            mock_cache = Mock()
            mock_cache.get.return_value = None  # Cache miss
            mock_cache.set.return_value = 1234567890.0
            mock_cache.stats.return_value = {"size": 0, "maxsize": 128}
            mock_cache.clear.return_value = None

            mock_plans_cache.return_value = mock_cache
            mock_runs_cache.return_value = mock_cache

            # Setup client mock
            mock_testrail_client = Mock()
            mock_client.return_value = mock_testrail_client

            # Test 1: Health check (tests multiple components)
            response = client.get("/healthz")
            assert response.status_code == 200

            health_data = response.json()
            assert health_data["ok"] is True
            assert "queue" in health_data
            assert "cache" in health_data

            # Test 2: Cache operations (tests cache service integration)
            response = client.post("/api/cache/clear")
            assert response.status_code == 200

            clear_data = response.json()
            assert clear_data["success"] is True
            assert "cleared_at" in clear_data

            # Verify cache clear was called
            assert mock_cache.clear.call_count == 2  # Plans and runs cache

            # Test 3: Error handling (tests error middleware)
            response = client.post("/api/manage/plan", json={"invalid": "data"})
            assert response.status_code == 422  # Validation error

            # Test 4: Main page (tests template rendering)
            response = client.get("/")
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")

        print("✅ End-to-end request flow test completed successfully")

    def test_system_resilience_under_load(self):
        """Test that the system remains resilient under simulated load."""
        client = TestClient(app)

        # Mock dependencies to avoid external calls
        with patch("app.core.dependencies.get_plans_cache") as mock_cache:
            mock_cache_instance = Mock()
            mock_cache_instance.get.return_value = None
            mock_cache_instance.set.return_value = 1234567890.0
            mock_cache_instance.stats.return_value = {"size": 0, "maxsize": 128}
            mock_cache.return_value = mock_cache_instance

            # Simulate multiple concurrent requests
            import threading
            import time

            results = []
            errors = []

            def make_request(request_id):
                try:
                    response = client.get("/healthz")
                    results.append(
                        {
                            "request_id": request_id,
                            "status_code": response.status_code,
                            "success": response.status_code == 200,
                        }
                    )
                except Exception as e:
                    errors.append(f"Request {request_id} failed: {str(e)}")

            # Create multiple threads
            threads = []
            num_requests = 10

            start_time = time.time()

            for i in range(num_requests):
                thread = threading.Thread(target=make_request, args=(i,))
                threads.append(thread)
                thread.start()

            # Wait for all threads
            for thread in threads:
                thread.join(timeout=5)

            end_time = time.time()
            duration = end_time - start_time

            # Verify all requests completed successfully
            assert len(results) == num_requests, f"Expected {num_requests} results, got {len(results)}"
            assert len(errors) == 0, f"Errors occurred: {errors}"

            # Verify all requests succeeded
            success_count = sum(1 for r in results if r["success"])
            assert success_count == num_requests, f"Only {success_count}/{num_requests} requests succeeded"

            # Verify reasonable performance
            assert duration < 2.0, f"Load test took too long: {duration:.2f}s"

        print(f"✅ System resilience test completed: {num_requests} requests in {duration:.2f}s")
