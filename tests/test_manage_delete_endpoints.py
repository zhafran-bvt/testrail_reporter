"""
Property-based tests for management delete endpoints.

These tests verify the correctness properties for deleting plans, runs, and cases.
"""

import types
import unittest
from unittest.mock import Mock

from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

import app.main as main
from tests.test_base import BaseAPITestCase


class TestPlanDeletionConfirmation(BaseAPITestCase):
    """
    Property-based tests for plan deletion confirmation.

    **Feature: testrail-dashboard, Property 27: Plan deletion confirmation requirement**
    **Validates: Requirements 12.1**

    For any plan deletion request, a confirmation dialog should be displayed
    before the deletion is executed.

    Note: This property is enforced at the UI level. The API endpoint itself
    does not enforce confirmation - it's the responsibility of the client to
    show a confirmation dialog before calling the delete endpoint.
    """

    @settings(max_examples=100, deadline=None)
    @given(
        plan_id=st.integers(min_value=1, max_value=10000),
    )
    def test_plan_deletion_requires_explicit_call(self, plan_id):
        """
        **Feature: testrail-dashboard, Property 27: Plan deletion confirmation requirement**
        **Validates: Requirements 12.1**

        The API endpoint requires an explicit DELETE request, which should only
        be made after user confirmation in the UI.
        """
        client = TestClient(main.app)

        # Create a fake client
        fake = types.SimpleNamespace()
        deletion_called = {"called": False}

        def delete_plan(pid):
            deletion_called["called"] = True
            deletion_called["plan_id"] = pid
            return {}

        fake.delete_plan = delete_plan

        # Patch the client
        import app.main as main_module

        main_module._make_client = lambda: fake
        main_module._write_enabled = lambda: True

        # Verify that deletion only happens when explicitly called
        # (not on GET, not automatically)
        resp = client.delete(f"/api/manage/plan/{plan_id}")

        # The deletion should have been called
        assert deletion_called["called"], "Deletion should be called when DELETE request is made"
        assert deletion_called["plan_id"] == plan_id, "Correct plan ID should be passed"

        # Response should indicate success
        assert resp.status_code == 200
        result = resp.json()
        assert result["success"] is True
        assert result["plan_id"] == plan_id


class TestPlanDeletionSuccess(BaseAPITestCase):
    """
    Property-based tests for plan deletion success.

    **Feature: testrail-dashboard, Property 28: Plan deletion success removes plan**
    **Validates: Requirements 12.3**

    For any successful plan deletion, the plan should no longer appear in
    subsequent plan list requests.
    """

    @settings(max_examples=100, deadline=None)
    @given(
        plan_id=st.integers(min_value=1, max_value=10000),
    )
    def test_plan_deletion_success_removes_plan(self, plan_id):
        """
        **Feature: testrail-dashboard, Property 28: Plan deletion success removes plan**
        **Validates: Requirements 12.3**

        For any successful plan deletion, the plan should no longer appear in
        subsequent plan list requests.
        """
        client = TestClient(main.app)

        # Create a fake client that simulates plan removal
        fake = types.SimpleNamespace()
        plans_db = {plan_id: {"id": plan_id, "name": f"Plan {plan_id}"}}

        def delete_plan(pid):
            if pid in plans_db:
                del plans_db[pid]
                return {}
            else:
                import requests

                response = Mock()
                response.status_code = 404
                raise requests.exceptions.HTTPError(response=response)

        def get_plans_for_project(project, is_completed=None):
            return list(plans_db.values())

        fake.delete_plan = delete_plan
        fake.get_plans_for_project = get_plans_for_project

        # Patch the client
        import app.main as main_module

        main_module._make_client = lambda: fake
        main_module._write_enabled = lambda: True

        # Verify plan exists before deletion
        assert plan_id in plans_db, "Plan should exist before deletion"

        # Delete the plan
        resp = client.delete(f"/api/manage/plan/{plan_id}")

        # Verify successful deletion
        assert resp.status_code == 200
        result = resp.json()
        assert result["success"] is True

        # Property: Plan should no longer exist after successful deletion
        assert plan_id not in plans_db, "Plan should be removed after successful deletion"

        # Verify plan doesn't appear in subsequent list requests
        remaining_plans = get_plans_for_project(1)
        plan_ids = [p["id"] for p in remaining_plans]
        assert plan_id not in plan_ids, "Deleted plan should not appear in plan list"


