/* eslint-disable @typescript-eslint/no-explicit-any */
import { showToast, requestJson, escapeHtml } from "./utils";

// Run edit modal state
let currentEditRunId: number | null = null;

// ========================================
// Focus Trap Utility
// ========================================

/**
 * Get all focusable elements within a container
 * Implements Requirement 7.4
 */
function getFocusableElements(container: HTMLElement): HTMLElement[] {
  const focusableSelectors = [
    'a[href]',
    'button:not([disabled])',
    'textarea:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    '[tabindex]:not([tabindex="-1"])'
  ].join(', ');

  return Array.from(container.querySelectorAll(focusableSelectors)) as HTMLElement[];
}

/**
 * Setup focus trap for a modal
 * Implements Requirement 7.4
 * 
 * @param modalId - The ID of the modal to trap focus within
 * @returns Cleanup function to remove the focus trap
 */
function setupFocusTrap(modalId: string): () => void {
  const modal = document.getElementById(modalId);
  if (!modal) return () => {};

  const handleTabKey = (e: KeyboardEvent) => {
    // Only trap Tab key
    if (e.key !== 'Tab') return;

    const focusableElements = getFocusableElements(modal);
    if (focusableElements.length === 0) return;

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    // Shift + Tab on first element -> go to last element
    if (e.shiftKey && document.activeElement === firstElement) {
      e.preventDefault();
      lastElement.focus();
    }
    // Tab on last element -> go to first element
    else if (!e.shiftKey && document.activeElement === lastElement) {
      e.preventDefault();
      firstElement.focus();
    }
  };

  // Add event listener
  modal.addEventListener('keydown', handleTabKey);

  // Return cleanup function
  return () => {
    modal.removeEventListener('keydown', handleTabKey);
  };
}

// Store focus trap cleanup functions for each modal
const focusTrapCleanups: Map<string, () => void> = new Map();

// Store the element that triggered each modal for focus restoration
const modalTriggerElements: Map<string, HTMLElement | null> = new Map();

/**
 * Activate focus trap for a modal
 * Implements Requirement 7.4
 */
function activateFocusTrap(modalId: string): void {
  // Clean up any existing trap for this modal
  deactivateFocusTrap(modalId);

  // Setup new focus trap
  const cleanup = setupFocusTrap(modalId);
  focusTrapCleanups.set(modalId, cleanup);
}

/**
 * Deactivate focus trap for a modal
 * Implements Requirement 7.4
 */
function deactivateFocusTrap(modalId: string): void {
  const cleanup = focusTrapCleanups.get(modalId);
  if (cleanup) {
    cleanup();
    focusTrapCleanups.delete(modalId);
  }
}

/**
 * Store the element that triggered a modal for focus restoration
 * Implements Requirement 7.5
 */
function storeTriggerElement(modalId: string, element: HTMLElement | null): void {
  modalTriggerElements.set(modalId, element);
}

/**
 * Restore focus to the element that triggered a modal
 * Implements Requirement 7.5
 */
function restoreFocus(modalId: string): void {
  const triggerElement = modalTriggerElements.get(modalId);
  if (triggerElement && document.contains(triggerElement)) {
    setTimeout(() => {
      triggerElement.focus();
    }, 100);
  }
  // Clean up the stored reference
  modalTriggerElements.delete(modalId);
}

// ========================================
// Breadcrumb Navigation Component
// ========================================

/**
 * Navigation context interface
 * Defines the structure for tracking current position in the hierarchy
 */
interface NavigationContext {
  level: 'plans' | 'runs' | 'cases' | 'case-edit';
  planId?: number;
  planName?: string;
  runId?: number;
  runName?: string;
  caseId?: number;
  caseTitle?: string;
}

/**
 * Generate breadcrumb HTML based on navigation context
 * Implements Requirements: 6.1, 6.2, 6.3, 6.4
 * 
 * @param context - The current navigation context
 * @returns HTML string for the breadcrumb navigation
 */
export function generateBreadcrumbHTML(context: NavigationContext): string {
  const segments: Array<{ label: string; id: string; isCurrent: boolean }> = [];

  // Always start with Plans
  segments.push({
    label: 'Plans',
    id: 'breadcrumb-plans',
    isCurrent: context.level === 'plans'
  });

  // Add Plan Name if we're at runs level or deeper
  if (context.level !== 'plans' && context.planName) {
    segments.push({
      label: context.planName,
      id: 'breadcrumb-plan-name',
      isCurrent: context.level === 'runs'
    });
  }

  // Add Run Name if we're at cases level or deeper
  if ((context.level === 'cases' || context.level === 'case-edit') && context.runName) {
    segments.push({
      label: context.runName,
      id: 'breadcrumb-run-name',
      isCurrent: context.level === 'cases'
    });
  }

  // Add Case Title if we're at case-edit level
  if (context.level === 'case-edit' && context.caseTitle) {
    segments.push({
      label: context.caseTitle,
      id: 'breadcrumb-case-title',
      isCurrent: true
    });
  }

  // Generate HTML
  const items = segments.map((segment, index) => {
    const isLast = index === segments.length - 1;
    const separator = isLast ? '' : '<li aria-hidden="true" style="color: var(--muted);">›</li>';
    
    if (segment.isCurrent) {
      // Current page - not clickable
      return `
        <li aria-current="page" style="color: var(--text); font-weight: 500;">
          <span id="${segment.id}">${escapeHtml(segment.label)}</span>
        </li>
        ${separator}
      `;
    } else {
      // Clickable link
      return `
        <li>
          <a href="#" id="${segment.id}" style="color: var(--primary); text-decoration: none; font-weight: 500;">${escapeHtml(segment.label)}</a>
        </li>
        ${separator}
      `;
    }
  }).join('');

  return `
    <nav aria-label="Breadcrumb" style="font-size: 13px; color: var(--muted);">
      <ol style="list-style: none; padding: 0; margin: 0; display: flex; align-items: center; gap: 6px;">
        ${items}
      </ol>
    </nav>
  `;
}

/**
 * Update breadcrumb in a modal
 * Implements Requirements: 6.1, 6.2, 6.3
 * 
 * @param modalId - The ID of the modal containing the breadcrumb
 * @param context - The current navigation context
 */
export function updateBreadcrumb(modalId: string, context: NavigationContext): void {
  const modal = document.getElementById(modalId);
  if (!modal) return;

  // Find the breadcrumb container in the modal
  const breadcrumbContainer = modal.querySelector('nav[aria-label="Breadcrumb"]');
  if (!breadcrumbContainer) return;

  // Generate and set new breadcrumb HTML
  breadcrumbContainer.outerHTML = generateBreadcrumbHTML(context);

  // Attach click handlers to the new breadcrumb links
  attachBreadcrumbClickHandlers(modalId, context);
}

/**
 * Attach click handlers to breadcrumb links
 * Implements Requirements: 6.4, 6.5
 * 
 * @param modalId - The ID of the modal containing the breadcrumb
 * @param context - The current navigation context
 */
function attachBreadcrumbClickHandlers(modalId: string, context: NavigationContext): void {
  const modal = document.getElementById(modalId);
  if (!modal) return;

  // Plans link - navigate to plans list
  const plansLink = modal.querySelector('#breadcrumb-plans');
  if (plansLink) {
    plansLink.addEventListener('click', (e) => {
      e.preventDefault();
      navigateToBreadcrumbLevel('plans', context);
    });
  }

  // Plan name link - navigate to runs modal
  const planNameLink = modal.querySelector('#breadcrumb-plan-name');
  if (planNameLink) {
    planNameLink.addEventListener('click', (e) => {
      e.preventDefault();
      navigateToBreadcrumbLevel('runs', context);
    });
  }

  // Run name link - navigate to run details modal
  const runNameLink = modal.querySelector('#breadcrumb-run-name');
  if (runNameLink) {
    runNameLink.addEventListener('click', (e) => {
      e.preventDefault();
      navigateToBreadcrumbLevel('cases', context);
    });
  }
}

/**
 * Navigate to a specific breadcrumb level
 * Implements Requirements: 6.4, 6.5, 12.2
 * 
 * @param level - The level to navigate to
 * @param context - The current navigation context
 */
function navigateToBreadcrumbLevel(level: 'plans' | 'runs' | 'cases', context: NavigationContext): void {
  switch (level) {
    case 'plans':
      // Close all modals and return to plans list (Requirement 6.4, 12.2)
      // hidePlanRunsModal will restore scroll position
      hideCaseEditModal();
      hideRunDetailsModal();
      hidePlanRunsModal();
      announceStatus('Navigated to plans list');
      break;

    case 'runs':
      // Close case edit and run details modals, show plan runs modal (Requirement 6.4, 6.5, 12.2)
      hideCaseEditModal();
      hideRunDetailsModal();
      if (context.planId && context.planName) {
        showPlanRunsModal(context.planId, context.planName, currentPlanEditButton || undefined);
        announceStatus(`Navigated to runs for ${context.planName}`);
      }
      break;

    case 'cases':
      // Close case edit modal, show run details modal (Requirement 6.4, 6.5)
      hideCaseEditModal();
      if (context.runId) {
        showRunDetailsModal(context.runId);
        announceStatus(`Navigated to cases for ${context.runName || 'run'}`);
      }
      break;
  }
}

/**
 * Announce status to screen readers via live region
 * Implements accessibility requirement for dynamic content updates
 */
function announceStatus(message: string) {
  const announcer = document.getElementById("manageStatusAnnouncer");
  if (announcer) {
    announcer.textContent = message;
    // Clear after announcement to allow repeated announcements
    setTimeout(() => {
      announcer.textContent = "";
    }, 1000);
  }
}

/**
 * Set aria-busy state on subsection content
 * Indicates to screen readers that content is being updated
 */
function setSubsectionBusy(subsection: "plans" | "runs" | "cases", busy: boolean) {
  const subsectionName = subsection.charAt(0).toUpperCase() + subsection.slice(1);
  const content = document.querySelector(`#manage${subsectionName}Subsection .subsection-content`);
  if (content) {
    content.setAttribute("aria-busy", busy ? "true" : "false");
  }
}

// Delete confirmation state
let deleteConfirmCallback: (() => void) | null = null;
let deleteConfirmRequireTyping = false;
let deleteConfirmExpectedName = "";

/**
 * Show delete confirmation modal
 * Implements Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
 */
export function showDeleteConfirmation(
  entityType: "plan" | "run" | "case",
  entityName: string,
  entityId: number,
  onConfirm: () => void,
  options?: {
    requireTyping?: boolean;
    cascadeWarning?: string;
  }
) {
  const modal = document.getElementById("deleteConfirmModal");
  const nameEl = document.getElementById("deleteConfirmEntityName");
  const typeEl = document.getElementById("deleteConfirmEntityType");
  const cascadeWarningEl = document.getElementById("deleteConfirmCascadeWarning");
  const cascadeMessageEl = document.getElementById("deleteConfirmCascadeMessage");
  const typeSectionEl = document.getElementById("deleteConfirmTypeSection");
  const typeNameEl = document.getElementById("deleteConfirmTypeName");
  const typeInputEl = document.getElementById("deleteConfirmTypeInput") as HTMLInputElement;
  const typeErrorEl = document.getElementById("deleteConfirmTypeError");
  const deleteBtn = document.getElementById("deleteConfirmDelete") as HTMLButtonElement;

  if (!modal || !nameEl || !typeEl) return;

  // Set entity details - prominently display entity name (Requirement 8.1)
  nameEl.textContent = entityName;
  
  // Show entity type and ID (Requirement 8.2)
  const entityTypeCapitalized = entityType.charAt(0).toUpperCase() + entityType.slice(1);
  typeEl.textContent = `${entityTypeCapitalized} ID: ${entityId}`;

  // Handle cascade warning for plans (Requirement 8.3)
  if (cascadeWarningEl && cascadeMessageEl) {
    if (options?.cascadeWarning) {
      cascadeWarningEl.classList.remove("hidden");
      cascadeMessageEl.textContent = options.cascadeWarning;
    } else {
      cascadeWarningEl.classList.add("hidden");
    }
  }

  // Handle "type to confirm" feature (Requirement 8.5 - optional)
  deleteConfirmRequireTyping = options?.requireTyping || false;
  deleteConfirmExpectedName = entityName;
  
  if (typeSectionEl && typeNameEl && typeInputEl && typeErrorEl) {
    if (deleteConfirmRequireTyping) {
      typeSectionEl.classList.remove("hidden");
      typeNameEl.textContent = entityName;
      typeInputEl.value = "";
      typeErrorEl.classList.add("hidden");
      
      // Disable delete button initially
      if (deleteBtn) {
        deleteBtn.disabled = true;
        deleteBtn.style.opacity = "0.5";
        deleteBtn.style.cursor = "not-allowed";
      }
    } else {
      typeSectionEl.classList.add("hidden");
      
      // Enable delete button
      if (deleteBtn) {
        deleteBtn.disabled = false;
        deleteBtn.style.opacity = "1";
        deleteBtn.style.cursor = "pointer";
      }
    }
  }

  // Store callback
  deleteConfirmCallback = onConfirm;

  // Store the currently focused element for focus restoration (Requirement 7.5)
  const activeElement = document.activeElement as HTMLElement;
  storeTriggerElement("deleteConfirmModal", activeElement);

  // Show modal with higher z-index to appear on top of other modals (Requirement 8.4)
  modal.classList.remove("hidden");
  modal.style.zIndex = "13000"; // Higher than case edit modal (12000) and run details modal (11000)
  
  // Activate focus trap (Requirement 7.4)
  activateFocusTrap("deleteConfirmModal");
  
  // Focus the type input if typing is required, otherwise focus cancel button
  setTimeout(() => {
    if (deleteConfirmRequireTyping && typeInputEl) {
      typeInputEl.focus();
    } else {
      const cancelBtn = document.getElementById("deleteConfirmCancel");
      if (cancelBtn) cancelBtn.focus();
    }
  }, 100);
}

/**
 * Hide delete confirmation modal
 */
export function hideDeleteConfirmation() {
  const modal = document.getElementById("deleteConfirmModal");
  const typeInputEl = document.getElementById("deleteConfirmTypeInput") as HTMLInputElement;
  const typeErrorEl = document.getElementById("deleteConfirmTypeError");
  
  if (!modal) return;

  modal.classList.add("hidden");
  
  // Reset z-index
  modal.style.zIndex = "";
  
  // Deactivate focus trap (Requirement 7.4)
  deactivateFocusTrap("deleteConfirmModal");
  
  // Restore focus to triggering element (Requirement 7.5)
  restoreFocus("deleteConfirmModal");
  
  deleteConfirmCallback = null;
  deleteConfirmRequireTyping = false;
  deleteConfirmExpectedName = "";
  
  // Reset type input
  if (typeInputEl) {
    typeInputEl.value = "";
  }
  if (typeErrorEl) {
    typeErrorEl.classList.add("hidden");
  }
}

/**
 * Execute delete confirmation
 * Validates typed name if required before executing
 */
export function executeDeleteConfirmation() {
  // If typing is required, validate the input
  if (deleteConfirmRequireTyping) {
    const typeInputEl = document.getElementById("deleteConfirmTypeInput") as HTMLInputElement;
    const typeErrorEl = document.getElementById("deleteConfirmTypeError");
    
    if (typeInputEl && typeErrorEl) {
      const typedValue = typeInputEl.value.trim();
      
      if (typedValue !== deleteConfirmExpectedName) {
        // Show error message
        typeErrorEl.classList.remove("hidden");
        typeInputEl.style.borderColor = "#ef4444";
        typeInputEl.focus();
        return; // Don't proceed with deletion
      }
    }
  }
  
  // Execute the callback
  if (deleteConfirmCallback) {
    deleteConfirmCallback();
  }
  hideDeleteConfirmation();
}

/**
 * Show delete confirmation dialog and return a promise
 * Implements Requirements: 5.1, 5.2, 5.3, 5.4
 * 
 * @param entityType - The type of entity being deleted ("plan", "run", or "case")
 * @param entityName - The name of the entity being deleted
 * @param entityId - The ID of the entity being deleted
 * @returns Promise that resolves on confirm, rejects on cancel
 */
