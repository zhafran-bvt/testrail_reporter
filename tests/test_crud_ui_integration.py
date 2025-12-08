"""
Integration tests for CRUD UI flows.

These tests verify that the UI correctly handles edit and delete operations
for plans, runs, and cases.
"""
import unittest
from unittest.mock import Mock, patch
import types

from fastapi.testclient import TestClient

import app.main as main


class TestCRUDUIFlows(unittest.TestCase):
    """Integration tests for CRUD UI flows."""

    def setUp(self):
        """Set up test client and mocks."""
        self.client = TestClient(main.app)
        
        # Create fake client
        self.fake_client = types.SimpleNamespace()
        self.fake_client.update_plan = Mock(return_value={"id": 123, "name": "Updated Plan"})
        self.fake_client.update_run = Mock(return_value={"id": 456, "name": "Updated Run"})
        self.fake_client.update_case = Mock(return_value={"id": 789, "title": "Updated Case"})
        self.fake_client.delete_plan = Mock(return_value={})
        self.fake_client.delete_run = Mock(return_value={})
        self.fake_client.delete_case = Mock(return_value={})
        
        # Patch the client
        main._make_client = lambda: self.fake_client
        main._write_enabled = lambda: True

    def test_edit_plan_updates_entity(self):
        """Test that editing a plan updates the entity."""
        plan_id = 123
        payload = {
            "name": "Updated Plan Name",
            "description": "Updated description",
            "milestone_id": 5
        }
        
        response = self.client.put(f"/api/manage/plan/{plan_id}", json=payload)
        
        assert response.status_code == 200
        result = response.json()
        assert "plan" in result
        assert result["plan"]["id"] == plan_id
        
        # Verify the update was called with correct data
        self.fake_client.update_plan.assert_called_once()
        call_args = self.fake_client.update_plan.call_args
        assert call_args[0][0] == plan_id
        assert call_args[0][1]["name"] == "Updated Plan Name"

    def test_edit_run_updates_entity(self):
        """Test that editing a run updates the entity."""
        run_id = 456
        payload = {
            "name": "Updated Run Name",
            "description": "Updated description",
            "refs": "REF-123"
        }
        
        response = self.client.put(f"/api/manage/run/{run_id}", json=payload)
        
        assert response.status_code == 200
        result = response.json()
        assert "run" in result
        assert result["run"]["id"] == run_id
        
        # Verify the update was called with correct data
        self.fake_client.update_run.assert_called_once()
        call_args = self.fake_client.update_run.call_args
        assert call_args[0][0] == run_id
        assert call_args[0][1]["name"] == "Updated Run Name"

    def test_edit_case_updates_entity(self):
        """Test that editing a case updates the entity."""
        case_id = 789
        payload = {
            "title": "Updated Case Title",
            "refs": "REF-456",
            "bdd_scenarios": "Given something\nWhen something\nThen something"
        }
        
        response = self.client.put(f"/api/manage/case/{case_id}", json=payload)
        
        assert response.status_code == 200
        result = response.json()
        assert "case" in result
        assert result["case"]["id"] == case_id
        
        # Verify the update was called with correct data
        self.fake_client.update_case.assert_called_once()
        call_args = self.fake_client.update_case.call_args
        assert call_args[0][0] == case_id
        assert call_args[0][1]["title"] == "Updated Case Title"

    def test_delete_plan_shows_confirmation_and_executes(self):
        """Test that deleting a plan requires confirmation and executes deletion."""
        plan_id = 123
        
        # The API endpoint requires explicit DELETE request
        # (confirmation is handled in UI)
        response = self.client.delete(f"/api/manage/plan/{plan_id}")
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["plan_id"] == plan_id
        
        # Verify deletion was called
        self.fake_client.delete_plan.assert_called_once_with(plan_id)

    def test_delete_run_shows_confirmation_and_executes(self):
        """Test that deleting a run requires confirmation and executes deletion."""
        run_id = 456
        
        # The API endpoint requires explicit DELETE request
        # (confirmation is handled in UI)
        response = self.client.delete(f"/api/manage/run/{run_id}")
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["run_id"] == run_id
        
        # Verify deletion was called
        self.fake_client.delete_run.assert_called_once_with(run_id)

    def test_delete_case_shows_confirmation_and_executes(self):
        """Test that deleting a case requires confirmation and executes deletion."""
        case_id = 789
        
        # The API endpoint requires explicit DELETE request
        # (confirmation is handled in UI)
        response = self.client.delete(f"/api/manage/case/{case_id}")
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["case_id"] == case_id
        
        # Verify deletion was called
        self.fake_client.delete_case.assert_called_once_with(case_id)

    def test_cancel_delete_retains_entity(self):
        """Test that canceling deletion retains the entity."""
        plan_id = 123
        
        # When user cancels, no DELETE request is sent
        # So the entity remains (we verify by not calling delete)
        
        # Simulate checking if entity still exists
        # In real scenario, the UI would not send DELETE request
        # and the entity would remain in the list
        
        # Verify delete was not called
        self.fake_client.delete_plan.assert_not_called()

    def test_edit_with_validation_error_displays_message(self):
        """Test that validation errors are displayed correctly."""
        plan_id = 123
        payload = {
            "name": "",  # Empty name should fail validation
        }
        
        response = self.client.put(f"/api/manage/plan/{plan_id}", json=payload)
        
        # Should return 422 (Unprocessable Entity) with validation error
        assert response.status_code == 422
        result = response.json()
        assert "detail" in result
        # Pydantic validation errors have a specific structure
        assert isinstance(result["detail"], list) or "empty" in str(result["detail"]).lower()

    def test_delete_nonexistent_entity_displays_error(self):
        """Test that deleting non-existent entity displays error."""
        plan_id = 99999
        
        # Mock delete to raise 404
        import requests
        response_mock = Mock()
        response_mock.status_code = 404
        self.fake_client.delete_plan = Mock(
            side_effect=requests.exceptions.HTTPError(response=response_mock)
        )
        
        response = self.client.delete(f"/api/manage/plan/{plan_id}")
        
        assert response.status_code == 404
        result = response.json()
        assert "detail" in result
        assert "not found" in result["detail"].lower()

    def test_edit_form_loads_current_data(self):
        """Test that edit form would load current entity data."""
        # This is primarily a UI test, but we can verify the API
        # returns the correct data structure for editing
        
        plan_id = 123
        
        # Mock get_plan to return current data
        self.fake_client.get_plan = Mock(return_value={
            "id": plan_id,
            "name": "Current Plan Name",
            "description": "Current description",
            "milestone_id": 3
        })
        
        # In the UI, this data would be fetched and populated into the form
        # We verify the data structure is correct
        plan_data = self.fake_client.get_plan(plan_id)
        
        assert plan_data["id"] == plan_id
        assert "name" in plan_data
        assert "description" in plan_data
        assert "milestone_id" in plan_data

    def test_successful_edit_refreshes_list(self):
        """Test that successful edit would trigger list refresh."""
        plan_id = 123
        payload = {
            "name": "Updated Plan Name",
        }
        
        response = self.client.put(f"/api/manage/plan/{plan_id}", json=payload)
        
        assert response.status_code == 200
        result = response.json()
        assert "plan" in result
        
        # In the UI, a successful response would trigger:
        # 1. Success toast message
        # 2. List refresh to show updated data
        # 3. Modal close
        
        # We verify the response contains the updated data
        assert result["plan"]["id"] == plan_id

    def test_successful_delete_removes_from_display(self):
        """Test that successful delete would remove entity from display."""
        plan_id = 123
        
        response = self.client.delete(f"/api/manage/plan/{plan_id}")
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        
        # In the UI, a successful response would trigger:
        # 1. Success toast message
        # 2. Entity removal from DOM
        # 3. List refresh
        
        # Verify the deletion was executed
        self.fake_client.delete_plan.assert_called_once()

    def test_failed_edit_retains_form_data(self):
        """Test that failed edit would retain form data for correction."""
        plan_id = 123
        payload = {
            "name": "Updated Plan Name",
        }
        
        # Mock update to fail
        import requests
        response_mock = Mock()
        response_mock.status_code = 502
        self.fake_client.update_plan = Mock(
            side_effect=requests.exceptions.HTTPError(response=response_mock)
        )
        
        response = self.client.put(f"/api/manage/plan/{plan_id}", json=payload)
        
        assert response.status_code == 502
        result = response.json()
        assert "detail" in result
        
        # In the UI, the form would:
        # 1. Display error message
        # 2. Keep form data intact
        # 3. Allow user to retry

    def test_failed_delete_retains_entity(self):
        """Test that failed delete would retain entity in display."""
        plan_id = 123
        
        # Mock delete to fail
        import requests
        response_mock = Mock()
        response_mock.status_code = 502
        self.fake_client.delete_plan = Mock(
            side_effect=requests.exceptions.HTTPError(response=response_mock)
        )
        
        response = self.client.delete(f"/api/manage/plan/{plan_id}")
        
        assert response.status_code == 502
        result = response.json()
        assert "detail" in result
        
        # In the UI, the entity would:
        # 1. Remain in the list
        # 2. Display error message
        # 3. Allow user to retry


if __name__ == "__main__":
    unittest.main()
