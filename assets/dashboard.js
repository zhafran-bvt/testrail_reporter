/**
 * Dashboard Module for TestRail Reporter
 * 
 * This module provides the client-side functionality for the TestRail Dashboard,
 * including data fetching, filtering, sorting, and rendering of test plans and runs.
 * 
 * Key Features:
 * - Fetches and displays paginated list of test plans with statistics
 * - Client-side filtering by search term, completion status, and date range
 * - Client-side sorting by name, date, pass rate, and test count
 * - Expandable plan cards to show detailed run statistics
 * - Report generation integration for plans and runs
 * - Refresh functionality to clear cache and fetch latest data
 * - Responsive design that adapts to different screen sizes
 * 
 * Architecture:
 * - State management through dashboardState object
 * - Event-driven UI updates with debouncing for performance
 * - Template-based rendering using HTML <template> elements
 * - Caching of loaded data to minimize API calls
 * 
 * API Endpoints Used:
 * - GET /api/dashboard/plans - Fetch paginated plans with statistics
 * - GET /api/dashboard/plan/{id} - Fetch detailed plan with runs
 * - POST /api/dashboard/cache/clear - Clear server-side cache
 * - GET /api/report - Generate HTML reports
 * 
 * State Management:
 * - currentProject: Active project ID
 * - currentOffset/currentLimit: Pagination state
 * - filters: Search term, completion status, date range
 * - sort: Current sort column and direction
 * - expandedPlans: Set of plan IDs with expanded runs
 * - loadedRuns: Map of plan IDs to their loaded run data
 * - cachedPlans: Array of plans for client-side sorting
 * 
 * Performance Optimizations:
 * - Debounced search input (500ms delay)
 * - Client-side sorting to avoid server round-trips
 * - Lazy loading of run details (only when expanded)
 * - Caching of loaded run data
 * 
 * Accessibility:
 * - Semantic HTML structure
 * - ARIA labels and roles
 * - Keyboard navigation support
 * - Screen reader compatible
 */

// Dashboard state
const dashboardState = {
  currentProject: 1,
  currentOffset: 0,
  currentLimit: 50,
  filters: {
    search: '',
    isCompleted: null,
    createdAfter: null,
    createdBefore: null
  },
  sort: {
    column: 'created_on',  // Default sort by creation date
    direction: 'desc'       // Default to newest first
  },
  expandedPlans: new Set(),
  loadedRuns: new Map(), // planId -> runs array
  cachedPlans: []  // Store plans for client-side sorting
};

