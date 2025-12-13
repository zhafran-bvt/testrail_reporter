"""
Base test class with proper mocking setup for TestRail API tests.
"""

import unittest
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.core.dependencies import get_testrail_client, require_write_enabled
from app.main import app


class BaseTestCase(unittest.TestCase):
    """Base test case with proper TestRail client mocking."""

    def setUp(self):
        """Set up test client and mocks."""
        # Create mock TestRail client
        self.mock_client = Mock()
        
        # Set up default mock responses
        self.mock_client.add_plan.return_value = {"id": 123, "name": "Test Plan"}
        self.mock_client.add_plan_entry.return_value = {"id": 456, "name": "Test Run"}
        self.mock_client.add_run.return_value = {"id": 456, "name": "Test Run"}
        self.mock_client.add_case.return_value = {"id": 789, "title": "Test Case"}
        self.mock_client.update_plan.return_value = {"id": 123, "name": "Updated Plan"}
        self.mock_client.update_run.return_value = {"id": 456, "name": "Updated Run"}
        self.mock_client.update_case.return_value = {"id": 789, "title": "Updated Case"}
        self.mock_client.delete_plan.return_value = {}
        self.mock_client.delete_run.return_value = {}
        self.mock_client.delete_case.return_value = {}
        self.mock_client.get_plan.return_value = {
            "id": 123, 
            "name": "Test Plan",
            "entries": []
        }
        self.mock_client.get_run.return_value = {
            "id": 456, 
            "name": "Test Run",
            "plan_id": None
        }
        self.mock_client.get_case.return_value = {
            "id": 789, 
            "title": "Test Case",
            "refs": "REF-123"
        }
        self.mock_client.get_tests_for_run.return_value = []
        self.mock_client.get_plans_for_project.return_value = []
        
        # Override dependencies using FastAPI's dependency override system
        app.dependency_overrides[get_testrail_client] = lambda: self.mock_client
        app.dependency_overrides[require_write_enabled] = lambda: True
        
        # Create test client
        self.client = TestClient(app)

    def tearDown(self):
        """Clean up dependency overrides."""
        app.dependency_overrides.clear()


class BaseAPITestCase(BaseTestCase):
    """Base test case for API endpoint testing with additional setup."""
    
    def setUp(self):
        """Set up with additional API-specific mocks."""
        super().setUp()
        
        # No need to mock config - it should work with real config values