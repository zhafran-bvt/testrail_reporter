"""
Tests for report generation integration from dashboard.

This module contains property-based tests for report generation integration.
"""

import unittest
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st


class TestReportGenerationIntegration(unittest.TestCase):
    """
    **Feature: testrail-dashboard, Property 15: Report generation integration**
    **Validates: Requirements 6.3**
    """

    @settings(max_examples=100, deadline=None)
    @given(
        project_id=st.integers(min_value=1, max_value=100),
        plan_id=st.integers(min_value=1, max_value=10000),
    )
    def test_plan_report_generation_uses_correct_parameters(self, project_id, plan_id):
        """For any plan selected, report generation uses correct parameters."""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)

        # Mock the report generation
        with patch("app.main.generate_report") as mock_generate:
            mock_generate.return_value = f"out/report_{plan_id}.html"

            # Call the synchronous report endpoint (which dashboard uses)
            response = client.get(f"/api/report?project={project_id}&plan={plan_id}")

            # Verify response
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("path", data)
            self.assertIn("url", data)

            # Verify generate_report was called with correct parameters
            mock_generate.assert_called_once()
            call_args = mock_generate.call_args

            # Verify parameters
            self.assertEqual(call_args.kwargs.get("project"), project_id)
            self.assertEqual(call_args.kwargs.get("plan"), plan_id)
            self.assertIsNone(call_args.kwargs.get("run"))

    @settings(max_examples=100, deadline=None)
    @given(
        project_id=st.integers(min_value=1, max_value=100),
        run_id=st.integers(min_value=1, max_value=10000),
    )
    def test_run_report_generation_uses_correct_parameters(self, project_id, run_id):
        """For any run selected, report generation uses correct parameters."""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)

        # Mock the report generation
        with patch("app.main.generate_report") as mock_generate:
            mock_generate.return_value = f"out/report_{run_id}.html"

            # Call the synchronous report endpoint (which dashboard uses)
            response = client.get(f"/api/report?project={project_id}&run={run_id}")

            # Verify response
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("path", data)
            self.assertIn("url", data)

            # Verify generate_report was called with correct parameters
            mock_generate.assert_called_once()
            call_args = mock_generate.call_args

            # Verify parameters
            self.assertEqual(call_args.kwargs.get("project"), project_id)
            self.assertEqual(call_args.kwargs.get("run"), run_id)
            self.assertIsNone(call_args.kwargs.get("plan"))

    @settings(max_examples=100, deadline=None)
    @given(
        project_id=st.integers(min_value=1, max_value=100),
        entity_id=st.integers(min_value=1, max_value=10000),
        is_plan=st.booleans(),
    )
    def test_report_generation_returns_valid_url(self, project_id, entity_id, is_plan):
        """For any plan or run, report generation should return a valid URL."""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)

        # Mock the report generation
        with patch("app.main.generate_report") as mock_generate:
            mock_generate.return_value = f"out/report_{entity_id}.html"

            # Build request URL
            if is_plan:
                url = f"/api/report?project={project_id}&plan={entity_id}"
            else:
                url = f"/api/report?project={project_id}&run={entity_id}"

            # Call the endpoint
            response = client.get(url)

            # Verify response
            self.assertEqual(response.status_code, 200)
            data = response.json()

            # Verify URL format
            self.assertIn("url", data)
            self.assertTrue(data["url"].startswith("/reports/"))
            self.assertTrue(data["url"].endswith(".html"))

            # Verify path is returned
            self.assertIn("path", data)
            self.assertTrue(data["path"].startswith("out/"))


if __name__ == "__main__":
    unittest.main()


