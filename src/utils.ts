/* eslint-disable @typescript-eslint/no-explicit-any */
declare const bootstrap: any;
import { appConfig } from "./config";

export const escapeHtml = (s: any): string =>
  String(s).replace(/[&<>"]/g, (c) => {
    const map: Record<string, string> = {
      "&": "&" + "amp;",
      "<": "&" + "lt;",
      ">": "&" + "gt;",
      '"': "&" + "quot;"
    };
    return map[c] || c;
  });

export type ToastType = "error" | "success" | "info" | "warning";
export type ToastPosition = "top-right" | "top-left" | "bottom-right" | "bottom-left" | "top-center" | "bottom-center";

export interface ToastOptions {
  type?: ToastType;
  position?: ToastPosition;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
  showProgress?: boolean;
}

export function showToast(message: string, typeOrOptions?: ToastType | ToastOptions) {
  // Handle backward compatibility
  let options: ToastOptions;
  if (typeof typeOrOptions === 'string') {
    options = { type: typeOrOptions };
  } else {
    options = typeOrOptions || {};
  }

  const {
    type = "info",
    position = "top-right",
    duration = 4000,
    action,
    showProgress = false
  } = options;

  // Get or create container for this position
  const containerId = `toastContainer-${position}`;
  let container = document.getElementById(containerId);
  
  if (!container) {
    container = document.createElement("div");
    container.id = containerId;
    container.className = `toast-container position-fixed p-3 toast-position-${position}`;
    container.style.zIndex = "12000";
    
    // Set position styles
    switch (position) {
      case "top-right":
        container.style.top = "16px";
        container.style.right = "16px";
        break;
      case "top-left":
        container.style.top = "16px";
        container.style.left = "16px";
        break;
      case "bottom-right":
        container.style.bottom = "16px";
        container.style.right = "16px";
        break;
      case "bottom-left":
        container.style.bottom = "16px";
        container.style.left = "16px";
        break;
      case "top-center":
        container.style.top = "16px";
        container.style.left = "50%";
        container.style.transform = "translateX(-50%)";
        break;
      case "bottom-center":
        container.style.bottom = "16px";
        container.style.left = "50%";
        container.style.transform = "translateX(-50%)";
        break;
    }
    
    document.body.appendChild(container);
  }

  const div = document.createElement("div");
  const variant =
    type === "error"
      ? "bg-danger text-white"
      : type === "success"
      ? "bg-success text-white"
      : type === "warning"
      ? "bg-warning text-dark"
      : "bg-info text-white";
  
  div.className = `toast align-items-center ${variant}`;
  div.setAttribute("role", "alert");
  div.setAttribute("aria-live", "assertive");
  div.setAttribute("aria-atomic", "true");
  
  const safeMessage = escapeHtml(message ?? "");
  
  let progressHtml = "";
  if (showProgress) {
    progressHtml = `
      <div class="toast-progress-bar" style="position: absolute; bottom: 0; left: 0; right: 0; height: 3px; background: rgba(255,255,255,0.3); overflow: hidden;">
        <div class="toast-progress-fill" style="height: 100%; background: rgba(255,255,255,0.8); width: 100%; animation: toastProgress ${duration}ms linear;"></div>
      </div>
    `;
  }
  
  let actionHtml = "";
  if (action) {
    actionHtml = `
      <button type="button" class="btn btn-sm btn-light toast-action-btn" style="margin-right: 8px;">
        ${escapeHtml(action.label)}
      </button>
    `;
  }
  
  div.innerHTML = `
    <div class="d-flex align-items-center" style="position: relative;">
      <div class="toast-body" style="flex: 1;">${safeMessage}</div>
      ${actionHtml}
      <button type="button" class="btn-close ${type === 'warning' ? '' : 'btn-close-white'}" data-bs-dismiss="toast" aria-label="Close"></button>
      ${progressHtml}
    </div>
  `;
  
  container.appendChild(div);
  
  // Add action button handler
  if (action) {
    const actionBtn = div.querySelector('.toast-action-btn');
    if (actionBtn) {
      actionBtn.addEventListener('click', () => {
        action.onClick();
        const toastObj = bootstrap.Toast.getInstance(div);
        if (toastObj) {
          toastObj.hide();
        }
      });
    }
  }
  
  const toastObj = new bootstrap.Toast(div, { delay: duration, autohide: duration > 0 });
  toastObj.show();
  
  div.addEventListener("hidden.bs.toast", () => {
    if (div.parentNode === container) {
      container.removeChild(div);
    }
  });
  
  return {
    hide: () => toastObj.hide(),
    element: div
  };
}

// Add CSS for toast progress animation
if (typeof document !== 'undefined' && !document.getElementById('toast-progress-styles')) {
  const style = document.createElement('style');
  style.id = 'toast-progress-styles';
  style.textContent = `
    @keyframes toastProgress {
      from { width: 100%; }
      to { width: 0%; }
    }
  `;
  document.head.appendChild(style);
}

export async function requestJson<T = any>(url: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(url, options);
  const text = await resp.text();
  let data: any = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch (err) {
      data = null;
    }
  }
  if (!resp.ok) {
    const detail = data && typeof data === "object" ? (data.detail || data.error) : "";
    throw new Error(detail || text || `Request to ${url} failed (${resp.status})`);
  }
  return (data || {}) as T;
}

export const parseIntMaybe = (value: any): number | null => {
  const num = parseInt(value, 10);
  return Number.isFinite(num) ? num : null;
};

export const parseIdList = (text: string): number[] => {
  if (!text) return [];
  return text
    .split(",")
    .map((x) => parseInt(x.trim(), 10))
    .filter((x) => Number.isFinite(x));
};

export const formatDuration = (ms: number | null | undefined): string | null => {
  if (ms === null || ms === undefined) return null;
  const secs = Math.max(0, Math.round(ms / 1000));
  if (secs >= 3600) {
    const hours = Math.floor(secs / 3600);
    const mins = Math.floor((secs % 3600) / 60);
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  }
  if (secs >= 90) {
    const mins = Math.floor(secs / 60);
    const rem = secs % 60;
    return rem > 0 ? `${mins}m ${rem}s` : `${mins}m`;
  }
  if (secs >= 60) {
    return `1m ${secs - 60}s`;
  }
  return `${secs}s`;
};

export { appConfig };
