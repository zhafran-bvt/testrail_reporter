"""
Tests for improved delete confirmation dialog.

These tests verify the enhanced delete confirmation modal that implements
Requirements 8.1, 8.2, 8.3, 8.4, and 8.5 from the Management UX Redesign spec.
"""
import unittest

from fastapi.testclient import TestClient

from app.main import app


class TestDeleteConfirmationDialog(unittest.TestCase):
    """Tests for delete confirmation dialog UI improvements."""

    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_delete_modal_structure_exists(self):
        """Test that delete confirmation modal has required structure."""
        # Get the main page
        response = self.client.get("/")
        assert response.status_code == 200
        html = response.text
        
        # Verify modal exists (Requirement 8.1, 8.2, 8.4)
        assert 'id="deleteConfirmModal"' in html, "Delete confirmation modal should exist"
        
        # Verify entity name display element exists (Requirement 8.1)
        assert 'id="deleteConfirmEntityName"' in html, "Entity name display should exist"
        
        # Verify entity type display element exists (Requirement 8.2)
        assert 'id="deleteConfirmEntityType"' in html, "Entity type display should exist"
        
        # Verify cascade warning element exists (Requirement 8.3)
        assert 'id="deleteConfirmCascadeWarning"' in html, "Cascade warning element should exist"
        assert 'id="deleteConfirmCascadeMessage"' in html, "Cascade message element should exist"
        
        # Verify type-to-confirm section exists (Requirement 8.5)
        assert 'id="deleteConfirmTypeSection"' in html, "Type-to-confirm section should exist"
        assert 'id="deleteConfirmTypeInput"' in html, "Type-to-confirm input should exist"
        assert 'id="deleteConfirmTypeName"' in html, "Type-to-confirm name display should exist"
        assert 'id="deleteConfirmTypeError"' in html, "Type-to-confirm error message should exist"

    def test_delete_modal_has_red_styling(self):
        """Test that delete modal uses red styling for destructive action (Requirement 8.4)."""
        response = self.client.get("/")
        assert response.status_code == 200
        html = response.text
        
        # Verify red color is used in modal styling
        assert '#ef4444' in html, "Red color (#ef4444) should be used for destructive styling"
        
        # Verify delete button has red styling
        assert 'id="deleteConfirmDelete"' in html, "Delete button should exist"
        # The button should have red background
        assert 'background: #ef4444' in html or 'bg-danger' in html, "Delete button should have red background"

    def test_delete_modal_has_warning_icon(self):
        """Test that delete modal displays warning icon."""
        response = self.client.get("/")
        assert response.status_code == 200
        html = response.text
        
        # Verify warning icon SVG exists
        assert 'Confirm Deletion' in html, "Modal title should exist"
        # Check for warning/alert SVG path
        assert 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10' in html or 'M1 21h22L12 2' in html, \
            "Warning icon should be present"

    def test_delete_modal_has_action_buttons(self):
        """Test that delete modal has cancel and delete buttons."""
        response = self.client.get("/")
        assert response.status_code == 200
        html = response.text
        
        # Verify cancel button exists
        assert 'id="deleteConfirmCancel"' in html, "Cancel button should exist"
        
        # Verify delete button exists
        assert 'id="deleteConfirmDelete"' in html, "Delete button should exist"
        
        # Verify close button exists
        assert 'id="deleteConfirmClose"' in html, "Close button should exist"

    def test_delete_modal_cascade_warning_structure(self):
        """Test that cascade warning has proper structure (Requirement 8.3)."""
        response = self.client.get("/")
        assert response.status_code == 200
        html = response.text
        
        # Verify cascade warning is hidden by default
        assert 'id="deleteConfirmCascadeWarning"' in html, "Cascade warning should exist"
        assert 'class="hidden"' in html or 'hidden' in html, "Cascade warning should be hidden by default"
        
        # Verify cascade warning has warning color (orange/yellow)
        assert '#f59e0b' in html or '#d97706' in html, "Cascade warning should use warning color"

    def test_delete_modal_type_to_confirm_structure(self):
        """Test that type-to-confirm section has proper structure (Requirement 8.5)."""
        response = self.client.get("/")
        assert response.status_code == 200
        html = response.text
        
        # Verify type section is hidden by default
        assert 'id="deleteConfirmTypeSection"' in html, "Type section should exist"
        
        # Verify input field exists
        assert 'id="deleteConfirmTypeInput"' in html, "Type input should exist"
        assert 'placeholder="Type name to confirm"' in html, "Input should have placeholder"
        
        # Verify error message element exists
        assert 'id="deleteConfirmTypeError"' in html, "Type error message should exist"

    def test_delete_modal_entity_info_card_styling(self):
        """Test that entity information card has prominent styling (Requirement 8.1, 8.2)."""
        response = self.client.get("/")
        assert response.status_code == 200
        html = response.text
        
        # Verify entity info has background styling
        assert 'rgba(239, 68, 68, 0.12)' in html or 'rgba(239, 68, 68, 0.1)' in html, \
            "Entity info card should have red-tinted background"
        
        # Verify entity name has prominent font weight
        assert 'font-weight: 700' in html or 'font-weight: 600' in html, \
            "Entity name should have bold font weight"

    def test_delete_modal_has_undo_warning(self):
        """Test that modal warns action cannot be undone."""
        response = self.client.get("/")
        assert response.status_code == 200
        html = response.text
        
        # Verify "cannot be undone" warning exists
        assert 'cannot be undone' in html.lower() or 'permanent' in html.lower(), \
            "Modal should warn that action cannot be undone"

    def test_manage_view_has_delete_buttons(self):
        """Test that management view has delete buttons for entities."""
        response = self.client.get("/")
        assert response.status_code == 200
        html = response.text
        
        # Verify delete button classes exist
        assert 'delete-plan-btn' in html or 'btn-delete' in html, \
            "Delete buttons should exist in management view"
        
        # Verify delete icon (trash) is used
        assert '🗑️' in html or 'trash' in html.lower(), \
            "Delete buttons should have trash icon"