export function confirmDelete(
  entityType: "plan" | "run" | "case",
  entityName: string,
  entityId: number
): Promise<void> {
  return new Promise((resolve, reject) => {
    // Show the delete confirmation modal
    showDeleteConfirmation(
      entityType,
      entityName,
      entityId,
      () => {
        // User confirmed - resolve the promise
        resolve();
      },
      // Add cascade warning for plans
      entityType === "plan" 
        ? { cascadeWarning: "⚠️ Warning: Deleting this plan will also permanently delete all associated test runs." }
        : undefined
    );

    // Store the original callback to handle cancellation
    const originalCallback = deleteConfirmCallback;
    
    // Override the hide function to reject on cancel
    const originalHide = hideDeleteConfirmation;
    (window as any)._tempHideDeleteConfirmation = () => {
      // Check if this is a cancellation (callback wasn't executed)
      if (deleteConfirmCallback === originalCallback) {
        reject(new Error("Delete cancelled"));
      }
      originalHide();
    };
  });
}

/**
 * Show run edit modal with pre-populated data
 * Implements Requirements: 1.1, 5.1
 * 
 * @param runId - The ID of the run to edit
 * @param runName - The current name of the run
 * @param description - The current description (optional)
 * @param refs - The current references (optional)
 */
export function showRunEditModal(
  runId: number,
  runName: string,
  description: string | null = null,
  refs: string | null = null
) {
  const modal = document.getElementById("runEditModal");
  const idInput = document.getElementById("runEditId") as HTMLInputElement;
  const nameInput = document.getElementById("runEditName") as HTMLInputElement;
  const descInput = document.getElementById("runEditDescription") as HTMLTextAreaElement;
  const refsInput = document.getElementById("runEditRefs") as HTMLInputElement;
  const nameError = document.getElementById("runEditNameError");
  const loadingOverlay = document.getElementById("runEditLoadingOverlay");

  if (!modal || !idInput || !nameInput || !descInput || !refsInput) {
    console.error("Run edit modal elements not found");
    return;
  }

  // Store current run ID
  currentEditRunId = runId;
  
  // Store the currently focused element for focus restoration (Requirement 7.5)
  const activeElement = document.activeElement as HTMLElement;
  storeTriggerElement("runEditModal", activeElement);

  // Pre-populate fields with run data (Requirement 1.1)
  idInput.value = String(runId);
  nameInput.value = runName || "";
  descInput.value = description || "";
  refsInput.value = refs || "";

  // Clear any previous validation errors
  if (nameError) {
    nameError.classList.add("hidden");
  }
  nameInput.style.borderColor = "var(--border)";

  // Hide loading overlay
  if (loadingOverlay) {
    loadingOverlay.classList.add("hidden");
  }

  // Show modal
  modal.classList.remove("hidden");
  
  // Activate focus trap (Requirement 7.4)
  activateFocusTrap("runEditModal");

  // Focus first input field on open (Requirement 5.1)
  setTimeout(() => {
    nameInput.focus();
    nameInput.select();
  }, 100);
}

/**
 * Hide run edit modal
 */
export function hideRunEditModal() {
  const modal = document.getElementById("runEditModal");
  const nameInput = document.getElementById("runEditName") as HTMLInputElement;
  const descInput = document.getElementById("runEditDescription") as HTMLTextAreaElement;
  const refsInput = document.getElementById("runEditRefs") as HTMLInputElement;
  const nameError = document.getElementById("runEditNameError");
  const loadingOverlay = document.getElementById("runEditLoadingOverlay");

  if (!modal) return;

  // Hide modal
  modal.classList.add("hidden");
  
  // Deactivate focus trap (Requirement 7.4)
  deactivateFocusTrap("runEditModal");
  
  // Restore focus to triggering element (Requirement 7.5)
  restoreFocus("runEditModal");

  // Reset state
  currentEditRunId = null;

  // Clear form fields
  if (nameInput) nameInput.value = "";
  if (descInput) descInput.value = "";
  if (refsInput) refsInput.value = "";

  // Clear validation errors
  if (nameError) {
    nameError.classList.add("hidden");
  }
  if (nameInput) {
    nameInput.style.borderColor = "var(--border)";
  }

  // Hide loading overlay
  if (loadingOverlay) {
    loadingOverlay.classList.add("hidden");
  }
}

/**
 * Validate run name - must not be empty or whitespace only
 * Implements Requirement 4.1
 * 
 * @param name - The name to validate
 * @returns true if valid, false otherwise
 */
function validateRunName(name: string): boolean {
  return name.trim().length > 0;
}

/**
 * Show validation error for run name field
 * Implements Requirement 4.3
 */
function showRunNameValidationError() {
  const nameInput = document.getElementById("runEditName") as HTMLInputElement;
  const nameError = document.getElementById("runEditNameError");

  if (nameInput) {
    nameInput.style.borderColor = "#ef4444";
  }
  if (nameError) {
    nameError.classList.remove("hidden");
  }
}

/**
 * Clear validation error for run name field
 * Implements Requirement 4.4
 */
function clearRunNameValidationError() {
  const nameInput = document.getElementById("runEditName") as HTMLInputElement;
  const nameError = document.getElementById("runEditNameError");

  if (nameInput) {
    nameInput.style.borderColor = "var(--border)";
  }
  if (nameError) {
    nameError.classList.add("hidden");
  }
}

/**
 * Save run edit - validates and sends update request
 * Implements Requirements: 1.2, 1.4, 1.5, 4.1, 4.3
 */
