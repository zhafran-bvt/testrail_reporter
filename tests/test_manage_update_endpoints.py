"""
Property-based tests for management update endpoints.

These tests verify the correctness properties for updating plans, runs, and cases.
"""

import types
import unittest
from unittest.mock import Mock

from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

import app.main as main


# Hypothesis strategies for generating test data
@st.composite
def gen_plan_update_data(draw):
    """Generate random plan update data."""
    # Generate at least one non-None field
    has_name = draw(st.booleans())
    has_description = draw(st.booleans())
    has_milestone = draw(st.booleans())

    # Ensure at least one field is present
    if not (has_name or has_description or has_milestone):
        has_name = True

    # Generate name with at least one non-whitespace character if present
    name = None
    if has_name:
        # Generate text that has at least one non-whitespace character
        name = draw(st.text(min_size=1, max_size=100).filter(lambda s: s.strip() != ""))

    return {
        "name": name,
        "description": draw(st.text(min_size=0, max_size=500)) if has_description else None,
        "milestone_id": draw(st.integers(min_value=1, max_value=1000)) if has_milestone else None,
    }


@st.composite
def gen_run_update_data(draw):
    """Generate random run update data."""
    # Generate at least one non-None field
    has_name = draw(st.booleans())
    has_description = draw(st.booleans())
    has_refs = draw(st.booleans())

    # Ensure at least one field is present
    if not (has_name or has_description or has_refs):
        has_name = True

    # Generate name with at least one non-whitespace character if present
    name = None
    if has_name:
        # Generate text that has at least one non-whitespace character
        name = draw(st.text(min_size=1, max_size=100).filter(lambda s: s.strip() != ""))

    return {
        "name": name,
        "description": draw(st.text(min_size=0, max_size=500)) if has_description else None,
        "refs": draw(st.text(min_size=0, max_size=100)) if has_refs else None,
    }


@st.composite
def gen_case_update_data(draw):
    """Generate random case update data."""
    # Generate at least one non-None, non-empty field
    has_title = draw(st.booleans())
    has_refs = draw(st.booleans())
    has_bdd = draw(st.booleans())

    # Ensure at least one field is present
    if not (has_title or has_refs or has_bdd):
        has_title = True

    # Generate title with at least one non-whitespace character if present
    title = None
    if has_title:
        # Generate text that has at least one non-whitespace character
        title = draw(st.text(min_size=1, max_size=100).filter(lambda s: s.strip() != ""))

    # For bdd_scenarios, we need to ensure it's either None or has content
    # Empty string for bdd_scenarios doesn't count as a field update
    bdd = None
    if has_bdd:
        # Either generate None or a non-empty string
        bdd = draw(st.one_of(st.none(), st.text(min_size=1, max_size=500)))

    # Ensure at least one field will actually be sent (not None and not empty for bdd)
    result = {
        "title": title,
        "refs": draw(st.text(min_size=0, max_size=100)) if has_refs else None,
        "bdd_scenarios": bdd,
    }

    # Check if at least one field will be sent
    has_valid_field = (
        (result["title"] is not None)
        or (result["refs"] is not None)
        or (result["bdd_scenarios"] is not None and result["bdd_scenarios"].strip() != "")
    )

    # If no valid fields, ensure title is present
    if not has_valid_field:
        result["title"] = draw(st.text(min_size=1, max_size=100).filter(lambda s: s.strip() != ""))

    return result


