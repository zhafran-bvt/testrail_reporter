"""
Integration tests for dashboard sorting functionality.

This module tests the sorting functionality in the context of the dashboard UI.
"""

import unittest


class TestDashboardSortingIntegration(unittest.TestCase):
    """Integration tests for dashboard sorting."""

    def test_sort_function_exists(self):
        """Verify that the sort function is defined in dashboard.js."""
        with open("assets/dashboard.js", "r") as f:
            content = f.read()
            self.assertIn("function sortPlans", content)
            self.assertIn("function handleSortClick", content)
            self.assertIn("function updateSortIndicators", content)
            self.assertIn("function renderSortedPlans", content)

    def test_sort_state_in_dashboard_state(self):
        """Verify that sort state is tracked in dashboardState."""
        with open("assets/dashboard.js", "r") as f:
            content = f.read()
            self.assertIn("sort:", content)
            self.assertIn("column:", content)
            self.assertIn("direction:", content)

    def test_sort_controls_in_html(self):
        """Verify that sort controls are present in the HTML template."""
        with open("templates/index.html", "r") as f:
            content = f.read()
            self.assertIn("dashboard-sort-header", content)
            self.assertIn('data-sort-column="created_on"', content)
            self.assertIn('data-sort-column="name"', content)
            self.assertIn('data-sort-column="pass_rate"', content)
            self.assertIn('data-sort-column="total_tests"', content)

    def test_sort_css_styles_present(self):
        """Verify that sort-related CSS styles are present."""
        with open("templates/index.html", "r") as f:
            content = f.read()
            self.assertIn(".dashboard-sort-header", content)
            self.assertIn("sort-active", content)
            self.assertIn("sort-asc", content)
            self.assertIn("sort-desc", content)

    def test_sort_event_listeners_setup(self):
        """Verify that sort event listeners are set up in initDashboard."""
        with open("assets/dashboard.js", "r") as f:
            content = f.read()
            self.assertIn("querySelectorAll('.dashboard-sort-header')", content)
            self.assertIn("handleSortClick", content)


if __name__ == "__main__":
    unittest.main()
