/**
 * Filter Manager Module
 * 
 * Manages saved filter configurations for the dashboard.
 * Allows users to save, load, edit, and delete filter combinations.
 */

export interface SavedFilter {
  id: string;
  name: string;
  description?: string;
  filters: {
    search?: string;
    isCompleted?: number | null;
    createdAfter?: number | null;
    createdBefore?: number | null;
    assignees?: number[];
    priorities?: number[];
    tags?: string[];
    customFields?: Record<string, any>;
  };
  sortColumn?: string;
  sortDirection?: 'asc' | 'desc';
  isDefault?: boolean;
  createdAt: number;
  updatedAt: number;
}

class FilterManager {
  private storageKey: string = 'testrail_saved_filters';
  private maxFilters: number = 10;

  /**
   * Get all saved filters
   */
  getAllFilters(): SavedFilter[] {
    try {
      const stored = localStorage.getItem(this.storageKey);
      if (!stored) {
        return [];
      }

      const filters = JSON.parse(stored);
      return Array.isArray(filters) ? filters : [];
    } catch (error) {
      console.error('Failed to load saved filters:', error);
      return [];
    }
  }

  /**
   * Get a filter by ID
   */
  getFilter(id: string): SavedFilter | null {
    const filters = this.getAllFilters();
    return filters.find(f => f.id === id) || null;
  }

  /**
   * Get the default filter (if any)
   */
  getDefaultFilter(): SavedFilter | null {
    const filters = this.getAllFilters();
    return filters.find(f => f.isDefault) || null;
  }

  /**
   * Save a new filter
   */
  saveFilter(filter: Omit<SavedFilter, 'id' | 'createdAt' | 'updatedAt'>): SavedFilter {
    const filters = this.getAllFilters();

    // Check if we've reached the maximum number of filters
    if (filters.length >= this.maxFilters) {
      throw new Error(`Maximum of ${this.maxFilters} saved filters reached. Please delete an existing filter first.`);
    }

    // Check for duplicate names
    if (filters.some(f => f.name.toLowerCase() === filter.name.toLowerCase())) {
      throw new Error('A filter with this name already exists.');
    }

    const now = Date.now();
    const newFilter: SavedFilter = {
      ...filter,
      id: this.generateId(),
      createdAt: now,
      updatedAt: now
    };

    // If this is set as default, unset other defaults
    if (newFilter.isDefault) {
      filters.forEach(f => f.isDefault = false);
    }

    filters.push(newFilter);
    this.saveToStorage(filters);

    return newFilter;
  }

  /**
   * Update an existing filter
   */
  updateFilter(id: string, updates: Partial<Omit<SavedFilter, 'id' | 'createdAt'>>): SavedFilter {
    const filters = this.getAllFilters();
    const index = filters.findIndex(f => f.id === id);

    if (index === -1) {
      throw new Error('Filter not found.');
    }

    // Check for duplicate names (excluding current filter)
    if (updates.name) {
      const duplicate = filters.find(f => 
        f.id !== id && f.name.toLowerCase() === updates.name!.toLowerCase()
      );
      if (duplicate) {
        throw new Error('A filter with this name already exists.');
      }
    }

    // If setting as default, unset other defaults
    if (updates.isDefault) {
      filters.forEach(f => f.isDefault = false);
    }

    const updatedFilter: SavedFilter = {
      ...filters[index],
      ...updates,
      updatedAt: Date.now()
    };

    filters[index] = updatedFilter;
    this.saveToStorage(filters);

    return updatedFilter;
  }

  /**
   * Delete a filter
   */
  deleteFilter(id: string): void {
    const filters = this.getAllFilters();
    const filtered = filters.filter(f => f.id !== id);

    if (filtered.length === filters.length) {
      throw new Error('Filter not found.');
    }

    this.saveToStorage(filtered);
  }

  /**
   * Set a filter as default
   */
  setDefaultFilter(id: string): void {
    const filters = this.getAllFilters();
    const filter = filters.find(f => f.id === id);

    if (!filter) {
      throw new Error('Filter not found.');
    }

    // Unset all defaults
    filters.forEach(f => f.isDefault = false);

    // Set the new default
    filter.isDefault = true;
    filter.updatedAt = Date.now();

    this.saveToStorage(filters);
  }

  /**
   * Clear the default filter
   */
  clearDefaultFilter(): void {
    const filters = this.getAllFilters();
    filters.forEach(f => f.isDefault = false);
    this.saveToStorage(filters);
  }

  /**
   * Export a filter as JSON
   */
  exportFilter(id: string): string {
    const filter = this.getFilter(id);
    if (!filter) {
      throw new Error('Filter not found.');
    }

    return JSON.stringify(filter, null, 2);
  }

  /**
   * Import a filter from JSON
   */
  importFilter(json: string): SavedFilter {
    try {
      const filter = JSON.parse(json);

      // Validate required fields
      if (!filter.name || !filter.filters) {
        throw new Error('Invalid filter format.');
      }

      // Remove ID to create a new filter
      const { id, createdAt, updatedAt, ...filterData } = filter;

      return this.saveFilter(filterData);
    } catch (error) {
      if (error instanceof SyntaxError) {
        throw new Error('Invalid JSON format.');
      }
      throw error;
    }
  }

