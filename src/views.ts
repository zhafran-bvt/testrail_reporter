export function switchView(target: "reporter" | "manage" | "howto") {
  const reporter = document.getElementById("reporterView");
  const manage = document.getElementById("manageView");
  const howto = document.getElementById("howToView");
  const linkReporter = document.getElementById("linkReporter");
  const linkManage = document.getElementById("linkManage");
  const linkHowto = document.getElementById("linkHowTo");
  reporter?.classList.add("hidden");
  manage?.classList.add("hidden");
  howto?.classList.add("hidden");
  linkReporter?.classList.remove("active");
  linkManage?.classList.remove("active");
  linkHowto?.classList.remove("active");
  if (target === "manage") {
    manage?.classList.remove("hidden");
    linkManage?.classList.add("active");
  } else if (target === "howto") {
    howto?.classList.remove("hidden");
    linkHowto?.classList.add("active");
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