// Debounce utility
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Escape HTML to prevent XSS
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// Format date from Unix timestamp
function formatDate(timestamp) {
  if (!timestamp) return 'N/A';
  const date = new Date(timestamp * 1000);
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Get pass rate color class
function getPassRateColorClass(passRate) {
  if (passRate >= 80) return 'pass-rate-high';
  if (passRate >= 50) return 'pass-rate-medium';
  return 'pass-rate-low';
}

// Get completion badge class
function getCompletionBadgeClass(isCompleted, failedCount, blockedCount, totalTests) {
  if (!isCompleted) return 'badge-active';
  
  // Check for critical issues
  const failRate = totalTests > 0 ? (failedCount / totalTests) * 100 : 0;
  const blockRate = totalTests > 0 ? (blockedCount / totalTests) * 100 : 0;
  
  if (failRate > 20 || blockRate > 10) {
    return 'badge-critical';
  }
  
  return 'badge-completed';
}

// Get completion badge text
function getCompletionBadgeText(isCompleted) {
  return isCompleted ? 'Completed' : 'Active';
}

/**
 * Render a single plan card
 */
function renderPlanCard(plan) {
  const template = document.getElementById('dashboardPlanCardTemplate');
  if (!template) return null;
  
  const clone = template.content.cloneNode(true);
  const card = clone.querySelector('.dashboard-plan-card');
  
  if (!card) return null;
  
  // Set plan ID
  card.dataset.planId = plan.plan_id;
  
  // Set plan title and metadata
  card.querySelector('.dashboard-plan-title').textContent = plan.plan_name || `Plan ${plan.plan_id}`;
  card.querySelector('.plan-created').textContent = `Created: ${formatDate(plan.created_on)}`;
  card.querySelector('.plan-updated').textContent = plan.updated_on ? `Updated: ${formatDate(plan.updated_on)}` : '';
  
  // Set completion badge
  const badge = card.querySelector('.badge-status');
  const badgeClass = getCompletionBadgeClass(
    plan.is_completed,
    plan.failed_count || 0,
    plan.blocked_count || 0,
    plan.total_tests || 0
  );
  badge.className = `dashboard-badge ${badgeClass}`;
  badge.textContent = getCompletionBadgeText(plan.is_completed);
  
  // Set statistics
  card.querySelector('.plan-total-tests').textContent = plan.total_tests || 0;
  
  const passRate = plan.pass_rate || 0;
  const passRateEl = card.querySelector('.plan-pass-rate');
  passRateEl.textContent = `${passRate.toFixed(1)}%`;
  passRateEl.className = `dashboard-stat-value ${getPassRateColorClass(passRate)}`;
  
  card.querySelector('.plan-completion-rate').textContent = `${(plan.completion_rate || 0).toFixed(1)}%`;
  card.querySelector('.plan-total-runs').textContent = plan.total_runs || 0;
  
  // Set status distribution
  const statusDist = plan.status_distribution || {};
  const totalTests = plan.total_tests || 1; // Avoid division by zero
  
  // Backend returns status names, not IDs
  const passed = statusDist['Passed'] || 0;
  const failed = statusDist['Failed'] || 0;
  const blocked = statusDist['Blocked'] || 0;
  const retest = statusDist['Retest'] || 0;
  const untested = statusDist['Untested'] || 0;
  
  // Update status bar widths
  card.querySelector('[data-status="passed"]').style.width = `${(passed / totalTests) * 100}%`;
  card.querySelector('[data-status="failed"]').style.width = `${(failed / totalTests) * 100}%`;
  card.querySelector('[data-status="blocked"]').style.width = `${(blocked / totalTests) * 100}%`;
  card.querySelector('[data-status="retest"]').style.width = `${(retest / totalTests) * 100}%`;
  card.querySelector('[data-status="untested"]').style.width = `${(untested / totalTests) * 100}%`;
  
  // Update status legend counts
  card.querySelector('.status-count-passed').textContent = passed;
  card.querySelector('.status-count-failed').textContent = failed;
  card.querySelector('.status-count-blocked').textContent = blocked;
  card.querySelector('.status-count-retest').textContent = retest;
  card.querySelector('.status-count-untested').textContent = untested;
  
  // Show runs section if there are runs
  if (plan.total_runs > 0) {
    const runsSection = card.querySelector('.dashboard-runs-section');
    runsSection.style.display = 'block';
    runsSection.querySelector('.runs-count-text').textContent = `View Runs (${plan.total_runs})`;
    
    // Add expand/collapse handler
    const toggleBtn = runsSection.querySelector('.dashboard-runs-toggle');
    toggleBtn.addEventListener('click', () => togglePlanRuns(plan.plan_id));
  }
  
  // Add report button handler
  const reportBtn = card.querySelector('.plan-report-btn');
  reportBtn.addEventListener('click', () => generatePlanReport(plan.plan_id));
  
  return card;
}

/**
 * Render a single run card
 */
function renderRunCard(run) {
  const template = document.getElementById('dashboardRunCardTemplate');
  if (!template) return null;
  
  const clone = template.content.cloneNode(true);
  const card = clone.querySelector('.dashboard-run-card');
  
  if (!card) return null;
  
  // Set run ID
  card.dataset.runId = run.run_id;
  
  // Set run title and metadata
  card.querySelector('.dashboard-run-title').textContent = run.run_name || `Run ${run.run_id}`;
  card.querySelector('.dashboard-run-suite').textContent = run.suite_name || 'No suite';
  
  // Set completion badge
  const badge = card.querySelector('.badge-status');
  badge.className = `dashboard-badge ${run.is_completed ? 'badge-completed' : 'badge-active'}`;
  badge.textContent = run.is_completed ? 'Completed' : 'Active';
  
  // Set statistics
  card.querySelector('.run-total-tests').textContent = run.total_tests || 0;
  
  const passRate = run.pass_rate || 0;
  const passRateEl = card.querySelector('.run-pass-rate');
  passRateEl.textContent = `${passRate.toFixed(1)}%`;
  passRateEl.className = `dashboard-run-stat-value ${getPassRateColorClass(passRate)}`;
  
  card.querySelector('.run-completion-rate').textContent = `${(run.completion_rate || 0).toFixed(1)}%`;
  
  // Set status distribution
  const statusDist = run.status_distribution || {};
  const totalTests = run.total_tests || 1;
  
  // Backend returns status names, not IDs
  const passed = statusDist['Passed'] || 0;
  const failed = statusDist['Failed'] || 0;
  const blocked = statusDist['Blocked'] || 0;
  const retest = statusDist['Retest'] || 0;
  const untested = statusDist['Untested'] || 0;
  
  // Update status bar widths
  card.querySelector('[data-status="passed"]').style.width = `${(passed / totalTests) * 100}%`;
  card.querySelector('[data-status="failed"]').style.width = `${(failed / totalTests) * 100}%`;
  card.querySelector('[data-status="blocked"]').style.width = `${(blocked / totalTests) * 100}%`;
  card.querySelector('[data-status="retest"]').style.width = `${(retest / totalTests) * 100}%`;
  card.querySelector('[data-status="untested"]').style.width = `${(untested / totalTests) * 100}%`;
  
  // Update status legend counts
  card.querySelector('.status-count-passed').textContent = passed;
  card.querySelector('.status-count-failed').textContent = failed;
  card.querySelector('.status-count-blocked').textContent = blocked;
  card.querySelector('.status-count-retest').textContent = retest;
  card.querySelector('.status-count-untested').textContent = untested;
  
  // Add report button handler
  const reportBtn = card.querySelector('.run-report-btn');
  reportBtn.addEventListener('click', () => generateRunReport(run.run_id));
  
  return card;
}

/**
 * Sort plans by specified column and direction
 */
function sortPlans(plans, column, direction) {
  // Map column names to plan keys
  const columnMap = {
    'name': 'plan_name',
    'created_on': 'created_on',
    'pass_rate': 'pass_rate',
    'total_tests': 'total_tests'
  };
  
  const sortKey = columnMap[column] || 'plan_name';
  const reverse = direction === 'desc';
  
  // Create a copy to avoid mutating original
  const sortedPlans = [...plans];
  
  sortedPlans.sort((a, b) => {
    let valueA = a[sortKey];
    let valueB = b[sortKey];
    
    // Handle null/undefined values (put them at the end)
    if (valueA == null && valueB == null) return 0;
    if (valueA == null) return reverse ? -1 : 1;
    if (valueB == null) return reverse ? 1 : -1;
    
    // For string values, use case-insensitive comparison
    if (sortKey === 'plan_name') {
      valueA = valueA.toString().toLowerCase();
      valueB = valueB.toString().toLowerCase();
    }
    
    // Compare values
    if (valueA < valueB) return reverse ? 1 : -1;
    if (valueA > valueB) return reverse ? -1 : 1;
    return 0;
  });
  
  return sortedPlans;
}

/**
 * Update sort indicators in the UI
 */
function updateSortIndicators() {
  // Remove all active sort indicators
  document.querySelectorAll('.dashboard-sort-header').forEach(header => {
    header.classList.remove('sort-active', 'sort-asc', 'sort-desc');
  });
  
  // Add active indicator to current sort column
  const activeHeader = document.querySelector(`[data-sort-column="${dashboardState.sort.column}"]`);
  if (activeHeader) {
    activeHeader.classList.add('sort-active', `sort-${dashboardState.sort.direction}`);
  }
}

/**
 * Handle sort column click
 */
function handleSortClick(column) {
  // If clicking the same column, toggle direction
  if (dashboardState.sort.column === column) {
    dashboardState.sort.direction = dashboardState.sort.direction === 'asc' ? 'desc' : 'asc';
  } else {
    // New column, default to ascending (except for dates, which default to descending)
    dashboardState.sort.column = column;
    dashboardState.sort.direction = column === 'created_on' ? 'desc' : 'asc';
  }
  
  // Update UI indicators
  updateSortIndicators();
  
  // Re-render with sorted data
  renderSortedPlans();
}

/**
 * Render plans with current sort order
 */
function renderSortedPlans() {
  const container = document.getElementById('dashboardPlansList');
  if (!container) return;
  
  // Sort the cached plans
  const sortedPlans = sortPlans(
    dashboardState.cachedPlans,
    dashboardState.sort.column,
    dashboardState.sort.direction
  );
  
  // Clear container
  container.innerHTML = '';
  
  // Render sorted plan cards
  sortedPlans.forEach(plan => {
    const card = renderPlanCard(plan);
    if (card) {
      container.appendChild(card);
    }
  });
}

/**
 * Load and display dashboard plans
 */
async function loadDashboardPlans() {
  const container = document.getElementById('dashboardPlansList');
  const loading = document.getElementById('dashboardLoading');
  const empty = document.getElementById('dashboardEmpty');
  const pagination = document.getElementById('dashboardPagination');
  
  if (!container || !loading || !empty) return;
  
  // Show loading state
  loading.style.display = 'block';
  empty.style.display = 'none';
  container.innerHTML = '';
  if (pagination) pagination.style.display = 'none';
  
  try {
    // Build query parameters
    const params = new URLSearchParams({
      project: dashboardState.currentProject,
      offset: dashboardState.currentOffset,
      limit: dashboardState.currentLimit
    });
    
    if (dashboardState.filters.isCompleted !== null) {
      params.append('is_completed', dashboardState.filters.isCompleted);
    }
    
    if (dashboardState.filters.search) {
      params.append('search', dashboardState.filters.search);
    }
    
    if (dashboardState.filters.createdAfter) {
      params.append('created_after', dashboardState.filters.createdAfter);
    }
    
    if (dashboardState.filters.createdBefore) {
      params.append('created_before', dashboardState.filters.createdBefore);
    }
    
    // Fetch plans
    const response = await fetch(`/api/dashboard/plans?${params.toString()}`);
    
    if (!response.ok) {
      throw new Error(`Failed to load plans: ${response.statusText}`);
    }
    
    const data = await response.json();
    const plans = data.plans || [];
    
    // Hide loading
    loading.style.display = 'none';
    
    // Show empty state if no plans
    if (plans.length === 0) {
      empty.style.display = 'block';
      dashboardState.cachedPlans = [];
      return;
    }
    
    // Cache plans for client-side sorting
    dashboardState.cachedPlans = plans;
    
    // Sort and render plan cards
    const sortedPlans = sortPlans(plans, dashboardState.sort.column, dashboardState.sort.direction);
    sortedPlans.forEach(plan => {
      const card = renderPlanCard(plan);
      if (card) {
        container.appendChild(card);
      }
    });
    
    // Update sort indicators
    updateSortIndicators();
    
    // Update pagination
    updatePagination(data);
    
  } catch (error) {
    console.error('Error loading dashboard plans:', error);
    loading.style.display = 'none';
    empty.style.display = 'block';
    
    // Show error toast if available
    if (typeof showToast === 'function') {
      showToast('Failed to load dashboard plans. Please try again.', 'error');
    }
  }
}

/**
 * Load plan details with runs
 */
async function loadPlanDetails(planId) {
  try {
    const response = await fetch(`/api/dashboard/plan/${planId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to load plan details: ${response.statusText}`);
    }
    
    const data = await response.json();
    return data;
    
  } catch (error) {
    console.error('Error loading plan details:', error);
    if (typeof showToast === 'function') {
      showToast('Failed to load plan details. Please try again.', 'error');
    }
    return null;
  }
}

