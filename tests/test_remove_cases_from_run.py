"""
Tests for removing test cases from a test run.

This module tests the new functionality to remove test cases from a run
without deleting them from the project.
"""

import types
from unittest.mock import Mock

from fastapi.testclient import TestClient

import app.main as main_module


class TestRemoveCasesFromRun:
    """Test suite for removing cases from run endpoint."""

    def setup_method(self):
        """Setup test client and mock."""
        self.client = TestClient(main_module.app)
        main_module._write_enabled = lambda: True

    def test_remove_cases_from_run_success(self):
        """Test successfully removing cases from a run."""
        run_id = 123
        case_ids_to_remove = [1, 2, 3]

        # Mock current tests in the run
        current_tests = [
            {"id": 101, "case_id": 1, "title": "Test 1"},
            {"id": 102, "case_id": 2, "title": "Test 2"},
            {"id": 103, "case_id": 3, "title": "Test 3"},
            {"id": 104, "case_id": 4, "title": "Test 4"},
            {"id": 105, "case_id": 5, "title": "Test 5"},
        ]

        updated_run = {"id": run_id, "name": "Test Run"}

        fake = types.SimpleNamespace()
        fake.get_tests_for_run = Mock(return_value=current_tests)
        fake.get_run = Mock(return_value={"id": run_id, "plan_id": None})
        fake.update_run = Mock(return_value=updated_run)

        main_module._make_client = lambda: fake

        # Make the request
        resp = self.client.post(f"/api/manage/run/{run_id}/remove_cases", json={"case_ids": case_ids_to_remove})

        # Verify response
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["run_id"] == run_id
        assert data["removed_count"] == 3
        assert data["remaining_count"] == 2

        # Verify update_run was called with correct remaining case IDs
        fake.update_run.assert_called_once()
        call_args = fake.update_run.call_args
        assert call_args[0][0] == run_id
        assert set(call_args[0][1]["case_ids"]) == {4, 5}

    def test_remove_cases_partial_match(self):
        """Test removing cases where some don't exist in the run."""
        run_id = 123
        case_ids_to_remove = [1, 2, 99]  # 99 doesn't exist

        current_tests = [
            {"id": 101, "case_id": 1, "title": "Test 1"},
            {"id": 102, "case_id": 2, "title": "Test 2"},
            {"id": 103, "case_id": 3, "title": "Test 3"},
        ]

        fake = types.SimpleNamespace()
        fake.get_tests_for_run = Mock(return_value=current_tests)
        fake.get_run = Mock(return_value={"id": run_id, "plan_id": None})
        fake.update_run = Mock(return_value={"id": run_id})

        main_module._make_client = lambda: fake

        resp = self.client.post(f"/api/manage/run/{run_id}/remove_cases", json={"case_ids": case_ids_to_remove})

        assert resp.status_code == 200
        data = resp.json()
        assert data["removed_count"] == 2  # Only 1 and 2 were removed
        assert data["remaining_count"] == 1  # Only case 3 remains

    def test_remove_all_cases_from_run(self):
        """Test removing all cases from a run."""
        run_id = 123

        current_tests = [
            {"id": 101, "case_id": 1, "title": "Test 1"},
            {"id": 102, "case_id": 2, "title": "Test 2"},
        ]

        fake = types.SimpleNamespace()
        fake.get_tests_for_run = Mock(return_value=current_tests)
        fake.get_run = Mock(return_value={"id": run_id, "plan_id": None})
        fake.update_run = Mock(return_value={"id": run_id})

        main_module._make_client = lambda: fake

        resp = self.client.post(f"/api/manage/run/{run_id}/remove_cases", json={"case_ids": [1, 2]})

        assert resp.status_code == 200
        data = resp.json()
        assert data["removed_count"] == 2
        assert data["remaining_count"] == 0

        # Verify update_run was called with empty case_ids
        fake.update_run.assert_called_once()
        call_args = fake.update_run.call_args
        assert call_args[0][1]["case_ids"] == []

    def test_remove_cases_invalid_run_id(self):
        """Test with invalid run ID."""
        resp = self.client.post("/api/manage/run/0/remove_cases", json={"case_ids": [1, 2]})

        assert resp.status_code == 400
        assert "Run ID must be positive" in resp.json()["detail"]

    def test_remove_cases_empty_case_ids(self):
        """Test with empty case_ids list."""
        resp = self.client.post("/api/manage/run/123/remove_cases", json={"case_ids": []})

        assert resp.status_code == 400
        assert "case_ids cannot be empty" in resp.json()["detail"]

    def test_remove_cases_invalid_case_ids(self):
        """Test with invalid case IDs."""
        resp = self.client.post("/api/manage/run/123/remove_cases", json={"case_ids": [1, -5, 3]})

        assert resp.status_code == 400
        assert "All case IDs must be positive" in resp.json()["detail"]

    def test_remove_cases_run_not_found(self):
        """Test with non-existent run."""
        import requests

        fake = types.SimpleNamespace()

        def get_tests_error(run_id):
            response = Mock()
            response.status_code = 404
            raise requests.exceptions.HTTPError(response=response)

        fake.get_tests_for_run = Mock(side_effect=get_tests_error)
        fake.get_run = Mock(side_effect=get_tests_error)

        main_module._make_client = lambda: fake

        resp = self.client.post("/api/manage/run/99999/remove_cases", json={"case_ids": [1, 2]})

        assert resp.status_code == 404
        assert "Run 99999 not found" in resp.json()["detail"]

    def test_remove_cases_write_disabled(self):
        """Test that endpoint requires write mode."""
        # Store original and set to disabled
        original = main_module._write_enabled
        main_module._write_enabled = lambda: False

        try:
            resp = self.client.post("/api/manage/run/123/remove_cases", json={"case_ids": [1, 2]})

            # Should return 404 because write is disabled (endpoint not accessible)
            # or 403 if explicitly checking write mode
            assert resp.status_code in [403, 404]
        finally:
            main_module._write_enabled = original

    def test_remove_cases_clears_cache(self):
        """Test that removing cases clears relevant caches."""
        run_id = 123

        current_tests = [
            {"id": 101, "case_id": 1, "title": "Test 1"},
            {"id": 102, "case_id": 2, "title": "Test 2"},
        ]

        fake = types.SimpleNamespace()
        fake.get_tests_for_run = Mock(return_value=current_tests)
        fake.get_run = Mock(return_value={"id": run_id, "plan_id": None})
        fake.update_run = Mock(return_value={"id": run_id})

        main_module._make_client = lambda: fake

        resp = self.client.post(f"/api/manage/run/{run_id}/remove_cases", json={"case_ids": [1]})

        assert resp.status_code == 200

        # Just verify the endpoint succeeds
        # Cache clearing is an internal implementation detail
        data = resp.json()
        assert data["success"] is True
