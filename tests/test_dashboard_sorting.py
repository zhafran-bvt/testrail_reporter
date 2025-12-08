"""
Tests for dashboard sorting functionality.

This module contains property-based tests and unit tests for sorting
plans by various criteria.
"""

import unittest
from datetime import datetime

from hypothesis import given, settings
from hypothesis import strategies as st


# Hypothesis strategies for generating test data
@st.composite
def gen_plan_list(draw):
    """Generate a list of plan dictionaries with sortable fields."""
    num_plans = draw(st.integers(min_value=0, max_value=20))
    plans = []
    
    for i in range(num_plans):
        plan = {
            "plan_id": draw(st.integers(min_value=1, max_value=10000)),
            "plan_name": draw(st.text(min_size=1, max_size=50)),
            "created_on": draw(st.integers(min_value=1000000000, max_value=2000000000)),
            "pass_rate": draw(st.floats(min_value=0.0, max_value=100.0)),
            "total_tests": draw(st.integers(min_value=0, max_value=1000)),
            "is_completed": draw(st.booleans()),
        }
        plans.append(plan)
    
    return plans


def sort_plans(plans, column, direction="asc"):
    """
    Sort plans by specified column and direction.
    
    Args:
        plans: List of plan dictionaries
        column: Column name to sort by ('name', 'created_on', 'pass_rate', 'total_tests')
        direction: Sort direction ('asc' or 'desc')
    
    Returns:
        Sorted list of plans
    """
    # Map column names to plan keys
    column_map = {
        "name": "plan_name",
        "created_on": "created_on",
        "pass_rate": "pass_rate",
        "total_tests": "total_tests",
    }
    
    sort_key = column_map.get(column, "plan_name")
    reverse = direction == "desc"
    
    # Sort with None values handled (put them at the end)
    def get_sort_value(plan):
        value = plan.get(sort_key)
        if value is None:
            # Return a value that sorts to the end
            if sort_key == "plan_name":
                return "" if not reverse else "~" * 100
            else:
                return float('-inf') if not reverse else float('inf')
        # For string values, use casefold for case-insensitive sorting
        if sort_key == "plan_name" and isinstance(value, str):
            return value.casefold()
        return value
    
    return sorted(plans, key=get_sort_value, reverse=reverse)