/**
 * Toggle plan runs expansion
 */
async function togglePlanRuns(planId) {
  const card = document.querySelector(`[data-plan-id="${planId}"]`);
  if (!card) return;
  
  const toggleBtn = card.querySelector('.dashboard-runs-toggle');
  const runsList = card.querySelector('.dashboard-runs-list');
  
  if (!toggleBtn || !runsList) return;
  
  // Check if already expanded
  const isExpanded = dashboardState.expandedPlans.has(planId);
  
  if (isExpanded) {
    // Collapse
    dashboardState.expandedPlans.delete(planId);
    runsList.style.display = 'none';
    toggleBtn.classList.remove('expanded');
  } else {
    // Expand
    dashboardState.expandedPlans.add(planId);
    toggleBtn.classList.add('expanded');
    runsList.style.display = 'block';
    
    // Load runs if not already loaded
    if (!dashboardState.loadedRuns.has(planId)) {
      runsList.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--muted);">Loading runs...</div>';
      
      const planDetails = await loadPlanDetails(planId);
      
      if (planDetails && planDetails.runs) {
        dashboardState.loadedRuns.set(planId, planDetails.runs);
        
        // Clear loading message
        runsList.innerHTML = '';
        
        // Render run cards
        planDetails.runs.forEach(run => {
          const runCard = renderRunCard(run);
          if (runCard) {
            runsList.appendChild(runCard);
          }
        });
      } else {
        runsList.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--muted);">Failed to load runs.</div>';
      }
    }
  }
}

