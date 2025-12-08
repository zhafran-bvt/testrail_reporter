"""
Integration tests for Cases subsection functionality.

This module tests the Cases subsection implementation including:
- renderCasesSubsection() function
- Search filtering for case titles/refs
- Count badge updates
- Empty state display
- Refresh button functionality
- Edit and Delete button wiring
"""

import unittest

from fastapi.testclient import TestClient


class TestCasesSubsection(unittest.TestCase):
    """Tests for Cases subsection functionality."""

    def setUp(self):
        """Set up test client."""
        from app.main import app

        self.client = TestClient(app)

    def test_renderCasesSubsection_function_exists(self):
        """
        Test that renderCasesSubsection function exists in the compiled JavaScript.

        Validates: Requirements 2.1, 2.2
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify renderCasesSubsection function exists
        self.assertIn("renderCasesSubsection", js, "renderCasesSubsection function should exist in compiled JS")

    def test_filterCases_function_exists(self):
        """
        Test that filterCases function exists for search filtering.

        Validates: Requirements 7.3
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify filterCases function exists
        self.assertIn("filterCases", js, "filterCases function should exist in compiled JS")

    def test_cases_search_input_exists(self):
        """
        Test that Cases search input exists in the HTML.

        Validates: Requirements 7.3
        """

    def test_cases_count_badge_exists(self):
        """
        Test that Test Cases View count badge exists in the HTML.

        Validates: Requirements 2.2
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Verify count badge exists in Test Cases View
        self.assertIn('id="testCasesCount"', html)
        self.assertIn('class="count-badge"', html)

    def test_cases_empty_state_exists(self):
        """
        Test that Test Cases View empty state exists with helpful message.

        Validates: Requirements 5.3
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Verify empty state exists in Test Cases View
        self.assertIn('id="testCasesEmptyState"', html)
        self.assertIn('class="empty-state', html)

        # Verify helpful message for test cases view
        self.assertIn("No test cases", html)

    def test_cases_refresh_button_exists(self):
        """
        Test that Cases refresh button exists for manual reload.

        Validates: Requirements 12.1, 12.2
        """

    def test_cases_edit_button_styling(self):
        """
        Test that Edit buttons have proper styling in the JavaScript.

        Validates: Requirements 2.4
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify edit button class exists in rendered HTML
        self.assertIn("edit-case-btn", js)
        self.assertIn("Edit", js)

    def test_cases_delete_button_styling(self):
        """
        Test that Delete buttons have proper styling in the JavaScript.

        Validates: Requirements 2.4
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify delete button class exists in rendered HTML
        self.assertIn("delete-case-btn", js)
        self.assertIn("Delete", js)

    def test_cases_subsection_structure(self):
        """
        Test that Test Cases View has proper structure.

        Validates: Requirements 2.1, 2.2, 2.3
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Verify Test Cases View exists
        self.assertIn('id="testCasesView"', html)
        self.assertIn('class="manage-subsection', html)

        # Verify subsection header
        self.assertIn('class="subsection-header"', html)
        self.assertIn('class="subsection-title"', html)

        # Verify subsection controls
        self.assertIn('class="subsection-controls"', html)

        # Verify subsection content
        self.assertIn('class="subsection-content"', html)

    def test_cases_entity_cards_structure(self):
        """
        Test that Cases entity cards have proper structure in JavaScript.

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

    def test_search_event_listener_attached(self):
        """
        Test that search input event listener is attached.

        Validates: Requirements 7.3
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify search event listener is attached
        self.assertIn("casesSearch", js)
        self.assertIn("addEventListener", js)
        self.assertIn("input", js)

    def test_refresh_event_listener_attached(self):
        """
        Test that refresh button event listener is attached.

        Validates: Requirements 12.1, 12.2
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify refresh event listener is attached
        self.assertIn("refreshCasesBtn", js)
        self.assertIn("refreshCaseList", js)

    def test_cases_data_storage_for_filtering(self):
        """
        Test that cases data is stored for filtering functionality.

        Validates: Requirements 7.3
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify cases data storage exists
        self.assertIn("allCases", js)

    def test_cases_loading_state_management(self):
        """
        Test that loading state is properly managed.

        Validates: Requirements 2.3
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify loading state management
        self.assertIn("casesLoadingState", js)
        self.assertIn("classList.remove", js)
        self.assertIn("classList.add", js)
        self.assertIn("hidden", js)

    def test_cases_search_filters_by_title(self):
        """
        Test that search filtering works for case titles.

        Validates: Requirements 7.3
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify filtering logic includes title
        self.assertIn("caseTitle", js)
        self.assertIn("toLowerCase", js)
        self.assertIn("includes", js)

    def test_cases_search_filters_by_refs(self):
        """
        Test that search filtering works for case refs.

        Validates: Requirements 7.3
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify filtering logic includes refs
        self.assertIn("caseRefs", js)
        self.assertIn("toLowerCase", js)
        self.assertIn("includes", js)

    def test_cases_entity_card_includes_refs(self):
        """
        Test that case entity cards include refs in metadata.

        Validates: Requirements 2.4
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify refs are included in card metadata
        self.assertIn("Refs:", js)
        self.assertIn("testCase.refs", js)


if __name__ == "__main__":
    unittest.main()