export async function saveRunEdit() {
  const nameInput = document.getElementById("runEditName") as HTMLInputElement;
  const descInput = document.getElementById("runEditDescription") as HTMLTextAreaElement;
  const refsInput = document.getElementById("runEditRefs") as HTMLInputElement;
  const loadingOverlay = document.getElementById("runEditLoadingOverlay");
  const saveBtn = document.getElementById("runEditSave") as HTMLButtonElement;

  if (!nameInput || !descInput || !refsInput || currentEditRunId === null) {
    console.error("Run edit form elements not found or no run selected");
    return;
  }

  const name = nameInput.value;
  const description = descInput.value;
  const refs = refsInput.value;

  // Validate name (Requirement 4.1)
  if (!validateRunName(name)) {
    showRunNameValidationError();
    nameInput.focus();
    return;
  }

  // Clear any previous validation errors
  clearRunNameValidationError();

  // Show loading overlay
  if (loadingOverlay) {
    loadingOverlay.classList.remove("hidden");
  }
  if (saveBtn) {
    saveBtn.disabled = true;
  }

  try {
    // Send PUT request to update run (Requirement 1.2)
    const response = await requestJson(`/api/manage/run/${currentEditRunId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name: name.trim(),
        description: description || null,
        refs: refs || null,
      }),
    });

    if (response.success) {
      // Show success toast
      showToast(`Run "${name.trim()}" updated successfully`, "success");
      
      // Hide modal
      hideRunEditModal();
      
      // Refresh removed - runs subsection no longer exists in hierarchical navigation
    } else {
      throw new Error(response.message || "Failed to update run");
    }
  } catch (err: any) {
    // Show error toast (Requirement 1.4)
    showToast(err?.message || "Failed to update run", "error");
  } finally {
    // Hide loading overlay
    if (loadingOverlay) {
      loadingOverlay.classList.add("hidden");
    }
    if (saveBtn) {
      saveBtn.disabled = false;
    }
  }
}

/**
 * Delete a plan
 */
export async function deletePlan(planId: number, planName: string) {
  try {
    const response = await requestJson(`/api/manage/plan/${planId}`, {
      method: "DELETE",
    });

    if (response.success) {
      showToast(`Plan "${planName}" deleted successfully`, "success");
      // Refresh the plan list
      refreshPlanList();
      return true;
    } else {
      throw new Error(response.message || "Failed to delete plan");
    }
  } catch (err: any) {
    showToast(err?.message || "Failed to delete plan", "error");
    return false;
  }
}

/**
 * Delete a run
 */
export async function deleteRun(runId: number, runName: string) {
  try {
    const response = await requestJson(`/api/manage/run/${runId}`, {
      method: "DELETE",
    });

    if (response.success) {
      showToast(`Run "${runName}" deleted successfully`, "success");
      // Refresh removed - runs subsection no longer exists in hierarchical navigation
      return true;
    } else {
      throw new Error(response.message || "Failed to delete run");
    }
  } catch (err: any) {
    showToast(err?.message || "Failed to delete run", "error");
    return false;
  }
}

/**
 * Delete a case
 */
export async function deleteCase(caseId: number, caseTitle: string) {
  try {
    const response = await requestJson(`/api/manage/case/${caseId}`, {
      method: "DELETE",
    });

    if (response.success) {
      showToast(`Case "${caseTitle}" deleted successfully`, "success");
      // Refresh removed - cases subsection no longer exists in hierarchical navigation
      return true;
    } else {
      throw new Error(response.message || "Failed to delete case");
    }
  } catch (err: any) {
    showToast(err?.message || "Failed to delete case", "error");
    return false;
  }
}

/**
 * Disable all entity action buttons for a specific entity type
 */
function disableEntityButtons(entityType: "plan" | "run" | "case") {
  const editButtons = document.querySelectorAll(`.edit-${entityType}-btn`) as NodeListOf<HTMLButtonElement>;
  const deleteButtons = document.querySelectorAll(`.delete-${entityType}-btn`) as NodeListOf<HTMLButtonElement>;
  
  editButtons.forEach(btn => btn.disabled = true);
  deleteButtons.forEach(btn => btn.disabled = true);
}

/**
 * Enable all entity action buttons for a specific entity type
 */
function enableEntityButtons(entityType: "plan" | "run" | "case") {
  const editButtons = document.querySelectorAll(`.edit-${entityType}-btn`) as NodeListOf<HTMLButtonElement>;
  const deleteButtons = document.querySelectorAll(`.delete-${entityType}-btn`) as NodeListOf<HTMLButtonElement>;
  
  editButtons.forEach(btn => btn.disabled = false);
  deleteButtons.forEach(btn => btn.disabled = false);
}

/**
 * Show error state with retry button
 * Includes accessibility attributes for screen readers
 */
function showErrorState(subsection: "plans" | "runs" | "cases", errorMessage: string, retryCallback: () => void) {
  const container = document.getElementById(`${subsection}ListContainer`);
  const loadingState = document.getElementById(`${subsection}LoadingState`);
  const emptyState = document.getElementById(`${subsection}EmptyState`);

  if (!container || !loadingState || !emptyState) return;

  // Hide loading and empty states
  loadingState.classList.add("hidden");
  emptyState.classList.add("hidden");
  
  // Show error state in container with accessibility attributes
  container.classList.remove("hidden");
  container.innerHTML = `
    <div class="error-state" role="alert" aria-live="assertive" style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 40px 20px; text-align: center;">
      <div style="font-size: 48px; margin-bottom: 12px; opacity: 0.5; line-height: 1;" aria-hidden="true">⚠️</div>
      <h4 style="margin: 0 0 8px; font-size: 16px; font-weight: 500; color: var(--text);">Failed to load ${subsection}</h4>
      <p style="margin: 0 0 16px; font-size: 14px; color: var(--muted); max-width: 400px;">${escapeHtml(errorMessage)}</p>
      <button type="button" class="refresh-btn" style="padding: 8px 16px; font-size: 13px;" aria-label="Retry loading ${subsection}">
        <span class="icon" aria-hidden="true">🔄</span> Retry
      </button>
    </div>
  `;

  // Attach retry event listener
  const retryBtn = container.querySelector(".refresh-btn");
  if (retryBtn) {
    retryBtn.addEventListener("click", retryCallback);
  }
}

/**
 * Refresh plan list in management view
 * This is called by the refresh button in the Plans subsection
 * Implements Requirements: 12.1, 12.2, 12.3, 12.4, 12.5
 */
export async function refreshPlanList() {
  // Preserve scroll position (Requirement 12.4)
  const container = document.getElementById("plansListContainer");
  const scrollPosition = container?.scrollTop || 0;
  
  await loadManagePlans();
  
  // Restore scroll position after refresh
  if (container) {
    // Use requestAnimationFrame to ensure DOM has updated
    requestAnimationFrame(() => {
      container.scrollTop = scrollPosition;
    });
  }
}

// Refresh functions for runs and cases removed - no longer needed for hierarchical navigation

// ========================================
// Plan Runs Modal Functions
// ========================================

// Current plan context for runs modal
let currentPlanId: number | null = null;
let currentPlanName: string = "";
let currentPlanEditButton: HTMLElement | null = null;

// Scroll position preservation for plans list (Requirement 9.4, 12.2)
let savedPlansScrollPosition: number = 0;

/**
 * Show plan runs modal
 * Implements Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 8.1
 * 
 * @param planId - The ID of the plan to show runs for
 * @param planName - The name of the plan (for header display)
 * @param triggerElement - The element that triggered the modal (for focus restoration)
 */
export async function showPlanRunsModal(planId: number, planName: string, triggerElement?: HTMLElement) {
  // Save plans list scroll position before opening modal (Requirement 9.4, 12.2)
  const plansListContainer = document.getElementById("plansListContainer");
  if (plansListContainer) {
    savedPlansScrollPosition = plansListContainer.scrollTop;
  }

  // Store current plan context
  currentPlanId = planId;
  currentPlanName = planName;
  currentPlanEditButton = triggerElement || null;
  
  // Store trigger element for focus restoration (Requirement 7.5)
  storeTriggerElement("planRunsModal", triggerElement || null);

  const modal = document.getElementById("planRunsModal");
  const planNameDisplay = document.getElementById("planRunsModalPlanName");
  const breadcrumbPlanName = document.getElementById("planRunsBreadcrumbPlanName");
  const loadingOverlay = document.getElementById("planRunsLoadingOverlay");
  const loadingState = document.getElementById("planRunsLoadingState");
  const errorState = document.getElementById("planRunsErrorState");
  const emptyState = document.getElementById("planRunsEmptyState");
  const runsList = document.getElementById("planRunsList");

  if (!modal) {
    console.error("Plan runs modal not found");
    return;
  }

  // Set plan name in header (Requirement 2.2)
  if (planNameDisplay) {
    planNameDisplay.textContent = planName;
  }
  if (breadcrumbPlanName) {
    breadcrumbPlanName.textContent = planName;
  }

  // Show modal
  modal.classList.remove("hidden");
  
  // Activate focus trap (Requirement 7.4)
  activateFocusTrap("planRunsModal");

  // Show loading overlay (Requirement 8.1)
  if (loadingOverlay) {
    loadingOverlay.classList.remove("hidden");
  }
  if (loadingState) {
    loadingState.classList.remove("hidden");
  }
  if (errorState) {
    errorState.classList.add("hidden");
  }
  if (emptyState) {
    emptyState.classList.add("hidden");
  }
  if (runsList) {
    runsList.classList.add("hidden");
  }

  // Announce to screen readers
  announceStatus(`Loading runs for ${planName}...`);

  try {
    // Fetch runs for the plan from API (Requirement 2.1)
    const data = await requestJson(`/api/runs?plan=${planId}&project=1`);
    const runs = Array.isArray(data.runs) ? data.runs : [];

    // Hide loading overlay
    if (loadingOverlay) {
      loadingOverlay.classList.add("hidden");
    }
    if (loadingState) {
      loadingState.classList.add("hidden");
    }

    if (runs.length === 0) {
      // Show empty state (Requirement 2.5)
      if (emptyState) {
        emptyState.classList.remove("hidden");
      }
      announceStatus("No runs found");
    } else {
      // Render runs list (Requirement 2.3, 2.4)
      renderPlanRunsList(runs);
      announceStatus(`Loaded ${runs.length} run${runs.length !== 1 ? 's' : ''}`);
    }
  } catch (err: any) {
    // Hide loading overlay
    if (loadingOverlay) {
      loadingOverlay.classList.add("hidden");
    }
    if (loadingState) {
      loadingState.classList.add("hidden");
    }

    // Show error state (Requirement 8.1)
    if (errorState) {
      errorState.classList.remove("hidden");
      const errorMessage = document.getElementById("planRunsErrorMessage");
      if (errorMessage) {
        errorMessage.textContent = err?.message || "An error occurred while loading runs.";
      }
    }

    showToast(err?.message || "Failed to load runs", "error");
    announceStatus("Failed to load runs");
  }
}

/**
 * Render runs list in the plan runs modal
 * Implements Requirements: 2.3, 2.4
 * 
 * @param runs - Array of run objects from the API
 */
function renderPlanRunsList(runs: any[]) {
  const runsList = document.getElementById("planRunsList");
  const emptyState = document.getElementById("planRunsEmptyState");
  const errorState = document.getElementById("planRunsErrorState");

  if (!runsList) return;

  // Hide empty and error states
  if (emptyState) emptyState.classList.add("hidden");
  if (errorState) errorState.classList.add("hidden");

  // Render run cards with edit/delete buttons (Requirement 2.3, 2.4)
  runsList.innerHTML = runs
    .map((run: any) => {
      const runName = escapeHtml(run.name || `Run ${run.id}`);
      const runId = run.id;
      const isCompleted = run.is_completed === true || run.is_completed === 1;
      const badgeClass = isCompleted ? 'badge-completed' : 'badge-active';
      const badgeText = isCompleted ? 'Completed' : 'Active';
      const suiteName = run.suite_name ? escapeHtml(String(run.suite_name)) : "";
      
      return `
        <div class="entity-card" role="listitem" data-entity-type="run" data-entity-id="${runId}" aria-label="Run: ${runName}, Status: ${badgeText}">
          <div class="entity-card-header">
            <div class="entity-card-title" id="run-title-${runId}">${runName}</div>
            <div class="entity-card-badges">
              <span class="badge ${badgeClass}" role="status" aria-label="Status: ${badgeText}">${badgeText}</span>
            </div>
          </div>
          <div class="entity-card-meta">
            <span class="meta-item">
              <span class="icon" aria-hidden="true">🆔</span> Run ID: ${runId}
            </span>
            ${suiteName ? `<span class="meta-item"><span class="icon" aria-hidden="true">📦</span> Suite: ${suiteName}</span>` : ''}
          </div>
          <div class="entity-card-actions" role="group" aria-label="Actions for ${runName}">
            <button type="button" class="btn-edit edit-run-btn-modal" data-run-id="${runId}" data-run-name="${escapeHtml(run.name || '')}" aria-label="Edit run ${runName}" aria-describedby="run-title-${runId}">
              <span class="icon" aria-hidden="true">✏️</span> Edit
            </button>
            <button type="button" class="btn-delete delete-run-btn-modal" data-run-id="${runId}" data-run-name="${escapeHtml(run.name || '')}" aria-label="Delete run ${runName}" aria-describedby="run-title-${runId}">
              <span class="icon" aria-hidden="true">🗑️</span> Delete
            </button>
          </div>
        </div>
      `;
    })
    .join("");

  // Show runs list
  runsList.classList.remove("hidden");

  // Attach event listeners for edit/delete buttons
  attachPlanRunsModalEventListeners();
}

/**
 * Attach event listeners to runs modal buttons
 */
function attachPlanRunsModalEventListeners() {
  // Edit buttons - open run details modal (Requirement 3.1)
  document.querySelectorAll(".edit-run-btn-modal").forEach((btn) => {
    const handleEdit = (e: Event | KeyboardEvent) => {
      e.stopPropagation();
      const target = e.currentTarget as HTMLElement;
      const runId = parseInt(target.dataset.runId || "0", 10);
      
      // Open run details modal (Requirement 5.4)
      showRunDetailsModal(runId);
    };

    btn.addEventListener("click", handleEdit);
    
    // Enter key handler (Requirement 7.3)
    btn.addEventListener("keydown", (e) => {
      const keyEvent = e as KeyboardEvent;
      if (keyEvent.key === "Enter") {
        keyEvent.preventDefault();
        handleEdit(keyEvent);
      }
    });
  });

  // Delete buttons
  document.querySelectorAll(".delete-run-btn-modal").forEach((btn) => {
    const handleDelete = (e: Event | KeyboardEvent) => {
      e.stopPropagation();
      const target = e.currentTarget as HTMLElement;
      const runId = parseInt(target.dataset.runId || "0", 10);
      const runName = target.dataset.runName || `Run ${runId}`;

      showDeleteConfirmation("run", runName, runId, async () => {
        const success = await deleteRun(runId, runName);
        if (success && currentPlanId !== null) {
          // Refresh runs list after deletion
          showPlanRunsModal(currentPlanId, currentPlanName, currentPlanEditButton || undefined);
        }
      });
    };

    btn.addEventListener("click", handleDelete);
    
    // Enter key handler (Requirement 7.2)
    btn.addEventListener("keydown", (e) => {
      const keyEvent = e as KeyboardEvent;
      if (keyEvent.key === "Enter") {
        keyEvent.preventDefault();
        handleDelete(keyEvent);
      }
    });
  });
}

/**
 * Hide plan runs modal
 * Implements Requirements: 2.6, 7.1, 7.5, 9.4, 12.2
 */
export function hidePlanRunsModal() {
  const modal = document.getElementById("planRunsModal");
  if (!modal) return;

  // Hide modal
  modal.classList.add("hidden");
  
  // Deactivate focus trap (Requirement 7.4)
  deactivateFocusTrap("planRunsModal");

  // Return focus to the element that opened the modal (Requirement 7.5)
  restoreFocus("planRunsModal");

  // Restore plans list scroll position (Requirement 9.4, 12.2)
  const plansListContainer = document.getElementById("plansListContainer");
  if (plansListContainer) {
    // Use requestAnimationFrame to ensure DOM has updated
    requestAnimationFrame(() => {
      plansListContainer.scrollTop = savedPlansScrollPosition;
    });
  }

  // Clear state
  currentPlanId = null;
  currentPlanName = "";
  currentPlanEditButton = null;

  // Announce to screen readers
  announceStatus("Returned to plans list");
}

// ========================================
// Run Details Modal Functions
// ========================================

// Current run context for run details modal
let currentRunId: number | null = null;
let currentRunName: string = "";
let currentRunIsDirty: boolean = false;

/**
 * Show run details modal
 * Implements Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 8.2
 * 
 * @param runId - The ID of the run to show details for
 */
export async function showRunDetailsModal(runId: number) {
  // Store current run context
  currentRunId = runId;
  currentRunIsDirty = false;
  
  // Store the currently focused element for focus restoration (Requirement 7.5)
  const activeElement = document.activeElement as HTMLElement;
  storeTriggerElement("runDetailsModal", activeElement);

  const modal = document.getElementById("runDetailsModal");
  const runNameDisplay = document.getElementById("runDetailsModalRunName");
  const breadcrumbPlanName = document.getElementById("runDetailsBreadcrumbPlanName");
  const breadcrumbRunName = document.getElementById("runDetailsBreadcrumbRunName");
  const loadingOverlay = document.getElementById("runDetailsLoadingOverlay");
  const formContainer = document.getElementById("runDetailsFormContainer");
  const casesContainer = document.getElementById("runDetailsCasesContainer");

  if (!modal) {
    console.error("Run details modal not found");
    return;
  }

  // Show modal
  modal.classList.remove("hidden");
  
  // Activate focus trap (Requirement 7.4)
  activateFocusTrap("runDetailsModal");

  // Show loading overlay (Requirement 8.2)
  if (loadingOverlay) {
    loadingOverlay.classList.remove("hidden");
  }
  if (formContainer) {
    formContainer.classList.add("hidden");
  }
  if (casesContainer) {
    casesContainer.classList.add("hidden");
  }

  // Set breadcrumb plan name from current plan context
  if (breadcrumbPlanName) {
    breadcrumbPlanName.textContent = currentPlanName;
  }

  // Announce to screen readers
  announceStatus("Loading run details...");

  try {
    // Fetch run details from API (Requirement 3.1)
    const runData = await requestJson(`/api/run/${runId}`);
    const run = runData.run;

    if (!run) {
      throw new Error("Run not found");
    }

    // Store run name
    currentRunName = run.name || `Run ${runId}`;

    // Set run name in header (Requirement 3.2)
    if (runNameDisplay) {
      runNameDisplay.textContent = currentRunName;
    }
    if (breadcrumbRunName) {
      breadcrumbRunName.textContent = currentRunName;
    }

    // Pre-populate form fields with run data (Requirement 3.2)
    const nameInput = document.getElementById("runDetailsName") as HTMLInputElement;
    const descInput = document.getElementById("runDetailsDescription") as HTMLTextAreaElement;
    const refsInput = document.getElementById("runDetailsRefs") as HTMLInputElement;

    if (nameInput) {
      nameInput.value = run.name || "";
    }
    if (descInput) {
      descInput.value = run.description || "";
    }
    if (refsInput) {
      refsInput.value = run.refs || "";
    }

    // Show form container
    if (formContainer) {
      formContainer.classList.remove("hidden");
    }

    // Fetch test cases for the run (Requirement 3.3)
    await loadRunDetailsCases(runId);

    // Hide loading overlay
    if (loadingOverlay) {
      loadingOverlay.classList.add("hidden");
    }

    // Show cases container
    if (casesContainer) {
      casesContainer.classList.remove("hidden");
    }

    announceStatus(`Loaded run details for ${currentRunName}`);
  } catch (err: any) {
    // Hide loading overlay
    if (loadingOverlay) {
      loadingOverlay.classList.add("hidden");
    }

    // Show error message
    showToast(err?.message || "Failed to load run details", "error");
    announceStatus("Failed to load run details");

    // Close modal on error
    hideRunDetailsModal();
  }
}

/**
 * Load test cases for the run details modal
 * Implements Requirements: 3.3, 3.4, 3.5, 8.2
 * 
 * @param runId - The ID of the run to load test cases for
 */
async function loadRunDetailsCases(runId: number) {
  const loadingState = document.getElementById("runDetailsCasesLoadingState");
  const errorState = document.getElementById("runDetailsCasesErrorState");
  const emptyState = document.getElementById("runDetailsCasesEmptyState");
  const casesList = document.getElementById("runDetailsCasesList");

  if (!loadingState || !errorState || !emptyState || !casesList) return;

  // Show loading state (Requirement 8.2)
  loadingState.classList.remove("hidden");
  errorState.classList.add("hidden");
  emptyState.classList.add("hidden");
  casesList.classList.add("hidden");

  try {
    // Fetch test cases from API (Requirement 3.3)
    const data = await requestJson(`/api/tests/${runId}`);
    const tests = Array.isArray(data.tests) ? data.tests : [];

    // Hide loading state
    loadingState.classList.add("hidden");

    if (tests.length === 0) {
      // Show empty state (Requirement 3.5)
      emptyState.classList.remove("hidden");
    } else {
      // Render test cases list (Requirement 3.3, 3.4)
      renderRunDetailsCases(tests);
    }
  } catch (err: any) {
    // Hide loading state
    loadingState.classList.add("hidden");

    // Show error state (Requirement 8.2)
    errorState.classList.remove("hidden");
    const errorMessage = document.getElementById("runDetailsCasesErrorMessage");
    if (errorMessage) {
      errorMessage.textContent = err?.message || "An error occurred while loading test cases.";
    }

    showToast(err?.message || "Failed to load test cases", "error");
  }
}

// Track selected case IDs for bulk operations
let selectedCaseIds: Set<number> = new Set();

// Track selected case IDs for adding to run
let selectedAddCaseIds: Set<number> = new Set();
let availableCasesData: any[] = [];

// Track current test for adding result
let currentTestId: number | null = null;
let currentTestTitle: string = "";

/**
 * Update bulk action toolbar visibility and count
 */
function updateBulkActionToolbar() {
  const toolbar = document.getElementById("runDetailsBulkToolbar");
  const countEl = document.getElementById("runDetailsBulkCount");
  
  if (!toolbar || !countEl) return;
  
  const count = selectedCaseIds.size;
  
  if (count > 0) {
    toolbar.classList.remove("hidden");
    countEl.textContent = String(count);
  } else {
    toolbar.classList.add("hidden");
  }
}

/**
 * Toggle case selection
 */
function toggleCaseSelection(caseId: number, checked: boolean) {
  if (checked) {
    selectedCaseIds.add(caseId);
  } else {
    selectedCaseIds.delete(caseId);
  }
  updateBulkActionToolbar();
}

/**
 * Select all cases
 */
function selectAllCases() {
  const checkboxes = document.querySelectorAll(".case-checkbox") as NodeListOf<HTMLInputElement>;
  checkboxes.forEach(checkbox => {
    checkbox.checked = true;
    const caseId = parseInt(checkbox.dataset.caseId || "0", 10);
    if (caseId > 0) {
      selectedCaseIds.add(caseId);
    }
  });
  updateBulkActionToolbar();
}

/**
 * Deselect all cases
 */
function deselectAllCases() {
  const checkboxes = document.querySelectorAll(".case-checkbox") as NodeListOf<HTMLInputElement>;
  checkboxes.forEach(checkbox => {
    checkbox.checked = false;
  });
  selectedCaseIds.clear();
  updateBulkActionToolbar();
}

/**
 * Show add test result modal
 */
export function showAddTestResultModal(testId: number, testTitle: string) {
  const modal = document.getElementById("addTestResultModal");
  const titleEl = document.getElementById("addResultTestTitle");
  const statusSelect = document.getElementById("resultStatus") as HTMLSelectElement;
  const commentInput = document.getElementById("resultComment") as HTMLTextAreaElement;
  const elapsedInput = document.getElementById("resultElapsed") as HTMLInputElement;
  const defectsInput = document.getElementById("resultDefects") as HTMLInputElement;
  const versionInput = document.getElementById("resultVersion") as HTMLInputElement;
  const attachmentsInput = document.getElementById("resultAttachments") as HTMLInputElement;
  
  if (!modal) return;
  
  // Store current test
  currentTestId = testId;
  currentTestTitle = testTitle;
  
  // Set test title
  if (titleEl) {
    titleEl.textContent = testTitle;
  }
  
  // Reset form
  if (statusSelect) statusSelect.value = "";
  if (commentInput) commentInput.value = "";
  if (elapsedInput) elapsedInput.value = "";
  if (defectsInput) defectsInput.value = "";
  if (versionInput) versionInput.value = "";
  if (attachmentsInput) attachmentsInput.value = "";
  
  // Show modal
  modal.classList.remove("hidden");
  activateFocusTrap("addTestResultModal");
  
  // Focus status select
  setTimeout(() => {
    if (statusSelect) statusSelect.focus();
  }, 100);
}

/**
 * Hide add test result modal
 */
export function hideAddTestResultModal() {
  const modal = document.getElementById("addTestResultModal");
  if (!modal) return;
  
  modal.classList.add("hidden");
  deactivateFocusTrap("addTestResultModal");
  
  currentTestId = null;
  currentTestTitle = "";
}

/**
 * Submit test result with attachments
 */
async function submitTestResult() {
  if (currentTestId === null) return;
  
  const statusSelect = document.getElementById("resultStatus") as HTMLSelectElement;
  const commentInput = document.getElementById("resultComment") as HTMLTextAreaElement;
  const elapsedInput = document.getElementById("resultElapsed") as HTMLInputElement;
  const defectsInput = document.getElementById("resultDefects") as HTMLInputElement;
  const versionInput = document.getElementById("resultVersion") as HTMLInputElement;
  const attachmentsInput = document.getElementById("resultAttachments") as HTMLInputElement;
  const loadingOverlay = document.getElementById("addResultLoadingOverlay");
  const submitBtn = document.getElementById("addResultSubmitBtn") as HTMLButtonElement;
  
  // Validate status
  if (!statusSelect || !statusSelect.value) {
    showToast("Please select a status", "error");
    if (statusSelect) statusSelect.focus();
    return;
  }
  
  const statusId = parseInt(statusSelect.value, 10);
  
  // Show loading
  if (loadingOverlay) loadingOverlay.classList.remove("hidden");
  if (submitBtn) submitBtn.disabled = true;
  
  try {
    // Step 1: Add test result
    const resultPayload: any = {
      status_id: statusId,
    };
    
    if (commentInput && commentInput.value.trim()) {
      resultPayload.comment = commentInput.value.trim();
    }
    if (elapsedInput && elapsedInput.value.trim()) {
      resultPayload.elapsed = elapsedInput.value.trim();
    }
    if (defectsInput && defectsInput.value.trim()) {
      resultPayload.defects = defectsInput.value.trim();
    }
    if (versionInput && versionInput.value.trim()) {
      resultPayload.version = versionInput.value.trim();
    }
    
    const resultResponse = await requestJson(`/api/manage/test/${currentTestId}/result`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(resultPayload),
    });
    
    if (!resultResponse.success) {
      throw new Error(resultResponse.message || "Failed to add result");
    }
    
    const resultId = resultResponse.result.id;
    
    // Step 2: Upload attachments if any
    if (attachmentsInput && attachmentsInput.files && attachmentsInput.files.length > 0) {
      const files = Array.from(attachmentsInput.files);
      let uploadedCount = 0;
      
      for (const file of files) {
        try {
          const formData = new FormData();
          formData.append("file", file);
          
          const attachResponse = await fetch(`/api/manage/result/${resultId}/attachment`, {
            method: "POST",
            body: formData,
          });
          
          if (attachResponse.ok) {
            uploadedCount++;
          }
        } catch (err) {
          console.error(`Failed to upload ${file.name}:`, err);
        }
      }
      
      if (uploadedCount > 0) {
        showToast(`Result added with ${uploadedCount} attachment(s)`, "success");
      } else {
        showToast("Result added (some attachments failed to upload)", "success");
      }
    } else {
      showToast("Test result added successfully", "success");
    }
    
    // Close modal
    hideAddTestResultModal();
    
    // Reload test cases to show updated status
    if (currentRunId !== null) {
      await loadRunDetailsCases(currentRunId);
    }
    
  } catch (err: any) {
    showToast(err?.message || "Failed to add test result", "error");
  } finally {
    if (loadingOverlay) loadingOverlay.classList.add("hidden");
    if (submitBtn) submitBtn.disabled = false;
  }
}

/**
 * Show add cases to run modal
 */
export async function showAddCasesToRunModal() {
  if (currentRunId === null) return;
  
  const modal = document.getElementById("addCasesToRunModal");
  const loadingOverlay = document.getElementById("addCasesLoadingOverlay");
  const loadingState = document.getElementById("addCasesLoadingState");
  const errorState = document.getElementById("addCasesErrorState");
  const emptyState = document.getElementById("addCasesEmptyState");
  const casesList = document.getElementById("addCasesList");
  
  if (!modal) return;
  
  // Reset state
  selectedAddCaseIds.clear();
  availableCasesData = [];
  updateAddCasesCount();
  
  // Show modal
  modal.classList.remove("hidden");
  activateFocusTrap("addCasesToRunModal");
  
  // Show loading
  if (loadingOverlay) loadingOverlay.classList.remove("hidden");
  if (loadingState) loadingState.classList.remove("hidden");
  if (errorState) errorState.classList.add("hidden");
  if (emptyState) emptyState.classList.add("hidden");
  if (casesList) casesList.classList.add("hidden");
  
  try {
    // Fetch available cases
    const response = await requestJson(`/api/manage/run/${currentRunId}/available_cases?project=1`);
    
    if (response.success) {
      availableCasesData = response.available_cases || [];
      
      if (loadingOverlay) loadingOverlay.classList.add("hidden");
      if (loadingState) loadingState.classList.add("hidden");
      
      if (availableCasesData.length === 0) {
        if (emptyState) emptyState.classList.remove("hidden");
      } else {
        renderAvailableCases(availableCasesData);
      }
    } else {
      throw new Error(response.message || "Failed to load available cases");
    }
  } catch (err: any) {
    if (loadingOverlay) loadingOverlay.classList.add("hidden");
    if (loadingState) loadingState.classList.add("hidden");
    if (errorState) {
      errorState.classList.remove("hidden");
      const errorMessage = document.getElementById("addCasesErrorMessage");
      if (errorMessage) {
        errorMessage.textContent = err?.message || "Failed to load available cases";
      }
    }
    showToast(err?.message || "Failed to load available cases", "error");
  }
}

/**
 * Hide add cases to run modal
 */
export function hideAddCasesToRunModal() {
  const modal = document.getElementById("addCasesToRunModal");
  if (!modal) return;
  
  modal.classList.add("hidden");
  deactivateFocusTrap("addCasesToRunModal");
  
  // Reset state
  selectedAddCaseIds.clear();
  availableCasesData = [];
  
  const searchInput = document.getElementById("addCasesSearch") as HTMLInputElement;
  if (searchInput) searchInput.value = "";
}

/**
 * Render available cases list
 */
function renderAvailableCases(cases: any[]) {
  const casesList = document.getElementById("addCasesList");
  if (!casesList) return;
  
  casesList.innerHTML = cases
    .map((testCase: any) => {
      const caseId = testCase.id;
      const title = escapeHtml(testCase.title || `Case ${caseId}`);
      const refs = testCase.refs ? escapeHtml(String(testCase.refs)) : "";
      const sectionName = testCase.section_name ? escapeHtml(String(testCase.section_name)) : "";
      
      return `
        <div class="add-case-item" data-case-id="${caseId}" data-case-title="${escapeHtml(testCase.title || '')}" style="padding: 12px 16px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 12px; cursor: pointer; transition: background 0.15s ease;">
          <input 
            type="checkbox" 
            class="add-case-checkbox" 
            data-case-id="${caseId}"
            style="width: 18px; height: 18px; cursor: pointer; flex-shrink: 0;"
          />
          <div style="flex: 1; min-width: 0;">
            <div style="font-weight: 600; font-size: 14px; color: var(--text); margin-bottom: 4px;">${title}</div>
            <div style="font-size: 13px; color: var(--muted); display: flex; gap: 12px; flex-wrap: wrap;">
              <span><span class="icon" aria-hidden="true">🆔</span> C${caseId}</span>
              ${refs ? `<span><span class="icon" aria-hidden="true">🔗</span> ${refs}</span>` : ''}
              ${sectionName ? `<span><span class="icon" aria-hidden="true">📁</span> ${sectionName}</span>` : ''}
            </div>
          </div>
        </div>
      `;
    })
    .join("");
  
  casesList.classList.remove("hidden");
  
  // Attach checkbox event listeners
  const checkboxes = casesList.querySelectorAll(".add-case-checkbox") as NodeListOf<HTMLInputElement>;
  checkboxes.forEach(checkbox => {
    checkbox.addEventListener("change", (e) => {
      const target = e.target as HTMLInputElement;
      const caseId = parseInt(target.dataset.caseId || "0", 10);
      toggleAddCaseSelection(caseId, target.checked);
    });
  });
  
  // Make entire row clickable
  const items = casesList.querySelectorAll(".add-case-item");
  items.forEach(item => {
    item.addEventListener("click", (e) => {
      if ((e.target as HTMLElement).classList.contains("add-case-checkbox")) return;
      const checkbox = item.querySelector(".add-case-checkbox") as HTMLInputElement;
      if (checkbox) {
        checkbox.checked = !checkbox.checked;
        const caseId = parseInt(checkbox.dataset.caseId || "0", 10);
        toggleAddCaseSelection(caseId, checkbox.checked);
      }
    });
  });
}

/**
 * Toggle case selection for adding
 */
function toggleAddCaseSelection(caseId: number, checked: boolean) {
  if (checked) {
    selectedAddCaseIds.add(caseId);
  } else {
    selectedAddCaseIds.delete(caseId);
  }
  updateAddCasesCount();
}

/**
 * Update add cases count and button state
 */
function updateAddCasesCount() {
  const countEl = document.getElementById("addCasesSelectedCount");
  const confirmBtn = document.getElementById("addCasesConfirmBtn") as HTMLButtonElement;
  
  const count = selectedAddCaseIds.size;
  
  if (countEl) {
    countEl.textContent = String(count);
  }
  
  if (confirmBtn) {
    confirmBtn.disabled = count === 0;
    confirmBtn.style.opacity = count === 0 ? "0.5" : "1";
    confirmBtn.style.cursor = count === 0 ? "not-allowed" : "pointer";
  }
}

/**
 * Select all available cases
 */
function selectAllAddCases() {
  const checkboxes = document.querySelectorAll(".add-case-checkbox") as NodeListOf<HTMLInputElement>;
  checkboxes.forEach(checkbox => {
    checkbox.checked = true;
    const caseId = parseInt(checkbox.dataset.caseId || "0", 10);
    if (caseId > 0) {
      selectedAddCaseIds.add(caseId);
    }
  });
  updateAddCasesCount();
}

/**
 * Deselect all available cases
 */
function deselectAllAddCases() {
  const checkboxes = document.querySelectorAll(".add-case-checkbox") as NodeListOf<HTMLInputElement>;
  checkboxes.forEach(checkbox => {
    checkbox.checked = false;
  });
  selectedAddCaseIds.clear();
  updateAddCasesCount();
}

/**
 * Filter available cases by search term
 */
function filterAvailableCases(searchTerm: string) {
  const term = searchTerm.toLowerCase().trim();
  
  if (!term) {
    renderAvailableCases(availableCasesData);
    return;
  }
  
  const filtered = availableCasesData.filter((testCase: any) => {
    const title = (testCase.title || "").toLowerCase();
    const id = String(testCase.id);
    const refs = (testCase.refs || "").toLowerCase();
    
    return title.includes(term) || id.includes(term) || refs.includes(term);
  });
  
  renderAvailableCases(filtered);
}

/**
 * Add selected cases to run
 */
async function addSelectedCasesToRun() {
  if (selectedAddCaseIds.size === 0 || currentRunId === null) return;
  
  const count = selectedAddCaseIds.size;
  const caseIdsArray = Array.from(selectedAddCaseIds);
  const confirmBtn = document.getElementById("addCasesConfirmBtn") as HTMLButtonElement;
  
  try {
    if (confirmBtn) confirmBtn.disabled = true;
    
    const response = await requestJson(`/api/manage/run/${currentRunId}/add_cases`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        case_ids: caseIdsArray,
      }),
    });
    
    if (response.success) {
      const message = response.skipped_count > 0 
        ? `Added ${response.added_count} case(s) (${response.skipped_count} already in run)`
        : `Added ${response.added_count} case(s) to run`;
      
      showToast(message, "success");
      
      // Close modal
      hideAddCasesToRunModal();
      
      // Reload cases list in run details modal
      await loadRunDetailsCases(currentRunId);
    } else {
      throw new Error(response.message || "Failed to add cases to run");
    }
  } catch (err: any) {
    // Check if it's a 403 error (TestRail limitation)
    const errorMessage = err?.message || "Failed to add cases to run";
    
    if (errorMessage.includes("403") || errorMessage.includes("test results")) {
      showToast("⚠️ Cannot modify this run - it has test results. TestRail doesn't allow adding cases to runs with results.", "error");
    } else {
      showToast(errorMessage, "error");
    }
  } finally {
    if (confirmBtn) confirmBtn.disabled = false;
  }
}

/**
 * Remove selected cases from run
 */
async function removeSelectedCasesFromRun() {
  if (selectedCaseIds.size === 0 || currentRunId === null) return;
  
  const count = selectedCaseIds.size;
  const caseIdsArray = Array.from(selectedCaseIds);
  
  // Show confirmation
  const confirmed = confirm(`Remove ${count} test case${count > 1 ? 's' : ''} from this run?\n\nNote: This will only remove them from the run, not delete them from the project.`);
  
  if (!confirmed) return;
  
  try {
    // Show loading state
    const toolbar = document.getElementById("runDetailsBulkToolbar");
    const removeBtn = document.getElementById("runDetailsBulkRemove") as HTMLButtonElement;
    if (removeBtn) removeBtn.disabled = true;
    
    // Send request to remove cases
    const response = await requestJson(`/api/manage/run/${currentRunId}/remove_cases`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        case_ids: caseIdsArray,
      }),
    });
    
    if (response.success) {
      showToast(`Removed ${response.removed_count} case(s) from run`, "success");
      
      // Clear selection
      selectedCaseIds.clear();
      updateBulkActionToolbar();
      
      // Reload cases list
      await loadRunDetailsCases(currentRunId);
    } else {
      throw new Error(response.message || "Failed to remove cases from run");
    }
  } catch (err: any) {
    // Check if it's a 403 error (TestRail limitation)
    const errorMessage = err?.message || "Failed to remove cases from run";
    
    if (errorMessage.includes("403") || errorMessage.includes("test results")) {
      showToast("⚠️ Cannot modify this run - it has test results. TestRail doesn't allow removing cases from runs with results.", "error");
    } else {
      showToast(errorMessage, "error");
    }
  } finally {
    const removeBtn = document.getElementById("runDetailsBulkRemove") as HTMLButtonElement;
    if (removeBtn) removeBtn.disabled = false;
  }
}

/**
 * Render test cases in the run details modal
 * Implements Requirements: 3.3, 3.4
 * Updated to support multi-select for bulk removal
 * 
 * @param tests - Array of test case objects from the API
 */
function renderRunDetailsCases(tests: any[]) {
  const casesList = document.getElementById("runDetailsCasesList");
  const emptyState = document.getElementById("runDetailsCasesEmptyState");
  const errorState = document.getElementById("runDetailsCasesErrorState");

  if (!casesList) return;

  // Hide empty and error states
  if (emptyState) emptyState.classList.add("hidden");
  if (errorState) errorState.classList.add("hidden");

  // Clear selection when re-rendering
  selectedCaseIds.clear();
  updateBulkActionToolbar();

  // Render test case cards with checkboxes and edit button (removed delete button)
  casesList.innerHTML = tests
    .map((test: any) => {
      const testTitle = escapeHtml(test.title || `Test ${test.id}`);
      const testId = test.id;
      const caseId = test.case_id;
      const statusId = test.status_id || 3;
      const statusName = escapeHtml(test.status_name || "Untested");
      const refs = test.refs ? escapeHtml(String(test.refs)) : "";
      const badgeClass = getStatusBadgeClass(statusId);
      
      return `
        <div class="entity-card" role="listitem" data-entity-type="test" data-entity-id="${testId}" data-case-id="${caseId}" aria-label="Test: ${testTitle}, Status: ${statusName}">
          <div class="entity-card-header" style="display: flex; align-items: flex-start; gap: 12px;">
            <input 
              type="checkbox" 
              class="case-checkbox" 
              data-case-id="${caseId}"
              aria-label="Select ${testTitle}"
              style="margin-top: 4px; width: 18px; height: 18px; cursor: pointer; flex-shrink: 0;"
            />
            <div style="flex: 1; min-width: 0;">
              <div class="entity-card-title" id="test-title-${testId}">${testTitle}</div>
              <div class="entity-card-badges" style="margin-top: 6px;">
                <span class="badge ${badgeClass}" role="status" aria-label="Status: ${statusName}">${statusName}</span>
              </div>
            </div>
          </div>
          <div class="entity-card-meta">
            <span class="meta-item">
              <span class="icon" aria-hidden="true">🆔</span> Test ID: ${testId}
            </span>
            <span class="meta-item">
              <span class="icon" aria-hidden="true">📋</span> Case ID: ${caseId}
            </span>
            ${refs ? `<span class="meta-item"><span class="icon" aria-hidden="true">🔗</span> Refs: ${refs}</span>` : ''}
          </div>
          <div class="entity-card-actions" role="group" aria-label="Actions for ${testTitle}">
            <button type="button" class="btn-edit add-result-btn-modal" data-test-id="${testId}" data-test-title="${escapeHtml(test.title || '')}" aria-label="Add result for ${testTitle}" aria-describedby="test-title-${testId}" style="background: var(--primary); color: white; border-color: var(--primary);">
              <span class="icon" aria-hidden="true">✅</span> Add Result
            </button>
            <button type="button" class="btn-edit edit-case-btn-modal" data-case-id="${caseId}" data-case-title="${escapeHtml(test.title || '')}" data-case-refs="${escapeHtml(test.refs || '')}" aria-label="Edit case ${testTitle}" aria-describedby="test-title-${testId}">
              <span class="icon" aria-hidden="true">✏️</span> Edit
            </button>
          </div>
        </div>
      `;
    })
    .join("");

  // Show cases list
  casesList.classList.remove("hidden");

  // Attach checkbox event listeners
  const checkboxes = document.querySelectorAll(".case-checkbox") as NodeListOf<HTMLInputElement>;
  checkboxes.forEach(checkbox => {
    checkbox.addEventListener("change", (e) => {
      const target = e.target as HTMLInputElement;
      const caseId = parseInt(target.dataset.caseId || "0", 10);
      toggleCaseSelection(caseId, target.checked);
    });
  });

  // Event listeners for edit buttons are attached via event delegation in initRunDetailsModal()
}

/**
 * Save run details
 * Implements Requirements: 3.6
 */
export async function saveRunDetails() {
  const nameInput = document.getElementById("runDetailsName") as HTMLInputElement;
  const descInput = document.getElementById("runDetailsDescription") as HTMLTextAreaElement;
  const refsInput = document.getElementById("runDetailsRefs") as HTMLInputElement;
  const saveBtn = document.getElementById("runDetailsSaveBtn") as HTMLButtonElement;

  if (!nameInput || !descInput || !refsInput || currentRunId === null) {
    console.error("Run details form elements not found or no run selected");
    return;
  }

  const name = nameInput.value;
  const description = descInput.value;
  const refs = refsInput.value;

  // Validate name (must not be empty)
  if (!name.trim()) {
    showToast("Run name cannot be empty", "error");
    nameInput.focus();
    return;
  }

  // Disable save button during save
  if (saveBtn) {
    saveBtn.disabled = true;
  }

  try {
    // Send PUT request to update run (Requirement 3.6)
    const response = await requestJson(`/api/manage/run/${currentRunId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name: name.trim(),
        description: description || null,
        refs: refs || null,
      }),
    });

    if (response.success) {
      // Show success toast
      showToast(`Run "${name.trim()}" updated successfully`, "success");
      
      // Update current run name
      currentRunName = name.trim();
      
      // Update modal header
      const runNameDisplay = document.getElementById("runDetailsModalRunName");
      const breadcrumbRunName = document.getElementById("runDetailsBreadcrumbRunName");
      if (runNameDisplay) {
        runNameDisplay.textContent = currentRunName;
      }
      if (breadcrumbRunName) {
        breadcrumbRunName.textContent = currentRunName;
      }
      
      // Clear dirty flag
      currentRunIsDirty = false;
      
      // Refresh test cases list (Requirement 3.6)
      await loadRunDetailsCases(currentRunId);
    } else {
      throw new Error(response.message || "Failed to update run");
    }
  } catch (err: any) {
    // Show error toast
    showToast(err?.message || "Failed to update run", "error");
  } finally {
    // Re-enable save button
    if (saveBtn) {
      saveBtn.disabled = false;
    }
  }
}

