import unittest

from fastapi.testclient import TestClient

from app.main import app


class TestKeyboardNavigationFocusIndicators(unittest.TestCase):
    """Tests for keyboard navigation focus indicators (Requirement 11.5)"""
    
    def setUp(self):
        self.client = TestClient(app)
    
    def test_refresh_button_has_focus_style(self):
        """Test that refresh buttons have visible focus indicators"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text
        
        # Verify refresh button focus style exists
        self.assertIn('.refresh-btn:focus', html)
        self.assertIn('outline: 2px solid var(--primary)', html)
    
    def test_delete_button_has_focus_style(self):
        """Test that delete buttons have visible focus indicators"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text
        
        # Verify delete button focus style exists
        self.assertIn('.delete-btn:focus', html)
        self.assertIn('.btn-delete:focus', html)
    
    def test_edit_button_has_focus_style(self):
        """Test that edit buttons have visible focus indicators"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text
        
        # Verify edit button focus style exists
        self.assertIn('.btn-edit:focus', html)
    
    def test_modal_close_button_has_focus_style(self):
        """Test that modal close buttons have visible focus indicators"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text
        
        # Verify modal close button focus style exists
        self.assertIn('.modal-close:focus', html)
    
    def test_create_section_toggle_has_focus_style(self):
        """Test that create section toggle has visible focus indicator"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text
        
        # Verify create section toggle focus style exists
        self.assertIn('.create-section-toggle:focus', html)
    
    def test_input_fields_have_focus_style(self):
        """Test that input fields have visible focus indicators"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text
        
        # Verify input focus style exists
        self.assertIn('input:focus', html)
        self.assertIn('select:focus', html)
    
    def test_entity_card_focus_within_style(self):
        """Test that entity cards highlight when buttons inside are focused"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text
        
        # Verify entity card focus-within style exists
        self.assertIn('.entity-card:focus-within', html)
    
    def test_empty_state_button_has_focus_style(self):
        """Test that empty state buttons have visible focus indicators"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text
        
        # Verify empty state button focus style exists
        self.assertIn('.empty-state .btn-primary:focus', html)
    
    def test_modal_delete_button_has_focus_style(self):
        """Test that modal delete button has visible focus indicator"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text
        
        # Verify modal delete button focus style exists
        self.assertIn('.btn-modal-delete:focus', html)
    
    def test_general_button_has_focus_style(self):
        """Test that general buttons have visible focus indicators"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text
        
        # Verify general button focus style exists
        self.assertIn('button:not(.panel-toggle):focus', html)


class TestKeyboardNavigationEnterSpace(unittest.TestCase):
    """Tests for Enter/Space keyboard support (Requirement 11.2)"""
    
    def setUp(self):
        self.client = TestClient(app)
    
    def test_create_section_toggle_keyboard_support(self):
        """Test that create section toggle supports Enter and Space keys"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text
        
        # Verify keyboard event listener for Enter and Space
        self.assertIn("e.key === 'Enter'", html)
        self.assertIn("e.key === ' '", html)
        self.assertIn('toggleCreateSection()', html)


class TestKeyboardNavigationEscape(unittest.TestCase):
    """Tests for Escape key support (Requirements 11.3, 11.4)"""
    
    def setUp(self):
        self.client = TestClient(app)
    
    def test_escape_closes_create_section(self):
        """Test that Escape key collapses Create section"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text
        
        # Verify Escape key handler exists
        self.assertIn("e.key === 'Escape'", html)
        self.assertIn('collapseCreateSection', html)
    
    def test_escape_closes_modal(self):
        """Test that Escape key closes modals"""
        # Get the compiled JavaScript file
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        js = response.text
        
        # Verify Escape key handler for modals exists
        self.assertIn('Escape', js)
        self.assertIn('hideDeleteConfirmation', js)


class TestKeyboardNavigationTabOrder(unittest.TestCase):
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
        self.assertIn('id="refreshRunsBtn"', html)
        self.assertIn('id="refreshTestCasesBtn"', html)
        
        # Verify search inputs exist
        self.assertIn('id="plansSearch"', html)
        
        # Verify create section toggle exists
        self.assertIn('class="create-section-toggle"', html)
    
    def test_create_section_toggle_has_aria_expanded(self):
        """Test that create section toggle has proper ARIA attributes"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text
        
        # Verify ARIA attributes exist
        self.assertIn('aria-expanded', html)
    
    def test_modal_close_buttons_have_aria_label(self):
        """Test that modal close buttons have aria-label for accessibility"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text
        
        # Verify aria-label exists on close buttons
        self.assertIn('aria-label="Close"', html)


class TestKeyboardNavigationFocusManagement(unittest.TestCase):
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
        self.assertIn('deleteConfirmCancel', js)
        self.assertIn('focus', js)
    
    def test_expand_create_section_focuses_toggle(self):
        """Test that expanding create section focuses the toggle button"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text
        
        # Verify focus management in expandCreateSection
        self.assertIn('toggleButton.focus()', html)


if __name__ == '__main__':
    unittest.main()