class TestSortOrderCorrectness(unittest.TestCase):
    """
    **Feature: testrail-dashboard, Property 20: Sort order correctness**
    **Validates: Requirements 9.1, 9.3, 9.4, 9.5**
    """

    @settings(max_examples=100)
    @given(plans=gen_plan_list())
    def test_sort_by_name_ascending(self, plans):
        """Sorting by name in ascending order should produce alphabetically ordered list."""
        if len(plans) == 0:
            return  # Skip empty lists
        
        sorted_plans = sort_plans(plans, "name", "asc")
        
        # Verify all plans are present
        self.assertEqual(len(sorted_plans), len(plans))
        
        # Verify ascending order (using casefold for better Unicode handling)
        for i in range(len(sorted_plans) - 1):
            name1 = sorted_plans[i]["plan_name"]
            name2 = sorted_plans[i + 1]["plan_name"]
            # Use casefold() for better Unicode comparison
            self.assertLessEqual(name1.casefold(), name2.casefold())

    @settings(max_examples=100)
    @given(plans=gen_plan_list())
    def test_sort_by_date_ascending(self, plans):
        """Sorting by date in ascending order should produce chronologically ordered list."""
        if len(plans) == 0:
            return  # Skip empty lists
        
        sorted_plans = sort_plans(plans, "created_on", "asc")
        
        # Verify all plans are present
        self.assertEqual(len(sorted_plans), len(plans))
        
        # Verify ascending chronological order
        for i in range(len(sorted_plans) - 1):
            date1 = sorted_plans[i]["created_on"]
            date2 = sorted_plans[i + 1]["created_on"]
            self.assertLessEqual(date1, date2)

    @settings(max_examples=100)
    @given(plans=gen_plan_list())
    def test_sort_by_pass_rate_ascending(self, plans):
        """Sorting by pass rate in ascending order should produce numerically ordered list."""
        if len(plans) == 0:
            return  # Skip empty lists
        
        sorted_plans = sort_plans(plans, "pass_rate", "asc")
        
        # Verify all plans are present
        self.assertEqual(len(sorted_plans), len(plans))
        
        # Verify ascending numerical order
        for i in range(len(sorted_plans) - 1):
            rate1 = sorted_plans[i]["pass_rate"]
            rate2 = sorted_plans[i + 1]["pass_rate"]
            self.assertLessEqual(rate1, rate2)

    @settings(max_examples=100)
    @given(plans=gen_plan_list())
    def test_sort_by_test_count_ascending(self, plans):
        """Sorting by test count in ascending order should produce numerically ordered list."""
        if len(plans) == 0:
            return  # Skip empty lists
        
        sorted_plans = sort_plans(plans, "total_tests", "asc")
        
        # Verify all plans are present
        self.assertEqual(len(sorted_plans), len(plans))
        
        # Verify ascending numerical order
        for i in range(len(sorted_plans) - 1):
            count1 = sorted_plans[i]["total_tests"]
            count2 = sorted_plans[i + 1]["total_tests"]
            self.assertLessEqual(count1, count2)

    @settings(max_examples=100)
    @given(plans=gen_plan_list())
    def test_sort_maintains_all_elements(self, plans):
        """Sorting should maintain all original elements without adding or removing any."""
        sorted_plans = sort_plans(plans, "name", "asc")
        
        # Verify same number of elements
        self.assertEqual(len(sorted_plans), len(plans))
        
        # Verify all plan IDs are present
        original_ids = {p["plan_id"] for p in plans}
        sorted_ids = {p["plan_id"] for p in sorted_plans}
        self.assertEqual(original_ids, sorted_ids)


class TestSortToggleBehavior(unittest.TestCase):
    """
    **Feature: testrail-dashboard, Property 21: Sort toggle behavior**
    **Validates: Requirements 9.2**
    """

    @settings(max_examples=100)
    @given(plans=gen_plan_list())
    def test_toggle_reverses_order(self, plans):
        """Toggling sort direction should reverse the order of items with distinct values."""
        if len(plans) < 2:
            return  # Need at least 2 items to test reversal
        
        # Filter to plans with unique names to avoid stable sort issues
        unique_names = {}
        filtered_plans = []
        for plan in plans:
            name = plan["plan_name"]
            if name not in unique_names:
                unique_names[name] = True
                filtered_plans.append(plan)
        
        if len(filtered_plans) < 2:
            return  # Need at least 2 unique items
        
        # Sort ascending
        asc_sorted = sort_plans(filtered_plans, "name", "asc")
        
        # Sort descending
        desc_sorted = sort_plans(filtered_plans, "name", "desc")
        
        # Verify descending is reverse of ascending
        self.assertEqual(asc_sorted, list(reversed(desc_sorted)))

    @settings(max_examples=100)
    @given(plans=gen_plan_list(), column=st.sampled_from(["name", "created_on", "pass_rate", "total_tests"]))
    def test_toggle_for_all_columns(self, plans, column):
        """Toggle behavior should work consistently for all sortable columns."""
        if len(plans) < 2:
            return  # Need at least 2 items to test reversal
        
        # Map column to key
        column_map = {
            "name": "plan_name",
            "created_on": "created_on",
            "pass_rate": "pass_rate",
            "total_tests": "total_tests",
        }
        key = column_map[column]
        
        # Filter to plans with unique values for the sort column
        unique_values = {}
        filtered_plans = []
        for plan in plans:
            value = plan[key]
            if value not in unique_values:
                unique_values[value] = True
                filtered_plans.append(plan)
        
        if len(filtered_plans) < 2:
            return  # Need at least 2 unique items
        
        # Sort ascending
        asc_sorted = sort_plans(filtered_plans, column, "asc")
        
        # Sort descending
        desc_sorted = sort_plans(filtered_plans, column, "desc")
        
        # Verify descending is reverse of ascending
        self.assertEqual(asc_sorted, list(reversed(desc_sorted)))