/**
 * Handle back navigation from run details modal
 * Implements Requirements: 3.7, 12.2
 */
export async function handleRunDetailsBack() {
  // Check if there are unsaved changes
  if (currentRunIsDirty) {
    // Save changes before navigating back (Requirement 3.7)
    await saveRunDetails();
  }

  // Close run details modal
  hideRunDetailsModal();

  // Return to plan runs modal (Requirement 3.7, 12.2)
  // Note: showPlanRunsModal will preserve the plans list scroll position
  if (currentPlanId !== null) {
    showPlanRunsModal(currentPlanId, currentPlanName, currentPlanEditButton || undefined);
  }
}

/**
 * Hide run details modal
 * Implements Requirements: 3.7
 */
export function hideRunDetailsModal() {
  const modal = document.getElementById("runDetailsModal");
  if (!modal) return;

  // Hide modal
  modal.classList.add("hidden");
  
  // Deactivate focus trap (Requirement 7.4)
  deactivateFocusTrap("runDetailsModal");
  
  // Restore focus to triggering element (Requirement 7.5)
  restoreFocus("runDetailsModal");

  // Clear state
  currentRunId = null;
  currentRunName = "";
  currentRunIsDirty = false;

  // Announce to screen readers
  announceStatus("Closed run details");
}