class TestReportGenerationFlow(unittest.TestCase):
    """Integration tests for report generation flow from dashboard."""

    def test_clicking_plan_generates_report_for_that_plan(self):
        """Test that clicking plan report button generates report for that plan."""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)

        project_id = 1
        plan_id = 123

        # Mock the report generation
        with patch("app.main.generate_report") as mock_generate:
            mock_generate.return_value = f"out/report_plan_{plan_id}.html"

            # Simulate clicking the plan report button (calls /api/report)
            response = client.get(f"/api/report?project={project_id}&plan={plan_id}")

            # Verify response
            self.assertEqual(response.status_code, 200)
            data = response.json()

            # Verify report was generated for the correct plan
            mock_generate.assert_called_once()
            call_kwargs = mock_generate.call_args.kwargs
            self.assertEqual(call_kwargs["project"], project_id)
            self.assertEqual(call_kwargs["plan"], plan_id)
            self.assertIsNone(call_kwargs.get("run"))

            # Verify URL is returned
            self.assertIn("url", data)
            self.assertTrue(data["url"].startswith("/reports/"))

    def test_clicking_run_generates_report_for_that_run(self):
        """Test that clicking run report button generates report for that run."""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)

        project_id = 1
        run_id = 456

        # Mock the report generation
        with patch("app.main.generate_report") as mock_generate:
            mock_generate.return_value = f"out/report_run_{run_id}.html"

            # Simulate clicking the run report button (calls /api/report)
            response = client.get(f"/api/report?project={project_id}&run={run_id}")

            # Verify response
            self.assertEqual(response.status_code, 200)
            data = response.json()

            # Verify report was generated for the correct run
            mock_generate.assert_called_once()
            call_kwargs = mock_generate.call_args.kwargs
            self.assertEqual(call_kwargs["project"], project_id)
            self.assertEqual(call_kwargs["run"], run_id)
            self.assertIsNone(call_kwargs.get("plan"))

            # Verify URL is returned
            self.assertIn("url", data)
            self.assertTrue(data["url"].startswith("/reports/"))

    def test_report_opens_in_new_tab(self):
        """Test that report URL can be opened (simulates opening in new tab)."""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)

        project_id = 1
        plan_id = 789

        # Mock the report generation
        with patch("app.main.generate_report") as mock_generate:
            # Create a mock report file
            report_filename = f"report_plan_{plan_id}.html"
            mock_generate.return_value = f"out/{report_filename}"

            # Generate report
            response = client.get(f"/api/report?project={project_id}&plan={plan_id}")

            self.assertEqual(response.status_code, 200)
            data = response.json()

            # Verify URL format is correct for opening in new tab
            report_url = data["url"]
            self.assertTrue(report_url.startswith("/reports/"))
            self.assertTrue(report_url.endswith(".html"))

            # The URL should be accessible (in real scenario, browser would open this)
            # We verify the URL format is valid
            self.assertIn(report_filename, report_url)

    def test_report_generation_with_error_handling(self):
        """Test that report generation errors result in error responses."""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)

        project_id = 1
        plan_id = 999

        # Mock the report generation to raise an error
        with patch("app.main.generate_report") as mock_generate:
            mock_generate.side_effect = ValueError("Invalid plan ID")

            # Attempt to generate report - exception will propagate as 500
            with self.assertRaises(ValueError):
                client.get(f"/api/report?project={project_id}&plan={plan_id}")

    def test_report_generation_with_api_error(self):
        """Test that TestRail API errors during report generation propagate."""
        import requests
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)

        project_id = 1
        plan_id = 888

        # Mock the report generation to raise API error
        with patch("app.main.generate_report") as mock_generate:
            err_msg = "API connection failed"
            mock_generate.side_effect = requests.exceptions.RequestException(err_msg)

            # Attempt to generate report - exception will propagate
            with self.assertRaises(requests.exceptions.RequestException):
                client.get(f"/api/report?project={project_id}&plan={plan_id}")

    def test_multiple_report_generations(self):
        """Test that multiple reports can be generated sequentially."""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)

        project_id = 1
        plan_ids = [100, 200, 300]

        # Mock the report generation
        with patch("app.main.generate_report") as mock_generate:
            for plan_id in plan_ids:
                mock_generate.return_value = f"out/report_plan_{plan_id}.html"

                # Generate report for each plan
                response = client.get(f"/api/report?project={project_id}&plan={plan_id}")

                # Verify each response
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertIn("url", data)
                self.assertIn(f"report_plan_{plan_id}.html", data["url"])

            # Verify all reports were generated
            self.assertEqual(mock_generate.call_count, len(plan_ids))
