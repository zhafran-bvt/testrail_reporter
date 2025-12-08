"""
Tests for loading states implementation in Management view.

Requirements tested:
- 9.1: WHEN entities are loading THEN the system SHALL display a spinner icon with "Loading..." text
- 9.2: WHEN entities are loading THEN the system SHALL disable action buttons to prevent duplicate requests
- 9.3: WHEN entity loading fails THEN the system SHALL display an error message with a retry button
- 9.4: WHEN entity loading completes successfully THEN the system SHALL remove loading indicators
- 9.5: WHEN entity loading completes successfully THEN the system SHALL enable all action buttons
"""

import unittest
from pathlib import Path


class TestLoadingStates(unittest.TestCase):
    """Test loading states implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.html_path = Path("templates/index.html")
        self.ts_path = Path("src/manage.ts")
        self.js_path = Path("assets/app.js")

    def test_loading_state_html_structure(self):
        """Test that loading state HTML structure exists for all subsections."""
        with open(self.html_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Requirement 9.1: Loading state with spinner and text
        # Verify Plans loading state
        self.assertIn('id="plansLoadingState"', html)
        self.assertIn('class="loading-state"', html)
        self.assertIn('class="spinner"', html)
        self.assertIn('class="loading-text"', html)
        self.assertIn('Loading plans...', html)

        # Verify Runs loading state
        self.assertIn('id="runsLoadingState"', html)
        self.assertIn('Loading runs...', html)

        # Verify Test Cases View loading state (replaces Cases subsection)
        self.assertIn('id="testCasesLoadingState"', html)
        self.assertIn('Loading test cases...', html)

    def test_loading_state_css_spinner_animation(self):
        """Test that spinner CSS animation is defined."""
        with open(self.html_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Requirement 9.1: Spinner animation
        self.assertIn('.loading-state .spinner', html)
        self.assertIn('animation: spin', html)
        self.assertIn('@keyframes spin', html)
        self.assertIn('transform: rotate(360deg)', html)

    def test_loading_state_css_styling(self):
        """Test that loading state CSS styling is defined."""
        with open(self.html_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Requirement 9.1: Loading state styling
        self.assertIn('.loading-state', html)
        self.assertIn('display: flex', html)
        self.assertIn('flex-direction: column', html)
        self.assertIn('align-items: center', html)
        self.assertIn('justify-content: center', html)

    def test_button_disabled_styles(self):
        """Test that disabled button styles are defined."""
        with open(self.html_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Requirement 9.2: Disabled button styles
        self.assertIn('.refresh-btn:disabled', html)
        self.assertIn('.btn-edit:disabled', html)
        self.assertIn('.btn-delete:disabled', html)
        self.assertIn('cursor: not-allowed', html)
        self.assertIn('opacity:', html)

    def test_disable_buttons_during_loading_plans(self):
        """Test that buttons are disabled during plans loading."""
        with open(self.ts_path, "r", encoding="utf-8") as f:
            ts = f.read()

        # Requirement 9.2: Disable action buttons during loading
        # Find the loadManagePlans function
        self.assertIn('async function loadManagePlans()', ts)
        
        # Verify refresh button is disabled
        self.assertIn('refreshBtn.disabled = true', ts)
        
        # Verify search input is disabled
        self.assertIn('searchInput.disabled = true', ts)
        
        # Verify entity buttons are disabled
        self.assertIn('disableEntityButtons("plan")', ts)

    def test_disable_buttons_during_loading_runs(self):
        """Test that buttons are disabled during runs loading."""
        with open(self.ts_path, "r", encoding="utf-8") as f:
            ts = f.read()

        # Requirement 9.2: Disable action buttons during loading
        # Find the loadManageRuns function
        self.assertIn('async function loadManageRuns()', ts)
        
        # Verify refresh button is disabled
        self.assertIn('refreshBtn.disabled = true', ts)
        
        # Verify plan filter is disabled
        self.assertIn('planFilter.disabled = true', ts)
        
        # Verify entity buttons are disabled
        self.assertIn('disableEntityButtons("run")', ts)

    def test_disable_buttons_during_loading_cases(self):
        """Test that buttons are disabled during cases loading."""
        with open(self.ts_path, "r", encoding="utf-8") as f:
            ts = f.read()

        # Requirement 9.2: Disable action buttons during loading
        # Find the loadManageCases function
        self.assertIn('async function loadManageCases()', ts)
        
        # Verify refresh button is disabled
        self.assertIn('refreshBtn.disabled = true', ts)
        
        # Verify search input is disabled
        self.assertIn('searchInput.disabled = true', ts)
        
        # Verify entity buttons are disabled
        self.assertIn('disableEntityButtons("case")', ts)

    def test_disable_entity_buttons_function(self):
        """Test that disableEntityButtons function exists and works correctly."""
        with open(self.ts_path, "r", encoding="utf-8") as f:
            ts = f.read()

        # Requirement 9.2: Function to disable entity buttons
        self.assertIn('function disableEntityButtons', ts)
        self.assertIn('entityType: "plan" | "run" | "case"', ts)
        self.assertIn('querySelectorAll(`.edit-${entityType}-btn`)', ts)
        self.assertIn('querySelectorAll(`.delete-${entityType}-btn`)', ts)
        self.assertIn('btn.disabled = true', ts)

    def test_enable_entity_buttons_function(self):
        """Test that enableEntityButtons function exists."""
        with open(self.ts_path, "r", encoding="utf-8") as f:
            ts = f.read()

        # Requirement 9.5: Function to enable entity buttons
        self.assertIn('function enableEntityButtons', ts)
        self.assertIn('btn.disabled = false', ts)

    def test_error_state_function(self):
        """Test that showErrorState function exists and displays error with retry."""
        with open(self.ts_path, "r", encoding="utf-8") as f:
            ts = f.read()

        # Requirement 9.3: Error state with retry button
        self.assertIn('function showErrorState', ts)
        self.assertIn('subsection: "plans" | "runs" | "cases"', ts)
        self.assertIn('errorMessage: string', ts)
        self.assertIn('retryCallback: () => void', ts)
        self.assertIn('class="error-state"', ts)
        self.assertIn('Failed to load', ts)
        self.assertIn('Retry', ts)
        self.assertIn('addEventListener("click", retryCallback)', ts)

    def test_error_state_called_on_failure_plans(self):
        """Test that error state is shown when plans loading fails."""
        with open(self.ts_path, "r", encoding="utf-8") as f:
            ts = f.read()

        # Requirement 9.3: Show error state on failure
        # Find the loadManagePlans function and its catch block
        self.assertIn('catch (err: any)', ts)
        self.assertIn('showErrorState("plans"', ts)
        self.assertIn('refreshPlanList', ts)

    def test_error_state_called_on_failure_runs(self):
        """Test that error state is shown when runs loading fails."""
        with open(self.ts_path, "r", encoding="utf-8") as f:
            ts = f.read()

        # Requirement 9.3: Show error state on failure
        self.assertIn('showErrorState("runs"', ts)
        self.assertIn('refreshRunList', ts)

    def test_error_state_called_on_failure_cases(self):
        """Test that error state is shown when cases loading fails."""
        with open(self.ts_path, "r", encoding="utf-8") as f:
            ts = f.read()

        # Requirement 9.3: Show error state on failure
        self.assertIn('showErrorState("cases"', ts)
        self.assertIn('refreshCaseList', ts)

    def test_buttons_reenabled_after_loading_plans(self):
        """Test that buttons are re-enabled after plans loading completes."""
        with open(self.ts_path, "r", encoding="utf-8") as f:
            ts = f.read()

        # Requirement 9.5: Re-enable buttons after loading
        # Find the loadManagePlans function and its finally block
        self.assertIn('finally {', ts)
        self.assertIn('refreshBtn.disabled = false', ts)
        self.assertIn('searchInput.disabled = false', ts)

    def test_buttons_reenabled_after_loading_runs(self):
        """Test that buttons are re-enabled after runs loading completes."""
        with open(self.ts_path, "r", encoding="utf-8") as f:
            ts = f.read()

        # Requirement 9.5: Re-enable buttons after loading
        # Verify finally block re-enables buttons
        self.assertIn('finally {', ts)
        self.assertIn('refreshBtn.disabled = false', ts)
        self.assertIn('planFilter.disabled = false', ts)

    def test_buttons_reenabled_after_loading_cases(self):
        """Test that buttons are re-enabled after cases loading completes."""
        with open(self.ts_path, "r", encoding="utf-8") as f:
            ts = f.read()

        # Requirement 9.5: Re-enable buttons after loading
        # Verify finally block re-enables buttons
        self.assertIn('finally {', ts)
        self.assertIn('refreshBtn.disabled = false', ts)
        self.assertIn('searchInput.disabled = false', ts)

    def test_loading_state_hidden_on_success(self):
        """Test that loading state is hidden when data loads successfully."""
        with open(self.ts_path, "r", encoding="utf-8") as f:
            ts = f.read()

        # Requirement 9.4: Remove loading indicators on success
        # Verify renderPlansSubsection hides loading state
        self.assertIn('function renderPlansSubsection', ts)
        self.assertIn('loadingState.classList.add("hidden")', ts)

    def test_loading_state_shown_at_start(self):
        """Test that loading state is shown at the start of loading."""
        with open(self.ts_path, "r", encoding="utf-8") as f:
            ts = f.read()

        # Requirement 9.1: Show loading state during fetch
        # Verify loading state is shown at start
        self.assertIn('loadingState.classList.remove("hidden")', ts)
        self.assertIn('emptyState.classList.add("hidden")', ts)
        self.assertIn('container.classList.add("hidden")', ts)

    def test_consistent_loading_ux_across_subsections(self):
        """Test that loading UX is consistent across all subsections."""
        with open(self.ts_path, "r", encoding="utf-8") as f:
            ts = f.read()

        # Requirement 9.5: Consistent loading UX
        # Plans and Runs load functions should follow the same pattern
        # (Cases subsection was removed, replaced by Test Cases View)
        
        # Pattern 1: Show loading state (at least 2 for plans and runs)
        self.assertGreaterEqual(ts.count('loadingState.classList.remove("hidden")'), 2)
        
        # Pattern 2: Disable buttons (at least 2 for plans and runs)
        self.assertGreaterEqual(ts.count('refreshBtn.disabled = true'), 2)
        
        # Pattern 3: Call showErrorState on error
        self.assertGreaterEqual(ts.count('showErrorState('), 2)
        
        # Pattern 4: Re-enable buttons in finally (at least 2 for plans and runs)
        self.assertGreaterEqual(ts.count('refreshBtn.disabled = false'), 2)

    def test_compiled_javascript_includes_loading_logic(self):
        """Test that compiled JavaScript includes loading state logic."""
        with open(self.js_path, "r", encoding="utf-8") as f:
            js = f.read()

        # Verify key loading state functions are compiled
        self.assertIn('disableEntityButtons', js)
        self.assertIn('showErrorState', js)
        self.assertIn('disabled = true', js)
        self.assertIn('disabled = false', js)

    def test_error_state_icon_and_styling(self):
        """Test that error state has proper icon and styling."""
        with open(self.ts_path, "r", encoding="utf-8") as f:
            ts = f.read()

        # Requirement 9.3: Error state styling
        self.assertIn('class="error-state"', ts)
        self.assertIn('⚠️', ts)  # Warning emoji icon
        self.assertIn('Failed to load', ts)
        self.assertIn('font-size: 48px', ts)  # Large icon
        self.assertIn('opacity: 0.5', ts)  # Muted icon

    def test_retry_button_in_error_state(self):
        """Test that retry button is present in error state."""
        with open(self.ts_path, "r", encoding="utf-8") as f:
            ts = f.read()

        # Requirement 9.3: Retry button
        self.assertIn('class="refresh-btn"', ts)
        self.assertIn('Retry', ts)
        self.assertIn('🔄', ts)  # Refresh icon
        self.assertIn('addEventListener("click", retryCallback)', ts)

    def test_input_disabled_styles(self):
        """Test that input and select disabled styles are defined."""
        with open(self.html_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Requirement 9.2: Disabled input styles
        self.assertIn('input[type="search"]:disabled', html)
        self.assertIn('select:disabled', html)


if __name__ == "__main__":
    unittest.main()