/**
 * Attach event listeners to plan buttons
 */
function attachPlanEventListeners() {
  // Delete buttons
  document.querySelectorAll(".delete-plan-btn").forEach((btn) => {
    const handleDelete = (e: Event | KeyboardEvent) => {
      const target = e.currentTarget as HTMLElement;
      const planId = parseInt(target.dataset.planId || "0", 10);
      const planName = target.dataset.planName || `Plan ${planId}`;

      // Show delete confirmation with cascade warning for plans (Requirement 8.3)
      showDeleteConfirmation("plan", planName, planId, () => {
        deletePlan(planId, planName);
      }, {
        cascadeWarning: "⚠️ Warning: Deleting this plan will also permanently delete all associated test runs."
      });
    };

    btn.addEventListener("click", handleDelete);
    
    // Enter key handler (Requirement 7.2)
    btn.addEventListener("keydown", (e) => {
      const keyEvent = e as KeyboardEvent;
      if (keyEvent.key === "Enter") {
        keyEvent.preventDefault();
        handleDelete(keyEvent);
      }
    });
  });

  // Edit buttons - open plan runs modal (Requirement 2.1)
  document.querySelectorAll(".edit-plan-btn").forEach((btn) => {
    const handleEdit = (e: Event | KeyboardEvent) => {
      const target = e.currentTarget as HTMLElement;
      const planId = parseInt(target.dataset.planId || "0", 10);
      const planName = target.dataset.planName || `Plan ${planId}`;
      
      // Open plan runs modal
      showPlanRunsModal(planId, planName, target);
    };

    btn.addEventListener("click", handleEdit);
    
    // Enter key handler (Requirement 7.3)
    btn.addEventListener("keydown", (e) => {
      const keyEvent = e as KeyboardEvent;
      if (keyEvent.key === "Enter") {
        keyEvent.preventDefault();
        handleEdit(keyEvent);
      }
    });
  });
}

/**
 * Attach event listeners to run buttons
 */
function attachRunEventListeners() {
  // Run card click handler - opens test cases view (Requirement 2.1)
  // Click on run card (not edit/delete buttons) opens cases view
  document.querySelectorAll('.entity-card[data-entity-type="run"]').forEach((card) => {
    card.addEventListener("click", (e) => {
      // Don't trigger if clicking on a button
      const target = e.target as HTMLElement;
      if (target.closest("button")) {
        return;
      }
      
      const cardEl = e.currentTarget as HTMLElement;
      const runId = parseInt(cardEl.dataset.entityId || "0", 10);
      // Get run name from the title element
      const titleEl = cardEl.querySelector(".entity-card-title");
      const runName = titleEl?.textContent || `Run ${runId}`;
      
      showTestCasesView(runId, runName);
    });
    
    // Add cursor pointer to indicate clickable
    (card as HTMLElement).style.cursor = "pointer";
  });

  // Delete buttons
  document.querySelectorAll(".delete-run-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation(); // Prevent card click from triggering
      const target = e.currentTarget as HTMLElement;
      const runId = parseInt(target.dataset.runId || "0", 10);
      const runName = target.dataset.runName || `Run ${runId}`;

      showDeleteConfirmation("run", runName, runId, () => {
        deleteRun(runId, runName);
      });
    });
  });

  // Edit buttons - open run edit modal (Requirement 1.1)
  document.querySelectorAll(".edit-run-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation(); // Prevent card click from triggering
      const target = e.currentTarget as HTMLElement;
      const runId = parseInt(target.dataset.runId || "0", 10);
      const runName = target.dataset.runName || "";
      const description = target.dataset.runDescription || null;
      const refs = target.dataset.runRefs || null;
      
      showRunEditModal(runId, runName, description, refs);
    });
  });

  // View Cases buttons - show test cases for run (Requirement 2.1)
  document.querySelectorAll(".view-cases-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation(); // Prevent card click from triggering
      const target = e.currentTarget as HTMLElement;
      const runId = parseInt(target.dataset.runId || "0", 10);
      const runName = target.dataset.runName || `Run ${runId}`;
      
      showTestCasesView(runId, runName);
    });
  });
}

/**
 * Attach event listeners to case buttons
 */
function attachCaseEventListeners() {
  // Delete buttons
  document.querySelectorAll(".delete-case-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const target = e.currentTarget as HTMLElement;
      const caseId = parseInt(target.dataset.caseId || "0", 10);
      const caseTitle = target.dataset.caseTitle || `Case ${caseId}`;

      showDeleteConfirmation("case", caseTitle, caseId, () => {
        deleteCase(caseId, caseTitle);
      });
    });
  });

  // Edit buttons - open case edit modal (Requirement 3.1)
  document.querySelectorAll(".edit-case-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation(); // Prevent card click from triggering
      const target = e.currentTarget as HTMLElement;
      const caseId = parseInt(target.dataset.caseId || "0", 10);
      const caseTitle = target.dataset.caseTitle || "";
      const refs = target.dataset.caseRefs || null;
      const bddScenarios = target.dataset.caseBddScenarios || null;
      
      showCaseEditModal(caseId, caseTitle, refs, bddScenarios);
    });
  });
}

// Debounce timer references
let plansSearchDebounceTimer: number | null = null;
let casesSearchDebounceTimer: number | null = null;

/**
 * Debounce function - delays execution until after wait milliseconds have elapsed
 * since the last time it was invoked
 */
function debounce(func: () => void, wait: number): () => void {
  let timeout: number | null = null;
  return () => {
    if (timeout !== null) {
      clearTimeout(timeout);
    }
    timeout = window.setTimeout(() => {
      func();
    }, wait);
  };
}

/**
 * Initialize management functionality
 */
export function initManagement() {
  // Delete confirmation modal event listeners
  document.getElementById("deleteConfirmCancel")?.addEventListener("click", hideDeleteConfirmation);
  document.getElementById("deleteConfirmClose")?.addEventListener("click", hideDeleteConfirmation);
  document.getElementById("deleteConfirmDelete")?.addEventListener("click", executeDeleteConfirmation);

  // Close modal on backdrop click
  document.getElementById("deleteConfirmModal")?.addEventListener("click", (e) => {
    if ((e.target as HTMLElement)?.id === "deleteConfirmModal") {
      hideDeleteConfirmation();
    }
  });
  
  // Type to confirm input validation
  const typeInputEl = document.getElementById("deleteConfirmTypeInput") as HTMLInputElement;
  const deleteBtn = document.getElementById("deleteConfirmDelete") as HTMLButtonElement;
  const typeErrorEl = document.getElementById("deleteConfirmTypeError");
  
  if (typeInputEl && deleteBtn) {
    typeInputEl.addEventListener("input", () => {
      const typedValue = typeInputEl.value.trim();
      
      if (deleteConfirmRequireTyping) {
        if (typedValue === deleteConfirmExpectedName) {
          // Enable delete button
          deleteBtn.disabled = false;
          deleteBtn.style.opacity = "1";
          deleteBtn.style.cursor = "pointer";
          typeInputEl.style.borderColor = "#10b981"; // Green border
          if (typeErrorEl) {
            typeErrorEl.classList.add("hidden");
          }
        } else {
          // Disable delete button
          deleteBtn.disabled = true;
          deleteBtn.style.opacity = "0.5";
          deleteBtn.style.cursor = "not-allowed";
          typeInputEl.style.borderColor = "var(--border)";
        }
      }
    });
    
    // Allow Enter key to submit if name matches
    typeInputEl.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !deleteBtn.disabled) {
        e.preventDefault();
        executeDeleteConfirmation();
      }
    });
  }
  
  // Escape key to close modal
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      const modal = document.getElementById("deleteConfirmModal");
      if (modal && !modal.classList.contains("hidden")) {
        hideDeleteConfirmation();
      }
    }
  });

  // Create Section toggle button event listener
  const createSectionToggle = document.querySelector(".create-section-toggle");
  const createSectionContent = document.getElementById("createSectionContent");
  
  if (createSectionToggle && createSectionContent) {
    createSectionToggle.addEventListener("click", () => {
      const isExpanded = createSectionToggle.getAttribute("aria-expanded") === "true";
      
      // Toggle the expanded state
      createSectionToggle.setAttribute("aria-expanded", isExpanded ? "false" : "true");
      
      // Toggle the content visibility
      if (isExpanded) {
        createSectionContent.classList.add("hidden");
      } else {
        createSectionContent.classList.remove("hidden");
      }
      
      // Update the toggle indicator
      const indicator = createSectionToggle.querySelector(".toggle-indicator");
      if (indicator) {
        indicator.textContent = isExpanded ? "▼" : "▲";
      }
    });
  }

  // Refresh button event listeners for new Manage section
  document.getElementById("refreshPlansBtn")?.addEventListener("click", refreshPlanList);

  // Search filtering for Plans subsection with debouncing (300ms)
  const plansSearchInput = document.getElementById("plansSearch") as HTMLInputElement | null;
  if (plansSearchInput) {
    const debouncedPlansFilter = debounce(() => {
      filterPlans(plansSearchInput.value);
    }, 300);
    
    plansSearchInput.addEventListener("input", debouncedPlansFilter);
  }

  // Run Edit Modal event listeners
  initRunEditModal();

  // Case Edit Modal event listeners
  initCaseEditModal();

  // Test Cases View event listeners
  initTestCasesView();

  // Plan Runs Modal event listeners
  initPlanRunsModal();

  // Run Details Modal event listeners
  initRunDetailsModal();

  // Global keyboard handler for case edit modal (Requirement 5.2, 5.3)
  document.addEventListener("keydown", (e) => {
    const caseModal = document.getElementById("caseEditModal");
    if (!caseModal || caseModal.classList.contains("hidden")) return;

    if (e.key === "Escape") {
      e.preventDefault();
      hideCaseEditModal();
    }

    // Enter key in single-line inputs submits form (Requirement 5.3)
    // But NOT in textarea (BDD scenarios field)
    if (e.key === "Enter") {
      const activeElement = document.activeElement;
      // Only submit if focus is on a single-line input (not textarea)
      if (activeElement && activeElement.tagName === "INPUT" && 
          (activeElement as HTMLInputElement).type === "text") {
        e.preventDefault();
        saveCaseEdit();
      }
    }
  });
}

/**
 * Initialize Plan Runs Modal event listeners
 * Implements Requirements: 2.6, 7.1, 7.5
 */
function initPlanRunsModal() {
  // Close button
  document.getElementById("planRunsModalClose")?.addEventListener("click", hidePlanRunsModal);
  document.getElementById("planRunsCloseBtn")?.addEventListener("click", hidePlanRunsModal);

  // Close modal on backdrop click (Requirement 2.6)
  document.getElementById("planRunsModal")?.addEventListener("click", (e) => {
    if ((e.target as HTMLElement)?.id === "planRunsModal") {
      hidePlanRunsModal();
    }
  });

  // Breadcrumb "Plans" link - close modal and return to plans list
  document.getElementById("planRunsBreadcrumbPlans")?.addEventListener("click", (e) => {
    e.preventDefault();
    const context: NavigationContext = {
      level: 'runs',
      planId: currentPlanId || undefined,
      planName: currentPlanName || undefined
    };
    navigateToBreadcrumbLevel('plans', context);
  });

  // Retry button in error state
  document.getElementById("planRunsRetryBtn")?.addEventListener("click", () => {
    if (currentPlanId !== null) {
      showPlanRunsModal(currentPlanId, currentPlanName, currentPlanEditButton || undefined);
    }
  });

  // Escape key closes modal (Requirement 7.1)
  document.addEventListener("keydown", (e) => {
    const modal = document.getElementById("planRunsModal");
    if (!modal || modal.classList.contains("hidden")) return;

    if (e.key === "Escape") {
      e.preventDefault();
      hidePlanRunsModal();
    }
  });
}

/**
 * Initialize Run Details Modal event listeners
 * Implements Requirements: 3.6, 3.7, 7.1
 */
