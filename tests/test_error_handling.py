"""
Unit tests for error handling in dashboard endpoints and statistics calculations.

This module tests error handling for:
- API failure handling
- Invalid parameter handling
- Division by zero handling
- Missing field handling
"""

import unittest
from unittest.mock import Mock, patch

import requests
from fastapi.testclient import TestClient

from app.dashboard_stats import (
    calculate_completion_rate,
    calculate_pass_rate,
    calculate_plan_statistics,
    calculate_run_statistics,
    calculate_status_distribution,
)
from app.main import app


class TestAPIFailureHandling(unittest.TestCase):
    """Test API failure handling in dashboard endpoints."""

    def test_plans_endpoint_handles_timeout(self):
        """Plans endpoint should handle API timeout gracefully."""
        from app.main import _dashboard_plans_cache

        _dashboard_plans_cache.clear()
        client = TestClient(app)

        with patch("app.main._make_client") as mock_make_client:
            mock_tr_client = Mock()
            mock_make_client.return_value = mock_tr_client
            mock_tr_client.get_plans_for_project.side_effect = requests.exceptions.Timeout(
                "Request timed out"
            )

            response = client.get("/api/dashboard/plans?project=1")
            self.assertEqual(response.status_code, 504)
            self.assertIn("timed out", response.json()["detail"].lower())

    def test_plans_endpoint_handles_connection_error(self):
        """Plans endpoint should handle connection errors gracefully."""
        from app.main import _dashboard_plans_cache

        _dashboard_plans_cache.clear()
        client = TestClient(app)

        with patch("app.main._make_client") as mock_make_client:
            mock_tr_client = Mock()
            mock_make_client.return_value = mock_tr_client
            mock_tr_client.get_plans_for_project.side_effect = (
                requests.exceptions.ConnectionError("Connection failed")
            )

            response = client.get("/api/dashboard/plans?project=1")
            self.assertEqual(response.status_code, 502)
            self.assertIn("connect", response.json()["detail"].lower())

    def test_plan_detail_endpoint_handles_timeout(self):
        """Plan detail endpoint should handle API timeout gracefully."""
        from app.main import _dashboard_plan_detail_cache

        _dashboard_plan_detail_cache.clear()
        client = TestClient(app)

        with patch("app.main._make_client") as mock_make_client:
            mock_tr_client = Mock()
            mock_make_client.return_value = mock_tr_client

            with patch(
                "app.dashboard_stats.calculate_plan_statistics"
            ) as mock_calc_stats:
                mock_calc_stats.side_effect = requests.exceptions.Timeout(
                    "Request timed out"
                )

                response = client.get("/api/dashboard/plan/1")
                self.assertEqual(response.status_code, 504)
                self.assertIn("timed out", response.json()["detail"].lower())

    def test_runs_endpoint_handles_connection_error(self):
        """Runs endpoint should handle connection errors gracefully."""
        from app.main import _dashboard_stats_cache

        _dashboard_stats_cache.clear()
        client = TestClient(app)

        with patch("app.main._make_client") as mock_make_client:
            mock_tr_client = Mock()
            mock_make_client.return_value = mock_tr_client
            mock_tr_client.get_plan.side_effect = requests.exceptions.ConnectionError(
                "Connection failed"
            )

            response = client.get("/api/dashboard/runs/1")
            self.assertEqual(response.status_code, 502)
            self.assertIn("connect", response.json()["detail"].lower())

    def test_plans_endpoint_handles_invalid_response_type(self):
        """Plans endpoint should handle invalid response data types."""
        from app.main import _dashboard_plans_cache

        _dashboard_plans_cache.clear()
        client = TestClient(app)

        with patch("app.main._make_client") as mock_make_client:
            mock_tr_client = Mock()
            mock_make_client.return_value = mock_tr_client
            # Return invalid type (string instead of list)
            mock_tr_client.get_plans_for_project.return_value = "invalid"

            response = client.get("/api/dashboard/plans?project=1")
            self.assertEqual(response.status_code, 500)
            self.assertIn("Invalid response", response.json()["detail"])


