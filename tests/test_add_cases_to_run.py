"""
Tests for adding test cases to a test run.
"""

import types
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

import app.main as main_module


class TestAddCasesToRun:
    """Test suite for adding cases to run endpoints."""

    def setup_method(self):
        """Setup test client and mock."""
        self.client = TestClient(main_module.app)
        main_module._write_enabled = lambda: True

    def test_add_cases_to_run_success(self):
        """Test successfully adding cases to a run."""
        run_id = 123
        case_ids_to_add = [4, 5, 6]

        # Mock current tests in the run
        current_tests = [
            {"id": 101, "case_id": 1, "title": "Test 1"},
            {"id": 102, "case_id": 2, "title": "Test 2"},
            {"id": 103, "case_id": 3, "title": "Test 3"},
        ]

        updated_run = {"id": run_id, "name": "Test Run"}

        fake = types.SimpleNamespace()
        fake.get_tests_for_run = Mock(return_value=current_tests)
        fake.update_run = Mock(return_value=updated_run)

        main_module._make_client = lambda: fake

        # Make the request
        resp = self.client.post(f"/api/manage/run/{run_id}/add_cases", json={"case_ids": case_ids_to_add})

        # Verify response
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["run_id"] == run_id
        assert data["added_count"] == 3
        assert data["total_count"] == 6
        assert data["skipped_count"] == 0

        # Verify update_run was called with correct combined case IDs
        fake.update_run.assert_called_once()
        call_args = fake.update_run.call_args
        assert call_args[0][0] == run_id
        assert set(call_args[0][1]["case_ids"]) == {1, 2, 3, 4, 5, 6}

    def test_add_cases_with_duplicates(self):
        """Test adding cases where some already exist in the run."""
        run_id = 123
        case_ids_to_add = [2, 3, 4, 5]  # 2 and 3 already exist

        current_tests = [
            {"id": 101, "case_id": 1, "title": "Test 1"},
            {"id": 102, "case_id": 2, "title": "Test 2"},
            {"id": 103, "case_id": 3, "title": "Test 3"},
        ]

        fake = types.SimpleNamespace()
        fake.get_tests_for_run = Mock(return_value=current_tests)
        fake.update_run = Mock(return_value={"id": run_id})

        main_module._make_client = lambda: fake

        resp = self.client.post(f"/api/manage/run/{run_id}/add_cases", json={"case_ids": case_ids_to_add})

        assert resp.status_code == 200
        data = resp.json()
        assert data["added_count"] == 2  # Only 4 and 5 were added
        assert data["skipped_count"] == 2  # 2 and 3 were skipped
        assert data["total_count"] == 5  # 1, 2, 3, 4, 5

    def test_add_cases_to_empty_run(self):
        """Test adding cases to a run with no existing cases."""
        run_id = 123
        case_ids_to_add = [1, 2, 3]

        fake = types.SimpleNamespace()
        fake.get_tests_for_run = Mock(return_value=[])
        fake.update_run = Mock(return_value={"id": run_id})

        main_module._make_client = lambda: fake

        resp = self.client.post(f"/api/manage/run/{run_id}/add_cases", json={"case_ids": case_ids_to_add})

        assert resp.status_code == 200
        data = resp.json()
        assert data["added_count"] == 3
        assert data["total_count"] == 3
        assert data["skipped_count"] == 0

    def test_add_cases_invalid_run_id(self):
        """Test with invalid run ID."""
        resp = self.client.post("/api/manage/run/0/add_cases", json={"case_ids": [1, 2]})

        assert resp.status_code == 400
        assert "Run ID must be positive" in resp.json()["detail"]

    def test_add_cases_empty_case_ids(self):
        """Test with empty case_ids list."""
        resp = self.client.post("/api/manage/run/123/add_cases", json={"case_ids": []})

        assert resp.status_code == 400
        assert "case_ids cannot be empty" in resp.json()["detail"]

    def test_add_cases_invalid_case_ids(self):
        """Test with invalid case IDs."""
        resp = self.client.post("/api/manage/run/123/add_cases", json={"case_ids": [1, -5, 3]})

        assert resp.status_code == 400
        assert "All case IDs must be positive" in resp.json()["detail"]

    def test_get_available_cases_success(self):
        """Test getting available cases for a run."""
        run_id = 123

        current_tests = [
            {"id": 101, "case_id": 1, "title": "Test 1"},
            {"id": 102, "case_id": 2, "title": "Test 2"},
        ]

        all_cases = [
            {"id": 1, "title": "Case 1"},
            {"id": 2, "title": "Case 2"},
            {"id": 3, "title": "Case 3"},
            {"id": 4, "title": "Case 4"},
        ]

        fake = types.SimpleNamespace()
        fake.get_tests_for_run = Mock(return_value=current_tests)
        fake.get_cases = Mock(return_value=all_cases)

        main_module._make_client = lambda: fake

        resp = self.client.get(f"/api/manage/run/{run_id}/available_cases?project=1")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["run_id"] == run_id
        assert data["total_available"] == 2

        # Should only return cases 3 and 4 (not in run)
        available_ids = [case["id"] for case in data["available_cases"]]
        assert set(available_ids) == {3, 4}

    def test_get_available_cases_all_added(self):
        """Test getting available cases when all are already in run."""
        run_id = 123

        current_tests = [
            {"id": 101, "case_id": 1, "title": "Test 1"},
            {"id": 102, "case_id": 2, "title": "Test 2"},
        ]

        all_cases = [
            {"id": 1, "title": "Case 1"},
            {"id": 2, "title": "Case 2"},
        ]

        fake = types.SimpleNamespace()
        fake.get_tests_for_run = Mock(return_value=current_tests)
        fake.get_cases = Mock(return_value=all_cases)

        main_module._make_client = lambda: fake

        resp = self.client.get(f"/api/manage/run/{run_id}/available_cases?project=1")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_available"] == 0
        assert len(data["available_cases"]) == 0

    def test_get_available_cases_invalid_run_id(self):
        """Test with invalid run ID."""
        resp = self.client.get("/api/manage/run/0/available_cases?project=1")

        assert resp.status_code == 400
        assert "Run ID must be positive" in resp.json()["detail"]