function initRunDetailsModal() {
  // Close button
  document.getElementById("runDetailsModalClose")?.addEventListener("click", () => {
    handleRunDetailsBack();
  });

  // Back buttons
  document.getElementById("runDetailsBackBtn")?.addEventListener("click", () => {
    handleRunDetailsBack();
  });
  document.getElementById("runDetailsBackFooterBtn")?.addEventListener("click", () => {
    handleRunDetailsBack();
  });

  // Save button (Requirement 3.6)
  document.getElementById("runDetailsSaveBtn")?.addEventListener("click", saveRunDetails);

  // Close modal on backdrop click
  document.getElementById("runDetailsModal")?.addEventListener("click", (e) => {
    if ((e.target as HTMLElement)?.id === "runDetailsModal") {
      handleRunDetailsBack();
    }
  });

  // Breadcrumb navigation
  document.getElementById("runDetailsBreadcrumbPlans")?.addEventListener("click", (e) => {
    e.preventDefault();
    const context: NavigationContext = {
      level: 'cases',
      planId: currentPlanId || undefined,
      planName: currentPlanName || undefined,
      runId: currentRunId || undefined,
      runName: currentRunName || undefined
    };
    navigateToBreadcrumbLevel('plans', context);
  });

  document.getElementById("runDetailsBreadcrumbPlanName")?.addEventListener("click", (e) => {
    e.preventDefault();
    const context: NavigationContext = {
      level: 'cases',
      planId: currentPlanId || undefined,
      planName: currentPlanName || undefined,
      runId: currentRunId || undefined,
      runName: currentRunName || undefined
    };
    navigateToBreadcrumbLevel('runs', context);
  });

  // Retry button in error state
  document.getElementById("runDetailsCasesRetryBtn")?.addEventListener("click", () => {
    if (currentRunId !== null) {
      loadRunDetailsCases(currentRunId);
    }
  });

  // Track form changes to set dirty flag
  const nameInput = document.getElementById("runDetailsName") as HTMLInputElement;
  const descInput = document.getElementById("runDetailsDescription") as HTMLTextAreaElement;
  const refsInput = document.getElementById("runDetailsRefs") as HTMLInputElement;

  const markDirty = () => {
    currentRunIsDirty = true;
  };

  if (nameInput) {
    nameInput.addEventListener("input", markDirty);
  }
  if (descInput) {
    descInput.addEventListener("input", markDirty);
  }
  if (refsInput) {
    refsInput.addEventListener("input", markDirty);
  }

  // Escape key closes modal (Requirement 7.1)
  document.addEventListener("keydown", (e) => {
    const modal = document.getElementById("runDetailsModal");
    if (!modal || modal.classList.contains("hidden")) return;

    if (e.key === "Escape") {
      e.preventDefault();
      handleRunDetailsBack();
    }
  });

  // Add cases button
  document.getElementById("runDetailsAddCases")?.addEventListener("click", showAddCasesToRunModal);
  
  // Bulk action buttons
  document.getElementById("runDetailsSelectAll")?.addEventListener("click", selectAllCases);
  document.getElementById("runDetailsDeselectAll")?.addEventListener("click", deselectAllCases);
  document.getElementById("runDetailsBulkRemove")?.addEventListener("click", removeSelectedCasesFromRun);
  
  // Add cases modal event listeners
  document.getElementById("addCasesToRunModalClose")?.addEventListener("click", hideAddCasesToRunModal);
  document.getElementById("addCasesCancelBtn")?.addEventListener("click", hideAddCasesToRunModal);
  document.getElementById("addCasesConfirmBtn")?.addEventListener("click", addSelectedCasesToRun);
  document.getElementById("addCasesSelectAll")?.addEventListener("click", selectAllAddCases);
  document.getElementById("addCasesDeselectAll")?.addEventListener("click", deselectAllAddCases);
  
  // Search input for add cases modal
  const addCasesSearch = document.getElementById("addCasesSearch") as HTMLInputElement;
  if (addCasesSearch) {
    addCasesSearch.addEventListener("input", (e) => {
      const target = e.target as HTMLInputElement;
      filterAvailableCases(target.value);
    });
  }
  
  // Close add cases modal on backdrop click
  document.getElementById("addCasesToRunModal")?.addEventListener("click", (e) => {
    if ((e.target as HTMLElement)?.id === "addCasesToRunModal") {
      hideAddCasesToRunModal();
    }
  });
  
  // Escape key closes add cases modal
  document.addEventListener("keydown", (e) => {
    const modal = document.getElementById("addCasesToRunModal");
    if (!modal || modal.classList.contains("hidden")) return;
    
    if (e.key === "Escape") {
      e.preventDefault();
      hideAddCasesToRunModal();
    }
  });

  // Add result modal event listeners
  document.getElementById("addTestResultModalClose")?.addEventListener("click", hideAddTestResultModal);
  document.getElementById("addResultCancelBtn")?.addEventListener("click", hideAddTestResultModal);
  document.getElementById("addResultSubmitBtn")?.addEventListener("click", submitTestResult);
  
  // Close add result modal on backdrop click
  document.getElementById("addTestResultModal")?.addEventListener("click", (e) => {
    if ((e.target as HTMLElement)?.id === "addTestResultModal") {
      hideAddTestResultModal();
    }
  });
  
  // Escape key closes add result modal
  document.addEventListener("keydown", (e) => {
    const modal = document.getElementById("addTestResultModal");
    if (!modal || modal.classList.contains("hidden")) return;
    
    if (e.key === "Escape") {
      e.preventDefault();
      hideAddTestResultModal();
    }
  });

  // Event delegation for case edit and add result buttons (Requirement 4.1)
  // Using event delegation to avoid duplicate listeners when cases list is re-rendered
  const casesList = document.getElementById("runDetailsCasesList");
  if (casesList) {
    casesList.addEventListener("click", async (e) => {
      const target = e.target as HTMLElement;
      
      // Handle add result button clicks
      if (target.closest(".add-result-btn-modal")) {
        e.stopPropagation();
        const btn = target.closest(".add-result-btn-modal") as HTMLElement;
        const testId = parseInt(btn.dataset.testId || "0", 10);
        const testTitle = btn.dataset.testTitle || "";
        
        showAddTestResultModal(testId, testTitle);
      }
      
      // Handle edit button clicks
      if (target.closest(".edit-case-btn-modal")) {
        e.stopPropagation();
        const btn = target.closest(".edit-case-btn-modal") as HTMLElement;
        const caseId = parseInt(btn.dataset.caseId || "0", 10);
        const caseTitle = btn.dataset.caseTitle || "";
        const refs = btn.dataset.caseRefs || null;
        
        // Disable button and show loading state (Requirement 8.2)
        const btnElement = btn as HTMLButtonElement;
        const originalText = btnElement.innerHTML;
        btnElement.disabled = true;
        btnElement.innerHTML = '<span class="icon" aria-hidden="true">⏳</span> Loading...';
        
        // Fetch full case details to get BDD scenarios
        try {
          const response = await requestJson(`/api/manage/case/${caseId}`);
          const caseData = response.case;
          
          if (caseData) {
            // Open case edit modal with full data and navigation context
            showCaseEditModal(
              caseId,
              caseData.title || caseTitle,
              caseData.refs || refs,
              caseData.custom_bdd_scenario || null
            );
          } else {
            // Fallback to basic data if full details not available
            showCaseEditModal(caseId, caseTitle, refs, null);
          }
        } catch (err: any) {
          console.error("Failed to fetch case details:", err);
          showToast(err?.message || "Failed to load case details", "error");
          // Fallback to basic data on error
          showCaseEditModal(caseId, caseTitle, refs, null);
        } finally {
          // Restore button state
          btnElement.disabled = false;
          btnElement.innerHTML = originalText;
        }
      }
    });
  }
}

/**
 * Initialize Run Edit Modal event listeners
 * Implements Requirements: 1.2, 1.3, 4.1, 4.3, 4.4, 5.2, 5.3
 */
function initRunEditModal() {
  // Cancel button closes modal (Requirement 1.3)
  document.getElementById("runEditCancel")?.addEventListener("click", hideRunEditModal);
  document.getElementById("runEditModalClose")?.addEventListener("click", hideRunEditModal);

  // Close modal on backdrop click (Requirement 1.3)
  document.getElementById("runEditModal")?.addEventListener("click", (e) => {
    if ((e.target as HTMLElement)?.id === "runEditModal") {
      hideRunEditModal();
    }
  });

  // Form submission handler (Requirement 1.2)
  const runEditForm = document.getElementById("runEditForm") as HTMLFormElement;
  if (runEditForm) {
    runEditForm.addEventListener("submit", (e) => {
      e.preventDefault();
      saveRunEdit();
    });
  }

  // Name input validation - clear error on input (Requirement 4.4)
  const nameInput = document.getElementById("runEditName") as HTMLInputElement;
  if (nameInput) {
    nameInput.addEventListener("input", () => {
      const nameError = document.getElementById("runEditNameError");
      if (nameError && !nameError.classList.contains("hidden")) {
        // Clear error when user starts typing
        if (nameInput.value.trim().length > 0) {
          nameError.classList.add("hidden");
          nameInput.style.borderColor = "var(--border)";
        }
      }
    });
  }

  // Escape key closes modal (Requirement 5.2)
  // Enter key submits form in single-line inputs (Requirement 5.3)
  document.addEventListener("keydown", (e) => {
    const modal = document.getElementById("runEditModal");
    if (!modal || modal.classList.contains("hidden")) return;

    if (e.key === "Escape") {
      e.preventDefault();
      hideRunEditModal();
    }

    // Enter key in single-line inputs submits form (Requirement 5.3)
    if (e.key === "Enter") {
      const activeElement = document.activeElement;
      // Only submit if focus is on a single-line input (not textarea)
      if (activeElement && activeElement.tagName === "INPUT" && 
          (activeElement as HTMLInputElement).type === "text") {
        e.preventDefault();
        saveRunEdit();
      }
    }
  });
}

// Case edit modal state
let currentEditCaseId: number | null = null;
let currentEditCaseAttachments: any[] = [];

// File upload constants
const ALLOWED_FILE_TYPES = [
  "image/png",
  "image/jpeg",
  "image/gif",
  "video/mp4",
  "video/webm",
  "application/pdf",
];
const MAX_FILE_SIZE_MB = 25;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

/**
 * Show case edit modal with pre-populated data
 * Implements Requirements: 3.1, 5.1, 6.3
 * 
 * @param caseId - The ID of the case to edit
 * @param title - The current title of the case
 * @param refs - The current references (optional)
 * @param bddScenarios - The current BDD scenarios (optional)
 */
export function showCaseEditModal(
  caseId: number,
  title: string,
  refs: string | null = null,
  bddScenarios: string | null = null
) {
  const modal = document.getElementById("caseEditModal");
  const idInput = document.getElementById("caseEditId") as HTMLInputElement;
  const titleInput = document.getElementById("caseEditTitle") as HTMLInputElement;
  const refsInput = document.getElementById("caseEditRefs") as HTMLInputElement;
  const bddInput = document.getElementById("caseEditBddScenarios") as HTMLTextAreaElement;
  const titleError = document.getElementById("caseEditTitleError");
  const fileError = document.getElementById("caseEditFileError");
  const loadingOverlay = document.getElementById("caseEditLoadingOverlay");
  const attachmentsList = document.getElementById("caseEditAttachmentsList");

  if (!modal || !idInput || !titleInput || !refsInput || !bddInput) {
    console.error("Case edit modal elements not found");
    return;
  }

  // Store current case ID
  currentEditCaseId = caseId;
  currentEditCaseAttachments = [];
  
  // Store the currently focused element for focus restoration (Requirement 7.5)
  const activeElement = document.activeElement as HTMLElement;
  storeTriggerElement("caseEditModal", activeElement);

  // Pre-populate fields with case data (Requirement 3.1)
  idInput.value = String(caseId);
  titleInput.value = title || "";
  refsInput.value = refs || "";
  bddInput.value = bddScenarios || "";

  // Update breadcrumb with navigation context (Requirement 6.3)
  const breadcrumbPlanName = document.getElementById("caseEditBreadcrumbPlanName");
  const breadcrumbRunName = document.getElementById("caseEditBreadcrumbRunName");
  const breadcrumbCaseTitle = document.getElementById("caseEditBreadcrumbCaseTitle");

  if (breadcrumbPlanName) {
    breadcrumbPlanName.textContent = currentPlanName || "Test Plan";
  }
  if (breadcrumbRunName) {
    breadcrumbRunName.textContent = currentRunName || "Test Run";
  }
  if (breadcrumbCaseTitle) {
    breadcrumbCaseTitle.textContent = title || "Test Case";
  }

  // Clear any previous validation errors
  if (titleError) {
    titleError.classList.add("hidden");
  }
  if (fileError) {
    fileError.classList.add("hidden");
  }
  titleInput.style.borderColor = "var(--border)";

  // Hide loading overlay
  if (loadingOverlay) {
    loadingOverlay.classList.add("hidden");
  }

  // Clear attachments list
  if (attachmentsList) {
    attachmentsList.innerHTML = "";
  }

  // Show modal with higher z-index to appear on top of run details modal
  modal.classList.remove("hidden");
  modal.style.zIndex = "12000"; // Higher than run details modal (11000)
  
  // Activate focus trap (Requirement 7.4)
  activateFocusTrap("caseEditModal");

  // Focus first input field on open (Requirement 5.1)
  setTimeout(() => {
    titleInput.focus();
    titleInput.select();
  }, 100);

  // Load existing attachments
  loadCaseAttachments(caseId);
}

/**
 * Hide case edit modal and return to run details modal
 * Implements Requirements: 4.4
 */
export function hideCaseEditModal() {
  const modal = document.getElementById("caseEditModal");
  const titleInput = document.getElementById("caseEditTitle") as HTMLInputElement;
  const refsInput = document.getElementById("caseEditRefs") as HTMLInputElement;
  const bddInput = document.getElementById("caseEditBddScenarios") as HTMLTextAreaElement;
  const titleError = document.getElementById("caseEditTitleError");
  const fileError = document.getElementById("caseEditFileError");
  const loadingOverlay = document.getElementById("caseEditLoadingOverlay");
  const attachmentsList = document.getElementById("caseEditAttachmentsList");
  const uploadProgress = document.getElementById("caseEditUploadProgress");

  if (!modal) return;

  // Hide modal
  modal.classList.add("hidden");
  
  // Reset z-index
  modal.style.zIndex = "";
  
  // Deactivate focus trap (Requirement 7.4)
  deactivateFocusTrap("caseEditModal");
  
  // Restore focus to triggering element (Requirement 7.5)
  restoreFocus("caseEditModal");

  // Reset state
  currentEditCaseId = null;
  currentEditCaseAttachments = [];

  // Clear form fields
  if (titleInput) titleInput.value = "";
  if (refsInput) refsInput.value = "";
  if (bddInput) bddInput.value = "";

  // Clear validation errors
  if (titleError) {
    titleError.classList.add("hidden");
  }
  if (fileError) {
    fileError.classList.add("hidden");
  }
  if (titleInput) {
    titleInput.style.borderColor = "var(--border)";
  }

  // Hide loading overlay and upload progress
  if (loadingOverlay) {
    loadingOverlay.classList.add("hidden");
  }
  if (uploadProgress) {
    uploadProgress.classList.add("hidden");
  }

  // Clear attachments list
  if (attachmentsList) {
    attachmentsList.innerHTML = "";
  }

  // Return to run details modal if we have a current run context (Requirement 4.4)
  // This ensures the modal returns to the hierarchical context instead of closing completely
  if (currentRunId !== null) {
    // The run details modal should already be open in the background
    // We just need to ensure it's visible and refresh the cases list
    const runDetailsModal = document.getElementById("runDetailsModal");
    if (runDetailsModal && runDetailsModal.classList.contains("hidden")) {
      // If run details modal was closed, reopen it
      showRunDetailsModal(currentRunId);
    } else {
      // If it's already open, just refresh the cases list
      loadRunDetailsCases(currentRunId);
    }
  }
}

/**
 * Load existing attachments for a case
 * Implements Requirements: 3.10, 8.2
 */
async function loadCaseAttachments(caseId: number) {
  const attachmentsList = document.getElementById("caseEditAttachmentsList");
  if (!attachmentsList) return;

  // Show loading state (Requirement 8.2)
  attachmentsList.innerHTML = `
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 20px; text-align: center;">
      <div class="spinner" style="width: 24px; height: 24px; border: 2px solid rgba(0,0,0,0.1); border-top-color: var(--primary); border-radius: 50%; animation: spin 0.8s linear infinite;" aria-hidden="true"></div>
      <span style="margin-top: 8px; font-size: 12px; color: var(--muted);">Loading attachments...</span>
    </div>
  `;

  try {
    const response = await requestJson(`/api/manage/case/${caseId}/attachments`);
    const attachments = response.attachments || [];
    currentEditCaseAttachments = attachments;
    renderAttachmentsList(attachments);
  } catch (err: any) {
    console.error("Failed to load attachments:", err);
    // Show error state with retry option (Requirement 8.3, 8.4)
    attachmentsList.innerHTML = `
      <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 20px; text-align: center;">
        <div style="font-size: 32px; margin-bottom: 8px; opacity: 0.5;" aria-hidden="true">⚠️</div>
        <p style="margin: 0 0 8px; font-size: 13px; color: var(--text);">Failed to load attachments</p>
        <p style="margin: 0 0 12px; font-size: 12px; color: var(--muted);">${escapeHtml(err?.message || "An error occurred")}</p>
        <button type="button" class="btn-secondary" onclick="window.retryLoadAttachments(${caseId})" style="padding: 6px 12px; font-size: 12px;">
          <span class="icon" aria-hidden="true">🔄</span> Retry
        </button>
      </div>
    `;
  }
}

// Expose retry function globally for onclick handler
(window as any).retryLoadAttachments = (caseId: number) => {
  loadCaseAttachments(caseId);
};

/**
 * Render attachments list with thumbnails for images
 * Implements Requirement 3.10
 */
