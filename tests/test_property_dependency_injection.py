"""Property-based tests for dependency injection."""

from unittest.mock import patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.dependencies import get_plans_cache, get_runs_cache, get_testrail_client, require_write_enabled


class TestDependencyInjectionUsage:
    """Property 2: Dependency Injection Usage - For any API endpoint,
    dependencies should be injected via FastAPI's dependency system rather than using global variables."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(FastAPI())

    def test_testrail_client_dependency_injection(self, client):
        """Test that TestRail client is properly injected as dependency."""
        app = FastAPI()

        @app.get("/test-endpoint")
        def test_endpoint(client=Depends(get_testrail_client)):
            return {"client_type": type(client).__name__}

        # Mock the environment variables to avoid actual TestRail connection
        with patch.dict(
            "os.environ",
            {
                "TESTRAIL_BASE_URL": "https://test.testrail.io",
                "TESTRAIL_USER": "test@example.com",
                "TESTRAIL_API_KEY": "test-key",
            },
        ):
            test_client = TestClient(app)
            response = test_client.get("/test-endpoint")

            assert response.status_code == 200
            data = response.json()
            assert "client_type" in data
            assert data["client_type"] == "TestRailClient"

    def test_cache_dependency_injection(self, client):
        """Test that cache instances are properly injected as dependencies."""
        app = FastAPI()

        @app.get("/test-cache")
        def test_cache_endpoint(plans_cache=Depends(get_plans_cache), runs_cache=Depends(get_runs_cache)):
            return {
                "plans_cache_type": type(plans_cache).__name__,
                "runs_cache_type": type(runs_cache).__name__,
                "plans_cache_size": plans_cache.size(),
                "runs_cache_size": runs_cache.size(),
            }

        test_client = TestClient(app)
        response = test_client.get("/test-cache")

        assert response.status_code == 200
        data = response.json()
        assert data["plans_cache_type"] == "TTLCache"
        assert data["runs_cache_type"] == "TTLCache"
        assert isinstance(data["plans_cache_size"], int)
        assert isinstance(data["runs_cache_size"], int)

    def test_write_permission_dependency_injection(self, client):
        """Test that write permissions are checked via dependency injection."""
        app = FastAPI()

        @app.post("/test-write")
        def test_write_endpoint(write_enabled=Depends(require_write_enabled)):
            return {"write_enabled": write_enabled}

        test_client = TestClient(app)
        response = test_client.post("/test-write")

        assert response.status_code == 200
        data = response.json()
        assert "write_enabled" in data
        assert isinstance(data["write_enabled"], bool)

    def test_dependency_caching_behavior(self):
        """Test that dependencies are properly cached when using lru_cache."""
        # Call get_plans_cache multiple times and verify it returns the same instance
        cache1 = get_plans_cache()
        cache2 = get_plans_cache()

        # Should be the same instance due to @lru_cache
        assert cache1 is cache2, "Cached dependencies should return same instance"

        # Test with runs cache as well
        runs_cache1 = get_runs_cache()
        runs_cache2 = get_runs_cache()

        assert runs_cache1 is runs_cache2, "Cached dependencies should return same instance"

        # But different cache types should be different instances
        assert cache1 is not runs_cache1, "Different cache types should be different instances"

    def test_no_global_variables_in_dependencies(self):
        """Test that dependencies don't rely on global variables."""
        # This test ensures that our dependency functions can be called
        # without relying on global state

        # Mock environment to test TestRail client creation
        with patch.dict(
            "os.environ",
            {
                "TESTRAIL_BASE_URL": "https://test.testrail.io",
                "TESTRAIL_USER": "test@example.com",
                "TESTRAIL_API_KEY": "test-key",
            },
        ):
            # These should work without any global setup
            client = get_testrail_client()
            assert client is not None

        plans_cache = get_plans_cache()
        assert plans_cache is not None

        runs_cache = get_runs_cache()
        assert runs_cache is not None

        write_enabled = require_write_enabled()
        assert isinstance(write_enabled, bool)

    def test_dependency_isolation(self, client):
        """Test that dependencies are properly isolated and don't interfere with each other."""
        app = FastAPI()

        # Create multiple endpoints that use the same dependencies
        @app.get("/endpoint1")
        def endpoint1(cache=Depends(get_plans_cache)):
            cache.set(("test1",), "value1")
            return {"endpoint": "1", "cache_size": cache.size()}

        @app.get("/endpoint2")
        def endpoint2(cache=Depends(get_plans_cache)):
            cache.set(("test2",), "value2")
            return {"endpoint": "2", "cache_size": cache.size()}

        test_client = TestClient(app)

        # Call both endpoints
        response1 = test_client.get("/endpoint1")
        response2 = test_client.get("/endpoint2")

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Both should use the same cache instance (due to dependency injection)
        # So the second call should see the item from the first call
        data1 = response1.json()
        data2 = response2.json()

        assert data1["cache_size"] >= 1
        assert data2["cache_size"] >= 2  # Should have both items

    def test_dependency_error_handling(self, client):
        """Test that dependency injection handles errors gracefully."""
        app = FastAPI()

        @app.get("/test-error")
        def test_error_endpoint(client=Depends(get_testrail_client)):
            return {"status": "ok"}

        # Test without proper environment variables
        with patch.dict("os.environ", {}, clear=True):
            test_client = TestClient(app)
            response = test_client.get("/test-error")

            # Should get an error due to missing credentials
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "credentials" in data["detail"].lower()
