/**
 * Time Utilities Module
 * 
 * Provides functions for formatting timestamps in human-readable formats,
 * including relative time (e.g., "2 hours ago") and absolute time formatting.
 */

/**
 * Format a timestamp as relative time (e.g., "2 hours ago")
 * @param timestamp - Unix timestamp in seconds or Date object
 * @returns Relative time string
 */
export function formatRelativeTime(timestamp: number | Date): string {
  const now = Date.now();
  const date = timestamp instanceof Date ? timestamp : new Date(timestamp * 1000);
  const diffMs = now - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);
  const diffWeek = Math.floor(diffDay / 7);
  const diffMonth = Math.floor(diffDay / 30);
  const diffYear = Math.floor(diffDay / 365);

  // Future dates
  if (diffMs < 0) {
    return 'in the future';
  }

  // Just now (< 1 minute)
  if (diffMin < 1) {
    return 'just now';
  }

  // X minutes ago (< 1 hour)
  if (diffHour < 1) {
    return `${diffMin} minute${diffMin === 1 ? '' : 's'} ago`;
  }

  // X hours ago (< 24 hours)
  if (diffDay < 1) {
    return `${diffHour} hour${diffHour === 1 ? '' : 's'} ago`;
  }

  // Yesterday (1 day ago)
  if (diffDay === 1) {
    return 'yesterday';
  }

  // X days ago (< 7 days)
  if (diffWeek < 1) {
    return `${diffDay} day${diffDay === 1 ? '' : 's'} ago`;
  }

  // Last week (< 14 days)
  if (diffDay < 14) {
    return 'last week';
  }

  // X weeks ago (< 30 days)
  if (diffMonth < 1) {
    return `${diffWeek} week${diffWeek === 1 ? '' : 's'} ago`;
  }

  // Last month (< 60 days)
  if (diffDay < 60) {
    return 'last month';
  }

  // X months ago (< 365 days)
  if (diffYear < 1) {
    return `${diffMonth} month${diffMonth === 1 ? '' : 's'} ago`;
  }

  // Last year (< 730 days)
  if (diffDay < 730) {
    return 'last year';
  }

  // X years ago (> 730 days)
  return `${diffYear} year${diffYear === 1 ? '' : 's'} ago`;
}

/**
 * Format a timestamp as absolute time with date and time
 * @param timestamp - Unix timestamp in seconds or Date object
 * @returns Formatted date and time string
 */
export function formatAbsoluteTime(timestamp: number | Date): string {
  const date = timestamp instanceof Date ? timestamp : new Date(timestamp * 1000);
  
  const dateStr = date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
  
  const timeStr = date.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit'
  });
  
  return `${dateStr} at ${timeStr}`;
}

/**
 * Format a timestamp with both relative and absolute time
 * Returns an object with both formats for use in UI (e.g., relative as text, absolute as tooltip)
 * @param timestamp - Unix timestamp in seconds or Date object
 * @returns Object with relative and absolute time strings
 */
export function formatTimestamp(timestamp: number | Date): { relative: string; absolute: string } {
  return {
    relative: formatRelativeTime(timestamp),
    absolute: formatAbsoluteTime(timestamp)
  };
}

/**
 * Create a time element with relative time and absolute time tooltip
 * @param timestamp - Unix timestamp in seconds or Date object
 * @param className - Optional CSS class name
 * @returns HTML string for time element
 */
export function createTimeElement(timestamp: number | Date, className: string = ''): string {
  const { relative, absolute } = formatTimestamp(timestamp);
  const isoString = timestamp instanceof Date ? timestamp.toISOString() : new Date(timestamp * 1000).toISOString();
  
  return `<time datetime="${isoString}" title="${absolute}" class="${className}" data-timestamp="${typeof timestamp === 'number' ? timestamp : Math.floor(timestamp.getTime() / 1000)}">${relative}</time>`;
}

/**
 * Update all time elements on the page with fresh relative times
 * Should be called periodically (e.g., every minute) to keep times current
 */
export function updateAllTimeElements(): void {
  const timeElements = document.querySelectorAll('time[data-timestamp]');
  
  timeElements.forEach((element) => {
    const timestamp = parseInt(element.getAttribute('data-timestamp') || '0', 10);
    if (timestamp > 0) {
      const { relative, absolute } = formatTimestamp(timestamp);
      element.textContent = relative;
      element.setAttribute('title', absolute);
    }
  });
}

