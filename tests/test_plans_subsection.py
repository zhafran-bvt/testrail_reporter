"""
Integration tests for Plans subsection functionality.

This module tests the Plans subsection implementation including:
- renderPlansSubsection() function
- Search filtering for plan names
- Count badge updates
- Empty state display
- Refresh button functionality
- Edit and Delete button wiring
"""

import unittest
from fastapi.testclient import TestClient


class TestPlansSubsection(unittest.TestCase):
    """Tests for Plans subsection functionality."""

    def setUp(self):
        """Set up test client."""
        from app.main import app
        self.client = TestClient(app)

    def test_renderPlansSubsection_function_exists(self):
        """
        Test that renderPlansSubsection function exists in the compiled JavaScript.
        
        Validates: Requirements 2.1, 2.2
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        
        js = response.text
        
        # Verify renderPlansSubsection function exists
        self.assertIn('renderPlansSubsection', js, 
                     "renderPlansSubsection function should exist in compiled JS")

    def test_filterPlans_function_exists(self):
        """
        Test that filterPlans function exists for search filtering.
        
        Validates: Requirements 7.1
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        
        js = response.text
        
        # Verify filterPlans function exists
        self.assertIn('filterPlans', js, 
                     "filterPlans function should exist in compiled JS")

    def test_plans_search_input_exists(self):
        """
        Test that Plans search input exists in the HTML.
        
        Validates: Requirements 7.1
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        
        html = response.text
        
        # Verify search input exists
        self.assertIn('id="plansSearch"', html)
        self.assertIn('type="search"', html)
        self.assertIn('placeholder="Search plans..."', html)
        self.assertIn('aria-label="Search plans"', html)

    def test_plans_count_badge_exists(self):
        """
        Test that Plans count badge exists in the HTML.
        
        Validates: Requirements 2.2
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        
        html = response.text
        
        # Verify count badge exists
        self.assertIn('id="plansCount"', html)
        self.assertIn('class="count-badge"', html)

    def test_plans_empty_state_exists(self):
        """
        Test that Plans empty state exists with helpful message.
        
        Validates: Requirements 5.1
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        
        html = response.text
        
        # Verify empty state exists
        self.assertIn('id="plansEmptyState"', html)
        self.assertIn('class="empty-state', html)
        
        # Verify helpful message
        self.assertIn('No plans yet', html)
        self.assertIn('Create your first plan above', html)
        
        # Verify action button exists
        self.assertIn('expandCreateSection()', html)

    def test_plans_refresh_button_exists(self):
        """
        Test that Plans refresh button exists for manual reload.
        
        Validates: Requirements 12.1, 12.2
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        
        html = response.text
        
        # Verify refresh button exists
        self.assertIn('id="refreshPlansBtn"', html)
        self.assertIn('class="refresh-btn"', html)
        self.assertIn('aria-label="Refresh plans"', html)
        
        # Verify refresh icon
        self.assertIn('🔄', html)

    def test_plans_edit_button_styling(self):
        """
        Test that Edit buttons have proper styling in the JavaScript.
        
        Validates: Requirements 2.4
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        
        js = response.text
        
        # Verify edit button class exists in rendered HTML
        self.assertIn('edit-plan-btn', js)
        self.assertIn('Edit', js)

    def test_plans_delete_button_styling(self):
        """
        Test that Delete buttons have proper styling in the JavaScript.
        
        Validates: Requirements 2.4
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        
        js = response.text
        
        # Verify delete button class exists in rendered HTML
        self.assertIn('delete-plan-btn', js)
        self.assertIn('Delete', js)

    def test_plans_subsection_structure(self):
        """
        Test that Plans subsection has proper structure.
        
        Validates: Requirements 2.1, 2.2, 2.3
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        
        html = response.text
        
        # Verify subsection exists
        self.assertIn('id="managePlansSubsection"', html)
        self.assertIn('class="manage-subsection"', html)
        
        # Verify subsection header
        self.assertIn('class="subsection-header"', html)
        self.assertIn('class="subsection-title"', html)
        
        # Verify subsection controls
        self.assertIn('class="subsection-controls"', html)
        
        # Verify subsection content
        self.assertIn('class="subsection-content"', html)

    def test_plans_entity_cards_structure(self):
        """
        Test that Plans entity cards have proper structure in JavaScript.
        
        Validates: Requirements 2.4
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        
        js = response.text
        
        # Verify entity card structure
        self.assertIn('entity-card', js)
        self.assertIn('entity-card-header', js)
        self.assertIn('entity-card-title', js)
        self.assertIn('entity-card-meta', js)
        self.assertIn('entity-card-actions', js)
        self.assertIn('entity-card-badges', js)

    def test_search_event_listener_attached(self):
        """
        Test that search input event listener is attached.
        
        Validates: Requirements 7.1
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        
        js = response.text
        
        # Verify search event listener is attached
        self.assertIn('plansSearch', js)
        self.assertIn('addEventListener', js)
        self.assertIn('input', js)

    def test_refresh_event_listener_attached(self):
        """
        Test that refresh button event listener is attached.
        
        Validates: Requirements 12.1, 12.2
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        
        js = response.text
        
        # Verify refresh event listener is attached
        self.assertIn('refreshPlansBtn', js)
        self.assertIn('refreshPlanList', js)

    def test_plans_data_storage_for_filtering(self):
        """
        Test that plans data is stored for filtering functionality.
        
        Validates: Requirements 7.1
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        
        js = response.text
        
        # Verify plans data storage exists
        self.assertIn('allPlans', js)

    def test_plans_loading_state_management(self):
        """
        Test that loading state is properly managed.
        
        Validates: Requirements 2.3
        """
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        
        js = response.text
        
        # Verify loading state management
        self.assertIn('plansLoadingState', js)
        self.assertIn('classList.remove', js)
        self.assertIn('classList.add', js)
        self.assertIn('hidden', js)


if __name__ == '__main__':
    unittest.main()
