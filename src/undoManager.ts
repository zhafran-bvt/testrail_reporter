/**
 * Undo Manager Module
 * 
 * Provides undo/redo functionality for destructive actions like delete and update.
 * Stores action history and allows users to revert recent changes.
 */

export interface UndoAction {
  id: string;
  type: 'delete' | 'update' | 'bulk_delete';
  entityType: 'plan' | 'run' | 'case';
  entityId: number | number[];
  entityName: string;
  data: any;
  timestamp: number;
  expiresAt: number;
}

class UndoManager {
  private actions: UndoAction[] = [];
  private maxActions: number = 10;
  private defaultTTL: number = 10000; // 10 seconds
  private cleanupInterval: number | null = null;

  constructor() {
    this.startCleanup();
  }

  /**
   * Add an action to the undo history
   */
  addAction(action: Omit<UndoAction, 'id' | 'timestamp' | 'expiresAt'>): string {
    const id = this.generateId();
    const timestamp = Date.now();
    const expiresAt = timestamp + this.defaultTTL;

    const fullAction: UndoAction = {
      ...action,
      id,
      timestamp,
      expiresAt
    };

    this.actions.unshift(fullAction);

    // Keep only the most recent actions
    if (this.actions.length > this.maxActions) {
      this.actions = this.actions.slice(0, this.maxActions);
    }

    return id;
  }

  /**
   * Get an action by ID
   */
  getAction(id: string): UndoAction | null {
    return this.actions.find(action => action.id === id) || null;
  }

  /**
   * Remove an action from history
   */
  removeAction(id: string): void {
    this.actions = this.actions.filter(action => action.id !== id);
  }

  /**
   * Get all active (non-expired) actions
   */
  getActiveActions(): UndoAction[] {
    const now = Date.now();
    return this.actions.filter(action => action.expiresAt > now);
  }

  /**
   * Clear all actions
   */
  clearAll(): void {
    this.actions = [];
  }

  /**
   * Start periodic cleanup of expired actions
   */
  private startCleanup(): void {
    if (this.cleanupInterval !== null) {
      return;
    }

    this.cleanupInterval = window.setInterval(() => {
      this.cleanupExpired();
    }, 1000); // Check every second
  }

  /**
   * Stop periodic cleanup
   */
  stopCleanup(): void {
    if (this.cleanupInterval !== null) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }
  }

  /**
   * Remove expired actions
   */
  private cleanupExpired(): void {
    const now = Date.now();
    this.actions = this.actions.filter(action => action.expiresAt > now);
  }

  /**
   * Generate a unique ID for an action
   */
  private generateId(): string {
    return `undo_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Get time remaining until action expires (in milliseconds)
   */
  getTimeRemaining(id: string): number {
    const action = this.getAction(id);
    if (!action) {
      return 0;
    }

    const remaining = action.expiresAt - Date.now();
    return Math.max(0, remaining);
  }

  /**
   * Check if an action is still valid (not expired)
   */
  isActionValid(id: string): boolean {
    return this.getTimeRemaining(id) > 0;
  }
}

// Singleton instance
export const undoManager = new UndoManager();

/**
 * Show an undo toast notification with countdown
 */
export function showUndoToast(
  action: UndoAction,
  onUndo: (action: UndoAction) => void | Promise<void>
): void {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const div = document.createElement('div');
  div.className = 'toast align-items-center bg-warning text-dark';
  div.setAttribute('role', 'alert');
  div.setAttribute('aria-live', 'assertive');
  div.setAttribute('aria-atomic', 'true');
  div.setAttribute('data-undo-id', action.id);

  const entityLabel = action.entityType.charAt(0).toUpperCase() + action.entityType.slice(1);
  const actionLabel = action.type === 'delete' ? 'Deleted' : 
                      action.type === 'bulk_delete' ? 'Deleted' : 'Updated';
  
  const entityCount = Array.isArray(action.entityId) ? action.entityId.length : 1;
  const entityText = entityCount > 1 ? `${entityCount} ${entityLabel}s` : entityLabel;

  div.innerHTML = `
    <div class="d-flex align-items-center" style="padding: 12px;">
      <div class="toast-body" style="flex: 1;">
        <strong>${actionLabel} ${entityText}</strong>
        <div style="font-size: 12px; margin-top: 4px;">
          <span id="undo-countdown-${action.id}">10s</span> to undo
        </div>
      </div>
      <button type="button" class="btn btn-sm btn-dark" id="undo-btn-${action.id}" style="margin-right: 8px;">
        Undo
      </button>
      <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
  `;

  container.appendChild(div);

  // Initialize Bootstrap toast
  const toast = new (window as any).bootstrap.Toast(div, { 
    autohide: false // We'll handle hiding manually
  });
  toast.show();

  // Update countdown
  const countdownEl = document.getElementById(`undo-countdown-${action.id}`);
  const updateCountdown = () => {
    const remaining = undoManager.getTimeRemaining(action.id);
    if (remaining <= 0) {
      toast.hide();
      undoManager.removeAction(action.id);
      return;
    }

    const seconds = Math.ceil(remaining / 1000);
    if (countdownEl) {
      countdownEl.textContent = `${seconds}s`;
    }
  };

  const countdownInterval = setInterval(updateCountdown, 100);

  // Undo button handler
  const undoBtn = document.getElementById(`undo-btn-${action.id}`);
  if (undoBtn) {
    undoBtn.addEventListener('click', async () => {
      clearInterval(countdownInterval);
      
      // Disable button and show loading
      undoBtn.textContent = 'Undoing...';
      undoBtn.setAttribute('disabled', 'true');

      try {
        await onUndo(action);
        undoManager.removeAction(action.id);
        toast.hide();
        
        // Show success message
        if (typeof (window as any).showToast === 'function') {
          (window as any).showToast('Action undone successfully', 'success');
        }
      } catch (error) {
        console.error('Undo failed:', error);
        undoBtn.textContent = 'Undo';
        undoBtn.removeAttribute('disabled');
        
        if (typeof (window as any).showToast === 'function') {
          (window as any).showToast('Failed to undo action', 'error');
        }
      }
    });
  }

  // Clean up when toast is hidden
  div.addEventListener('hidden.bs.toast', () => {
    clearInterval(countdownInterval);
    if (div.parentNode === container) {
      container.removeChild(div);
    }
  });
}

/**
 * Helper function to create an undo action for delete operation
 */
export function createDeleteAction(
  entityType: 'plan' | 'run' | 'case',
  entityId: number,
  entityName: string,
  data: any
): string {
  return undoManager.addAction({
    type: 'delete',
    entityType,
    entityId,
    entityName,
    data
  });
}

/**
 * Helper function to create an undo action for bulk delete operation
 */
export function createBulkDeleteAction(
  entityType: 'plan' | 'run' | 'case',
  entityIds: number[],
  entityName: string,
  data: any
): string {
  return undoManager.addAction({
    type: 'bulk_delete',
    entityType,
    entityId: entityIds,
    entityName,
    data
  });
}

/**
 * Helper function to create an undo action for update operation
 */
export function createUpdateAction(
  entityType: 'plan' | 'run' | 'case',
  entityId: number,
  entityName: string,
  previousData: any
): string {
  return undoManager.addAction({
    type: 'update',
    entityType,
    entityId,
    entityName,
    data: previousData
  });
}

// Export the singleton instance
export default undoManager;