class TestRunDeletionConfirmation(BaseAPITestCase):
    """
    Property-based tests for run deletion confirmation.

    **Feature: testrail-dashboard, Property 31: Run deletion confirmation requirement**
    **Validates: Requirements 14.1**

    For any run deletion request, a confirmation dialog should be displayed
    before the deletion is executed.
    """

    @settings(max_examples=100, deadline=None)
    @given(
        run_id=st.integers(min_value=1, max_value=10000),
    )
    def test_run_deletion_requires_explicit_call(self, run_id):
        """
        **Feature: testrail-dashboard, Property 31: Run deletion confirmation requirement**
        **Validates: Requirements 14.1**

        The API endpoint requires an explicit DELETE request, which should only
        be made after user confirmation in the UI.
        """
        client = TestClient(main.app)

        # Create a fake client
        fake = types.SimpleNamespace()
        deletion_called = {"called": False}

        def delete_run(rid):
            deletion_called["called"] = True
            deletion_called["run_id"] = rid
            return {}

        fake.delete_run = delete_run
        fake.get_run = lambda rid: {"id": rid, "plan_id": None}

        # Patch the client
        import app.main as main_module

        main_module._make_client = lambda: fake
        main_module._write_enabled = lambda: True

        # Verify that deletion only happens when explicitly called
        resp = client.delete(f"/api/manage/run/{run_id}")

        # The deletion should have been called
        assert deletion_called["called"], "Deletion should be called when DELETE request is made"
        assert deletion_called["run_id"] == run_id, "Correct run ID should be passed"

        # Response should indicate success
        assert resp.status_code == 200
        result = resp.json()
        assert result["success"] is True
        assert result["run_id"] == run_id


class TestRunDeletionSuccess(BaseAPITestCase):
    """
    Property-based tests for run deletion success.

    **Feature: testrail-dashboard, Property 32: Run deletion success removes run**
    **Validates: Requirements 14.3**

    For any successful run deletion, the run should no longer appear in
    subsequent run list requests for that plan.
    """

    @settings(max_examples=100, deadline=None)
    @given(
        plan_id=st.integers(min_value=1, max_value=10000),
        run_id=st.integers(min_value=1, max_value=10000),
    )
    def test_run_deletion_success_removes_run(self, plan_id, run_id):
        """
        **Feature: testrail-dashboard, Property 32: Run deletion success removes run**
        **Validates: Requirements 14.3**

        For any successful run deletion, the run should no longer appear in
        subsequent run list requests for that plan.
        """
        client = TestClient(main.app)

        # Create a fake client that simulates run removal
        fake = types.SimpleNamespace()
        runs_db = {run_id: {"id": run_id, "name": f"Run {run_id}", "plan_id": plan_id}}

        def delete_run(rid):
            if rid in runs_db:
                del runs_db[rid]
                return {}
            else:
                import requests

                response = Mock()
                response.status_code = 404
                raise requests.exceptions.HTTPError(response=response)

        def get_plan(pid):
            # Return plan with runs
            plan_runs = [r for r in runs_db.values() if r.get("plan_id") == pid]
            return {"id": pid, "name": f"Plan {pid}", "entries": [{"runs": plan_runs}]}

        fake.delete_run = delete_run
        fake.get_plan = get_plan
        fake.get_run = lambda rid: {"id": rid, "plan_id": None}

        # Patch the client
        import app.main as main_module

        main_module._make_client = lambda: fake
        main_module._write_enabled = lambda: True

        # Verify run exists before deletion
        assert run_id in runs_db, "Run should exist before deletion"

        # Delete the run
        resp = client.delete(f"/api/manage/run/{run_id}")

        # Verify successful deletion
        assert resp.status_code == 200
        result = resp.json()
        assert result["success"] is True

        # Property: Run should no longer exist after successful deletion
        assert run_id not in runs_db, "Run should be removed after successful deletion"

        # Verify run doesn't appear in subsequent plan requests
        plan_data = get_plan(plan_id)
        run_ids = []
        for entry in plan_data.get("entries", []):
            for run in entry.get("runs", []):
                run_ids.append(run["id"])
        assert run_id not in run_ids, "Deleted run should not appear in plan's run list"


class TestCaseDeletionConfirmation(BaseAPITestCase):
    """
    Property-based tests for case deletion confirmation.

    **Feature: testrail-dashboard, Property 35: Case deletion confirmation requirement**
    **Validates: Requirements 16.1**

    For any case deletion request, a confirmation dialog should be displayed
    before the deletion is executed.
    """

    @settings(max_examples=100, deadline=None)
    @given(
        case_id=st.integers(min_value=1, max_value=10000),
    )
    def test_case_deletion_requires_explicit_call(self, case_id):
        """
        **Feature: testrail-dashboard, Property 35: Case deletion confirmation requirement**
        **Validates: Requirements 16.1**

        The API endpoint requires an explicit DELETE request, which should only
        be made after user confirmation in the UI.
        """
        client = TestClient(main.app)

        # Create a fake client
        fake = types.SimpleNamespace()
        deletion_called = {"called": False}

        def delete_case(cid):
            deletion_called["called"] = True
            deletion_called["case_id"] = cid
            return {}

        fake.delete_case = delete_case

        # Patch the client
        import app.main as main_module

        main_module._make_client = lambda: fake
        main_module._write_enabled = lambda: True

        # Verify that deletion only happens when explicitly called
        resp = client.delete(f"/api/manage/case/{case_id}")

        # The deletion should have been called
        assert deletion_called["called"], "Deletion should be called when DELETE request is made"
        assert deletion_called["case_id"] == case_id, "Correct case ID should be passed"

        # Response should indicate success
        assert resp.status_code == 200
        result = resp.json()
        assert result["success"] is True
        assert result["case_id"] == case_id


