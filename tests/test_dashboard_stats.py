"""
Tests for dashboard statistics calculation module.

This module contains both property-based tests and unit tests for the
dashboard statistics functions.
"""

import unittest
from unittest.mock import Mock

from hypothesis import given, settings
from hypothesis import strategies as st

from app.dashboard_stats import (
    PlanStatistics,
    RunStatistics,
    calculate_completion_rate,
    calculate_pass_rate,
    calculate_plan_statistics,
    calculate_run_statistics,
    calculate_status_distribution,
)
from testrail_client import TestRailClient


# Hypothesis strategies for generating test data
@st.composite
def gen_status_distribution(draw):
    """Generate a valid status distribution dictionary."""
    statuses = ["Passed", "Failed", "Blocked", "Untested", "Retest"]
    distribution = {}
    for status in statuses:
        # Generate counts between 0 and 100
        count = draw(st.integers(min_value=0, max_value=100))
        if count > 0:
            distribution[status] = count
    return distribution


@st.composite
def gen_test_results(draw):
    """Generate a list of test result dictionaries."""
    # Status IDs: 1=Passed, 2=Blocked, 3=Untested, 4=Retest, 5=Failed
    status_ids = [1, 2, 3, 4, 5, None]
    num_results = draw(st.integers(min_value=0, max_value=50))
    results = []
    for _ in range(num_results):
        status_id = draw(st.sampled_from(status_ids))
        results.append({"status_id": status_id})
    return results


class TestPassRateCalculation(unittest.TestCase):
    """
    **Feature: testrail-dashboard, Property 4: Pass rate calculation correctness**
    **Validates: Requirements 1.4, 2.4**
    """

    @settings(max_examples=100)
    @given(distribution=gen_status_distribution())
    def test_pass_rate_is_between_0_and_100(self, distribution):
        """Pass rate should always be between 0 and 100."""
        pass_rate = calculate_pass_rate(distribution)
        self.assertGreaterEqual(pass_rate, 0.0)
        self.assertLessEqual(pass_rate, 100.0)

    @settings(max_examples=100)
    @given(distribution=gen_status_distribution())
    def test_pass_rate_formula_correctness(self, distribution):
        """Pass rate should equal (passed / executed) * 100."""
        total = sum(distribution.values())
        untested = distribution.get("Untested", 0)
        executed = total - untested
        passed = distribution.get("Passed", 0)

        pass_rate = calculate_pass_rate(distribution)

        if executed == 0:
            self.assertEqual(pass_rate, 0.0)
        else:
            expected = (passed / executed) * 100.0
            self.assertAlmostEqual(pass_rate, expected, places=5)


class TestStatusDistribution(unittest.TestCase):
    """
    **Feature: testrail-dashboard, Property 5: Status distribution completeness**
    **Validates: Requirements 1.5, 2.5**
    """

    @settings(max_examples=100)
    @given(results=gen_test_results())
    def test_distribution_sum_equals_total(self, results):
        """Sum of all status counts should equal total number of tests."""
        distribution = calculate_status_distribution(results)
        total_from_distribution = sum(distribution.values())
        self.assertEqual(total_from_distribution, len(results))

    @settings(max_examples=100)
    @given(results=gen_test_results())
    def test_distribution_contains_all_statuses(self, results):
        """Distribution should account for all test results."""
        distribution = calculate_status_distribution(results)

        # Count expected statuses from results
        expected_counts = {}
        status_map = {
            1: "Passed",
            2: "Blocked",
            3: "Untested",
            4: "Retest",
            5: "Failed",
            None: "Untested",
        }

        for result in results:
            status_id = result.get("status_id")
            status_name = status_map.get(status_id, "Unknown")
            expected_counts[status_name] = expected_counts.get(status_name, 0) + 1

        # Verify distribution matches expected counts
        for status, count in expected_counts.items():
            self.assertEqual(distribution.get(status, 0), count)