class TestPlanUpdateProperties(unittest.TestCase):
    """
    Property-based tests for plan update operations.

    **Feature: testrail-dashboard, Property 25: Plan update field persistence**
    **Validates: Requirements 11.2**

    For any plan update request with non-null fields, the updated plan should
    reflect the new values for those fields while preserving unchanged fields.
    """

    @settings(max_examples=100, deadline=None)
    @given(
        plan_id=st.integers(min_value=1, max_value=10000),
        update_data=gen_plan_update_data(),
    )
    def test_plan_update_field_persistence(self, plan_id, update_data):
        """
        **Feature: testrail-dashboard, Property 25: Plan update field persistence**
        **Validates: Requirements 11.2**

        For any plan update request with non-null fields, the updated plan should
        reflect the new values for those fields while preserving unchanged fields.
        """
        client = TestClient(main.app)

        # Create a fake client that tracks what was sent
        fake = types.SimpleNamespace()
        called = {}

        # Original plan data (simulating existing plan)
        original_plan = {
            "id": plan_id,
            "name": "Original Plan Name",
            "description": "Original Description",
            "milestone_id": 42,
            "created_on": 1234567890,
            "is_completed": False,
        }

        def update_plan(pid, payload):
            called["plan_id"] = pid
            called["payload"] = payload

            # Simulate TestRail behavior: merge update with original
            updated = original_plan.copy()
            updated.update(payload)
            return updated

        fake.update_plan = update_plan

        # Patch the client
        import app.main as main_module

        main_module._make_client = lambda: fake
        main_module._write_enabled = lambda: True

        # Make the update request
        request_payload = {k: v for k, v in update_data.items() if v is not None}
        request_payload["dry_run"] = False

        resp = client.put(f"/api/manage/plan/{plan_id}", json=request_payload)

        # Verify response
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        result = resp.json()
        assert "plan" in result, "Response should contain 'plan' key"

        updated_plan = result["plan"]

        # Property: All non-None fields in update_data should be reflected in the result
        for field, value in update_data.items():
            if value is not None:
                assert field in updated_plan, f"Field '{field}' should be in updated plan"
                assert (
                    updated_plan[field] == value
                ), f"Field '{field}' should have value '{value}', got '{updated_plan[field]}'"

        # Property: Fields not in update_data should preserve original values
        if update_data.get("name") is None:
            assert updated_plan["name"] == original_plan["name"], "Unchanged name should preserve original value"

        if update_data.get("description") is None:
            assert (
                updated_plan["description"] == original_plan["description"]
            ), "Unchanged description should preserve original value"

        if update_data.get("milestone_id") is None:
            assert (
                updated_plan["milestone_id"] == original_plan["milestone_id"]
            ), "Unchanged milestone_id should preserve original value"


class TestPlanUpdateValidation(unittest.TestCase):
    """
    Property-based tests for plan update validation.

    **Feature: testrail-dashboard, Property 26: Plan update validation**
    **Validates: Requirements 11.5**

    For any plan update request with empty required fields, the system should
    reject the update and return a validation error.
    """

    @settings(max_examples=100, deadline=None)
    @given(
        plan_id=st.integers(min_value=1, max_value=10000),
    )
    def test_plan_update_rejects_empty_name(self, plan_id):
        """
        **Feature: testrail-dashboard, Property 26: Plan update validation**
        **Validates: Requirements 11.5**

        For any plan update request with empty name field, the system should
        reject the update and return a validation error.
        """
        client = TestClient(main.app)

        # Try to update with empty name (whitespace only)
        empty_names = ["", "   ", "\t", "\n", "  \t\n  "]

        for empty_name in empty_names:
            resp = client.put(f"/api/manage/plan/{plan_id}", json={"name": empty_name, "dry_run": False})

            # Should return validation error (422 for Pydantic validation)
            assert resp.status_code == 422, f"Empty name '{repr(empty_name)}' should return 422, got {resp.status_code}"