  /**
   * Clear all saved filters
   */
  clearAll(): void {
    localStorage.removeItem(this.storageKey);
  }

  /**
   * Save filters to localStorage
   */
  private saveToStorage(filters: SavedFilter[]): void {
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(filters));
    } catch (error) {
      console.error('Failed to save filters:', error);
      throw new Error('Failed to save filters. Storage may be full.');
    }
  }

  /**
   * Generate a unique ID
   */
  private generateId(): string {
    return `filter_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Get filter count
   */
  getFilterCount(): number {
    return this.getAllFilters().length;
  }

  /**
   * Check if maximum filters reached
   */
  isMaxFiltersReached(): boolean {
    return this.getFilterCount() >= this.maxFilters;
  }

  /**
   * Get available filter slots
   */
  getAvailableSlots(): number {
    return Math.max(0, this.maxFilters - this.getFilterCount());
  }
}

// Singleton instance
export const filterManager = new FilterManager();

/**
 * Apply a saved filter to the dashboard state
 */
export function applyFilter(filter: SavedFilter, dashboardState: any): void {
  // Apply filters
  if (filter.filters.search !== undefined) {
    dashboardState.filters.search = filter.filters.search;
  }
  if (filter.filters.isCompleted !== undefined) {
    dashboardState.filters.isCompleted = filter.filters.isCompleted;
  }
  if (filter.filters.createdAfter !== undefined) {
    dashboardState.filters.createdAfter = filter.filters.createdAfter;
  }
  if (filter.filters.createdBefore !== undefined) {
    dashboardState.filters.createdBefore = filter.filters.createdBefore;
  }
  if (filter.filters.assignees !== undefined) {
    dashboardState.filters.assignees = filter.filters.assignees;
  }
  if (filter.filters.priorities !== undefined) {
    dashboardState.filters.priorities = filter.filters.priorities;
  }
  if (filter.filters.tags !== undefined) {
    dashboardState.filters.tags = filter.filters.tags;
  }
  if (filter.filters.customFields !== undefined) {
    dashboardState.filters.customFields = filter.filters.customFields;
  }

  // Apply sort
  if (filter.sortColumn !== undefined) {
    dashboardState.sort.column = filter.sortColumn;
  }
  if (filter.sortDirection !== undefined) {
    dashboardState.sort.direction = filter.sortDirection;
  }

  // Reset pagination
  dashboardState.currentOffset = 0;
}

/**
 * Create a filter from current dashboard state
 */
export function createFilterFromState(dashboardState: any): Omit<SavedFilter, 'id' | 'name' | 'createdAt' | 'updatedAt'> {
  return {
    filters: {
      search: dashboardState.filters.search || undefined,
      isCompleted: dashboardState.filters.isCompleted !== null ? dashboardState.filters.isCompleted : undefined,
      createdAfter: dashboardState.filters.createdAfter || undefined,
      createdBefore: dashboardState.filters.createdBefore || undefined,
      assignees: dashboardState.filters.assignees || undefined,
      priorities: dashboardState.filters.priorities || undefined,
      tags: dashboardState.filters.tags || undefined,
      customFields: dashboardState.filters.customFields || undefined
    },
    sortColumn: dashboardState.sort.column,
    sortDirection: dashboardState.sort.direction
  };
}

/**
 * Check if current state matches a saved filter
 */
export function isFilterActive(filter: SavedFilter, dashboardState: any): boolean {
  const currentFilter = createFilterFromState(dashboardState);
  
  return JSON.stringify(currentFilter.filters) === JSON.stringify(filter.filters) &&
         currentFilter.sortColumn === filter.sortColumn &&
         currentFilter.sortDirection === filter.sortDirection;
}

/**
 * Get a human-readable description of a filter
 */
export function getFilterDescription(filter: SavedFilter): string {
  const parts: string[] = [];

  if (filter.filters.search) {
    parts.push(`Search: "${filter.filters.search}"`);
  }

  if (filter.filters.isCompleted === 0) {
    parts.push('Active only');
  } else if (filter.filters.isCompleted === 1) {
    parts.push('Completed only');
  }

  if (filter.filters.createdAfter || filter.filters.createdBefore) {
    parts.push('Date range');
  }

  if (filter.filters.assignees && filter.filters.assignees.length > 0) {
    parts.push(`${filter.filters.assignees.length} assignee(s)`);
  }

  if (filter.filters.priorities && filter.filters.priorities.length > 0) {
    parts.push(`${filter.filters.priorities.length} priority(ies)`);
  }

  if (filter.filters.tags && filter.filters.tags.length > 0) {
    parts.push(`${filter.filters.tags.length} tag(s)`);
  }

  if (filter.sortColumn) {
    parts.push(`Sort by ${filter.sortColumn}`);
  }

  return parts.length > 0 ? parts.join(' • ') : 'No filters applied';
}

// Export the singleton instance
export default filterManager;