/**
 * Apply current filters and reload plans
 */
function applyFilters() {
  // Reset to first page when filters change
  dashboardState.currentOffset = 0;
  
  // Clear expanded plans and loaded runs
  dashboardState.expandedPlans.clear();
  dashboardState.loadedRuns.clear();
  
  // Reload plans (sort state is preserved)
  loadDashboardPlans();
}

/**
 * Update pagination controls
 */
function updatePagination(data) {
  const pagination = document.getElementById('dashboardPagination');
  const paginationInfo = document.getElementById('dashboardPaginationInfo');
  const prevBtn = document.getElementById('dashboardPrevBtn');
  const nextBtn = document.getElementById('dashboardNextBtn');
  
  if (!pagination || !paginationInfo || !prevBtn || !nextBtn) return;
  
  const totalCount = data.total_count || 0;
  const offset = data.offset || 0;
  const limit = data.limit || 50;
  const hasMore = data.has_more || false;
  
  if (totalCount === 0) {
    pagination.style.display = 'none';
    return;
  }
  
  pagination.style.display = 'block';
  
  // Update info text
  const start = offset + 1;
  const end = Math.min(offset + limit, totalCount);
  paginationInfo.textContent = `Showing ${start}-${end} of ${totalCount} plans`;
  
  // Update button states
  prevBtn.disabled = offset === 0;
  nextBtn.disabled = !hasMore;
}