class TestRunUpdateProperties(unittest.TestCase):
    """
    Property-based tests for run update operations.

    **Feature: testrail-dashboard, Property 29: Run update field persistence**
    **Validates: Requirements 13.2**

    For any run update request with non-null fields, the updated run should
    reflect the new values for those fields while preserving unchanged fields.
    """

    @settings(max_examples=100, deadline=None)
    @given(
        run_id=st.integers(min_value=1, max_value=10000),
        update_data=gen_run_update_data(),
    )
    def test_run_update_field_persistence(self, run_id, update_data):
        """
        **Feature: testrail-dashboard, Property 29: Run update field persistence**
        **Validates: Requirements 13.2**

        For any run update request with non-null fields, the updated run should
        reflect the new values for those fields while preserving unchanged fields.
        """
        client = TestClient(main.app)

        # Create a fake client that tracks what was sent
        fake = types.SimpleNamespace()
        called = {}

        # Original run data (simulating existing run)
        original_run = {
            "id": run_id,
            "name": "Original Run Name",
            "description": "Original Description",
            "refs": "ORIG-123",
            "suite_id": 1,
            "is_completed": False,
        }

        def update_run(rid, payload):
            called["run_id"] = rid
            called["payload"] = payload

            # Simulate TestRail behavior: merge update with original
            updated = original_run.copy()
            updated.update(payload)
            return updated

        fake.update_run = update_run

        # Patch the client
        import app.main as main_module

        main_module._make_client = lambda: fake
        main_module._write_enabled = lambda: True

        # Make the update request
        request_payload = {k: v for k, v in update_data.items() if v is not None}
        request_payload["dry_run"] = False

        resp = client.put(f"/api/manage/run/{run_id}", json=request_payload)

        # Verify response
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        result = resp.json()
        assert "run" in result, "Response should contain 'run' key"

        updated_run = result["run"]

        # Property: All non-None fields in update_data should be reflected in the result
        for field, value in update_data.items():
            if value is not None:
                assert field in updated_run, f"Field '{field}' should be in updated run"
                assert (
                    updated_run[field] == value
                ), f"Field '{field}' should have value '{value}', got '{updated_run[field]}'"

        # Property: Fields not in update_data should preserve original values
        if update_data.get("name") is None:
            assert updated_run["name"] == original_run["name"], "Unchanged name should preserve original value"

        if update_data.get("description") is None:
            assert (
                updated_run["description"] == original_run["description"]
            ), "Unchanged description should preserve original value"

        if update_data.get("refs") is None:
            assert updated_run["refs"] == original_run["refs"], "Unchanged refs should preserve original value"


class TestRunUpdateValidation(unittest.TestCase):
    """
    Property-based tests for run update validation.

    **Feature: testrail-dashboard, Property 30: Run update validation**
    **Validates: Requirements 13.5**

    For any run update request with empty required fields, the system should
    reject the update and return a validation error.
    """

    @settings(max_examples=100, deadline=None)
    @given(
        run_id=st.integers(min_value=1, max_value=10000),
    )
    def test_run_update_rejects_empty_name(self, run_id):
        """
        **Feature: testrail-dashboard, Property 30: Run update validation**
        **Validates: Requirements 13.5**

        For any run update request with empty name field, the system should
        reject the update and return a validation error.
        """
        client = TestClient(main.app)

        # Try to update with empty name (whitespace only)
        empty_names = ["", "   ", "\t", "\n", "  \t\n  "]

        for empty_name in empty_names:
            resp = client.put(f"/api/manage/run/{run_id}", json={"name": empty_name, "dry_run": False})

            # Should return validation error (422 for Pydantic validation)
            assert resp.status_code == 422, f"Empty name '{repr(empty_name)}' should return 422, got {resp.status_code}"


class TestCaseUpdateProperties(unittest.TestCase):
    """
    Property-based tests for case update operations.

    **Feature: testrail-dashboard, Property 33: Case update field persistence**
    **Validates: Requirements 15.2**

    For any case update request with non-null fields, the updated case should
    reflect the new values for those fields while preserving unchanged fields.
    """

    @settings(max_examples=100, deadline=None)
    @given(
        case_id=st.integers(min_value=1, max_value=10000),
        update_data=gen_case_update_data(),
    )
    def test_case_update_field_persistence(self, case_id, update_data):
        """
        **Feature: testrail-dashboard, Property 33: Case update field persistence**
        **Validates: Requirements 15.2**

        For any case update request with non-null fields, the updated case should
        reflect the new values for those fields while preserving unchanged fields.
        """
        client = TestClient(main.app)

        # Create a fake client that tracks what was sent
        fake = types.SimpleNamespace()
        called = {}

        # Original case data (simulating existing case)
        original_case = {
            "id": case_id,
            "title": "Original Case Title",
            "refs": "ORIG-456",
            "custom_testrail_bdd_scenario": [{"content": "Original BDD"}],
            "section_id": 1,
        }

        def update_case(cid, payload):
            called["case_id"] = cid
            called["payload"] = payload

            # Simulate TestRail behavior: merge update with original
            updated = original_case.copy()
            updated.update(payload)
            return updated

        fake.update_case = update_case

        # Patch the client
        import app.main as main_module

        main_module._make_client = lambda: fake
        main_module._write_enabled = lambda: True

        # Make the update request
        request_payload = {k: v for k, v in update_data.items() if v is not None}
        request_payload["dry_run"] = False

        resp = client.put(f"/api/manage/case/{case_id}", json=request_payload)

        # Verify response
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        result = resp.json()
        assert "case" in result, "Response should contain 'case' key"

        updated_case = result["case"]

        # Property: All non-None fields in update_data should be reflected in the result
        # (except bdd_scenarios which gets transformed to custom_testrail_bdd_scenario)
        for field, value in update_data.items():
            if value is not None:
                if field == "bdd_scenarios":
                    # BDD scenarios get transformed
                    if value.strip():  # Only if non-empty
                        assert "custom_testrail_bdd_scenario" in updated_case, "BDD scenarios should be in updated case"
                else:
                    assert field in updated_case, f"Field '{field}' should be in updated case"
                    assert (
                        updated_case[field] == value
                    ), f"Field '{field}' should have value '{value}', got '{updated_case[field]}'"

        # Property: Fields not in update_data should preserve original values
        if update_data.get("title") is None:
            assert updated_case["title"] == original_case["title"], "Unchanged title should preserve original value"

        if update_data.get("refs") is None:
            assert updated_case["refs"] == original_case["refs"], "Unchanged refs should preserve original value"


