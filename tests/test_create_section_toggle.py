"""
Integration tests for Create section toggle functionality.

This module contains integration tests that verify the Create section
toggle functionality works correctly with proper HTML structure,
JavaScript functions, and accessibility attributes.

Tests Requirements: 1.4, 6.1, 6.2, 11.3, 11.4
"""

import unittest

from fastapi.testclient import TestClient

class TestCreateSectionToggle(BaseAPITestCase):
    """Integration tests for Create section toggle functionality."""

    def setUp(self):
        """Set up test client."""
        from app.main import app

        self.client = TestClient(app)

    def test_create_section_html_structure(self):
        """Test that Create section HTML structure is present with correct attributes."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Verify Create section container exists
        self.assertIn('class="create-section"', html)

        # Verify toggle button exists with correct attributes
        self.assertIn('class="create-section-toggle"', html)
        self.assertIn('aria-expanded="false"', html)
        self.assertIn('aria-controls="createSectionContent"', html)

        # Verify toggle button has icon and title (with aria-hidden for accessibility)
        self.assertIn('<span class="icon" aria-hidden="true">➕</span>', html)
        self.assertIn('<h2 id="createSectionHeading">Create New</h2>', html)
        self.assertIn('<span class="toggle-indicator" aria-hidden="true">▼</span>', html)

        # Verify content div exists with correct ID and hidden class
        self.assertIn('id="createSectionContent"', html)
        self.assertIn('class="create-section-content hidden"', html)

    def test_create_section_starts_collapsed(self):
        """Test that Create section starts in collapsed state (Requirement 1.4)."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Verify aria-expanded is false by default
        self.assertIn('aria-expanded="false"', html)

        # Verify content has hidden class
        self.assertIn('class="create-section-content hidden"', html)

    def test_toggle_function_exists(self):
        """Test that toggleCreateSection function is defined in JavaScript."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Verify toggle function is defined
        self.assertIn("function toggleCreateSection()", html)

        # Verify function manipulates aria-expanded attribute
        self.assertIn("getAttribute('aria-expanded')", html)
        self.assertIn("setAttribute('aria-expanded'", html)

    def test_expand_function_exists(self):
        """Test that expandCreateSection function is defined (Requirement 6.1)."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Verify expand function is defined
        self.assertIn("function expandCreateSection()", html)

        # Verify function removes hidden class
        self.assertIn("classList.remove('hidden')", html)

        # Verify function is globally available
        self.assertIn("window.expandCreateSection = expandCreateSection", html)

    def test_collapse_function_exists(self):
        """Test that collapseCreateSection function is defined (Requirement 11.4)."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Verify collapse function is defined
        self.assertIn("function collapseCreateSection()", html)

        # Verify function adds hidden class
        self.assertIn("classList.add('hidden')", html)

    def test_click_event_listener(self):
        """Test that click event listener is attached to toggle button (Requirement 6.2)."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Verify click event listener is added
        self.assertIn("addEventListener('click', toggleCreateSection)", html)

    def test_keyboard_support(self):
        """Test that keyboard support (Enter/Space) is implemented (Requirement 11.3)."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Verify keydown event listener is added
        self.assertIn("addEventListener('keydown'", html)

        # Verify Enter and Space keys are handled
        self.assertIn("e.key === 'Enter'", html)
        self.assertIn("e.key === ' '", html)

    def test_escape_key_support(self):
        """Test that Escape key collapses the Create section (Requirement 11.4)."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Verify global Escape key handler exists
        self.assertIn("e.key === 'Escape'", html)

        # Verify it calls collapse function
        self.assertIn("collapseCreateSection()", html)

    def test_smooth_animation_css(self):
        """Test that smooth animation CSS is present."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Verify transition CSS is present
        self.assertIn("transition:", html)

        # Verify animation for toggle indicator rotation
        self.assertIn("transform: rotate(180deg)", html)

        # Verify slideDown animation exists
        self.assertIn("@keyframes slideDown", html)

    def test_empty_state_buttons_use_expand_function(self):
        """Test that empty state buttons call expandCreateSection."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Verify empty state buttons call expandCreateSection
        self.assertIn('onclick="expandCreateSection()"', html)

        # Verify button exists for plans entity type only
        # Count should be 1 (plans only) - Runs and Cases subsections were removed for hierarchical navigation
        count = html.count('onclick="expandCreateSection()"')
        self.assertEqual(count, 1, "Should have 1 empty state button calling expandCreateSection (Plans only)")

    def test_aria_attributes_for_accessibility(self):
        """Test that proper ARIA attributes are present (Requirement 11.3, 11.4)."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Verify aria-expanded attribute
        self.assertIn("aria-expanded", html)

        # Verify aria-controls attribute
        self.assertIn('aria-controls="createSectionContent"', html)

    def test_dom_ready_initialization(self):
        """Test that initialization happens on DOMContentLoaded."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Verify DOMContentLoaded event listener
        self.assertIn("addEventListener('DOMContentLoaded'", html)

        # Verify initialization sets default state
        self.assertIn("content.classList.add('hidden')", html)
        self.assertIn("toggleButton.setAttribute('aria-expanded', 'false')", html)

    def test_create_forms_grid_structure(self):
        """Test that create forms grid structure exists."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.text

        # Verify forms grid container
        self.assertIn('class="create-forms-grid"', html)

        # Verify form cards exist
        self.assertIn('class="create-form-card"', html)

        # Verify all three form types exist
        self.assertIn("Create Test Plan", html)
        self.assertIn("Create Test Run", html)
        self.assertIn("Create Test Case", html)

if __name__ == "__main__":
    unittest.main()