function renderAttachmentsList(attachments: any[]) {
  const attachmentsList = document.getElementById("caseEditAttachmentsList");
  if (!attachmentsList) return;

  if (attachments.length === 0) {
    attachmentsList.innerHTML = `
      <p style="margin: 0; font-size: 13px; color: var(--muted); text-align: center; padding: 12px;">
        No attachments yet
      </p>
    `;
    return;
  }

  attachmentsList.innerHTML = attachments
    .map((attachment: any) => {
      const isImage = attachment.content_type?.startsWith("image/");
      const fileName = escapeHtml(attachment.filename || attachment.name || "Attachment");
      const fileSize = formatFileSize(attachment.size || 0);
      
      return `
        <div class="attachment-item" style="display: flex; align-items: center; gap: 12px; padding: 10px; background: rgba(0,0,0,0.02); border: 1px solid var(--border); border-radius: 8px;">
          ${isImage ? `
            <div style="width: 48px; height: 48px; border-radius: 6px; overflow: hidden; flex-shrink: 0; background: var(--border);">
              <img src="/api/manage/attachment/${attachment.id}/thumbnail" alt="${fileName}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.style.display='none'"/>
            </div>
          ` : `
            <div style="width: 48px; height: 48px; border-radius: 6px; display: flex; align-items: center; justify-content: center; background: rgba(26, 138, 133, 0.1); flex-shrink: 0;">
              <span style="font-size: 20px;" aria-hidden="true">${getFileIcon(attachment.content_type)}</span>
            </div>
          `}
          <div style="flex: 1; min-width: 0;">
            <p style="margin: 0 0 2px; font-size: 13px; font-weight: 500; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              ${fileName}
            </p>
            <p style="margin: 0; font-size: 11px; color: var(--muted);">
              ${fileSize}
            </p>
          </div>
        </div>
      `;
    })
    .join("");
}

/**
 * Get file icon based on content type
 */
function getFileIcon(contentType: string | null): string {
  if (!contentType) return "📄";
  if (contentType.startsWith("image/")) return "🖼️";
  if (contentType.startsWith("video/")) return "🎬";
  if (contentType === "application/pdf") return "📕";
  return "📄";
}

/**
 * Format file size in human-readable format
 */
function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

/**
 * Initialize Case Edit Modal event listeners
 * Implements Requirements: 3.2, 3.3, 3.6, 3.7, 3.8, 3.9, 4.2, 4.3, 4.4, 5.2, 5.3, 6.4
 */
function initCaseEditModal() {
  // Cancel button closes modal (Requirement 3.3)
  document.getElementById("caseEditCancel")?.addEventListener("click", hideCaseEditModal);
  document.getElementById("caseEditModalClose")?.addEventListener("click", hideCaseEditModal);

  // Close modal on backdrop click (Requirement 3.3)
  document.getElementById("caseEditModal")?.addEventListener("click", (e) => {
    if ((e.target as HTMLElement)?.id === "caseEditModal") {
      hideCaseEditModal();
    }
  });

  // Breadcrumb navigation (Requirement 6.4)
  document.getElementById("caseEditBreadcrumbPlans")?.addEventListener("click", (e) => {
    e.preventDefault();
    const titleInput = document.getElementById("caseEditTitle") as HTMLInputElement | null;
    const context: NavigationContext = {
      level: 'case-edit',
      planId: currentPlanId || undefined,
      planName: currentPlanName || undefined,
      runId: currentRunId || undefined,
      runName: currentRunName || undefined,
      caseId: currentEditCaseId || undefined,
      caseTitle: titleInput?.value || undefined
    };
    navigateToBreadcrumbLevel('plans', context);
  });

  document.getElementById("caseEditBreadcrumbPlanName")?.addEventListener("click", (e) => {
    e.preventDefault();
    const titleInput = document.getElementById("caseEditTitle") as HTMLInputElement | null;
    const context: NavigationContext = {
      level: 'case-edit',
      planId: currentPlanId || undefined,
      planName: currentPlanName || undefined,
      runId: currentRunId || undefined,
      runName: currentRunName || undefined,
      caseId: currentEditCaseId || undefined,
      caseTitle: titleInput?.value || undefined
    };
    navigateToBreadcrumbLevel('runs', context);
  });

  document.getElementById("caseEditBreadcrumbRunName")?.addEventListener("click", (e) => {
    e.preventDefault();
    const titleInput = document.getElementById("caseEditTitle") as HTMLInputElement | null;
    const context: NavigationContext = {
      level: 'case-edit',
      planId: currentPlanId || undefined,
      planName: currentPlanName || undefined,
      runId: currentRunId || undefined,
      runName: currentRunName || undefined,
      caseId: currentEditCaseId || undefined,
      caseTitle: titleInput?.value || undefined
    };
    navigateToBreadcrumbLevel('cases', context);
  });

  // Form submission handler (Requirement 3.2)
  const caseEditForm = document.getElementById("caseEditForm") as HTMLFormElement;
  if (caseEditForm) {
    caseEditForm.addEventListener("submit", (e) => {
      e.preventDefault();
      saveCaseEdit();
    });
  }

  // Title input validation - clear error on input (Requirement 4.4)
  const titleInput = document.getElementById("caseEditTitle") as HTMLInputElement;
  if (titleInput) {
    titleInput.addEventListener("input", () => {
      const titleError = document.getElementById("caseEditTitleError");
      if (titleError && !titleError.classList.contains("hidden")) {
        // Clear error when user starts typing
        if (titleInput.value.trim().length > 0) {
          titleError.classList.add("hidden");
          titleInput.style.borderColor = "var(--border)";
        }
      }
    });
  }

  // File upload handlers (Requirements 3.6, 3.7, 3.8, 3.9)
  initFileUploadHandlers();
}

/**
 * Initialize file upload handlers for drag-and-drop and click-to-browse
 * Implements Requirements: 3.6, 3.7, 3.8, 3.9
 */
function initFileUploadHandlers() {
  const dropZone = document.getElementById("caseEditDropZone");
  const fileInput = document.getElementById("caseEditFileInput") as HTMLInputElement;

  if (!dropZone || !fileInput) return;

  // Click to browse
  dropZone.addEventListener("click", () => {
    fileInput.click();
  });

  // Keyboard accessibility for drop zone
  dropZone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      fileInput.click();
    }
  });

  // File input change handler
  fileInput.addEventListener("change", () => {
    const file = fileInput.files?.[0];
    if (file) {
      handleFileUpload(file);
    }
    // Reset input so same file can be selected again
    fileInput.value = "";
  });

  // Drag and drop handlers
  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropZone.style.borderColor = "var(--primary)";
    dropZone.style.background = "rgba(26, 138, 133, 0.06)";
  });

  dropZone.addEventListener("dragleave", (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropZone.style.borderColor = "var(--border)";
    dropZone.style.background = "transparent";
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropZone.style.borderColor = "var(--border)";
    dropZone.style.background = "transparent";

    const file = e.dataTransfer?.files?.[0];
    if (file) {
      handleFileUpload(file);
    }
  });
}

/**
 * Validate case title - must not be empty or whitespace only
 * Implements Requirement 4.2
 * 
 * @param title - The title to validate
 * @returns true if valid, false otherwise
 */
function validateCaseTitle(title: string): boolean {
  return title.trim().length > 0;
}

/**
 * Show validation error for case title field
 * Implements Requirement 4.3
 */
function showCaseTitleValidationError() {
  const titleInput = document.getElementById("caseEditTitle") as HTMLInputElement;
  const titleError = document.getElementById("caseEditTitleError");

  if (titleInput) {
    titleInput.style.borderColor = "#ef4444";
  }
  if (titleError) {
    titleError.classList.remove("hidden");
  }
}

/**
 * Clear validation error for case title field
 * Implements Requirement 4.4
 */
function clearCaseTitleValidationError() {
  const titleInput = document.getElementById("caseEditTitle") as HTMLInputElement;
  const titleError = document.getElementById("caseEditTitleError");

  if (titleInput) {
    titleInput.style.borderColor = "var(--border)";
  }
  if (titleError) {
    titleError.classList.add("hidden");
  }
}

/**
 * Save case edit - validates and sends update request
 * Implements Requirements: 3.2, 3.4, 3.5, 4.2, 4.3
 */
export async function saveCaseEdit() {
  const titleInput = document.getElementById("caseEditTitle") as HTMLInputElement;
  const refsInput = document.getElementById("caseEditRefs") as HTMLInputElement;
  const bddInput = document.getElementById("caseEditBddScenarios") as HTMLTextAreaElement;
  const loadingOverlay = document.getElementById("caseEditLoadingOverlay");
  const saveBtn = document.getElementById("caseEditSave") as HTMLButtonElement;

  if (!titleInput || !refsInput || !bddInput || currentEditCaseId === null) {
    console.error("Case edit form elements not found or no case selected");
    return;
  }

  const title = titleInput.value;
  const refs = refsInput.value;
  const bddScenarios = bddInput.value;

  // Validate title (Requirement 4.2)
  if (!validateCaseTitle(title)) {
    showCaseTitleValidationError();
    titleInput.focus();
    return;
  }

  // Clear any previous validation errors
  clearCaseTitleValidationError();

  // Show loading overlay
  if (loadingOverlay) {
    loadingOverlay.classList.remove("hidden");
  }
  if (saveBtn) {
    saveBtn.disabled = true;
  }

  try {
    // Send PUT request to update case (Requirement 3.2)
    const response = await requestJson(`/api/manage/case/${currentEditCaseId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        title: title.trim(),
        refs: refs || null,
        custom_bdd_scenario: bddScenarios || null,
      }),
    });

    if (response.success) {
      // Show success toast
      showToast(`Case "${title.trim()}" updated successfully`, "success");
      
      // Hide modal
      hideCaseEditModal();
      
      // Refresh removed - cases subsection no longer exists in hierarchical navigation
    } else {
      throw new Error(response.message || "Failed to update case");
    }
  } catch (err: any) {
    // Show error toast (Requirement 3.4)
    showToast(err?.message || "Failed to update case", "error");
  } finally {
    // Hide loading overlay
    if (loadingOverlay) {
      loadingOverlay.classList.add("hidden");
    }
    if (saveBtn) {
      saveBtn.disabled = false;
    }
  }
}

/**
 * Validate file type
 * Implements Requirement 3.8
 * 
 * @param file - The file to validate
 * @returns true if valid, false otherwise
 */
function validateFileType(file: File): boolean {
  return ALLOWED_FILE_TYPES.includes(file.type);
}

/**
 * Validate file size
 * Implements Requirement 3.9
 * 
 * @param file - The file to validate
 * @returns true if valid, false otherwise
 */
function validateFileSize(file: File): boolean {
  return file.size <= MAX_FILE_SIZE_BYTES;
}

/**
 * Show file validation error
 */
function showFileValidationError(message: string) {
  const fileError = document.getElementById("caseEditFileError");
  if (fileError) {
    fileError.textContent = message;
    fileError.classList.remove("hidden");
  }
}

/**
 * Clear file validation error
 */
function clearFileValidationError() {
  const fileError = document.getElementById("caseEditFileError");
  if (fileError) {
    fileError.classList.add("hidden");
  }
}

/**
 * Handle file upload
 * Implements Requirements: 3.6, 3.7, 3.8, 3.9, 3.10
 * 
 * @param file - The file to upload
 */
async function handleFileUpload(file: File) {
  if (currentEditCaseId === null) {
    showToast("No case selected for attachment", "error");
    return;
  }

  // Clear previous errors
  clearFileValidationError();

  // Validate file type (Requirement 3.8)
  if (!validateFileType(file)) {
    showFileValidationError("File type not allowed. Accepted types: PNG, JPG, GIF, MP4, WebM, PDF");
    return;
  }

  // Validate file size (Requirement 3.9)
  if (!validateFileSize(file)) {
    showFileValidationError(`File size exceeds ${MAX_FILE_SIZE_MB}MB limit`);
    return;
  }

  const uploadProgress = document.getElementById("caseEditUploadProgress");
  const uploadFileName = document.getElementById("caseEditUploadFileName");

  // Show upload progress
  if (uploadProgress) {
    uploadProgress.classList.remove("hidden");
  }
  if (uploadFileName) {
    uploadFileName.textContent = `Uploading ${file.name}...`;
  }

  try {
    // Create FormData for file upload
    const formData = new FormData();
    formData.append("file", file);

    // Upload file via POST request (Requirement 3.7)
    const response = await fetch(`/api/manage/case/${currentEditCaseId}/attachment`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Upload failed with status ${response.status}`);
    }

    const result = await response.json();

    // Add new attachment to list (Requirement 3.10)
    if (result.attachment) {
      currentEditCaseAttachments.push(result.attachment);
      renderAttachmentsList(currentEditCaseAttachments);
    }

    showToast(`File "${file.name}" uploaded successfully`, "success");
  } catch (err: any) {
    showToast(err?.message || "Failed to upload file", "error");
  } finally {
    // Hide upload progress
    if (uploadProgress) {
      uploadProgress.classList.add("hidden");
    }
  }
}

/**
 * Initialize Manage View - Auto-load Plans subsection
 * Runs subsection requires a plan to be selected first
 * Cases subsection has been removed
 * This function is called when the user navigates to the Management view
 */
export async function initManageView() {
  try {
    // Reset pagination state
    plansCurrentPage = 0;
    
    // Load Plans only (Cases removed, Runs require plan selection)
    await loadManagePlans();
    
    // Plan filter and runs state initialization removed - no longer needed for hierarchical navigation
  } catch (err: any) {
    console.error("Error initializing manage view:", err);
    showToast("Failed to load management data", "error");
  }
}

// showRunsSelectPlanState function removed - no longer needed for hierarchical navigation

// Store plans data for filtering
let allPlans: any[] = [];

// Pagination state for plans
let plansCurrentPage = 0;
const PLANS_PAGE_SIZE = 10;

// Pagination state for runs removed - no longer needed for hierarchical navigation

/**
 * Load plans for Manage section
 */
async function loadManagePlans() {
  const container = document.getElementById("plansListContainer");
  const loadingState = document.getElementById("plansLoadingState");
  const emptyState = document.getElementById("plansEmptyState");
  const countBadge = document.getElementById("plansCount");
  const refreshBtn = document.getElementById("refreshPlansBtn") as HTMLButtonElement | null;
  const searchInput = document.getElementById("plansSearch") as HTMLInputElement | null;

  if (!container || !loadingState || !emptyState) return;

  // Preserve current search filter value
  const currentSearchValue = searchInput?.value || "";

  // Show loading state and disable action buttons
  loadingState.classList.remove("hidden");
  emptyState.classList.add("hidden");
  container.classList.add("hidden");
  setSubsectionBusy("plans", true);
  announceStatus("Loading plans...");
  
  // Disable action buttons during loading
  if (refreshBtn) refreshBtn.disabled = true;
  if (searchInput) searchInput.disabled = true;
  disableEntityButtons("plan");

  try {
    const projectInput = document.getElementById("planProject") as HTMLInputElement | null;
    const project = projectInput?.value || "1";

    const data = await requestJson(`/api/plans?project=${encodeURIComponent(project)}&is_completed=0`);
    const plans = Array.isArray(data.plans) ? data.plans : [];

    // Fetch runs for each plan to get the latest run update time
    const plansWithRunData = await Promise.all(
      plans.map(async (plan: any) => {
        try {
          const runsData = await requestJson(`/api/runs?plan=${plan.id}&project=${encodeURIComponent(project)}`);
          const runs = Array.isArray(runsData.runs) ? runsData.runs : [];
          
          // Find the most recent run update time
          let latestRunUpdate = 0;
          runs.forEach((run: any) => {
            const runTime = run.updated_on || run.created_on || 0;
            if (runTime > latestRunUpdate) {
              latestRunUpdate = runTime;
            }
          });
          
          // Use latest run update time, fallback to plan's own update time
          const effectiveUpdateTime = latestRunUpdate || plan.updated_on || plan.created_on || 0;
          
          return {
            ...plan,
            effective_updated_on: effectiveUpdateTime,
            latest_run_update: latestRunUpdate
          };
        } catch (err) {
          // If fetching runs fails, just use plan's own update time
          return {
            ...plan,
            effective_updated_on: plan.updated_on || plan.created_on || 0,
            latest_run_update: 0
          };
        }
      })
    );

    // Sort plans by effective update time (from runs or plan itself)
    plansWithRunData.sort((a: any, b: any) => {
      return b.effective_updated_on - a.effective_updated_on;
    });

    // Store plans for filtering
    allPlans = plansWithRunData;

    // Update count badge with total count (unfiltered)
    if (countBadge) {
      countBadge.textContent = String(plans.length);
    }

    // Apply preserved search filter if it exists
    if (currentSearchValue.trim()) {
      filterPlans(currentSearchValue);
    } else {
      // Render all plans if no filter
      renderPlansSubsection(plans);
    }
    
    // Announce completion to screen readers
    setSubsectionBusy("plans", false);
    announceStatus(`Loaded ${plans.length} plan${plans.length !== 1 ? 's' : ''}`);
  } catch (err: any) {
    // Show error state with retry button
    setSubsectionBusy("plans", false);
    announceStatus("Failed to load plans");
    showErrorState("plans", err?.message || "Failed to load plans", refreshPlanList);
    showToast(err?.message || "Failed to load plans", "error");
  } finally {
    // Re-enable action buttons after loading completes
    if (refreshBtn) refreshBtn.disabled = false;
    if (searchInput) searchInput.disabled = false;
  }
}