/**
 * Go to previous page
 */
function goToPreviousPage() {
  if (dashboardState.currentOffset > 0) {
    dashboardState.currentOffset = Math.max(0, dashboardState.currentOffset - dashboardState.currentLimit);
    loadDashboardPlans();
  }
}

/**
 * Go to next page
 */
function goToNextPage() {
  dashboardState.currentOffset += dashboardState.currentLimit;
  loadDashboardPlans();
}

/**
 * Refresh dashboard data
 */
async function refreshDashboard() {
  const refreshBtn = document.getElementById('dashboardRefreshBtn');
  
  if (refreshBtn) {
    refreshBtn.disabled = true;
    refreshBtn.textContent = 'Refreshing...';
  }
  
  try {
    // Clear cache on server
    await fetch('/api/dashboard/cache/clear', { method: 'POST' });
    
    // Clear local state
    dashboardState.expandedPlans.clear();
    dashboardState.loadedRuns.clear();
    
    // Reload plans
    await loadDashboardPlans();
    
    if (typeof showToast === 'function') {
      showToast('Dashboard refreshed successfully', 'success');
    }
    
  } catch (error) {
    console.error('Error refreshing dashboard:', error);
    if (typeof showToast === 'function') {
      showToast('Failed to refresh dashboard', 'error');
    }
  } finally {
    if (refreshBtn) {
      refreshBtn.disabled = false;
      refreshBtn.textContent = 'Refresh';
    }
  }
}

/**
 * Generate report for a plan
 */
