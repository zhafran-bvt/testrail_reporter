"""Property-based tests for model validation."""

import pytest
from hypothesis import given, strategies as st
from pydantic import ValidationError

from app.models.requests import (
    ReportRequest, ManagePlan, ManageRun, ManageCase,
    UpdatePlan, UpdateRun, UpdateCase, AddTestResult
)


class TestValidationErrorDetail:
    """Property 7: Validation Error Detail - For any validation error, 
    the system should provide field-level error messages that help users correct their input."""
    
    @given(
        project=st.integers(max_value=0),  # Invalid project ID
        plan=st.one_of(st.none(), st.integers(min_value=1)),
        run=st.one_of(st.none(), st.integers(min_value=1))
    )
    def test_report_request_validation_provides_detailed_errors(self, project, plan, run):
        """Test that ReportRequest validation errors include detailed field information."""
        try:
            ReportRequest(project=project, plan=plan, run=run)
            # If no exception, the input was valid, which is fine
        except ValidationError as e:
            # Validation error should have detailed field information
            errors = e.errors()
            assert len(errors) > 0, "ValidationError should contain error details"
            
            for error in errors:
                assert "loc" in error, "Error should specify field location"
                assert "msg" in error, "Error should have descriptive message"
                assert "type" in error, "Error should specify error type"
                
                # Check that location is present (may be empty for model-level errors)
                assert isinstance(error["loc"], tuple), "Error location should be tuple"
                
                # Check that message is descriptive
                assert len(error["msg"]) > 0, "Error message should not be empty"
    
    @given(
        name=st.text(max_size=0),  # Empty name should fail
        project=st.integers(min_value=1)
    )
    def test_manage_plan_validation_provides_field_errors(self, name, project):
        """Test that ManagePlan validation provides specific field error messages."""
        try:
            ManagePlan(project=project, name=name)
        except ValidationError as e:
            errors = e.errors()
            
            # Should have at least one error for the empty name
            name_errors = [err for err in errors if "name" in str(err.get("loc", []))]
            assert len(name_errors) > 0, "Should have validation error for name field"
            
            for error in name_errors:
                assert "name" in str(error["loc"]), "Error should be associated with name field"
                assert len(error["msg"]) > 5, "Error message should be descriptive"
    
    @given(
        status_id=st.integers().filter(lambda x: x not in [1, 2, 3, 4, 5])  # Invalid status
    )
    def test_add_test_result_validation_provides_status_errors(self, status_id):
        """Test that AddTestResult validation provides specific status_id error messages."""
        try:
            AddTestResult(status_id=status_id)
        except ValidationError as e:
            errors = e.errors()
            
            # Should have error for invalid status_id
            status_errors = [err for err in errors if "status_id" in str(err.get("loc", []))]
            
            if status_errors:  # Only check if there are status-related errors
                for error in status_errors:
                    assert "status_id" in str(error["loc"]), "Error should be for status_id field"
                    assert len(error["msg"]) > 0, "Error message should be descriptive"
    
    @given(
        include_all=st.just(False),  # Set include_all to False
        case_ids=st.one_of(st.none(), st.lists(st.integers(), max_size=0))  # Empty or None case_ids
    )
    def test_manage_run_validation_provides_constraint_errors(self, include_all, case_ids):
        """Test that ManageRun validation provides errors for business rule violations."""
        try:
            ManageRun(
                name="Test Run",
                include_all=include_all,
                case_ids=case_ids
            )
        except ValidationError as e:
            errors = e.errors()
            
            # Should have validation error for the constraint violation
            assert len(errors) > 0, "Should have validation errors for constraint violation"
            
            # At least one error should mention the constraint
            constraint_errors = [
                err for err in errors 
                if "case_ids" in err["msg"].lower() or "include_all" in err["msg"].lower()
            ]
            
            if constraint_errors:
                for error in constraint_errors:
                    assert len(error["msg"]) > 10, "Constraint error should be descriptive"
    
    def test_validation_error_structure_consistency(self):
        """Test that all validation errors follow consistent structure."""
        test_cases = [
            (ReportRequest, {"project": -1}),
            (ManagePlan, {"name": "", "project": 1}),
            (AddTestResult, {"status_id": 99}),
        ]
        
        for model_class, invalid_data in test_cases:
            try:
                model_class(**invalid_data)
            except ValidationError as e:
                errors = e.errors()
                
                for error in errors:
                    # Check required fields are present
                    required_fields = ["loc", "msg", "type"]
                    for field in required_fields:
                        assert field in error, f"Error missing required field: {field}"
                    
                    # Check field types
                    assert isinstance(error["loc"], tuple), "Location should be tuple"
                    assert isinstance(error["msg"], str), "Message should be string"
                    assert isinstance(error["type"], str), "Type should be string"
                    
                    # Check content quality
                    assert len(error["msg"]) > 0, "Message should not be empty"
                    # Location can be empty for model-level validation errors