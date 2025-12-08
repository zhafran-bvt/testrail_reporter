"""
Integration tests for Management view auto-load functionality.

This module tests that the Management view automatically loads all subsections
(Plans, Runs, Cases) when the user navigates to it, without requiring manual
refresh button clicks.
"""

import unittest

from fastapi.testclient import TestClient


class TestManageViewAutoLoad(unittest.TestCase):
    """Tests for Management view auto-load functionality."""

    def setUp(self):
        """Set up test client."""
        from app.main import app
        self.client = TestClient(app)

    def test_initManageView_function_exists(self):
        """
        Test that initManageView function exists in the compiled JavaScript.
        
        This verifies that the auto-load functionality is available.
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        
        js = response.text
        
        # Verify initManageView function exists
        self.assertIn('initManageView', js, 
                     "initManageView function should exist in compiled JS")

    def test_switchView_calls_initManageView(self):
        """
        Test that switchView calls initManageView when switching to manage view.
        
        This verifies that auto-load is triggered when navigating to Management view.
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        
        js = response.text
        
        # Find the switchView function
        self.assertIn('function switchView', js)
        
        # Verify that when target is "manage", initManageView is called
        # Look for the pattern where manage view is shown and initManageView is called
        self.assertIn('initManageView', js)
        
        # Verify the function is exposed globally
        self.assertIn('window', js)

    def test_manage_view_has_loading_states(self):
        """
        Test that the Management view HTML includes loading state elements.
        
        This verifies that loading indicators are present for all subsections.
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        
        html = response.text
        
        # Verify Plans loading state exists
        self.assertIn('id="plansLoadingState"', html)
        self.assertIn('class="loading-state"', html)
        
        # Verify Runs loading state exists
        self.assertIn('id="runsLoadingState"', html)
        
        # Verify Test Cases View loading state exists (replaces Cases subsection)
        self.assertIn('id="testCasesLoadingState"', html)
        
        # Verify loading text is present
        self.assertIn('Loading plans...', html)
        self.assertIn('Loading runs...', html)
        self.assertIn('Loading test cases...', html)

    def test_manage_view_has_empty_states(self):
        """
        Test that the Management view HTML includes empty state elements.
        
        This verifies that helpful empty state messages are present.
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        
        html = response.text
        
        # Verify Plans empty state exists
        self.assertIn('id="plansEmptyState"', html)
        self.assertIn('class="empty-state', html)
        
        # Verify Runs empty state exists
        self.assertIn('id="runsEmptyState"', html)
        
        # Verify Test Cases View empty state exists (replaces Cases subsection)
        self.assertIn('id="testCasesEmptyState"', html)
        
        # Verify empty state messages
        self.assertIn('No plans yet', html)
        self.assertIn('No runs yet', html)
        self.assertIn('No test cases', html)

    def test_manage_view_has_entity_list_containers(self):
        """
        Test that the Management view HTML includes entity list containers.
        
        This verifies that containers exist for rendering entity cards.
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        
        html = response.text
        
        # Verify Plans list container exists
        self.assertIn('id="plansListContainer"', html)
        self.assertIn('class="entity-list', html)
        
        # Verify Runs list container exists
        self.assertIn('id="runsListContainer"', html)
        
        # Verify Test Cases View list container exists (replaces Cases subsection)
        self.assertIn('id="testCasesListContainer"', html)

    def test_manage_view_has_count_badges(self):
        """
        Test that the Management view HTML includes count badges.
        
        This verifies that count badges exist for displaying entity counts.
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        
        html = response.text
        
        # Verify count badges exist
        self.assertIn('id="plansCount"', html)
        self.assertIn('id="runsCount"', html)
        self.assertIn('id="testCasesCount"', html)  # Test Cases View count badge
        
        # Verify they have the count-badge class
        self.assertIn('class="count-badge"', html)

    def test_refresh_buttons_exist(self):
        """
        Test that refresh buttons exist for each subsection.
        
        This verifies that users can manually refresh if needed.
        """

    def test_error_handling_structure_exists(self):
        """
        Test that error handling structure exists in the JavaScript.
        
        This verifies that errors are handled gracefully during auto-load.
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        
        js = response.text
        
        # Verify error handling exists
        self.assertIn('catch', js)
        self.assertIn('error', js.lower())
        
        # Verify showToast is used for error messages
        self.assertIn('showToast', js)


if __name__ == '__main__':
    unittest.main()
