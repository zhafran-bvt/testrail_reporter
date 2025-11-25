export function setupThemeToggle() {
  const themeToggle = document.getElementById("theme-toggle");
  const themeIcon = document.getElementById("report-theme-icon");
  const htmlEl = document.documentElement;
  if (!themeToggle || !themeIcon) return;

  const sunIcon =
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4.75a.75.75 0 0 1 .75-.75h.5a.75.75 0 0 1 0 1.5h-.5A.75.75 0 0 1 12 4.75Zm5.657 2.093a.75.75 0 1 1 1.06 1.06l-.354.354a.75.75 0 0 1-1.06-1.06l.354-.354ZM5.637 6.843a.75.75 0 0 1 1.06-1.06l.354.353a.75.75 0 0 1-1.06 1.061l-.354-.354ZM12 7.5A4.5 4.5 0 1 1 7.5 12 4.505 4.505 0 0 1 12 7.5Zm0 1.5A3 3 0 1 0 15 12a3 3 0 0 0-3-3Zm7.25 3.25a.75.75 0 0 1 0 1.5h-.5a.75.75 0 0 1 0-1.5h.5Zm-13 .75a.75.75 0 0 1-.75.75h-.5a.75.75 0 0 1 0-1.5h.5a.75.75 0 0 1 .75.75Zm10.657 4.657a.75.75 0 0 1 1.06 0l.354.354a.75.75 0 1 1-1.06 1.06l-.354-.353a.75.75 0 0 1 0-1.061Zm-10.657 0a.75.75 0 0 1 0 1.061l-.354.353a.75.75 0 0 1-1.06-1.06l.354-.354a.75.75 0 0 1 1.06 0Zm5.75.75a.75.75 0 0 1 .75.75v.5a.75.75 0 0 1-1.5 0v-.5a.75.75 0 0 1 .75-.75Z"/></svg>';
  const moonIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 14.5A8.5 8.5 0 1 1 9.5 3a.75.75 0 0 1 .808.407 6.5 6.5 0 0 0 10.285 7.186.75.75 0 0 1 .407.808z"/></svg>';

  function updateThemeIcon(theme: string) {
    const nextLabel = theme === "dark" ? "Switch to light mode" : "Switch to dark mode";
    themeToggle.setAttribute("aria-label", nextLabel);
    themeToggle.setAttribute("title", nextLabel);
    (themeToggle as HTMLElement).dataset.mode = theme;
    themeIcon.innerHTML = theme === "dark" ? sunIcon : moonIcon;
  }

  function applyTheme(theme: string) {
    const normalized = theme === "dark" ? "dark" : "light";
    htmlEl.setAttribute("data-theme", normalized);
    htmlEl.setAttribute("data-bs-theme", normalized);
    updateThemeIcon(normalized);
  }

  themeToggle.addEventListener("click", () => {
    const current = htmlEl.getAttribute("data-theme");
    const nextTheme = current === "dark" ? "light" : "dark";
    localStorage.setItem("theme", nextTheme);
    applyTheme(nextTheme);
  });

  const savedTheme = localStorage.getItem("theme");
  if (savedTheme) {
    applyTheme(savedTheme);
  } else {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    applyTheme(prefersDark ? "dark" : "light");
  }
}

export { appConfig };
