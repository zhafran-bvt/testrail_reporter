/* eslint-disable @typescript-eslint/no-explicit-any */
declare const bootstrap: any;
import { appConfig } from "./config";

export const escapeHtml = (s: any): string =>
  String(s).replace(/[&<>\"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c] || c));

export function showToast(message: string, type: "error" | "success" | "info" = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const div = document.createElement("div");
  const variant =
    type === "error"
      ? "bg-danger text-white"
      : type === "success"
      ? "bg-success text-white"
      : "bg-info text-white";
  div.className = `toast align-items-center ${variant}`;
  div.setAttribute("role", "alert");
  div.setAttribute("aria-live", "assertive");
  div.setAttribute("aria-atomic", "true");
  const safeMessage = escapeHtml(message ?? "");
  div.innerHTML = `<div class=\"d-flex\">
        <div class=\"toast-body\">${safeMessage}</div>
      </div>`;
  container.appendChild(div);
  const toastObj = new bootstrap.Toast(div, { delay: 4000 });
  toastObj.show();
  div.addEventListener("hidden.bs.toast", () => {
    if (div.parentNode === container) {
      container.removeChild(div);
    }
  });
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