class TestInvalidParameterHandling(unittest.TestCase):
    """Test invalid parameter handling in dashboard endpoints."""

    def test_plans_endpoint_rejects_negative_project_id(self):
        """Plans endpoint should reject negative project IDs."""
        client = TestClient(app)
        response = client.get("/api/dashboard/plans?project=-1")
        self.assertEqual(response.status_code, 400)
        self.assertIn("positive", response.json()["detail"].lower())

    def test_plans_endpoint_rejects_negative_offset(self):
        """Plans endpoint should reject negative offset."""
        client = TestClient(app)
        response = client.get("/api/dashboard/plans?project=1&offset=-5")
        self.assertEqual(response.status_code, 400)
        self.assertIn("non-negative", response.json()["detail"].lower())

    def test_plans_endpoint_rejects_invalid_is_completed(self):
        """Plans endpoint should reject invalid is_completed values."""
        client = TestClient(app)
        response = client.get("/api/dashboard/plans?project=1&is_completed=5")
        self.assertEqual(response.status_code, 400)
        self.assertIn("0 or 1", response.json()["detail"])

    def test_plans_endpoint_rejects_negative_created_after(self):
        """Plans endpoint should reject negative created_after timestamp."""
        client = TestClient(app)
        response = client.get("/api/dashboard/plans?project=1&created_after=-100")
        self.assertEqual(response.status_code, 400)
        self.assertIn("non-negative", response.json()["detail"].lower())

    def test_plans_endpoint_rejects_invalid_date_range(self):
        """Plans endpoint should reject invalid date ranges."""
        client = TestClient(app)
        response = client.get(
            "/api/dashboard/plans?project=1&created_after=2000000000&created_before=1000000000"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("less than or equal", response.json()["detail"])

    def test_plan_detail_endpoint_rejects_negative_plan_id(self):
        """Plan detail endpoint should reject negative plan IDs."""
        client = TestClient(app)
        response = client.get("/api/dashboard/plan/-1")
        self.assertEqual(response.status_code, 400)
        self.assertIn("positive", response.json()["detail"].lower())

    def test_runs_endpoint_rejects_negative_plan_id(self):
        """Runs endpoint should reject negative plan IDs."""
        client = TestClient(app)
        response = client.get("/api/dashboard/runs/-1")
        self.assertEqual(response.status_code, 400)
        self.assertIn("positive", response.json()["detail"].lower())

    def test_plans_endpoint_caps_limit_at_25(self):
        """Plans endpoint should cap limit parameter at 25."""
        from app.main import _dashboard_plans_cache

        _dashboard_plans_cache.clear()
        client = TestClient(app)

        with patch("app.main._make_client") as mock_make_client:
            mock_tr_client = Mock()
            mock_make_client.return_value = mock_tr_client
            mock_tr_client.get_plans_for_project.return_value = []

            response = client.get("/api/dashboard/plans?project=1&limit=500")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            # Limit should be capped at 25
            self.assertEqual(data["limit"], 25)


class TestDivisionByZeroHandling(unittest.TestCase):
    """Test division by zero handling in statistics calculations."""

    def test_pass_rate_with_no_tests(self):
        """Pass rate should return 0.0 when there are no tests."""
        distribution = {}
        result = calculate_pass_rate(distribution)
        self.assertEqual(result, 0.0)

    def test_pass_rate_with_all_untested(self):
        """Pass rate should return 0.0 when all tests are untested."""
        distribution = {"Untested": 10}
        result = calculate_pass_rate(distribution)
        self.assertEqual(result, 0.0)

    def test_pass_rate_with_no_executed_tests(self):
        """Pass rate should return 0.0 when no tests are executed."""
        distribution = {"Untested": 5, "Passed": 0, "Failed": 0}
        result = calculate_pass_rate(distribution)
        self.assertEqual(result, 0.0)

    def test_completion_rate_with_no_tests(self):
        """Completion rate should return 0.0 when there are no tests."""
        distribution = {}
        result = calculate_completion_rate(distribution)
        self.assertEqual(result, 0.0)

    def test_completion_rate_with_zero_total(self):
        """Completion rate should handle zero total gracefully."""
        distribution = {"Passed": 0, "Failed": 0, "Untested": 0}
        result = calculate_completion_rate(distribution)
        self.assertEqual(result, 0.0)

    def test_pass_rate_with_valid_data(self):
        """Pass rate should calculate correctly with valid data."""
        distribution = {"Passed": 8, "Failed": 2, "Untested": 0}
        result = calculate_pass_rate(distribution)
        self.assertEqual(result, 80.0)

    def test_completion_rate_with_valid_data(self):
        """Completion rate should calculate correctly with valid data."""
        distribution = {"Passed": 5, "Failed": 3, "Untested": 2}
        result = calculate_completion_rate(distribution)
        self.assertEqual(result, 80.0)


class TestMissingFieldHandling(unittest.TestCase):
    """Test missing field handling in statistics calculations."""

    def test_status_distribution_with_missing_status_id(self):
        """Status distribution should handle missing status_id fields."""
        results = [
            {"status_id": 1},
            {},  # Missing status_id
            {"status_id": 5},
        ]
        distribution = calculate_status_distribution(results)
        self.assertEqual(distribution["Passed"], 1)
        self.assertEqual(distribution["Untested"], 1)
        self.assertEqual(distribution["Failed"], 1)

    def test_status_distribution_with_null_status_id(self):
        """Status distribution should handle null status_id fields."""
        results = [
            {"status_id": 1},
            {"status_id": None},
            {"status_id": 5},
        ]
        distribution = calculate_status_distribution(results)
        self.assertEqual(distribution["Passed"], 1)
        self.assertEqual(distribution["Untested"], 1)
        self.assertEqual(distribution["Failed"], 1)

    def test_status_distribution_with_unknown_status_id(self):
        """Status distribution should handle unknown status IDs."""
        results = [
            {"status_id": 1},
            {"status_id": 999},  # Unknown status
            {"status_id": 5},
        ]
        distribution = calculate_status_distribution(results)
        self.assertEqual(distribution["Passed"], 1)
        self.assertEqual(distribution["Unknown"], 1)
        self.assertEqual(distribution["Failed"], 1)

    def test_status_distribution_with_non_dict_results(self):
        """Status distribution should skip non-dict results."""
        results = [
            {"status_id": 1},
            "invalid",  # Non-dict
            {"status_id": 5},
            None,  # Non-dict
        ]
        distribution = calculate_status_distribution(results)
        self.assertEqual(distribution["Passed"], 1)
        self.assertEqual(distribution["Failed"], 1)
        self.assertEqual(len(distribution), 2)

    def test_status_distribution_with_invalid_list(self):
        """Status distribution should raise error for non-list input."""
        with self.assertRaises(ValueError):
            calculate_status_distribution("not a list")

    def test_pass_rate_with_non_dict_input(self):
        """Pass rate should raise error for non-dict input."""
        with self.assertRaises(ValueError):
            calculate_pass_rate("not a dict")

    def test_completion_rate_with_non_dict_input(self):
        """Completion rate should raise error for non-dict input."""
        with self.assertRaises(ValueError):
            calculate_completion_rate("not a dict")

    def test_pass_rate_with_non_integer_counts(self):
        """Pass rate should handle non-integer count values."""
        distribution = {"Passed": "5", "Failed": "3", "Untested": "2"}
        # Should not raise, should handle gracefully
        result = calculate_pass_rate(distribution)
        # String values are converted to int: 5 passed out of 8 executed = 62.5%
        self.assertAlmostEqual(result, 62.5, places=1)
    
    def test_pass_rate_with_invalid_string_counts(self):
        """Pass rate should handle invalid string values gracefully."""
        distribution = {"Passed": "invalid", "Failed": 3, "Untested": 2}
        # Should not raise, should return 0.0 for invalid data
        result = calculate_pass_rate(distribution)
        # Invalid strings are treated as 0
        self.assertEqual(result, 0.0)

    def test_run_statistics_with_invalid_run_id(self):
        """Run statistics should raise error for invalid run_id."""
        mock_client = Mock()
        with self.assertRaises(ValueError):
            calculate_run_statistics(-1, mock_client)

    def test_run_statistics_with_none_client(self):
        """Run statistics should raise error for None client."""
        with self.assertRaises(ValueError):
            calculate_run_statistics(1, None)

    def test_plan_statistics_with_invalid_plan_id(self):
        """Plan statistics should raise error for invalid plan_id."""
        mock_client = Mock()
        with self.assertRaises(ValueError):
            calculate_plan_statistics(0, mock_client)

    def test_plan_statistics_with_none_client(self):
        """Plan statistics should raise error for None client."""
        with self.assertRaises(ValueError):
            calculate_plan_statistics(1, None)

    def test_plan_statistics_with_missing_plan_fields(self):
        """Plan statistics should handle missing plan fields gracefully."""
        mock_client = Mock()
        # Plan with missing fields
        mock_client.get_plan.return_value = {
            "id": 1,
            # Missing name, created_on, is_completed, etc.
            "entries": [],
        }

        stats = calculate_plan_statistics(1, mock_client)
        self.assertEqual(stats.plan_id, 1)
        self.assertEqual(stats.plan_name, "Plan 1")  # Default name
        self.assertEqual(stats.created_on, 0)  # Default value
        self.assertEqual(stats.is_completed, False)  # Default value

    def test_run_statistics_with_empty_tests(self):
        """Run statistics should handle empty test list."""
        mock_client = Mock()
        mock_client.get_tests_for_run.return_value = []

        stats = calculate_run_statistics(1, mock_client)
        self.assertEqual(stats.run_id, 1)
        self.assertEqual(stats.total_tests, 0)
        self.assertEqual(stats.pass_rate, 0.0)
        self.assertEqual(stats.completion_rate, 0.0)

    def test_plans_endpoint_handles_malformed_plan_data(self):
        """Plans endpoint should handle malformed plan data gracefully."""
        from app.main import _dashboard_plans_cache

        _dashboard_plans_cache.clear()
        client = TestClient(app)

        with patch("app.main._make_client") as mock_make_client:
            mock_tr_client = Mock()
            mock_make_client.return_value = mock_tr_client
            # Return plans with missing/invalid fields
            mock_tr_client.get_plans_for_project.return_value = [
                {"id": 1, "name": "Valid Plan", "created_on": 1234567890},
                {"id": 2},  # Missing name and created_on
                "invalid",  # Not a dict
                {"name": "No ID"},  # Missing ID
            ]

            with patch(
                "app.dashboard_stats.calculate_plan_statistics"
            ) as mock_calc_stats:
                from app.dashboard_stats import PlanStatistics

                def create_stats(plan_id, client):
                    return PlanStatistics(
                        plan_id=plan_id,
                        plan_name=f"Plan {plan_id}",
                        created_on=1234567890,
                        is_completed=False,
                        updated_on=None,
                        total_runs=0,
                        total_tests=0,
                        status_distribution={},
                        pass_rate=0.0,
                        completion_rate=0.0,
                        failed_count=0,
                        blocked_count=0,
                        untested_count=0,
                    )

                mock_calc_stats.side_effect = create_stats

                response = client.get("/api/dashboard/plans?project=1")
                self.assertEqual(response.status_code, 200)
                data = response.json()
                # Should only include valid plans (those with IDs)
                self.assertEqual(len(data["plans"]), 2)


if __name__ == "__main__":
    unittest.main()
