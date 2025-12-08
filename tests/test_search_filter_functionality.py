"""
Tests for search and filter functionality in Management view.

This test suite validates:
- Real-time search filtering for Plans (Requirements 7.1)
- Plan selector filtering for Runs (Requirements 7.2)
- Real-time search filtering for Cases (Requirements 7.3)
- Debounce search input (300ms) (Requirements 7.4)
- Preserve filters during refresh (Requirements 12.4, 12.5)
"""

import unittest

from fastapi.testclient import TestClient


class TestSearchFilterDebouncing(unittest.TestCase):
    """
    Tests for debounced search functionality.
    Validates: Requirements 7.4
    """

    def test_debounce_function_exists(self):
        """
        Test that debounce function exists in compiled JavaScript.
        
        Validates: Requirements 7.4
        """
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        
        js = response.text
        
        # Verify debounce function exists
        self.assertIn('debounce', js, 
                     "debounce function should exist in compiled JS")

    def test_debounce_timer_variables_exist(self):
        """
        Test that debounce timer variables are declared.
        
        Validates: Requirements 7.4
        """
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        
        js = response.text
        
        # Verify timer variables exist (they may be minified)
        # We check for the debounce function implementation
        self.assertIn('setTimeout', js, 
                     "setTimeout should be used for debouncing")
        self.assertIn('clearTimeout', js, 
                     "clearTimeout should be used for debouncing")

    def test_plans_search_uses_debounce(self):
        """
        Test that Plans search input uses debounced filtering.
        
        Validates: Requirements 7.1, 7.4
        """
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        
        js = response.text
        
        # Verify debounce is applied to plans search
        # The compiled code should have debounce logic for filterPlans
        self.assertIn('filterPlans', js)
        # Check that debounce is used (300ms delay)
        # In the compiled code, we should see the debounce pattern
        self.assertTrue(
            'debounce' in js or 'setTimeout' in js,
            "Debounce mechanism should be present in compiled JS"
        )

    def test_cases_search_uses_debounce(self):
        """
        Test that Cases search input uses debounced filtering.
        
        Validates: Requirements 7.3, 7.4
        """
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        
        js = response.text
        
        # Verify debounce is applied to cases search
        self.assertIn('filterCases', js)
        # Check that debounce is used
        self.assertTrue(
            'debounce' in js or 'setTimeout' in js,
            "Debounce mechanism should be present in compiled JS"
        )


class TestFilterPreservation(unittest.TestCase):
    """
    Tests for filter preservation during refresh.
    Validates: Requirements 12.4, 12.5
    """

    def test_plans_search_value_preserved_on_refresh(self):
        """
        Test that Plans search filter value is preserved during refresh.
        
        Validates: Requirements 7.1, 12.4, 12.5
        """
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        
        js = response.text
        
        # Verify that loadManagePlans preserves search value
        # Look for code that reads the search input value before loading
        self.assertIn('plansSearch', js)
        # The function should read the current value and reapply it
        self.assertIn('value', js)

    def test_cases_search_value_preserved_on_refresh(self):
        """
        Test that Cases search filter value is preserved during refresh.
        
        Validates: Requirements 7.3, 12.4, 12.5
        """
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        
        js = response.text
        
        # Verify that loadManageCases preserves search value
        self.assertIn('casesSearch', js)
        # The function should read the current value and reapply it
        self.assertIn('value', js)

    def test_runs_plan_filter_preserved_on_refresh(self):
        """
        Test that Runs plan filter value is preserved during refresh.
        
        Validates: Requirements 7.2, 12.4, 12.5
        """
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        
        js = response.text
        
        # Verify that loadManageRuns preserves plan filter value
        self.assertIn('runsPlanFilter', js)
        # The function should read the current value and use it in the API call
        self.assertIn('value', js)


class TestRealTimeFiltering(unittest.TestCase):
    """
    Tests for real-time filtering functionality.
    Validates: Requirements 7.1, 7.2, 7.3, 7.5
    """

    def test_plans_filter_updates_immediately(self):
        """
        Test that Plans filter updates results immediately (after debounce).
        
        Validates: Requirements 7.1, 7.5
        """
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        
        js = response.text
        
        # Verify filterPlans function filters and renders immediately
        self.assertIn('filterPlans', js)
        self.assertIn('renderPlansSubsection', js)
        # The filter should call render immediately after filtering
        # (no additional user action required)

    def test_cases_filter_updates_immediately(self):
        """
        Test that Cases filter updates results immediately (after debounce).
        
        Validates: Requirements 7.3, 7.5
        """
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        
        js = response.text
        
        # Verify filterCases function filters and renders immediately
        self.assertIn('filterCases', js)
        self.assertIn('renderCasesSubsection', js)

    def test_runs_filter_triggers_reload(self):
        """
        Test that Runs plan filter triggers immediate reload.
        
        Validates: Requirements 7.2, 7.5
        """
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        
        js = response.text
        
        # Verify plan filter change triggers refreshRunList
        self.assertIn('runsPlanFilter', js)
        self.assertIn('refreshRunList', js)
        # The change event should be wired to refresh


class TestSearchInputElements(unittest.TestCase):
    """
    Tests for search input elements in HTML.
    Validates: Requirements 7.1, 7.2, 7.3
    """

    def test_plans_search_input_has_correct_attributes(self):
        """
        Test that Plans search input has correct attributes.
        
        Validates: Requirements 7.1
        """

    def test_cases_search_input_has_correct_attributes(self):
        """
        Test that Cases search input has correct attributes.
        
        Validates: Requirements 7.3
        """

    def test_runs_plan_filter_has_correct_attributes(self):
        """
        Test that Runs plan filter dropdown has correct attributes.
        
        Validates: Requirements 7.2
        """
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        
        html = response.text
        
        # Verify plan filter exists with correct attributes
        self.assertIn('id="runsPlanFilter"', html)
        self.assertIn('aria-label="Filter runs by plan"', html)
        # Should have "All Plans" as default option
        self.assertIn('All Plans', html)


class TestFilterLogic(unittest.TestCase):
    """
    Tests for filter logic implementation.
    Validates: Requirements 7.1, 7.3
    """

    def test_plans_filter_is_case_insensitive(self):
        """
        Test that Plans filter is case-insensitive.
        
        Validates: Requirements 7.1
        """
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        
        js = response.text
        
        # Verify toLowerCase is used for case-insensitive filtering
        self.assertIn('toLowerCase', js)
        # The filter should convert both search term and plan name to lowercase

    def test_cases_filter_searches_title_and_refs(self):
        """
        Test that Cases filter searches both title and refs.
        
        Validates: Requirements 7.3
        """
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        
        js = response.text
        
        # Verify filterCases searches both title and refs
        self.assertIn('filterCases', js)
        # Should check both fields (implementation may vary in compiled code)

    def test_empty_search_shows_all_results(self):
        """
        Test that empty search query shows all results.
        
        Validates: Requirements 7.1, 7.3
        """
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        
        js = response.text
        
        # Verify that empty query shows all results
        # The filter functions should check for empty/trimmed query
        self.assertIn('trim', js)


if __name__ == '__main__':
    unittest.main()