class TestCaseDeletionSuccess(BaseAPITestCase):
    """
    Property-based tests for case deletion success.

    **Feature: testrail-dashboard, Property 36: Case deletion success removes case**
    **Validates: Requirements 16.3**

    For any successful case deletion, the case should no longer appear in
    subsequent case list requests for that section.
    """

    @settings(max_examples=100, deadline=None)
    @given(
        section_id=st.integers(min_value=1, max_value=1000),
        case_id=st.integers(min_value=1, max_value=10000),
    )
    def test_case_deletion_success_removes_case(self, section_id, case_id):
        """
        **Feature: testrail-dashboard, Property 36: Case deletion success removes case**
        **Validates: Requirements 16.3**

        For any successful case deletion, the case should no longer appear in
        subsequent case list requests for that section.
        """
        client = TestClient(main.app)

        # Create a fake client that simulates case removal
        fake = types.SimpleNamespace()
        cases_db = {case_id: {"id": case_id, "title": f"Case {case_id}", "section_id": section_id}}

        def delete_case(cid):
            if cid in cases_db:
                del cases_db[cid]
                return {}
            else:
                import requests

                response = Mock()
                response.status_code = 404
                raise requests.exceptions.HTTPError(response=response)

        def get_cases(project, suite_id=None, section_id=None):
            # Return cases for the section
            if section_id:
                return [c for c in cases_db.values() if c.get("section_id") == section_id]
            return list(cases_db.values())

        fake.delete_case = delete_case
        fake.get_cases = get_cases

        # Patch the client
        import app.main as main_module

        main_module._make_client = lambda: fake
        main_module._write_enabled = lambda: True

        # Verify case exists before deletion
        assert case_id in cases_db, "Case should exist before deletion"

        # Delete the case
        resp = client.delete(f"/api/manage/case/{case_id}")

        # Verify successful deletion
        assert resp.status_code == 200
        result = resp.json()
        assert result["success"] is True

        # Property: Case should no longer exist after successful deletion
        assert case_id not in cases_db, "Case should be removed after successful deletion"

        # Verify case doesn't appear in subsequent section requests
        section_cases = get_cases(1, section_id=section_id)
        case_ids = [c["id"] for c in section_cases]
        assert case_id not in case_ids, "Deleted case should not appear in section's case list"


