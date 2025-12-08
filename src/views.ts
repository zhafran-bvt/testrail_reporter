export function switchView(target: "reporter" | "manage" | "howto" | "dashboard") {
  const reporter = document.getElementById("reporterView");
  const manage = document.getElementById("manageView");
  const howto = document.getElementById("howToView");
  const dashboard = document.getElementById("dashboardView");
  const linkReporter = document.getElementById("linkReporter");
  const linkManage = document.getElementById("linkManage");
  const linkHowto = document.getElementById("linkHowTo");
  const linkDashboard = document.getElementById("linkDashboard");
  
  // Hide all views
  reporter?.classList.add("hidden");
  manage?.classList.add("hidden");
  howto?.classList.add("hidden");
  dashboard?.classList.add("hidden");
  
  // Remove active state from all nav links
  linkReporter?.classList.remove("active");
  linkManage?.classList.remove("active");
  linkHowto?.classList.remove("active");
  linkDashboard?.classList.remove("active");
  
  // Show target view and activate corresponding nav link
  if (target === "manage") {
    manage?.classList.remove("hidden");
    linkManage?.classList.add("active");
    // Auto-load all subsections when switching to management view (Requirements 3.1, 3.2, 3.3)
    if (typeof (window as any).initManageView === 'function') {
      (window as any).initManageView();
    }
  } else if (target === "howto") {
    howto?.classList.remove("hidden");
    linkHowto?.classList.add("active");
  } else if (target === "dashboard") {
    dashboard?.classList.remove("hidden");
    linkDashboard?.classList.add("active");
    // Initialize dashboard when switching to it
    if (typeof (window as any).dashboardModule !== 'undefined') {
      (window as any).dashboardModule.init();
    }
  } else {
    reporter?.classList.remove("hidden");
    linkReporter?.classList.add("active");
  }
}

export function togglePanel(id: string, action?: "open" | "close") {
  const panel = document.getElementById(id);
  if (!panel) return;
  const toggle = document.querySelector<HTMLElement>(`[data-panel="${id}"]`);
  const isHidden = panel.classList.contains("hidden");
  let shouldShow: boolean;
  if (action === "open") {
    shouldShow = true;
  } else if (action === "close") {
    shouldShow = false;
  } else {
    shouldShow = isHidden;
  }
  if (shouldShow) {
    panel.classList.remove("hidden");
  } else {
    panel.classList.add("hidden");
  }
  if (toggle) {
    toggle.setAttribute("aria-expanded", shouldShow ? "true" : "false");
    const icon = toggle.querySelector<HTMLElement>(".toggle-icon");
    if (icon) {
      icon.textContent = shouldShow ? "▼" : "▶";
    }
  }
}