class TestTestCaseCountAggregation(unittest.TestCase):
    """
    **Feature: testrail-dashboard, Property 3: Test case count accuracy**
    **Validates: Requirements 1.3**
    """

    @settings(max_examples=100)
    @given(
        num_runs=st.integers(min_value=1, max_value=10),
        tests_per_run=st.lists(st.integers(min_value=0, max_value=20), min_size=1, max_size=10),
    )
    def test_plan_total_equals_sum_of_runs(self, num_runs, tests_per_run):
        """Total test count for plan should equal sum of test counts across all runs."""
        # Ensure we have the right number of test counts
        tests_per_run = tests_per_run[:num_runs]
        if len(tests_per_run) < num_runs:
            tests_per_run.extend([0] * (num_runs - len(tests_per_run)))

        # Mock client
        mock_client = Mock(spec=TestRailClient)

        # Mock plan data
        plan_data = {
            "id": 1,
            "name": "Test Plan",
            "created_on": 1234567890,
            "is_completed": False,
            "entries": [],
        }

        # Create entries with runs
        for i in range(num_runs):
            entry = {
                "runs": [{"id": i + 1}]
            }
            plan_data["entries"].append(entry)

        mock_client.get_plan.return_value = plan_data

        # Mock test data for each run
        def get_tests_side_effect(run_id):
            # run_id is 1-indexed, tests_per_run is 0-indexed
            num_tests = tests_per_run[run_id - 1]
            return [{"status_id": 1} for _ in range(num_tests)]

        mock_client.get_tests_for_run.side_effect = get_tests_side_effect

        # Calculate plan statistics
        stats = calculate_plan_statistics(1, mock_client)

        # Verify total equals sum
        expected_total = sum(tests_per_run)
        self.assertEqual(stats.total_tests, expected_total)


class TestPlanMetadataCompleteness(unittest.TestCase):
    """
    **Feature: testrail-dashboard, Property 2: Plan metadata completeness**
    **Validates: Requirements 1.2**
    """

    @settings(max_examples=100)
    @given(
        plan_id=st.integers(min_value=1, max_value=10000),
        plan_name=st.text(min_size=1, max_size=100),
        created_on=st.integers(min_value=1000000000, max_value=2000000000),
        is_completed=st.booleans(),
        updated_on=st.one_of(st.none(), st.integers(min_value=1000000000, max_value=2000000000)),
        num_runs=st.integers(min_value=0, max_value=5),
    )
    def test_plan_statistics_contains_required_metadata(
        self, plan_id, plan_name, created_on, is_completed, updated_on, num_runs
    ):
        """Plan statistics should contain name, creation date, completion status, and last updated timestamp."""
        # Mock client
        mock_client = Mock(spec=TestRailClient)

        # Mock plan data with required metadata
        plan_data = {
            "id": plan_id,
            "name": plan_name,
            "created_on": created_on,
            "is_completed": is_completed,
            "updated_on": updated_on,
            "entries": [],
        }

        # Create entries with runs
        for i in range(num_runs):
            entry = {"runs": [{"id": i + 1}]}
            plan_data["entries"].append(entry)

        mock_client.get_plan.return_value = plan_data

        # Mock test data for each run (empty for this test)
        mock_client.get_tests_for_run.return_value = []

        # Calculate plan statistics
        stats = calculate_plan_statistics(plan_id, mock_client)

        # Verify all required metadata fields are present
        self.assertEqual(stats.plan_id, plan_id)
        self.assertEqual(stats.plan_name, plan_name)
        self.assertEqual(stats.created_on, created_on)
        self.assertEqual(stats.is_completed, is_completed)
        self.assertEqual(stats.updated_on, updated_on)

        # Verify the object has all required attributes
        self.assertTrue(hasattr(stats, "plan_id"))
        self.assertTrue(hasattr(stats, "plan_name"))
        self.assertTrue(hasattr(stats, "created_on"))
        self.assertTrue(hasattr(stats, "is_completed"))
        self.assertTrue(hasattr(stats, "updated_on"))