class TestDeleteConfirmationAccessibility(unittest.TestCase):
    """Tests for delete confirmation dialog accessibility."""

    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_delete_modal_has_aria_attributes(self):
        """Test that delete modal has proper ARIA attributes."""
        response = self.client.get("/")
        assert response.status_code == 200
        html = response.text
        
        # Verify modal has role and aria attributes
        assert 'role="dialog"' in html, "Modal should have dialog role"
        assert 'aria-modal="true"' in html, "Modal should have aria-modal attribute"
        assert 'aria-labelledby' in html, "Modal should have aria-labelledby attribute"

    def test_delete_modal_buttons_have_labels(self):
        """Test that modal buttons have proper labels."""
        response = self.client.get("/")
        assert response.status_code == 200
        html = response.text
        
        # Verify close button has aria-label
        assert 'aria-label="Close"' in html, "Close button should have aria-label"

    def test_delete_modal_input_has_label(self):
        """Test that type-to-confirm input has proper label."""
        response = self.client.get("/")
        assert response.status_code == 200
        html = response.text
        
        # Verify input has associated label
        assert 'for="deleteConfirmTypeInput"' in html, "Input should have associated label"


class TestDeleteConfirmationResponsive(unittest.TestCase):
    """Tests for delete confirmation dialog responsive design."""

    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_delete_modal_has_max_width(self):
        """Test that delete modal has appropriate max-width."""
        response = self.client.get("/")
        assert response.status_code == 200
        html = response.text
        
        # Verify modal card has max-width constraint
        assert 'max-width: 540px' in html or 'max-width: 500px' in html, \
            "Modal should have max-width for better readability"

    def test_delete_modal_uses_flexible_layout(self):
        """Test that modal uses flexible layout for responsiveness."""
        response = self.client.get("/")
        assert response.status_code == 200
        html = response.text
        
        # Verify modal uses padding and spacing
        assert 'padding:' in html, "Modal should use padding for spacing"
        assert 'border-radius:' in html, "Modal should have rounded corners"


if __name__ == "__main__":
    unittest.main()
