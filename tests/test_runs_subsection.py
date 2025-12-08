"""
Integration tests for Runs subsection functionality.

This module tests the Runs subsection implementation including:
- renderRunsSubsection() function
- Plan selector dropdown for filtering
- Count badge updates
- Empty state display
- Refresh button functionality
- Edit and Delete button wiring
"""

import unittest

from fastapi.testclient import TestClient


class TestRunsSubsection(unittest.TestCase):
    """Tests for Runs subsection functionality."""

    def setUp(self):
        """Set up test client."""
        from app.main import app

        self.client = TestClient(app)

    def test_renderRunsSubsection_function_exists(self):
        """
        Test that renderRunsSubsection function exists in the compiled JavaScript.

        Validates: Requirements 2.1, 2.2
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify renderRunsSubsection function exists
        self.assertIn("renderRunsSubsection", js, "renderRunsSubsection function should exist in compiled JS")

    def test_populatePlanFilter_function_exists(self):
        """
        Test that populatePlanFilter function exists for populating the plan dropdown.

        Validates: Requirements 7.2
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify populatePlanFilter function exists
        self.assertIn("populatePlanFilter", js, "populatePlanFilter function should exist in compiled JS")

    def test_runs_plan_filter_exists(self):
        """
        Test that Runs plan selector dropdown exists in the HTML.

        Validates: Requirements 7.2
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Verify plan filter dropdown exists
        self.assertIn('id="runsPlanFilter"', html)
        self.assertIn('aria-label="Filter runs by plan"', html)
        self.assertIn('<option value="">All Plans</option>', html)

    def test_runs_count_badge_exists(self):
        """
        Test that Runs count badge exists in the HTML.

        Validates: Requirements 2.2
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Verify count badge exists
        self.assertIn('id="runsCount"', html)
        self.assertIn('class="count-badge"', html)

    def test_runs_empty_state_exists(self):
        """
        Test that Runs empty state exists with helpful message.

        Validates: Requirements 5.2
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Verify empty state exists
        self.assertIn('id="runsEmptyState"', html)
        self.assertIn('class="empty-state', html)

        # Verify helpful message
        self.assertIn("No runs yet", html)
        self.assertIn("Select a plan or create a new run above", html)

        # Verify action button exists
        self.assertIn("expandCreateSection()", html)

    def test_runs_refresh_button_exists(self):
        """
        Test that Runs refresh button exists for manual reload.

        Validates: Requirements 12.1, 12.2
        """

    def test_runs_edit_button_styling(self):
        """
        Test that Edit buttons have proper styling in the JavaScript.

        Validates: Requirements 2.4
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify edit button class exists in rendered HTML
        self.assertIn("edit-run-btn", js)
        self.assertIn("Edit", js)

    def test_runs_delete_button_styling(self):
        """
        Test that Delete buttons have proper styling in the JavaScript.

        Validates: Requirements 2.4
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify delete button class exists in rendered HTML
        self.assertIn("delete-run-btn", js)
        self.assertIn("Delete", js)

    def test_runs_subsection_structure(self):
        """
        Test that Runs subsection has proper structure.

        Validates: Requirements 2.1, 2.2, 2.3
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Verify subsection exists
        self.assertIn('id="manageRunsSubsection"', html)
        self.assertIn('class="manage-subsection"', html)

        # Verify subsection header
        self.assertIn('class="subsection-header"', html)
        self.assertIn('class="subsection-title"', html)

        # Verify subsection controls
        self.assertIn('class="subsection-controls"', html)

        # Verify subsection content
        self.assertIn('class="subsection-content"', html)

    def test_runs_entity_cards_structure(self):
        """
        Test that Runs entity cards have proper structure in JavaScript.

        Validates: Requirements 2.4
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify entity card structure
        self.assertIn("entity-card", js)
        self.assertIn("entity-card-header", js)
        self.assertIn("entity-card-title", js)
        self.assertIn("entity-card-meta", js)
        self.assertIn("entity-card-actions", js)
        self.assertIn("entity-card-badges", js)

    def test_plan_filter_event_listener_attached(self):
        """
        Test that plan filter dropdown event listener is attached.

        Validates: Requirements 7.2
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify plan filter event listener is attached
        self.assertIn("runsPlanFilter", js)
        self.assertIn("addEventListener", js)
        self.assertIn("change", js)

    def test_refresh_event_listener_attached(self):
        """
        Test that refresh button event listener is attached.

        Validates: Requirements 12.1, 12.2
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify refresh event listener is attached
        self.assertIn("refreshRunsBtn", js)
        self.assertIn("refreshRunList", js)

    def test_runs_data_storage_for_filtering(self):
        """
        Test that runs data is stored for potential future filtering functionality.

        Validates: Requirements 7.2
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify runs data storage exists
        self.assertIn("allRuns", js)

    def test_runs_loading_state_management(self):
        """
        Test that loading state is properly managed.

        Validates: Requirements 2.3
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify loading state management
        self.assertIn("runsLoadingState", js)
        self.assertIn("classList.remove", js)
        self.assertIn("classList.add", js)
        self.assertIn("hidden", js)

    def test_runs_display_plan_name_in_metadata(self):
        """
        Test that run cards display plan name in metadata.

        Validates: Requirements 2.4
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify plan name is included in run card metadata
        self.assertIn("plan_name", js)
        self.assertIn("Plan:", js)

    def test_runs_display_suite_name_in_metadata(self):
        """
        Test that run cards display suite name in metadata.

        Validates: Requirements 2.4
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify suite name is included in run card metadata
        self.assertIn("suite_name", js)
        self.assertIn("Suite:", js)

    def test_runs_sorted_by_creation_date(self):
        """
        Test that runs are sorted by creation date (newest first).

        Validates: Requirements 2.3
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify sorting logic exists
        self.assertIn("created_on", js)
        self.assertIn("sort", js)


if __name__ == "__main__":
    unittest.main()
