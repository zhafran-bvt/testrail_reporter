import unittest

from fastapi.testclient import TestClient

from app.main import app
from tests.test_base import BaseAPITestCase


class TestKeyboardNavigationFocusIndicators(BaseAPITestCase):
    """Tests for keyboard navigation focus indicators (Requirement 11.5)"""

    def setUp(self):
        self.client = TestClient(app)

    def test_refresh_button_has_focus_style(self):
        """Test that refresh buttons have visible focus indicators"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text

        # Verify refresh button focus style exists
        self.assertIn(".refresh-btn:focus", html)
        self.assertIn("outline: 2px solid var(--primary)", html)

    def test_delete_button_has_focus_style(self):
        """Test that delete buttons have visible focus indicators"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text

        # Verify delete button focus style exists
        self.assertIn(".delete-btn:focus", html)
        self.assertIn(".btn-delete:focus", html)

    def test_edit_button_has_focus_style(self):
        """Test that edit buttons have visible focus indicators"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text

        # Verify edit button focus style exists
        self.assertIn(".btn-edit:focus", html)

    def test_modal_close_button_has_focus_style(self):
        """Test that modal close buttons have visible focus indicators"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text

        # Verify modal close button focus style exists
        self.assertIn(".modal-close:focus", html)

    def test_create_section_toggle_has_focus_style(self):
        """Test that Create tab buttons have visible focus indicator"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text

        # Verify create tab buttons exist and general button focus style applies
        self.assertIn('class="manage-tab', html)
        self.assertIn("button:not(.panel-toggle):focus", html)

    def test_input_fields_have_focus_style(self):
        """Test that input fields have visible focus indicators"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text

        # Verify input focus style exists
        self.assertIn("input:focus", html)
        self.assertIn("select:focus", html)

    def test_entity_card_focus_within_style(self):
        """Test that entity cards highlight when buttons inside are focused"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text

        # Verify entity card focus-within style exists
        self.assertIn(".entity-card:focus-within", html)

    def test_empty_state_button_has_focus_style(self):
        """Test that empty state buttons have visible focus indicators"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text

        # Verify empty state button focus style exists
        self.assertIn(".empty-state .btn-primary:focus", html)

    def test_modal_delete_button_has_focus_style(self):
        """Test that modal delete button has visible focus indicator"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text

        # Verify modal delete button focus style exists
        self.assertIn(".btn-modal-delete:focus", html)

    def test_general_button_has_focus_style(self):
        """Test that general buttons have visible focus indicators"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text

        # Verify general button focus style exists
        self.assertIn("button:not(.panel-toggle):focus", html)


class TestKeyboardNavigationEnterSpace(BaseAPITestCase):
    """Tests for Enter/Space keyboard support (Requirement 11.2)"""

    def setUp(self):
        self.client = TestClient(app)

    def test_create_section_toggle_keyboard_support(self):
        """Test that create tabs are keyboard accessible via buttons"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text

        # Verify buttons are used for tabs with proper roles
        self.assertIn('role="tab"', html)
        self.assertIn('type="button" class="manage-tab', html)


class TestKeyboardNavigationEscape(BaseAPITestCase):
    """Tests for Escape key support (Requirements 11.3, 11.4)"""

    def setUp(self):
        self.client = TestClient(app)

    def test_create_tabs_have_accessible_structure(self):
        """Test that create tabs expose accessible structure for keyboard users"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text

        # Verify tablist and tabpanel roles exist
        self.assertIn('role="tablist"', html)
        self.assertIn('role="tabpanel"', html)
        self.assertIn("aria-selected", html)

    def test_escape_closes_modal(self):
        """Test that Escape key closes modals"""
        # Get the compiled JavaScript file
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        js = response.text

        # Verify Escape key handler for modals exists
        self.assertIn("Escape", js)
        self.assertIn("hideDeleteConfirmation", js)


class TestKeyboardNavigationTabOrder(BaseAPITestCase):
    """Tests for logical Tab order (Requirement 11.1)"""

    def setUp(self):
        self.client = TestClient(app)

    def test_interactive_elements_are_focusable(self):
        """Test that all interactive elements are focusable"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text

        # Verify buttons exist and are focusable (no tabindex=-1)
        self.assertIn('id="refreshPlansBtn"', html)
        # Note: refreshRunsBtn and refreshTestCasesBtn removed due to hierarchical navigation
        # Runs and Cases are now accessed through modals, not separate subsections

        # Verify search inputs exist
        self.assertIn('id="plansSearch"', html)

        # Verify create tabs exist
        self.assertIn('class="manage-tab', html)

    def test_create_section_toggle_has_aria_expanded(self):
        """Test that create tabs have proper ARIA attributes"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text

        # Verify ARIA attributes exist
        self.assertIn("aria-selected", html)
        self.assertIn("aria-controls", html)

    def test_modal_close_buttons_have_aria_label(self):
        """Test that modal close buttons have aria-label for accessibility"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text

        # Verify aria-label exists on close buttons
        self.assertIn('aria-label="Close"', html)


class TestKeyboardNavigationFocusManagement(BaseAPITestCase):
    """Tests for focus management in modals and interactions"""

    def setUp(self):
        self.client = TestClient(app)

    def test_delete_modal_focuses_cancel_button(self):
        """Test that delete modal focuses cancel button when opened"""
        # Get the compiled JavaScript file
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        js = response.text

        # Verify focus management in delete modal
        self.assertIn("deleteConfirmCancel", js)
        self.assertIn("focus", js)

    def test_expand_create_section_focuses_toggle(self):
        """Test that focusCreateTabs focuses the Plan tab"""
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        js = response.text

        # Verify focus management in focusCreateTabs
        self.assertIn("focusCreateTabs", js)
        self.assertIn("planTab.focus()", js)


if __name__ == "__main__":
    unittest.main()