async function generatePlanReport(planId) {
  try {
    // Show loading indicator if available
    const loadingOverlay = document.getElementById('loadingOverlay');
    const loadingText = document.getElementById('loadingOverlayText');
    
    if (loadingOverlay && loadingText) {
      loadingText.textContent = 'Generating plan report...';
      loadingOverlay.style.display = 'flex';
    }
    
    // Use existing /api/report endpoint for synchronous report generation
    const response = await fetch(
      `/api/report?project=${dashboardState.currentProject}&plan=${planId}`
    );
    
    if (!response.ok) {
      throw new Error(`Failed to generate report: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    // Hide loading indicator
    if (loadingOverlay) {
      loadingOverlay.style.display = 'none';
    }
    
    // Open report in new tab
    if (data.url) {
      window.open(data.url, '_blank');
      
      // Show success toast if available
      if (typeof showToast === 'function') {
        showToast('Report generated successfully', 'success');
      }
    }
    
  } catch (error) {
    console.error('Error generating plan report:', error);
    
    // Hide loading indicator
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
      loadingOverlay.style.display = 'none';
    }
    
    // Show error toast if available
    if (typeof showToast === 'function') {
      showToast('Failed to generate report. Please try again.', 'error');
    }
  }
}

/**
 * Generate report for a run
 */
async function generateRunReport(runId) {
  try {
    // Show loading indicator if available
    const loadingOverlay = document.getElementById('loadingOverlay');
    const loadingText = document.getElementById('loadingOverlayText');
    
    if (loadingOverlay && loadingText) {
      loadingText.textContent = 'Generating run report...';
      loadingOverlay.style.display = 'flex';
    }
    
    // Use existing /api/report endpoint for synchronous report generation
    const response = await fetch(
      `/api/report?project=${dashboardState.currentProject}&run=${runId}`
    );
    
    if (!response.ok) {
      throw new Error(`Failed to generate report: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    // Hide loading indicator
    if (loadingOverlay) {
      loadingOverlay.style.display = 'none';
    }
    
    // Open report in new tab
    if (data.url) {
      window.open(data.url, '_blank');
      
      // Show success toast if available
      if (typeof showToast === 'function') {
        showToast('Report generated successfully', 'success');
      }
    }
    
  } catch (error) {
    console.error('Error generating run report:', error);
    
    // Hide loading indicator
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
      loadingOverlay.style.display = 'none';
    }
    
    // Show error toast if available
    if (typeof showToast === 'function') {
      showToast('Failed to generate report. Please try again.', 'error');
    }
  }
}

/**
 * Update statistics display (placeholder for future enhancements)
 */
function updateStatisticsDisplay(statistics) {
  // This function can be extended in the future to show aggregate statistics
  // across all plans, trends, etc.
  console.log('Statistics:', statistics);
}

/**
 * Initialize dashboard
 */
function initDashboard() {
  // Get project input
  const projectInput = document.getElementById('dashboardProject');
  if (projectInput) {
    dashboardState.currentProject = parseInt(projectInput.value) || 1;
    
    // Listen for project changes
    projectInput.addEventListener('change', () => {
      dashboardState.currentProject = parseInt(projectInput.value) || 1;
      applyFilters();
    });
  }
  
  // Setup filter inputs with debouncing
  const searchInput = document.getElementById('dashboardSearch');
  if (searchInput) {
    searchInput.addEventListener('input', debounce(() => {
      dashboardState.filters.search = searchInput.value.trim();
      applyFilters();
    }, 500));
  }
  
  const completionFilter = document.getElementById('dashboardCompletionFilter');
  if (completionFilter) {
    completionFilter.addEventListener('change', () => {
      const value = completionFilter.value;
      dashboardState.filters.isCompleted = value === '' ? null : parseInt(value);
      applyFilters();
    });
  }
  
  const dateFromInput = document.getElementById('dashboardDateFrom');
  if (dateFromInput) {
    dateFromInput.addEventListener('change', () => {
      const value = dateFromInput.value;
      dashboardState.filters.createdAfter = value ? Math.floor(new Date(value).getTime() / 1000) : null;
      applyFilters();
    });
  }
  
  const dateToInput = document.getElementById('dashboardDateTo');
  if (dateToInput) {
    dateToInput.addEventListener('change', () => {
      const value = dateToInput.value;
      dashboardState.filters.createdBefore = value ? Math.floor(new Date(value).getTime() / 1000) : null;
      applyFilters();
    });
  }
  
  // Setup refresh button
  const refreshBtn = document.getElementById('dashboardRefreshBtn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', refreshDashboard);
  }
  
  // Setup pagination buttons
  const prevBtn = document.getElementById('dashboardPrevBtn');
  if (prevBtn) {
    prevBtn.addEventListener('click', goToPreviousPage);
  }
  
  const nextBtn = document.getElementById('dashboardNextBtn');
  if (nextBtn) {
    nextBtn.addEventListener('click', goToNextPage);
  }
  
  // Setup sort buttons
  document.querySelectorAll('.dashboard-sort-header').forEach(button => {
    button.addEventListener('click', () => {
      const column = button.dataset.sortColumn;
      if (column) {
        handleSortClick(column);
      }
    });
  });
  
  // Load initial data
  loadDashboardPlans();
}

// Export functions for use in main app
if (typeof window !== 'undefined') {
  window.dashboardModule = {
    init: initDashboard,
    loadPlans: loadDashboardPlans,
    loadPlanDetails: loadPlanDetails,
    applyFilters: applyFilters,
    refreshDashboard: refreshDashboard,
    updateStatisticsDisplay: updateStatisticsDisplay
  };
}
