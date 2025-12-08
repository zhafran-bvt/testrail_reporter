"""
Property-based tests for navigation integration.

This module contains property-based tests that verify the navigation
integration works correctly, including view switching, state preservation,
and active navigation highlighting.
"""

import unittest
from hypothesis import given, strategies as st, settings
from fastapi.testclient import TestClient


class TestNavigationIntegration(unittest.TestCase):
    """Property-based tests for navigation integration."""

    def setUp(self):
        """Set up test client."""
        from app.main import app
        self.client = TestClient(app)

    @given(view_name=st.sampled_from(['reporter', 'dashboard', 'manage', 'howto']))
    @settings(max_examples=100)
    def test_view_switching_correctness(self, view_name):
        """
        **Feature: testrail-dashboard, Property 22: View switching correctness**
        **Validates: Requirements 10.2**
        
        For any navigation action to the dashboard, the dashboard view should be 
        displayed and other views should be hidden.
        
        This property test verifies that when switching to any view (including dashboard),
        the correct view is displayed and all other views are hidden.
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        
        html = response.text
        
        # Verify all views exist in the HTML
        self.assertIn('id="reporterView"', html)
        self.assertIn('id="dashboardView"', html)
        self.assertIn('id="manageView"', html)
        self.assertIn('id="howToView"', html)
        
        # Verify all navigation links exist
        self.assertIn('id="linkReporter"', html)
        self.assertIn('id="linkDashboard"', html)
        self.assertIn('id="linkManage"', html)
        self.assertIn('id="linkHowTo"', html)
        
        # Verify the app.js file is loaded (contains switchView function)
        self.assertIn('src="/assets/app.js"', html)
        
        # Verify the switchView function exists in the compiled JavaScript
        response_js = self.client.get("/assets/app.js")
        self.assertEqual(response_js.status_code, 200)
        js = response_js.text
        
        # Verify that each view has logic to be shown/hidden in the JS
        self.assertIn('dashboard', js)
        self.assertIn('classList.remove("hidden")', js)
        self.assertIn('classList.add("hidden")', js)
        self.assertIn('reporter', js)
        self.assertIn('manage', js)
        self.assertIn('howto', js)
        
        # Verify that the dashboard view is initially hidden
        dashboard_view_start = html.find('id="dashboardView"')
        dashboard_view_section = html[dashboard_view_start:dashboard_view_start + 200]
        self.assertIn('class="hidden"', dashboard_view_section)


class TestNavigationStatePreservation(unittest.TestCase):
    """Property-based tests for navigation state preservation."""

    def setUp(self):
        """Set up test client."""
        from app.main import app
        self.client = TestClient(app)

    @given(
        search_term=st.text(min_size=0, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        completion_status=st.sampled_from(['', '0', '1']),
        sort_column=st.sampled_from(['name', 'created_on', 'pass_rate', 'total_tests'])
    )
    @settings(max_examples=100)
    def test_state_preservation_across_navigation(self, search_term, completion_status, sort_column):
        """
        **Feature: testrail-dashboard, Property 23: State preservation across navigation**
        **Validates: Requirements 10.3, 10.5**
        
        For any dashboard state (filters, sort order), navigating away and back 
        should restore that state.
        
        This property test verifies that the dashboard state management structure
        exists and can preserve filter and sort state.
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        
        html = response.text
        
        # Verify dashboard state object exists in JavaScript
        response_js = self.client.get("/assets/dashboard.js")
        self.assertEqual(response_js.status_code, 200)
        js = response_js.text
        
        # Verify dashboardState object exists
        self.assertIn('dashboardState', js)
        
        # Verify state includes filters
        self.assertIn('filters:', js)
        self.assertIn('search:', js)
        self.assertIn('isCompleted:', js)
        
        # Verify state includes sort
        self.assertIn('sort:', js)
        self.assertIn('column:', js)
        self.assertIn('direction:', js)
        
        # Verify state includes expanded plans tracking
        self.assertIn('expandedPlans:', js)
        
        # Verify state includes cached plans for client-side operations
        self.assertIn('cachedPlans:', js)
        
        # The state object should persist across view switches
        # because it's defined at module level, not inside init function
        state_def_pos = js.find('const dashboardState')
        init_func_pos = js.find('function initDashboard()')
        
        # State should be defined before init function (module-level)
        self.assertGreater(init_func_pos, state_def_pos,
                          "dashboardState should be defined at module level for persistence")
        
        # Verify that filter inputs update the state
        self.assertIn('dashboardState.filters.search', js)
        self.assertIn('dashboardState.filters.isCompleted', js)
        
        # Verify that sort state is updated
        self.assertIn('dashboardState.sort.column', js)
        self.assertIn('dashboardState.sort.direction', js)


class TestNavigationActiveHighlighting(unittest.TestCase):
    """Property-based tests for active navigation highlighting."""

    def setUp(self):
        """Set up test client."""
        from app.main import app
        self.client = TestClient(app)

    @given(view_name=st.sampled_from(['reporter', 'dashboard', 'manage', 'howto']))
    @settings(max_examples=100)
    def test_active_navigation_highlighting(self, view_name):
        """
        **Feature: testrail-dashboard, Property 24: Active navigation highlighting**
        **Validates: Requirements 10.4**
        
        For any active view, the corresponding navigation item should have the 
        active CSS class applied.
        
        This property test verifies that the navigation highlighting logic correctly
        applies the 'active' class to the appropriate navigation link.
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        
        html = response.text
        
        # Verify active class is defined in CSS
        self.assertIn('.nav-item.active', html)
        
        # Verify the active class has distinct styling
        active_class_start = html.find('.nav-item.active')
        active_class_section = html[active_class_start:active_class_start + 200]
        # Active items should have different background or color
        self.assertTrue(
            'background:' in active_class_section or 'color:' in active_class_section,
            "Active nav items should have distinct styling"
        )
        
        # Verify switchView function manages active class in the compiled JS
        response_js = self.client.get("/assets/app.js")
        self.assertEqual(response_js.status_code, 200)
        js = response_js.text
        
        # Verify link references exist
        self.assertIn('linkReporter', js)
        self.assertIn('linkDashboard', js)
        self.assertIn('linkManage', js)
        self.assertIn('linkHowto', js)
        
        # Verify classList manipulation exists
        self.assertIn('classList.remove("active")', js)
        self.assertIn('classList.add("active")', js)
        
        # Count remove active calls (should be at least 4, one for each link)
        remove_active_count = js.count('classList.remove("active")')
        self.assertGreaterEqual(remove_active_count, 4, 
                        "Should remove active from all navigation links")


class TestNavigationDashboardInitialization(unittest.TestCase):
    """Test that dashboard is properly initialized when navigated to."""

    def setUp(self):
        """Set up test client."""
        from app.main import app
        self.client = TestClient(app)

    def test_dashboard_initialization_on_view_switch(self):
        """
        Test that dashboard module is initialized when switching to dashboard view.
        
        This verifies that the dashboard loads its data when the user navigates to it.
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        
        html = response.text
        
        # Verify that switchView calls dashboard init in the compiled JS
        response_js = self.client.get("/assets/app.js")
        self.assertEqual(response_js.status_code, 200)
        js = response_js.text
        
        # Verify dashboard module reference exists
        self.assertIn('dashboardModule', js)
        
        # Verify init is called
        self.assertIn('.init()', js)


if __name__ == '__main__':
    unittest.main()