class TestRunMetadataCompleteness(unittest.TestCase):
    """
    **Feature: testrail-dashboard, Property 7: Run metadata completeness**
    **Validates: Requirements 2.2, 2.3, 2.6**
    """

    @settings(max_examples=100)
    @given(
        run_id=st.integers(min_value=1, max_value=10000),
        run_name=st.text(min_size=1, max_size=100),
        suite_name=st.one_of(st.none(), st.text(min_size=1, max_size=100)),
        is_completed=st.booleans(),
        num_tests=st.integers(min_value=1, max_value=20),  # At least 1 test to have metadata
        updated_on=st.one_of(st.none(), st.integers(min_value=1000000000, max_value=2000000000)),
    )
    def test_run_statistics_contains_required_metadata(
        self, run_id, run_name, suite_name, is_completed, num_tests, updated_on
    ):
        """Run statistics should contain name, suite name, completion status, and total test count."""
        # Mock client
        mock_client = Mock(spec=TestRailClient)

        # Create test data with metadata
        tests = []
        for i in range(num_tests):
            test = {
                "id": i + 1,
                "status_id": 1 if is_completed else None,
                "run_name": run_name,
                "suite_name": suite_name,
                "updated_on": updated_on,
            }
            tests.append(test)

        mock_client.get_tests_for_run.return_value = tests

        # Calculate run statistics
        stats = calculate_run_statistics(run_id, mock_client)

        # Verify all required metadata fields are present
        self.assertEqual(stats.run_id, run_id)
        self.assertIsNotNone(stats.run_name)  # Should always have a name (default or actual)
        self.assertEqual(stats.suite_name, suite_name)
        self.assertEqual(stats.total_tests, num_tests)

        # Verify the object has all required attributes
        self.assertTrue(hasattr(stats, "run_id"))
        self.assertTrue(hasattr(stats, "run_name"))
        self.assertTrue(hasattr(stats, "suite_name"))
        self.assertTrue(hasattr(stats, "is_completed"))
        self.assertTrue(hasattr(stats, "total_tests"))
        self.assertTrue(hasattr(stats, "updated_on"))


class TestEdgeCases(unittest.TestCase):
    """Unit tests for edge cases in statistics calculation."""

    def test_pass_rate_with_zero_executed(self):
        """Pass rate should be 0.0 when no tests are executed."""
        distribution = {"Untested": 10}
        pass_rate = calculate_pass_rate(distribution)
        self.assertEqual(pass_rate, 0.0)

    def test_pass_rate_with_empty_distribution(self):
        """Pass rate should be 0.0 for empty distribution."""
        distribution = {}
        pass_rate = calculate_pass_rate(distribution)
        self.assertEqual(pass_rate, 0.0)

    def test_pass_rate_all_passed(self):
        """Pass rate should be 100.0 when all executed tests passed."""
        distribution = {"Passed": 10, "Untested": 5}
        pass_rate = calculate_pass_rate(distribution)
        self.assertEqual(pass_rate, 100.0)

    def test_pass_rate_all_untested(self):
        """Pass rate should be 0.0 when all tests are untested."""
        distribution = {"Untested": 20}
        pass_rate = calculate_pass_rate(distribution)
        self.assertEqual(pass_rate, 0.0)

    def test_completion_rate_with_zero_total(self):
        """Completion rate should be 0.0 for empty distribution."""
        distribution = {}
        completion_rate = calculate_completion_rate(distribution)
        self.assertEqual(completion_rate, 0.0)

    def test_completion_rate_all_executed(self):
        """Completion rate should be 100.0 when all tests are executed."""
        distribution = {"Passed": 5, "Failed": 3, "Blocked": 2}
        completion_rate = calculate_completion_rate(distribution)
        self.assertEqual(completion_rate, 100.0)

    def test_completion_rate_partial(self):
        """Completion rate should be correct for partial execution."""
        distribution = {"Passed": 5, "Failed": 3, "Untested": 2}
        # 8 executed out of 10 total = 80%
        completion_rate = calculate_completion_rate(distribution)
        self.assertEqual(completion_rate, 80.0)

    def test_status_distribution_empty_results(self):
        """Status distribution should be empty for empty results."""
        distribution = calculate_status_distribution([])
        self.assertEqual(distribution, {})

    def test_status_distribution_with_none_status(self):
        """None status_id should be treated as Untested."""
        results = [
            {"status_id": None},
            {"status_id": None},
            {"status_id": 1},
        ]
        distribution = calculate_status_distribution(results)
        self.assertEqual(distribution.get("Untested"), 2)
        self.assertEqual(distribution.get("Passed"), 1)


if __name__ == "__main__":
    unittest.main()