class TestCaseUpdateValidation(unittest.TestCase):
    """
    Property-based tests for case update validation.

    **Feature: testrail-dashboard, Property 34: Case update validation**
    **Validates: Requirements 15.5**

    For any case update request with empty title field, the system should
    reject the update and return a validation error.
    """

    @settings(max_examples=100, deadline=None)
    @given(
        case_id=st.integers(min_value=1, max_value=10000),
    )
    def test_case_update_rejects_empty_title(self, case_id):
        """
        **Feature: testrail-dashboard, Property 34: Case update validation**
        **Validates: Requirements 15.5**

        For any case update request with empty title field, the system should
        reject the update and return a validation error.
        """
        client = TestClient(main.app)

        # Try to update with empty title (whitespace only)
        empty_titles = ["", "   ", "\t", "\n", "  \t\n  "]

        for empty_title in empty_titles:
            resp = client.put(f"/api/manage/case/{case_id}", json={"title": empty_title, "dry_run": False})

            # Should return validation error (422 for Pydantic validation)
            assert (
                resp.status_code == 422
            ), f"Empty title '{repr(empty_title)}' should return 422, got {resp.status_code}"


class TestUpdateEndpointsUnit(unittest.TestCase):
    """Unit tests for update endpoints covering specific scenarios."""

    def test_update_plan_with_valid_data_returns_updated_entity(self):
        """Test that updating a plan with valid data returns the updated entity."""
        client = TestClient(main.app)

        fake = types.SimpleNamespace()

        def update_plan(plan_id, payload):
            return {
                "id": plan_id,
                "name": payload.get("name", "Original"),
                "description": payload.get("description", "Original Desc"),
                "milestone_id": payload.get("milestone_id", 1),
            }

        fake.update_plan = update_plan

        import app.main as main_module

        main_module._make_client = lambda: fake
        main_module._write_enabled = lambda: True

        resp = client.put("/api/manage/plan/123", json={"name": "Updated Plan", "description": "New description"})

        assert resp.status_code == 200
        result = resp.json()
        assert result["plan"]["name"] == "Updated Plan"
        assert result["plan"]["description"] == "New description"

    def test_update_plan_with_invalid_id_returns_404(self):
        """Test that updating a non-existent plan returns 404."""
        client = TestClient(main.app)

        fake = types.SimpleNamespace()

        def update_plan(plan_id, payload):
            import requests

            response = Mock()
            response.status_code = 404
            raise requests.exceptions.HTTPError(response=response)

        fake.update_plan = update_plan

        import app.main as main_module

        main_module._make_client = lambda: fake
        main_module._write_enabled = lambda: True

        resp = client.put("/api/manage/plan/99999", json={"name": "Updated Plan"})

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_update_plan_with_no_fields_returns_validation_error(self):
        """Test that updating with no fields returns validation error."""
        client = TestClient(main.app)

        resp = client.put("/api/manage/plan/123", json={"dry_run": False})

        assert resp.status_code == 400
        assert "at least one field" in resp.json()["detail"].lower()

    def test_update_plan_dry_run_returns_preview(self):
        """Test that dry_run mode returns preview without making changes."""
        client = TestClient(main.app)

        resp = client.put("/api/manage/plan/123", json={"name": "Test Plan", "dry_run": True})

        assert resp.status_code == 200
        result = resp.json()
        assert result["dry_run"] is True
        assert result["plan_id"] == 123
        assert result["payload"]["name"] == "Test Plan"

    def test_update_plan_partial_update_preserves_unchanged_fields(self):
        """Test that partial updates preserve unchanged fields."""
        client = TestClient(main.app)

        fake = types.SimpleNamespace()

        original = {
            "id": 123,
            "name": "Original Name",
            "description": "Original Description",
            "milestone_id": 42,
        }

        def update_plan(plan_id, payload):
            updated = original.copy()
            updated.update(payload)
            return updated

        fake.update_plan = update_plan

        import app.main as main_module

        main_module._make_client = lambda: fake
        main_module._write_enabled = lambda: True

        # Only update name
        resp = client.put("/api/manage/plan/123", json={"name": "New Name"})

        assert resp.status_code == 200
        result = resp.json()
        assert result["plan"]["name"] == "New Name"
        assert result["plan"]["description"] == "Original Description"
        assert result["plan"]["milestone_id"] == 42

    def test_update_run_with_valid_data_returns_updated_entity(self):
        """Test that updating a run with valid data returns the updated entity."""
        client = TestClient(main.app)

        fake = types.SimpleNamespace()

        def update_run(run_id, payload):
            return {
                "id": run_id,
                "name": payload.get("name", "Original"),
                "description": payload.get("description", "Original Desc"),
                "refs": payload.get("refs", ""),
            }

        fake.update_run = update_run

        import app.main as main_module

        main_module._make_client = lambda: fake
        main_module._write_enabled = lambda: True

        resp = client.put("/api/manage/run/456", json={"name": "Updated Run", "refs": "JIRA-123"})

        assert resp.status_code == 200
        result = resp.json()
        assert result["run"]["name"] == "Updated Run"
        assert result["run"]["refs"] == "JIRA-123"

    def test_update_run_with_invalid_id_returns_404(self):
        """Test that updating a non-existent run returns 404."""
        client = TestClient(main.app)

        fake = types.SimpleNamespace()

        def update_run(run_id, payload):
            import requests

            response = Mock()
            response.status_code = 404
            raise requests.exceptions.HTTPError(response=response)

        fake.update_run = update_run

        import app.main as main_module

        main_module._make_client = lambda: fake
        main_module._write_enabled = lambda: True

        resp = client.put("/api/manage/run/99999", json={"name": "Updated Run"})

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_update_case_with_valid_data_returns_updated_entity(self):
        """Test that updating a case with valid data returns the updated entity."""
        client = TestClient(main.app)

        fake = types.SimpleNamespace()

        def update_case(case_id, payload):
            return {
                "id": case_id,
                "title": payload.get("title", "Original"),
                "refs": payload.get("refs", ""),
                "custom_testrail_bdd_scenario": payload.get("custom_testrail_bdd_scenario", []),
            }

        fake.update_case = update_case

        import app.main as main_module

        main_module._make_client = lambda: fake
        main_module._write_enabled = lambda: True

        resp = client.put("/api/manage/case/789", json={"title": "Updated Case", "refs": "TEST-456"})

        assert resp.status_code == 200
        result = resp.json()
        assert result["case"]["title"] == "Updated Case"
        assert result["case"]["refs"] == "TEST-456"

    def test_update_case_with_invalid_id_returns_404(self):
        """Test that updating a non-existent case returns 404."""
        client = TestClient(main.app)

        fake = types.SimpleNamespace()

        def update_case(case_id, payload):
            import requests

            response = Mock()
            response.status_code = 404
            raise requests.exceptions.HTTPError(response=response)

        fake.update_case = update_case

        import app.main as main_module

        main_module._make_client = lambda: fake
        main_module._write_enabled = lambda: True

        resp = client.put("/api/manage/case/99999", json={"title": "Updated Case"})

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


if __name__ == "__main__":
    unittest.main()
