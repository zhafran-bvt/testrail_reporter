"""
Integration tests for Create tabs functionality.

This module validates the Create area now uses tabbed panels (Plan/Run/Case)
with accessible markup and initialization hooks.

Tests Requirements: 1.4, 6.1, 6.2, 11.3, 11.4
"""

import unittest

from fastapi.testclient import TestClient

from tests.test_base import BaseAPITestCase


class TestCreateSectionToggle(BaseAPITestCase):
    """Integration tests for Create tabs functionality."""

    def setUp(self):
        """Set up test self.client."""
        from app.main import app

        self.client = TestClient(app)

    def test_create_tabs_html_structure(self):
        """Test that Create tabs HTML structure is present with correct attributes."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Verify Create tabs container exists
        self.assertIn('class="manage-create-tabs"', html)
        self.assertIn('role="region"', html)
        self.assertIn('aria-labelledby="createTabsTitle"', html)

        # Verify tablist exists with correct attributes
        self.assertIn('class="manage-tablist"', html)
        self.assertIn('role="tablist"', html)
        self.assertIn('aria-label="Create entities"', html)

        # Verify all three tabs exist with controls
        self.assertIn('id="tabCreatePlan"', html)
        self.assertIn('id="tabCreateRun"', html)
        self.assertIn('id="tabCreateCase"', html)
        self.assertIn('aria-controls="createPlanTab"', html)
        self.assertIn('aria-controls="createRunTab"', html)
        self.assertIn('aria-controls="createCaseTab"', html)

        # Verify tab panels exist
        self.assertIn('id="createPlanTab"', html)
        self.assertIn('id="createRunTab"', html)
        self.assertIn('id="createCaseTab"', html)
        self.assertIn('role="tabpanel"', html)

    def test_create_tabs_default_active_tab(self):
        """Test that Plan tab is active by default (Requirement 1.4)."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Verify first tab is active by default
        self.assertIn('id="tabCreatePlan"', html)
        self.assertIn('class="manage-tab is-active"', html)
        self.assertIn('aria-selected="true"', html)
        self.assertIn('id="createPlanTab" class="manage-tab-panel is-active"', html)

    def test_tab_init_functions_exist(self):
        """Test that Create tab initialization functions exist in JavaScript."""
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify init functions are defined
        self.assertIn("function initScopedTabs", js)
        self.assertIn("function initManageTabs", js)

    def test_tab_activation_function_exists(self):
        """Test that tab activation logic exists (Requirement 6.1)."""
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify activation function exists in scoped tabs
        self.assertIn("activateTab", js)
        self.assertIn("aria-selected", js)
        self.assertIn('classList.toggle("is-active"', js)

    def test_click_event_listener(self):
        """Test that click event listener is attached to tab buttons (Requirement 6.2)."""
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify click event listener is added
        self.assertIn('addEventListener("click", () => activateTab(btn))', js)

    def test_keyboard_support(self):
        """Test that tab buttons are keyboard accessible (Requirement 11.3)."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Buttons are native elements with tab role and aria-selected
        self.assertIn('role="tab"', html)
        self.assertIn('type="button" class="manage-tab', html)
        self.assertIn('aria-selected="true"', html)

    def test_focus_create_tabs_function(self):
        """Test that focusCreateTabs helper exists for empty state CTA."""
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify focus helper is defined and exported
        self.assertIn("function focusCreateTabs()", js)
        self.assertIn("window.focusCreateTabs = focusCreateTabs", js)
        self.assertIn("scrollIntoView", js)
        self.assertIn("planTab.focus()", js)

    def test_smooth_animation_css(self):
        """Test that tab transition CSS is present."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Verify animation for tab panels exists
        self.assertIn("animation: fadeIn", html)
        self.assertIn("@keyframes fadeIn", html)

    def test_empty_state_buttons_use_focus_function(self):
        """Test that empty state buttons call focusCreateTabs."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Verify empty state buttons call focusCreateTabs
        self.assertIn('onclick="focusCreateTabs()"', html)

        # Verify button exists for plans entity type only
        # Count should be 1 (plans only) - Runs and Cases subsections were removed for hierarchical navigation
        count = html.count('onclick="focusCreateTabs()"')
        self.assertEqual(count, 1, "Should have 1 empty state button calling focusCreateTabs (Plans only)")

    def test_aria_attributes_for_accessibility(self):
        """Test that proper ARIA attributes are present (Requirement 11.3, 11.4)."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Verify aria-selected attribute
        self.assertIn("aria-selected", html)

        # Verify aria-controls attribute
        self.assertIn('aria-controls="createPlanTab"', html)

    def test_dom_ready_initialization(self):
        """Test that initialization happens on DOMContentLoaded."""
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)

        js = response.text

        # Verify DOMContentLoaded event listener
        self.assertIn('addEventListener("DOMContentLoaded", init)', js)

        # Verify initialization sets default state
        self.assertIn("initManageTabs()", js)

    def test_create_forms_stepper_structure(self):
        """Test that create forms stepper structure exists."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Verify stepper container
        self.assertIn('class="create-stepper"', html)

        # Verify step chips and content exist
        self.assertIn('class="create-step-chip', html)
        self.assertIn('class="create-step-content', html)

        # Verify create page headers exist
        self.assertIn("Plan Creation", html)
        self.assertIn("Run Creation", html)
        self.assertIn("Case Creation", html)


if __name__ == "__main__":
    unittest.main()