/**
 * Render Plans subsection with pagination (10 items per page)
 */
function renderPlansSubsection(plans: any[]) {
  const container = document.getElementById("plansListContainer");
  const loadingState = document.getElementById("plansLoadingState");
  const emptyState = document.getElementById("plansEmptyState");

  if (!container || !loadingState || !emptyState) return;

  if (plans.length === 0) {
    // Show empty state
    loadingState.classList.add("hidden");
    emptyState.classList.remove("hidden");
    container.classList.add("hidden");
    return;
  }

  // Calculate pagination
  const startIndex = plansCurrentPage * PLANS_PAGE_SIZE;
  const endIndex = startIndex + PLANS_PAGE_SIZE;
  const displayPlans = plans.slice(startIndex, endIndex);
  const totalPages = Math.ceil(plans.length / PLANS_PAGE_SIZE);
  const hasPrev = plansCurrentPage > 0;
  const hasNext = plansCurrentPage < totalPages - 1;

  // Render plan cards with accessibility attributes
  container.innerHTML = displayPlans
    .map((plan: any) => {
      const planName = escapeHtml(plan.name || `Plan ${plan.id}`);
      const planId = plan.id;
      const isCompleted = plan.is_completed === true || plan.is_completed === 1;
      const badgeClass = isCompleted ? 'badge-completed' : 'badge-active';
      const badgeText = isCompleted ? 'Completed' : 'Active';
      
      // Format last updated time - use effective_updated_on which includes run updates
      const updatedOn = plan.effective_updated_on || plan.updated_on || plan.created_on;
      let lastUpdatedText = '';
      if (updatedOn) {
        const date = new Date(updatedOn * 1000);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        
        if (diffDays === 0) {
          lastUpdatedText = 'Today';
        } else if (diffDays === 1) {
          lastUpdatedText = 'Yesterday';
        } else if (diffDays < 7) {
          lastUpdatedText = `${diffDays} days ago`;
        } else if (diffDays < 30) {
          const weeks = Math.floor(diffDays / 7);
          lastUpdatedText = `${weeks} week${weeks > 1 ? 's' : ''} ago`;
        } else if (diffDays < 365) {
          const months = Math.floor(diffDays / 30);
          lastUpdatedText = `${months} month${months > 1 ? 's' : ''} ago`;
        } else {
          const years = Math.floor(diffDays / 365);
          lastUpdatedText = `${years} year${years > 1 ? 's' : ''} ago`;
        }
      }
      
      return `
        <div class="entity-card" role="listitem" data-entity-type="plan" data-entity-id="${planId}" data-plan-name="${escapeHtml(plan.name || '').toLowerCase()}" aria-label="Plan: ${planName}, Status: ${badgeText}">
          <div class="entity-card-header">
            <div class="entity-card-title" id="plan-title-${planId}">${planName}</div>
            <div class="entity-card-badges">
              <span class="badge ${badgeClass}" role="status">${badgeText}</span>
            </div>
          </div>
          <div class="entity-card-meta">
            <span class="meta-item">
              <span class="icon" aria-hidden="true">🆔</span> Plan ID: ${planId}
            </span>
            ${lastUpdatedText ? `<span class="meta-item">
              <span class="icon" aria-hidden="true">🕒</span> Updated: ${lastUpdatedText}
            </span>` : ''}
          </div>
          <div class="entity-card-actions" role="group" aria-label="Actions for ${planName}">
            <button type="button" class="btn-edit edit-plan-btn" data-plan-id="${planId}" data-plan-name="${escapeHtml(plan.name || '')}" aria-label="Edit plan ${planName}" aria-describedby="plan-title-${planId}">
              <span class="icon" aria-hidden="true">✏️</span> Edit
            </button>
            <button type="button" class="btn-delete delete-plan-btn" data-plan-id="${planId}" data-plan-name="${escapeHtml(plan.name || '')}" aria-label="Delete plan ${planName}" aria-describedby="plan-title-${planId}">
              <span class="icon" aria-hidden="true">🗑️</span> Delete
            </button>
          </div>
        </div>
      `;
    })
    .join("");

  // Add pagination controls
  container.innerHTML += `
    <div class="pagination-controls" style="display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border-top: 1px solid var(--border); margin-top: 8px;">
      <span style="font-size: 13px; color: var(--muted);">
        Showing ${startIndex + 1}-${Math.min(endIndex, plans.length)} of ${plans.length} plans
      </span>
      <div style="display: flex; gap: 8px;">
        <button type="button" class="refresh-btn plans-prev-btn" ${!hasPrev ? 'disabled' : ''} aria-label="Previous page">
          ← Prev
        </button>
        <span style="font-size: 13px; color: var(--muted); padding: 6px 12px;">
          Page ${plansCurrentPage + 1} of ${totalPages}
        </span>
        <button type="button" class="refresh-btn plans-next-btn" ${!hasNext ? 'disabled' : ''} aria-label="Next page">
          Next →
        </button>
      </div>
    </div>
  `;

  // Show entity list
  loadingState.classList.add("hidden");
  emptyState.classList.add("hidden");
  container.classList.remove("hidden");

  // Attach event listeners
  attachPlanEventListeners();
  
  // Attach pagination event listeners
  container.querySelector(".plans-prev-btn")?.addEventListener("click", () => {
    if (plansCurrentPage > 0) {
      plansCurrentPage--;
      renderPlansSubsection(plans);
    }
  });
  
  container.querySelector(".plans-next-btn")?.addEventListener("click", () => {
    if (plansCurrentPage < totalPages - 1) {
      plansCurrentPage++;
      renderPlansSubsection(plans);
    }
  });
}

/**
 * Filter plans by search query
 */
function filterPlans(searchQuery: string) {
  const query = searchQuery.toLowerCase().trim();
  
  // Reset pagination when filtering
  plansCurrentPage = 0;
  
  if (!query) {
    // No search query, show all plans
    renderPlansSubsection(allPlans);
    return;
  }

  // Filter plans by name
  const filteredPlans = allPlans.filter((plan: any) => {
    const planName = (plan.name || `Plan ${plan.id}`).toLowerCase();
    return planName.includes(query);
  });

  // Render filtered plans
  renderPlansSubsection(filteredPlans);
}

// Runs and cases data storage removed - no longer needed for hierarchical navigation

// loadManageRuns function removed - no longer needed for hierarchical navigation

// populatePlanFilter function removed - no longer needed for hierarchical navigation

// renderRunsSubsection function removed - no longer needed for hierarchical navigation

// loadManageCases function removed - no longer needed for hierarchical navigation

// renderCasesSubsection and filterCases functions removed - no longer needed for hierarchical navigation

// ========================================
// Test Cases View Functions
// ========================================

// Current run context for test cases view
let currentTestCasesRunId: number | null = null;
let currentTestCasesRunName: string = "";

/**
 * Status badge color mapping
 * Implements Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
 * 
 * @param statusId - The status ID from TestRail
 * @returns CSS class for the status badge
 */
export function getStatusBadgeClass(statusId: number): string {
  switch (statusId) {
    case 1:
      return "badge-passed";    // Green for Passed
    case 2:
      return "badge-blocked";   // Orange for Blocked
    case 3:
      return "badge-untested";  // Gray for Untested
    case 4:
      return "badge-retest";    // Yellow for Retest
    case 5:
      return "badge-failed";    // Red for Failed
    default:
      return "badge-untested";  // Default to gray
  }
}

/**
 * Show test cases view for a specific run
 * Implements Requirements: 2.1, 7.1, 7.3, 12.1
 * Updated for hierarchical navigation - hides runs modal and shows test cases view
 * 
 * @param runId - The ID of the run to show test cases for
 * @param runName - The name of the run (for header display)
 */
export async function showTestCasesView(runId: number, runName: string) {
  // Store current run context
  currentTestCasesRunId = runId;
  currentTestCasesRunName = runName;

  // Hide runs modal if it's open (Requirement 12.1)
  const planRunsModal = document.getElementById("planRunsModal");
  if (planRunsModal && !planRunsModal.classList.contains("hidden")) {
    // Don't fully close the modal, just hide it temporarily
    // This preserves the plan context for back navigation
    planRunsModal.classList.add("hidden");
    // Deactivate focus trap while hidden
    deactivateFocusTrap("planRunsModal");
  }

  // Show test cases view
  const testCasesView = document.getElementById("testCasesView");
  const runNameDisplay = document.getElementById("testCasesRunName");

  if (testCasesView) {
    testCasesView.classList.remove("hidden");
  }
  
  // Display run name in header (Requirement 7.3)
  if (runNameDisplay) {
    runNameDisplay.textContent = `Run: ${runName}`;
  }

  // Load test cases
  await loadTestCases(runId);
}

/**
 * Hide test cases view and return to runs modal
 * Implements Requirements: 7.1, 7.2, 12.1
 * Updated for hierarchical navigation - returns to runs modal instead of runs subsection
 */
export function hideTestCasesView() {
  // Hide test cases view
  const testCasesView = document.getElementById("testCasesView");
  if (testCasesView) {
    testCasesView.classList.add("hidden");
  }

  // Clear test cases list
  const container = document.getElementById("testCasesListContainer");
  if (container) {
    container.innerHTML = "";
    container.classList.add("hidden");
  }

  // Return to runs modal if we have a plan context (Requirement 12.1)
  if (currentPlanId !== null && currentPlanName) {
    showPlanRunsModal(currentPlanId, currentPlanName, currentPlanEditButton || undefined);
    announceStatus(`Returned to runs for ${currentPlanName}`);
  } else {
    // Fallback: if no plan context, just hide the view
    announceStatus("Returned to plans list");
  }

  // Clear current run context
  currentTestCasesRunId = null;
  currentTestCasesRunName = "";
}

/**
 * Load test cases for a specific run
 * Implements Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
 * 
 * @param runId - The ID of the run to load test cases for
 */
export async function loadTestCases(runId: number) {
  const container = document.getElementById("testCasesListContainer");
  const loadingState = document.getElementById("testCasesLoadingState");
  const emptyState = document.getElementById("testCasesEmptyState");
  const errorState = document.getElementById("testCasesErrorState");
  const countBadge = document.getElementById("testCasesCount");
  const refreshBtn = document.getElementById("refreshTestCasesBtn") as HTMLButtonElement | null;

  if (!container || !loadingState || !emptyState || !errorState) return;

  // Show loading state (Requirement 2.2)
  loadingState.classList.remove("hidden");
  emptyState.classList.add("hidden");
  errorState.classList.add("hidden");
  container.classList.add("hidden");
  
  // Disable refresh button during loading
  if (refreshBtn) refreshBtn.disabled = true;
  
  // Announce to screen readers
  announceStatus("Loading test cases...");

  try {
    // Fetch test cases from API (Requirement 2.1)
    const data = await requestJson(`/api/tests/${runId}`);
    const tests = Array.isArray(data.tests) ? data.tests : [];

    // Update count badge
    if (countBadge) {
      countBadge.textContent = String(tests.length);
    }

    // Hide loading state
    loadingState.classList.add("hidden");

    if (tests.length === 0) {
      // Show empty state (Requirement 2.4)
      emptyState.classList.remove("hidden");
      container.classList.add("hidden");
      announceStatus("No test cases found");
    } else {
      // Render test cases (Requirement 2.3)
      renderTestCases(tests);
      announceStatus(`Loaded ${tests.length} test case${tests.length !== 1 ? 's' : ''}`);
    }
  } catch (err: any) {
    // Show error state with retry option (Requirement 2.5)
    loadingState.classList.add("hidden");
    errorState.classList.remove("hidden");
    container.classList.add("hidden");
    
    const errorMessage = document.getElementById("testCasesErrorMessage");
    if (errorMessage) {
      errorMessage.textContent = err?.message || "An error occurred while loading test cases.";
    }
    
    showToast(err?.message || "Failed to load test cases", "error");
    announceStatus("Failed to load test cases");
  } finally {
    // Re-enable refresh button
    if (refreshBtn) refreshBtn.disabled = false;
  }
}

/**
 * Render test cases in the list container
 * Implements Requirements: 2.3, 6.1, 6.2, 6.3, 6.4, 6.5
 * 
 * @param tests - Array of test case objects from the API
 */
function renderTestCases(tests: any[]) {
  const container = document.getElementById("testCasesListContainer");
  const emptyState = document.getElementById("testCasesEmptyState");
  const errorState = document.getElementById("testCasesErrorState");

  if (!container) return;

  // Hide empty and error states
  if (emptyState) emptyState.classList.add("hidden");
  if (errorState) errorState.classList.add("hidden");

  // Render test case cards with status badges
  container.innerHTML = tests
    .map((test: any) => {
      const testTitle = escapeHtml(test.title || `Test ${test.id}`);
      const testId = test.id;
      const caseId = test.case_id;
      const statusId = test.status_id || 3; // Default to Untested
      const statusName = escapeHtml(test.status_name || "Untested");
      const refs = test.refs ? escapeHtml(String(test.refs)) : "";
      const badgeClass = getStatusBadgeClass(statusId);
      
      return `
        <div class="entity-card" role="listitem" data-entity-type="test" data-entity-id="${testId}" data-case-id="${caseId}" aria-label="Test: ${testTitle}, Status: ${statusName}">
          <div class="entity-card-header">
            <div class="entity-card-title" id="test-title-${testId}">${testTitle}</div>
            <div class="entity-card-badges">
              <span class="badge ${badgeClass}" role="status" aria-label="Status: ${statusName}">${statusName}</span>
            </div>
          </div>
          <div class="entity-card-meta">
            <span class="meta-item">
              <span class="icon" aria-hidden="true">🆔</span> Test ID: ${testId}
            </span>
            <span class="meta-item">
              <span class="icon" aria-hidden="true">📋</span> Case ID: ${caseId}
            </span>
            ${refs ? `<span class="meta-item"><span class="icon" aria-hidden="true">🔗</span> Refs: ${refs}</span>` : ''}
          </div>
          <div class="entity-card-actions" role="group" aria-label="Actions for ${testTitle}">
            <button type="button" class="btn-edit edit-test-case-btn" data-case-id="${caseId}" data-case-title="${escapeHtml(test.title || '')}" data-case-refs="${escapeHtml(test.refs || '')}" aria-label="Edit case ${testTitle}" aria-describedby="test-title-${testId}">
              <span class="icon" aria-hidden="true">✏️</span> Edit Case
            </button>
          </div>
        </div>
      `;
    })
    .join("");

  // Show container
  container.classList.remove("hidden");

  // Attach event listeners for edit buttons
  attachTestCaseEventListeners();
}

/**
 * Attach event listeners to test case edit buttons
 */
function attachTestCaseEventListeners() {
  document.querySelectorAll(".edit-test-case-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const target = e.currentTarget as HTMLElement;
      const caseId = parseInt(target.dataset.caseId || "0", 10);
      const caseTitle = target.dataset.caseTitle || "";
      const refs = target.dataset.caseRefs || null;
      
      // Open case edit modal
      showCaseEditModal(caseId, caseTitle, refs, null);
    });
  });
}

/**
 * Initialize test cases view event listeners
 */
export function initTestCasesView() {
  // Back button - return to runs list (Requirement 7.1, 7.2)
  document.getElementById("testCasesBackBtn")?.addEventListener("click", hideTestCasesView);

  // Refresh button
  document.getElementById("refreshTestCasesBtn")?.addEventListener("click", () => {
    if (currentTestCasesRunId !== null) {
      loadTestCases(currentTestCasesRunId);
    }
  });

  // Retry button in error state
  document.getElementById("testCasesRetryBtn")?.addEventListener("click", () => {
    if (currentTestCasesRunId !== null) {
      loadTestCases(currentTestCasesRunId);
    }
  });
}