class TestDeleteEndpointsUnit(BaseAPITestCase):
    """Unit tests for delete endpoints covering specific scenarios."""

    def test_delete_plan_with_valid_id_returns_success(self):
        """Test that deleting a plan with valid ID returns success."""
        client = TestClient(main.app)

        fake = types.SimpleNamespace()

        def delete_plan(plan_id):
            return {}

        fake.delete_plan = delete_plan

        import app.main as main_module

        main_module._make_client = lambda: fake
        main_module._write_enabled = lambda: True

        resp = client.delete("/api/manage/plan/123")

        assert resp.status_code == 200
        result = resp.json()
        assert result["success"] is True
        assert result["plan_id"] == 123
        assert "deleted successfully" in result["message"]

    def test_delete_plan_with_invalid_id_returns_404(self):
        """Test that deleting a non-existent plan returns 404."""
        client = TestClient(main.app)

        fake = types.SimpleNamespace()

        def delete_plan(plan_id):
            import requests

            response = Mock()
            response.status_code = 404
            raise requests.exceptions.HTTPError(response=response)

        fake.delete_plan = delete_plan

        import app.main as main_module

        main_module._make_client = lambda: fake
        main_module._write_enabled = lambda: True

        resp = client.delete("/api/manage/plan/99999")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_delete_plan_dry_run_returns_preview(self):
        """Test that dry_run mode returns preview without deletion."""
        client = TestClient(main.app)

        resp = client.delete("/api/manage/plan/123?dry_run=true")

        assert resp.status_code == 200
        result = resp.json()
        assert result["dry_run"] is True
        assert result["plan_id"] == 123
        assert result["action"] == "delete_plan"

    def test_delete_plan_clears_cache(self):
        """Test that successful deletion clears relevant cache entries."""
        client = TestClient(main.app)

        fake = types.SimpleNamespace()

        def delete_plan(plan_id):
            return {}

        fake.delete_plan = delete_plan

        import app.main as main_module

        main_module._make_client = lambda: fake
        main_module._write_enabled = lambda: True

        # Add some data to caches
        main_module._plans_cache.set(("plans", 1, None), {"test": "data"})
        main_module._dashboard_plans_cache.set(("dashboard_plans", 1), {"test": "data"})

        # Delete plan
        resp = client.delete("/api/manage/plan/123")

        assert resp.status_code == 200

        # Verify caches were cleared
        assert main_module._plans_cache.get(("plans", 1, None)) is None
        assert main_module._dashboard_plans_cache.get(("dashboard_plans", 1)) is None

    def test_delete_run_with_valid_id_returns_success(self):
        """Test that deleting a run with valid ID returns success."""
        client = TestClient(main.app)

        fake = types.SimpleNamespace()

        def delete_run(run_id):
            return {}

        fake.delete_run = delete_run
        fake.get_run = lambda rid: {"id": rid, "plan_id": None}

        import app.main as main_module

        main_module._make_client = lambda: fake
        main_module._write_enabled = lambda: True

        resp = client.delete("/api/manage/run/456")

        assert resp.status_code == 200
        result = resp.json()
        assert result["success"] is True
        assert result["run_id"] == 456
        assert "deleted successfully" in result["message"]

    def test_delete_run_with_invalid_id_returns_404(self):
        """Test that deleting a non-existent run returns 404."""
        client = TestClient(main.app)

        fake = types.SimpleNamespace()

        def delete_run(run_id):
            import requests

            response = Mock()
            response.status_code = 404
            raise requests.exceptions.HTTPError(response=response)

        fake.delete_run = delete_run
        fake.get_run = delete_run

        import app.main as main_module

        main_module._make_client = lambda: fake
        main_module._write_enabled = lambda: True

        resp = client.delete("/api/manage/run/99999")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_delete_run_dry_run_returns_preview(self):
        """Test that dry_run mode returns preview without deletion."""
        client = TestClient(main.app)

        resp = client.delete("/api/manage/run/456?dry_run=true")

        assert resp.status_code == 200
        result = resp.json()
        assert result["dry_run"] is True
        assert result["run_id"] == 456
        assert result["action"] == "delete_run"

    def test_delete_case_with_valid_id_returns_success(self):
        """Test that deleting a case with valid ID returns success."""
        client = TestClient(main.app)

        fake = types.SimpleNamespace()

        def delete_case(case_id):
            return {}

        fake.delete_case = delete_case

        import app.main as main_module

        main_module._make_client = lambda: fake
        main_module._write_enabled = lambda: True

        resp = client.delete("/api/manage/case/789")

        assert resp.status_code == 200
        result = resp.json()
        assert result["success"] is True
        assert result["case_id"] == 789
        assert "deleted successfully" in result["message"]

    def test_delete_case_with_invalid_id_returns_404(self):
        """Test that deleting a non-existent case returns 404."""
        client = TestClient(main.app)

        fake = types.SimpleNamespace()

        def delete_case(case_id):
            import requests

            response = Mock()
            response.status_code = 404
            raise requests.exceptions.HTTPError(response=response)

        fake.delete_case = delete_case

        import app.main as main_module

        main_module._make_client = lambda: fake
        main_module._write_enabled = lambda: True

        resp = client.delete("/api/manage/case/99999")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_delete_case_dry_run_returns_preview(self):
        """Test that dry_run mode returns preview without deletion."""
        client = TestClient(main.app)

        resp = client.delete("/api/manage/case/789?dry_run=true")

        assert resp.status_code == 200
        result = resp.json()
        assert result["dry_run"] is True
        assert result["case_id"] == 789
        assert result["action"] == "delete_case"

    def test_delete_plan_with_negative_id_returns_400(self):
        """Test that deleting with negative ID returns 400."""
        client = TestClient(main.app)

        resp = client.delete("/api/manage/plan/-1")

        assert resp.status_code == 400
        assert "positive" in resp.json()["detail"].lower()

    def test_delete_run_with_negative_id_returns_400(self):
        """Test that deleting with negative ID returns 400."""
        client = TestClient(main.app)

        resp = client.delete("/api/manage/run/0")

        assert resp.status_code == 400
        assert "positive" in resp.json()["detail"].lower()

    def test_delete_case_with_negative_id_returns_400(self):
        """Test that deleting with negative ID returns 400."""
        client = TestClient(main.app)

        resp = client.delete("/api/manage/case/-5")

        assert resp.status_code == 400
        assert "positive" in resp.json()["detail"].lower()


if __name__ == "__main__":
    unittest.main()