/**
 * Start auto-updating time elements every minute
 * @returns Function to stop the auto-update
 */
export function startTimeUpdates(): () => void {
  const intervalId = setInterval(updateAllTimeElements, 60000); // Update every minute
  
  return () => clearInterval(intervalId);
}

/**
 * Format duration in milliseconds to human-readable format
 * @param ms - Duration in milliseconds
 * @returns Formatted duration string
 */
export function formatDurationMs(ms: number): string {
  if (ms < 1000) {
    return `${ms}ms`;
  }
  
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  
  if (hours > 0) {
    const remainingMinutes = minutes % 60;
    return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
  }
  
  if (minutes > 0) {
    const remainingSeconds = seconds % 60;
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
  }
  
  return `${seconds}s`;
}

/**
 * Parse a date string or timestamp and return a Date object
 * @param input - Date string, Unix timestamp (seconds), or Date object
 * @returns Date object or null if invalid
 */
export function parseDate(input: string | number | Date | null | undefined): Date | null {
  if (!input) {
    return null;
  }
  
  if (input instanceof Date) {
    return input;
  }
  
  if (typeof input === 'number') {
    // Assume Unix timestamp in seconds if less than a reasonable millisecond timestamp
    const timestamp = input < 10000000000 ? input * 1000 : input;
    return new Date(timestamp);
  }
  
  if (typeof input === 'string') {
    const date = new Date(input);
    return isNaN(date.getTime()) ? null : date;
  }
  
  return null;
}

/**
 * Check if a timestamp is today
 * @param timestamp - Unix timestamp in seconds or Date object
 * @returns True if timestamp is today
 */
export function isToday(timestamp: number | Date): boolean {
  const date = timestamp instanceof Date ? timestamp : new Date(timestamp * 1000);
  const today = new Date();
  
  return date.getDate() === today.getDate() &&
         date.getMonth() === today.getMonth() &&
         date.getFullYear() === today.getFullYear();
}

/**
 * Check if a timestamp is within the current week
 * @param timestamp - Unix timestamp in seconds or Date object
 * @returns True if timestamp is within current week
 */
export function isThisWeek(timestamp: number | Date): boolean {
  const date = timestamp instanceof Date ? timestamp : new Date(timestamp * 1000);
  const now = new Date();
  
  // Get start of week (Sunday)
  const startOfWeek = new Date(now);
  startOfWeek.setDate(now.getDate() - now.getDay());
  startOfWeek.setHours(0, 0, 0, 0);
  
  // Get end of week (Saturday)
  const endOfWeek = new Date(startOfWeek);
  endOfWeek.setDate(startOfWeek.getDate() + 6);
  endOfWeek.setHours(23, 59, 59, 999);
  
  return date >= startOfWeek && date <= endOfWeek;
}

/**
 * Check if a timestamp is within the current month
 * @param timestamp - Unix timestamp in seconds or Date object
 * @returns True if timestamp is within current month
 */
export function isThisMonth(timestamp: number | Date): boolean {
  const date = timestamp instanceof Date ? timestamp : new Date(timestamp * 1000);
  const now = new Date();
  
  return date.getMonth() === now.getMonth() &&
         date.getFullYear() === now.getFullYear();
}

/**
 * Get timestamp for start of today (00:00:00)
 * @returns Unix timestamp in seconds
 */
export function getStartOfToday(): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.floor(today.getTime() / 1000);
}

/**
 * Get timestamp for start of current week (Sunday 00:00:00)
 * @returns Unix timestamp in seconds
 */
export function getStartOfWeek(): number {
  const now = new Date();
  const startOfWeek = new Date(now);
  startOfWeek.setDate(now.getDate() - now.getDay());
  startOfWeek.setHours(0, 0, 0, 0);
  return Math.floor(startOfWeek.getTime() / 1000);
}

/**
 * Get timestamp for start of current month (1st day 00:00:00)
 * @returns Unix timestamp in seconds
 */
export function getStartOfMonth(): number {
  const now = new Date();
  const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1, 0, 0, 0, 0);
  return Math.floor(startOfMonth.getTime() / 1000);
}