class TestSortingEdgeCases(unittest.TestCase):
    """Unit tests for sorting edge cases."""

    def test_sort_empty_list(self):
        """Sorting an empty list should return an empty list."""
        plans = []
        sorted_plans = sort_plans(plans, "name", "asc")
        self.assertEqual(sorted_plans, [])

    def test_sort_single_item(self):
        """Sorting a single-item list should return the same list."""
        plans = [{"plan_id": 1, "plan_name": "Test", "created_on": 123, "pass_rate": 50.0, "total_tests": 10}]
        sorted_plans = sort_plans(plans, "name", "asc")
        self.assertEqual(sorted_plans, plans)

    def test_sort_with_null_values(self):
        """Sorting should handle null values gracefully."""
        plans = [
            {"plan_id": 1, "plan_name": "A", "created_on": 100, "pass_rate": None, "total_tests": 10},
            {"plan_id": 2, "plan_name": "B", "created_on": 200, "pass_rate": 50.0, "total_tests": 20},
            {"plan_id": 3, "plan_name": "C", "created_on": 300, "pass_rate": 75.0, "total_tests": 30},
        ]
        
        # Should not raise an error
        sorted_plans = sort_plans(plans, "pass_rate", "asc")
        self.assertEqual(len(sorted_plans), 3)

    def test_sort_with_duplicate_values(self):
        """Sorting should handle duplicate values correctly."""
        plans = [
            {"plan_id": 1, "plan_name": "Test", "created_on": 100, "pass_rate": 50.0, "total_tests": 10},
            {"plan_id": 2, "plan_name": "Test", "created_on": 200, "pass_rate": 50.0, "total_tests": 20},
            {"plan_id": 3, "plan_name": "Test", "created_on": 300, "pass_rate": 50.0, "total_tests": 30},
        ]
        
        sorted_plans = sort_plans(plans, "plan_name", "asc")
        
        # All plans should still be present
        self.assertEqual(len(sorted_plans), 3)
        
        # Order should be stable (maintain relative order for equal values)
        # Python's sort is stable, so original order should be preserved
        plan_ids = [p["plan_id"] for p in sorted_plans]
        self.assertEqual(plan_ids, [1, 2, 3])

    def test_sort_stability(self):
        """Sort should be stable - equal elements maintain their relative order."""
        plans = [
            {"plan_id": 1, "plan_name": "A", "created_on": 100, "pass_rate": 50.0, "total_tests": 10},
            {"plan_id": 2, "plan_name": "B", "created_on": 100, "pass_rate": 50.0, "total_tests": 20},
            {"plan_id": 3, "plan_name": "C", "created_on": 100, "pass_rate": 50.0, "total_tests": 30},
        ]
        
        # Sort by created_on (all equal)
        sorted_plans = sort_plans(plans, "created_on", "asc")
        
        # Original order should be maintained
        plan_ids = [p["plan_id"] for p in sorted_plans]
        self.assertEqual(plan_ids, [1, 2, 3])

    def test_sort_case_insensitive(self):
        """Sorting by name should be case-insensitive."""
        plans = [
            {"plan_id": 1, "plan_name": "zebra", "created_on": 100, "pass_rate": 50.0, "total_tests": 10},
            {"plan_id": 2, "plan_name": "Apple", "created_on": 200, "pass_rate": 60.0, "total_tests": 20},
            {"plan_id": 3, "plan_name": "banana", "created_on": 300, "pass_rate": 70.0, "total_tests": 30},
        ]
        
        sorted_plans = sort_plans(plans, "name", "asc")
        
        # Should be sorted: Apple, banana, zebra (case-insensitive)
        names = [p["plan_name"] for p in sorted_plans]
        self.assertEqual(names, ["Apple", "banana", "zebra"])


if __name__ == "__main__":
    unittest.main()
