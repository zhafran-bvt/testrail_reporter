(() => {
  var __defProp = Object.defineProperty;
  var __defProps = Object.defineProperties;
  var __getOwnPropDescs = Object.getOwnPropertyDescriptors;
  var __getOwnPropSymbols = Object.getOwnPropertySymbols;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __propIsEnum = Object.prototype.propertyIsEnumerable;
  var __defNormalProp = (obj, key, value) => key in obj ? __defProp(obj, key, { enumerable: true, configurable: true, writable: true, value }) : obj[key] = value;
  var __spreadValues = (a, b) => {
    for (var prop in b || (b = {}))
      if (__hasOwnProp.call(b, prop))
        __defNormalProp(a, prop, b[prop]);
    if (__getOwnPropSymbols)
      for (var prop of __getOwnPropSymbols(b)) {
        if (__propIsEnum.call(b, prop))
          __defNormalProp(a, prop, b[prop]);
      }
    return a;
  };
  var __spreadProps = (a, b) => __defProps(a, __getOwnPropDescs(b));
  var __publicField = (obj, key, value) => __defNormalProp(obj, typeof key !== "symbol" ? key + "" : key, value);

  // src/theme.ts
  function setupThemeToggle() {
    const themeToggle = document.getElementById("theme-toggle");
    const themeIcon = document.getElementById("report-theme-icon");
    const htmlEl = document.documentElement;
    if (!themeToggle || !themeIcon) return;
    const sunIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4.75a.75.75 0 0 1 .75-.75h.5a.75.75 0 0 1 0 1.5h-.5A.75.75 0 0 1 12 4.75Zm5.657 2.093a.75.75 0 1 1 1.06 1.06l-.354.354a.75.75 0 0 1-1.06-1.06l.354-.354ZM5.637 6.843a.75.75 0 0 1 1.06-1.06l.354.353a.75.75 0 0 1-1.06 1.061l-.354-.354ZM12 7.5A4.5 4.5 0 1 1 7.5 12 4.505 4.505 0 0 1 12 7.5Zm0 1.5A3 3 0 1 0 15 12a3 3 0 0 0-3-3Zm7.25 3.25a.75.75 0 0 1 0 1.5h-.5a.75.75 0 0 1 0-1.5h.5Zm-13 .75a.75.75 0 0 1-.75.75h-.5a.75.75 0 0 1 0-1.5h.5a.75.75 0 0 1 .75.75Zm10.657 4.657a.75.75 0 0 1 1.06 0l.354.354a.75.75 0 1 1-1.06 1.06l-.354-.353a.75.75 0 0 1 0-1.061Zm-10.657 0a.75.75 0 0 1 0 1.061l-.354.353a.75.75 0 0 1-1.06-1.06l.354-.354a.75.75 0 0 1 1.06 0Zm5.75.75a.75.75 0 0 1 .75.75v.5a.75.75 0 0 1-1.5 0v-.5a.75.75 0 0 1 .75-.75Z"/></svg>';
    const moonIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 14.5A8.5 8.5 0 1 1 9.5 3a.75.75 0 0 1 .808.407 6.5 6.5 0 0 0 10.285 7.186.75.75 0 0 1 .407.808z"/></svg>';
    function updateThemeIcon(theme) {
      const nextLabel = theme === "dark" ? "Switch to light mode" : "Switch to dark mode";
      themeToggle.setAttribute("aria-label", nextLabel);
      themeToggle.setAttribute("title", nextLabel);
      themeToggle.dataset.mode = theme;
      themeIcon.innerHTML = theme === "dark" ? sunIcon : moonIcon;
    }
    function applyTheme(theme) {
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

  // src/views.ts
  function switchView(target) {
    const reporter = document.getElementById("reporterView");
    const manage = document.getElementById("manageView");
    const howto = document.getElementById("howToView");
    const dashboard = document.getElementById("dashboardView");
    const linkReporter = document.getElementById("linkReporter");
    const linkManage = document.getElementById("linkManage");
    const linkHowto = document.getElementById("linkHowTo");
    const linkDashboard = document.getElementById("linkDashboard");
    reporter == null ? void 0 : reporter.classList.add("hidden");
    manage == null ? void 0 : manage.classList.add("hidden");
    howto == null ? void 0 : howto.classList.add("hidden");
    dashboard == null ? void 0 : dashboard.classList.add("hidden");
    linkReporter == null ? void 0 : linkReporter.classList.remove("active");
    linkManage == null ? void 0 : linkManage.classList.remove("active");
    linkHowto == null ? void 0 : linkHowto.classList.remove("active");
    linkDashboard == null ? void 0 : linkDashboard.classList.remove("active");
    if (target === "manage") {
      manage == null ? void 0 : manage.classList.remove("hidden");
      linkManage == null ? void 0 : linkManage.classList.add("active");
      if (typeof window.initManageView === "function") {
        window.initManageView();
      }
    } else if (target === "howto") {
      howto == null ? void 0 : howto.classList.remove("hidden");
      linkHowto == null ? void 0 : linkHowto.classList.add("active");
    } else if (target === "dashboard") {
      dashboard == null ? void 0 : dashboard.classList.remove("hidden");
      linkDashboard == null ? void 0 : linkDashboard.classList.add("active");
      if (typeof window.dashboardModule !== "undefined") {
        window.dashboardModule.init();
      }
    } else {
      reporter == null ? void 0 : reporter.classList.remove("hidden");
      linkReporter == null ? void 0 : linkReporter.classList.add("active");
    }
  }
  function togglePanel(id, action) {
    const panel = document.getElementById(id);
    if (!panel) return;
    const toggle = document.querySelector(`[data-panel="${id}"]`);
    const isHidden = panel.classList.contains("hidden");
    let shouldShow;
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
      const icon = toggle.querySelector(".toggle-icon");
      if (icon) {
        icon.textContent = shouldShow ? "\u25BC" : "\u25B6";
      }
    }
  }

  // src/config.ts
  var appConfig2 = window.__APP_CONFIG__ || {};

  // src/utils.ts
  var escapeHtml = (s) => String(s).replace(/[&<>\"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c] || c);
  function showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    if (!container) return;
    const div = document.createElement("div");
    const variant = type === "error" ? "bg-danger text-white" : type === "success" ? "bg-success text-white" : "bg-info text-white";
    div.className = `toast align-items-center ${variant}`;
    div.setAttribute("role", "alert");
    div.setAttribute("aria-live", "assertive");
    div.setAttribute("aria-atomic", "true");
    const safeMessage = escapeHtml(message != null ? message : "");
    div.innerHTML = `<div class="d-flex">
        <div class="toast-body">${safeMessage}</div>
      </div>`;
    container.appendChild(div);
    const toastObj = new bootstrap.Toast(div, { delay: 4e3 });
    toastObj.show();
    div.addEventListener("hidden.bs.toast", () => {
      if (div.parentNode === container) {
        container.removeChild(div);
      }
    });
  }
  async function requestJson(url, options) {
    const resp = await fetch(url, options);
    const text = await resp.text();
    let data = null;
    if (text) {
      try {
        data = JSON.parse(text);
      } catch (err) {
        data = null;
      }
    }
    if (!resp.ok) {
      const detail = data && typeof data === "object" ? data.detail || data.error : "";
      throw new Error(detail || text || `Request to ${url} failed (${resp.status})`);
    }
    return data || {};
  }
  var parseIntMaybe = (value) => {
    const num = parseInt(value, 10);
    return Number.isFinite(num) ? num : null;
  };
  var parseIdList = (text) => {
    if (!text) return [];
    return text.split(",").map((x) => parseInt(x.trim(), 10)).filter((x) => Number.isFinite(x));
  };
  var formatDuration = (ms) => {
    if (ms === null || ms === void 0) return null;
    const secs = Math.max(0, Math.round(ms / 1e3));
    if (secs >= 3600) {
      const hours = Math.floor(secs / 3600);
      const mins = Math.floor(secs % 3600 / 60);
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

  // src/runsUI.ts
  function renderRuns(runs) {
    const runList = document.getElementById("run-list");
    const runEmpty = document.getElementById("run-empty");
    if (!runList || !runEmpty) return;
    if (!runs || runs.length === 0) {
      runList.innerHTML = "";
      runEmpty.textContent = "No runs found in this plan.";
      runEmpty.style.display = "block";
      return;
    }
    runList.innerHTML = runs.map((run) => {
      const name = run.name ? escapeHtml2(run.name) : `Run ${run.id}`;
      const searchTokens = `${run.id} ${run.name || ""}`.toLowerCase();
      return `<label class="run-card" data-text="${escapeHtml2(searchTokens)}">
          <input type="checkbox" name="run_ids" value="${run.id}" checked>
          <div class="run-card-content">
            <span class="run-card-title">${name}</span>
            <span class="run-card-id">Run ID: ${run.id}</span>
            </div>
        </label>`;
    }).join("");
    runEmpty.style.display = "none";
    runList.querySelectorAll('input[name="run_ids"]').forEach((cb) => {
      cb.addEventListener("change", updateRunSummary);
    });
  }
  function filterRuns() {
    const runList = document.getElementById("run-list");
    const runEmpty = document.getElementById("run-empty");
    const runSearch = document.getElementById("runSearch");
    if (!runList || !runEmpty || !runSearch) return;
    const query = (runSearch.value || "").trim().toLowerCase();
    let visible = 0;
    runList.querySelectorAll(".run-card").forEach((card) => {
      var _a;
      const matches = !query || ((_a = card.dataset.text) == null ? void 0 : _a.includes(query));
      card.style.display = matches ? "" : "none";
      if (matches) visible++;
    });
    if (visible === 0) {
      runEmpty.textContent = query ? "No runs match your search." : "No runs found in this plan.";
      runEmpty.style.display = "block";
    } else {
      runEmpty.style.display = "none";
    }
    updateRunSummary();
  }
  function updateRunSummary() {
    var _a;
    const runsSection = document.getElementById("runs-section");
    if (!runsSection || runsSection.dataset.available !== "1") return;
    const runsNote = document.getElementById("runs-note");
    const runList = document.getElementById("run-list");
    if (!runsNote || !runList) return;
    const cards = Array.from(runList.querySelectorAll(".run-card"));
    const total = cards.length;
    if (total === 0) {
      runsNote.textContent = "No runs found in this plan.";
      return;
    }
    const selected = runList.querySelectorAll('input[name="run_ids"]:checked').length;
    const visible = cards.filter((card) => card.style.display !== "none").length;
    const query = ((_a = document.getElementById("runSearch")) == null ? void 0 : _a.value.trim()) || "";
    let text = `Selected ${selected} of ${total} runs.`;
    if (query) {
      text += ` Showing ${visible} matching runs.`;
    }
    runsNote.textContent = text;
  }
  var escapeHtml2 = (s) => String(s).replace(/[&<>\"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c] || c);

  // src/plansRuns.ts
  var cachedPlanOptionsHtml = "";
  async function loadRuns() {
    const planSel = document.getElementById("plan");
    const projectInput = document.getElementById("project");
    const runsSection = document.getElementById("runs-section");
    const runList = document.getElementById("run-list");
    const runEmpty = document.getElementById("run-empty");
    const runSearch = document.getElementById("runSearch");
    const runsNote = document.getElementById("runs-note");
    const planVal = planSel == null ? void 0 : planSel.value;
    if (runList) runList.innerHTML = "";
    if (!planVal || !runsSection || !runsNote) {
      if (runsSection) {
        runsSection.style.display = "none";
        runsSection.dataset.available = "0";
      }
      if (runsNote) runsNote.textContent = "Runs will appear after selecting a plan.";
      if (runEmpty) {
        runEmpty.textContent = "Runs will appear after selecting a plan.";
        runEmpty.style.display = "block";
      }
      return;
    }
    runsSection.style.display = "block";
    runsSection.dataset.available = "0";
    runsNote.textContent = "Loading runs\u2026";
    if (runEmpty) {
      runEmpty.textContent = "Loading runs\u2026";
      runEmpty.style.display = "block";
    }
    if (runSearch) {
      runSearch.value = "";
    }
    try {
      const resp = await fetch(
        `/api/runs?project=${encodeURIComponent((projectInput == null ? void 0 : projectInput.value) || "1")}&plan=${encodeURIComponent(planVal)}`
      );
      if (!resp.ok) {
        const text = await resp.text().catch(() => "");
        throw new Error(text || `Failed to fetch runs for plan ${planVal}`);
      }
      const data = await resp.json();
      const runs = Array.isArray(data.runs) ? data.runs : [];
      if (runs.length === 0) {
        runsSection.dataset.available = "0";
        runsNote.textContent = "No runs found in this plan.";
        if (runEmpty) {
          runEmpty.textContent = "No runs found in this plan.";
          runEmpty.style.display = "block";
        }
        if (runList) runList.innerHTML = "";
        return;
      }
      runsSection.dataset.available = "1";
      renderRuns(runs);
      filterRuns();
    } catch (e) {
      runsSection.dataset.available = "0";
      runsNote.textContent = "Error loading runs. Try refreshing.";
      if (runList) runList.innerHTML = "";
      if (runEmpty) {
        runEmpty.textContent = "Error loading runs.";
        runEmpty.style.display = "block";
      }
      showToast("Failed to load runs for the selected plan.", "error");
    }
  }
  async function loadPlans(force = false) {
    const projectInput = document.getElementById("project");
    const project = projectInput ? projectInput.value || "1" : "1";
    const planSel = document.getElementById("plan");
    const note = document.getElementById("plan-note");
    const refreshBtn = document.getElementById("refreshPlansBtn");
    if (!planSel) {
      return;
    }
    if (force) {
      cachedPlanOptionsHtml = "";
      try {
        await fetch("/api/cache/clear", { method: "POST" });
      } catch (e) {
        console.warn("Failed to clear server cache:", e);
      }
    }
    planSel.innerHTML = '<option value="" disabled selected>Loading plans\u2026</option>';
    planSel.disabled = true;
    if (refreshBtn) {
      refreshBtn.disabled = true;
      refreshBtn.textContent = "Refreshing\u2026";
    }
    async function fetchPlans(url) {
      const resp = await fetch(url);
      if (!resp.ok) {
        const text = await resp.text().catch(() => "");
        throw new Error(text || `Failed to fetch ${url}`);
      }
      const data = await resp.json();
      let plans = Array.isArray(data.plans) ? data.plans : [];
      plans.sort((a, b) => (b.created_on || 0) - (a.created_on || 0) || String(a.name || "").localeCompare(String(b.name || "")));
      return plans;
    }
    try {
      let plans = await fetchPlans(`/api/plans?project=${encodeURIComponent(project)}&is_completed=0`);
      if (plans.length === 0) {
        plans = await fetchPlans(`/api/plans?project=${encodeURIComponent(project)}`);
        if (plans.length > 0 && note) {
          note.textContent = `No open plans. Showing ${plans.length} total plan(s).`;
          note.style.display = "";
        }
      } else if (note) {
        note.textContent = `Loaded ${plans.length} open plan(s).`;
        note.style.display = "";
      }
      if (plans.length === 0) {
        planSel.innerHTML = '<option value="" disabled selected>No plans found</option>';
        if (note) {
          note.textContent = "No plans found for this project.";
          note.style.display = "";
        }
      } else {
        const planOptions = plans.map((p) => `<option value="${p.id}">${escapeHtml(p.name || "Plan " + p.id)} (ID ${p.id})</option>`).join("");
        planSel.innerHTML = planOptions;
        planSel.selectedIndex = 0;
        cachedPlanOptionsHtml = planOptions;
        setManagePlanOptions(planOptions);
      }
    } catch (e) {
      planSel.innerHTML = '<option value="" disabled selected>Error loading plans</option>';
      if (note) {
        note.textContent = "Error loading plans. Check credentials or API access.";
        note.style.display = "";
      }
      showToast("Failed to load plans. Verify TestRail credentials and project ID.", "error");
    } finally {
      planSel.disabled = false;
    }
    if (refreshBtn) {
      refreshBtn.disabled = false;
      refreshBtn.textContent = "Refresh";
    }
    await loadRuns();
  }
  function setManagePlanOptions(planOptions) {
    const runPlanSelect = document.getElementById("runPlanSelect");
    if (runPlanSelect) {
      runPlanSelect.innerHTML = planOptions || `<option value="">No plans found</option>`;
    }
  }
  async function loadManagePlans(force = false) {
    var _a, _b, _c;
    const projectVal = ((_a = document.getElementById("runProject")) == null ? void 0 : _a.value) || ((_b = document.getElementById("caseProject")) == null ? void 0 : _b.value) || ((_c = document.getElementById("project")) == null ? void 0 : _c.value) || "1";
    const refreshBtn = document.getElementById("refreshManagePlansBtn");
    if (force) {
      cachedPlanOptionsHtml = "";
    }
    if (refreshBtn) {
      refreshBtn.disabled = true;
      refreshBtn.textContent = "Refreshing\u2026";
    }
    if (cachedPlanOptionsHtml) {
      setManagePlanOptions(cachedPlanOptionsHtml);
    }
    try {
      const data = await requestJson(`/api/plans?project=${encodeURIComponent(projectVal)}&is_completed=0`);
      const plans = Array.isArray(data.plans) ? data.plans : [];
      plans.sort((a, b) => (b.created_on || 0) - (a.created_on || 0) || String(a.name || "").localeCompare(String(b.name || "")));
      const planOptions = plans.map((p) => `<option value="${p.id}">${escapeHtml(p.name || "Plan " + p.id)} (ID ${p.id})</option>`).join("");
      cachedPlanOptionsHtml = planOptions;
      setManagePlanOptions(planOptions);
    } catch (err) {
      showToast("Failed to load plans for management forms.", "error");
      if (!cachedPlanOptionsHtml) {
        setManagePlanOptions("");
      }
    } finally {
      if (refreshBtn) {
        refreshBtn.disabled = false;
        refreshBtn.textContent = "Refresh plans";
      }
    }
  }
  function ensurePlanSelected() {
    const planSel = document.getElementById("plan");
    if (!(planSel == null ? void 0 : planSel.value)) {
      alert("Please select a Test Plan");
      return false;
    }
    return true;
  }
  function ensureRunSelection() {
    const runsSection = document.getElementById("runs-section");
    if (!runsSection || runsSection.dataset.available !== "1") {
      return true;
    }
    const checked = document.querySelectorAll('#run-list input[name="run_ids"]:checked').length;
    if (checked === 0) {
      alert("Please select at least one Test Run.");
      return false;
    }
    return true;
  }
  function setRunSelections(state) {
    document.querySelectorAll('#run-list input[name="run_ids"]').forEach((cb) => {
      cb.checked = state;
    });
    updateRunSummary();
  }

  // src/casePicker.ts
  var selectedCases = /* @__PURE__ */ new Set();
  var cachedCases = [];
  var getSelectedCases = () => selectedCases;
  var resetSelectedCases = () => {
    selectedCases = /* @__PURE__ */ new Set();
  };
  function updateCasePickerStatus() {
    const status = document.getElementById("casePickerStatus");
    if (!status) return;
    const count = selectedCases.size;
    status.textContent = count ? `${count} case${count === 1 ? "" : "s"} selected` : "No cases selected.";
  }
  function updateCaseCount(count) {
    const label = document.getElementById("caseCountLabel");
    if (!label) return;
    if (typeof count === "number" && count >= 0) {
      label.textContent = `${count} case${count === 1 ? "" : "s"} loaded`;
    } else {
      label.textContent = "Cases";
    }
  }
  function syncCaseIdsInput() {
    const input = document.getElementById("runCaseIds");
    if (!input) return;
    const sorted = Array.from(selectedCases).sort((a, b) => a - b);
    input.value = sorted.join(", ");
    updateCasePickerStatus();
  }
  function applySelectionToList() {
    document.querySelectorAll('#caseList input[type="checkbox"]').forEach((cb) => {
      const id = parseInt(cb.value, 10);
      cb.checked = selectedCases.has(id);
    });
  }
  function renderCases(cases) {
    const list = document.getElementById("caseList");
    const empty = document.getElementById("caseEmpty");
    if (!list || !empty) return;
    if (!cases || cases.length === 0) {
      list.innerHTML = "";
      empty.textContent = "No cases found.";
      empty.style.display = "block";
      return;
    }
    list.innerHTML = cases.map((c) => {
      const id = c.id;
      const title = escapeHtml(c.title || `Case ${id}`);
      const refs = c.refs ? escapeHtml(String(c.refs)) : "";
      const searchTokens = `${id} ${c.title || ""} ${c.refs || ""}`.toLowerCase();
      const refsLabel = refs ? `<span class="case-card-meta">Refs: ${refs}</span>` : "";
      return `<label class="case-card" data-text="${escapeHtml(searchTokens)}">
          <input type="checkbox" value="${id}">
          <div>
            <div class="case-card-title">${title}</div>
            <div class="case-card-meta">Case ${id}${refs ? " \u2022 " + refsLabel : ""}</div>
          </div>
        </label>`;
    }).join("");
    empty.style.display = "none";
    applySelectionToList();
  }
  function filterCases() {
    const search = document.getElementById("caseSearch");
    const list = document.getElementById("caseList");
    const empty = document.getElementById("caseEmpty");
    if (!search || !list || !empty) return;
    const query = (search.value || "").trim().toLowerCase();
    let visible = 0;
    list.querySelectorAll(".case-card").forEach((card) => {
      var _a;
      const matches = !query || ((_a = card.dataset.text) == null ? void 0 : _a.includes(query));
      card.style.display = matches ? "" : "none";
      if (matches) visible += 1;
    });
    if (visible === 0) {
      empty.textContent = query ? "No cases match your search." : "No cases found.";
      empty.style.display = "block";
    } else {
      empty.style.display = "none";
    }
  }
  function loadCases(force = false) {
    var _a, _b;
    const projectVal = ((_a = document.getElementById("runProject")) == null ? void 0 : _a.value) || ((_b = document.getElementById("project")) == null ? void 0 : _b.value) || "1";
    const refreshBtn = document.getElementById("caseRefreshBtn");
    const empty = document.getElementById("caseEmpty");
    if (refreshBtn) {
      refreshBtn.disabled = true;
      refreshBtn.textContent = "Refreshing\u2026";
    }
    if (empty) {
      empty.textContent = "Loading cases\u2026";
      empty.style.display = "block";
    }
    const qs = new URLSearchParams({ project: projectVal });
    if (appConfig2.defaultSuiteId !== null && appConfig2.defaultSuiteId !== void 0) {
      qs.append("suite_id", String(appConfig2.defaultSuiteId));
    }
    if (appConfig2.defaultSectionId !== null && appConfig2.defaultSectionId !== void 0) {
      qs.append("section_id", String(appConfig2.defaultSectionId));
      const filterParam = JSON.stringify({
        mode: "1",
        filters: { "cases:section_id": { values: [String(appConfig2.defaultSectionId)] } }
      });
      qs.append("filters", filterParam);
    }
    return requestJson(`/api/cases?${qs.toString()}`).then((data) => {
      cachedCases = Array.isArray(data.cases) ? data.cases : [];
      cachedCases.sort((a, b) => {
        const ua = Number(a.updated_on) || 0;
        const ub = Number(b.updated_on) || 0;
        if (ub !== ua) return ub - ua;
        return (b.id || 0) - (a.id || 0);
      });
      updateCaseCount(cachedCases.length);
      renderCases(cachedCases);
      filterCases();
    }).catch((err) => {
      showToast((err == null ? void 0 : err.message) || "Failed to load cases.", "error");
      if (empty) {
        empty.textContent = "Failed to load cases.";
        empty.style.display = "block";
      }
      updateCaseCount(null);
    }).finally(() => {
      if (refreshBtn) {
        refreshBtn.disabled = false;
        refreshBtn.textContent = "Refresh";
      }
    });
  }
  function openCasePicker() {
    var _a;
    const modal = document.getElementById("casePickerModal");
    if (!modal) return;
    modal.classList.remove("hidden");
    const manual = parseIdList(((_a = document.getElementById("runCaseIds")) == null ? void 0 : _a.value) || "");
    manual.forEach((id) => selectedCases.add(id));
    updateCasePickerStatus();
    updateCaseCount(cachedCases.length || 0);
    loadCases().then(applySelectionToList);
  }
  function closeCasePicker() {
    const modal = document.getElementById("casePickerModal");
    if (!modal) return;
    modal.classList.add("hidden");
  }
  function handleCaseCheckboxChange(event) {
    const target = event.target;
    if (!target || target.type !== "checkbox") return;
    const id = parseInt(target.value, 10);
    if (!Number.isFinite(id)) return;
    if (target.checked) {
      selectedCases.add(id);
      const includeAll = document.getElementById("runIncludeAll");
      if (includeAll) {
        includeAll.checked = false;
      }
    } else {
      selectedCases.delete(id);
    }
    syncCaseIdsInput();
  }
  function selectVisibleCases(state) {
    document.querySelectorAll("#caseList .case-card").forEach((card) => {
      if (card.style.display === "none") return;
      const cb = card.querySelector('input[type="checkbox"]');
      if (!cb) return;
      cb.checked = state;
      const id = parseInt(cb.value, 10);
      if (state && Number.isFinite(id)) {
        selectedCases.add(id);
      } else if (Number.isFinite(id)) {
        selectedCases.delete(id);
      }
    });
    syncCaseIdsInput();
  }
  function clearCaseSelection() {
    selectedCases.clear();
    document.querySelectorAll('#caseList input[type="checkbox"]').forEach((cb) => cb.checked = false);
    syncCaseIdsInput();
  }

  // src/manage.ts
  var currentEditRunId = null;
  function getFocusableElements(container) {
    const focusableSelectors = [
      "a[href]",
      "button:not([disabled])",
      "textarea:not([disabled])",
      "input:not([disabled])",
      "select:not([disabled])",
      '[tabindex]:not([tabindex="-1"])'
    ].join(", ");
    return Array.from(container.querySelectorAll(focusableSelectors));
  }
  function setupFocusTrap(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return () => {
    };
    const handleTabKey = (e) => {
      if (e.key !== "Tab") return;
      const focusableElements = getFocusableElements(modal);
      if (focusableElements.length === 0) return;
      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];
      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault();
        lastElement.focus();
      } else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault();
        firstElement.focus();
      }
    };
    modal.addEventListener("keydown", handleTabKey);
    return () => {
      modal.removeEventListener("keydown", handleTabKey);
    };
  }
  var focusTrapCleanups = /* @__PURE__ */ new Map();
  var modalTriggerElements = /* @__PURE__ */ new Map();
  function activateFocusTrap(modalId) {
    deactivateFocusTrap(modalId);
    const cleanup = setupFocusTrap(modalId);
    focusTrapCleanups.set(modalId, cleanup);
  }
  function deactivateFocusTrap(modalId) {
    const cleanup = focusTrapCleanups.get(modalId);
    if (cleanup) {
      cleanup();
      focusTrapCleanups.delete(modalId);
    }
  }
  function storeTriggerElement(modalId, element) {
    modalTriggerElements.set(modalId, element);
  }
  function restoreFocus(modalId) {
    const triggerElement = modalTriggerElements.get(modalId);
    if (triggerElement && document.contains(triggerElement)) {
      setTimeout(() => {
        triggerElement.focus();
      }, 100);
    }
    modalTriggerElements.delete(modalId);
  }
  function navigateToBreadcrumbLevel(level, context) {
    switch (level) {
      case "plans":
        hideCaseEditModal();
        hideRunDetailsModal();
        hidePlanRunsModal();
        announceStatus("Navigated to plans list");
        break;
      case "runs":
        hideCaseEditModal();
        hideRunDetailsModal();
        if (context.planId && context.planName) {
          showPlanRunsModal(context.planId, context.planName, currentPlanEditButton || void 0);
          announceStatus(`Navigated to runs for ${context.planName}`);
        }
        break;
      case "cases":
        hideCaseEditModal();
        if (context.runId) {
          showRunDetailsModal(context.runId);
          announceStatus(`Navigated to cases for ${context.runName || "run"}`);
        }
        break;
    }
  }
  function announceStatus(message) {
    const announcer = document.getElementById("manageStatusAnnouncer");
    if (announcer) {
      announcer.textContent = message;
      setTimeout(() => {
        announcer.textContent = "";
      }, 1e3);
    }
  }
  function setSubsectionBusy(subsection, busy) {
    const subsectionName = subsection.charAt(0).toUpperCase() + subsection.slice(1);
    const content = document.querySelector(`#manage${subsectionName}Subsection .subsection-content`);
    if (content) {
      content.setAttribute("aria-busy", busy ? "true" : "false");
    }
  }
  var deleteConfirmCallback = null;
  var deleteConfirmRequireTyping = false;
  var deleteConfirmExpectedName = "";
  function showDeleteConfirmation(entityType, entityName, entityId, onConfirm, options) {
    const modal = document.getElementById("deleteConfirmModal");
    const nameEl = document.getElementById("deleteConfirmEntityName");
    const typeEl = document.getElementById("deleteConfirmEntityType");
    const cascadeWarningEl = document.getElementById("deleteConfirmCascadeWarning");
    const cascadeMessageEl = document.getElementById("deleteConfirmCascadeMessage");
    const typeSectionEl = document.getElementById("deleteConfirmTypeSection");
    const typeNameEl = document.getElementById("deleteConfirmTypeName");
    const typeInputEl = document.getElementById("deleteConfirmTypeInput");
    const typeErrorEl = document.getElementById("deleteConfirmTypeError");
    const deleteBtn = document.getElementById("deleteConfirmDelete");
    if (!modal || !nameEl || !typeEl) return;
    nameEl.textContent = entityName;
    const entityTypeCapitalized = entityType.charAt(0).toUpperCase() + entityType.slice(1);
    typeEl.textContent = `${entityTypeCapitalized} ID: ${entityId}`;
    if (cascadeWarningEl && cascadeMessageEl) {
      if (options == null ? void 0 : options.cascadeWarning) {
        cascadeWarningEl.classList.remove("hidden");
        cascadeMessageEl.textContent = options.cascadeWarning;
      } else {
        cascadeWarningEl.classList.add("hidden");
      }
    }
    deleteConfirmRequireTyping = (options == null ? void 0 : options.requireTyping) || false;
    deleteConfirmExpectedName = entityName;
    if (typeSectionEl && typeNameEl && typeInputEl && typeErrorEl) {
      if (deleteConfirmRequireTyping) {
        typeSectionEl.classList.remove("hidden");
        typeNameEl.textContent = entityName;
        typeInputEl.value = "";
        typeErrorEl.classList.add("hidden");
        if (deleteBtn) {
          deleteBtn.disabled = true;
          deleteBtn.style.opacity = "0.5";
          deleteBtn.style.cursor = "not-allowed";
        }
      } else {
        typeSectionEl.classList.add("hidden");
        if (deleteBtn) {
          deleteBtn.disabled = false;
          deleteBtn.style.opacity = "1";
          deleteBtn.style.cursor = "pointer";
        }
      }
    }
    deleteConfirmCallback = onConfirm;
    const activeElement = document.activeElement;
    storeTriggerElement("deleteConfirmModal", activeElement);
    modal.classList.remove("hidden");
    modal.style.zIndex = "13000";
    activateFocusTrap("deleteConfirmModal");
    setTimeout(() => {
      if (deleteConfirmRequireTyping && typeInputEl) {
        typeInputEl.focus();
      } else {
        const cancelBtn = document.getElementById("deleteConfirmCancel");
        if (cancelBtn) cancelBtn.focus();
      }
    }, 100);
  }
  function hideDeleteConfirmation() {
    const modal = document.getElementById("deleteConfirmModal");
    const typeInputEl = document.getElementById("deleteConfirmTypeInput");
    const typeErrorEl = document.getElementById("deleteConfirmTypeError");
    if (!modal) return;
    modal.classList.add("hidden");
    modal.style.zIndex = "";
    deactivateFocusTrap("deleteConfirmModal");
    restoreFocus("deleteConfirmModal");
    deleteConfirmCallback = null;
    deleteConfirmRequireTyping = false;
    deleteConfirmExpectedName = "";
    if (typeInputEl) {
      typeInputEl.value = "";
    }
    if (typeErrorEl) {
      typeErrorEl.classList.add("hidden");
    }
  }
  function executeDeleteConfirmation() {
    if (deleteConfirmRequireTyping) {
      const typeInputEl = document.getElementById("deleteConfirmTypeInput");
      const typeErrorEl = document.getElementById("deleteConfirmTypeError");
      if (typeInputEl && typeErrorEl) {
        const typedValue = typeInputEl.value.trim();
        if (typedValue !== deleteConfirmExpectedName) {
          typeErrorEl.classList.remove("hidden");
          typeInputEl.style.borderColor = "#ef4444";
          typeInputEl.focus();
          return;
        }
      }
    }
    if (deleteConfirmCallback) {
      deleteConfirmCallback();
    }
    hideDeleteConfirmation();
  }
  function hideRunEditModal() {
    const modal = document.getElementById("runEditModal");
    const nameInput = document.getElementById("runEditName");
    const descInput = document.getElementById("runEditDescription");
    const refsInput = document.getElementById("runEditRefs");
    const nameError = document.getElementById("runEditNameError");
    const loadingOverlay = document.getElementById("runEditLoadingOverlay");
    if (!modal) return;
    modal.classList.add("hidden");
    deactivateFocusTrap("runEditModal");
    restoreFocus("runEditModal");
    currentEditRunId = null;
    if (nameInput) nameInput.value = "";
    if (descInput) descInput.value = "";
    if (refsInput) refsInput.value = "";
    if (nameError) {
      nameError.classList.add("hidden");
    }
    if (nameInput) {
      nameInput.style.borderColor = "var(--border)";
    }
    if (loadingOverlay) {
      loadingOverlay.classList.add("hidden");
    }
  }
  function validateRunName(name) {
    return name.trim().length > 0;
  }
  function showRunNameValidationError() {
    const nameInput = document.getElementById("runEditName");
    const nameError = document.getElementById("runEditNameError");
    if (nameInput) {
      nameInput.style.borderColor = "#ef4444";
    }
    if (nameError) {
      nameError.classList.remove("hidden");
    }
  }
  function clearRunNameValidationError() {
    const nameInput = document.getElementById("runEditName");
    const nameError = document.getElementById("runEditNameError");
    if (nameInput) {
      nameInput.style.borderColor = "var(--border)";
    }
    if (nameError) {
      nameError.classList.add("hidden");
    }
  }
  async function saveRunEdit() {
    const nameInput = document.getElementById("runEditName");
    const descInput = document.getElementById("runEditDescription");
    const refsInput = document.getElementById("runEditRefs");
    const loadingOverlay = document.getElementById("runEditLoadingOverlay");
    const saveBtn = document.getElementById("runEditSave");
    if (!nameInput || !descInput || !refsInput || currentEditRunId === null) {
      console.error("Run edit form elements not found or no run selected");
      return;
    }
    const name = nameInput.value;
    const description = descInput.value;
    const refs = refsInput.value;
    if (!validateRunName(name)) {
      showRunNameValidationError();
      nameInput.focus();
      return;
    }
    clearRunNameValidationError();
    if (loadingOverlay) {
      loadingOverlay.classList.remove("hidden");
    }
    if (saveBtn) {
      saveBtn.disabled = true;
    }
    try {
      const response = await requestJson(`/api/manage/run/${currentEditRunId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          name: name.trim(),
          description: description || null,
          refs: refs || null
        })
      });
      if (response.success) {
        showToast(`Run "${name.trim()}" updated successfully`, "success");
        hideRunEditModal();
      } else {
        throw new Error(response.message || "Failed to update run");
      }
    } catch (err) {
      showToast((err == null ? void 0 : err.message) || "Failed to update run", "error");
    } finally {
      if (loadingOverlay) {
        loadingOverlay.classList.add("hidden");
      }
      if (saveBtn) {
        saveBtn.disabled = false;
      }
    }
  }
  async function deletePlan(planId, planName) {
    try {
      const response = await requestJson(`/api/manage/plan/${planId}`, {
        method: "DELETE"
      });
      if (response.success) {
        showToast(`Plan "${planName}" deleted successfully`, "success");
        refreshPlanList();
        return true;
      } else {
        throw new Error(response.message || "Failed to delete plan");
      }
    } catch (err) {
      showToast((err == null ? void 0 : err.message) || "Failed to delete plan", "error");
      return false;
    }
  }
  async function deleteRun(runId, runName) {
    try {
      const response = await requestJson(`/api/manage/run/${runId}`, {
        method: "DELETE"
      });
      if (response.success) {
        showToast(`Run "${runName}" deleted successfully`, "success");
        return true;
      } else {
        throw new Error(response.message || "Failed to delete run");
      }
    } catch (err) {
      showToast((err == null ? void 0 : err.message) || "Failed to delete run", "error");
      return false;
    }
  }
  function disableEntityButtons(entityType) {
    const editButtons = document.querySelectorAll(`.edit-${entityType}-btn`);
    const deleteButtons = document.querySelectorAll(`.delete-${entityType}-btn`);
    editButtons.forEach((btn) => btn.disabled = true);
    deleteButtons.forEach((btn) => btn.disabled = true);
  }
  function showErrorState(subsection, errorMessage, retryCallback) {
    const container = document.getElementById(`${subsection}ListContainer`);
    const loadingState = document.getElementById(`${subsection}LoadingState`);
    const emptyState = document.getElementById(`${subsection}EmptyState`);
    if (!container || !loadingState || !emptyState) return;
    loadingState.classList.add("hidden");
    emptyState.classList.add("hidden");
    container.classList.remove("hidden");
    container.innerHTML = `
    <div class="error-state" role="alert" aria-live="assertive" style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 40px 20px; text-align: center;">
      <div style="font-size: 48px; margin-bottom: 12px; opacity: 0.5; line-height: 1;" aria-hidden="true">\u26A0\uFE0F</div>
      <h4 style="margin: 0 0 8px; font-size: 16px; font-weight: 500; color: var(--text);">Failed to load ${subsection}</h4>
      <p style="margin: 0 0 16px; font-size: 14px; color: var(--muted); max-width: 400px;">${escapeHtml(errorMessage)}</p>
      <button type="button" class="refresh-btn" style="padding: 8px 16px; font-size: 13px;" aria-label="Retry loading ${subsection}">
        <span class="icon" aria-hidden="true">\u{1F504}</span> Retry
      </button>
    </div>
  `;
    const retryBtn = container.querySelector(".refresh-btn");
    if (retryBtn) {
      retryBtn.addEventListener("click", retryCallback);
    }
  }
  async function refreshPlanList() {
    const container = document.getElementById("plansListContainer");
    const scrollPosition = (container == null ? void 0 : container.scrollTop) || 0;
    await loadManagePlans2();
    if (container) {
      requestAnimationFrame(() => {
        container.scrollTop = scrollPosition;
      });
    }
  }
  var currentPlanId = null;
  var currentPlanName = "";
  var currentPlanEditButton = null;
  var savedPlansScrollPosition = 0;
  async function showPlanRunsModal(planId, planName, triggerElement) {
    const plansListContainer = document.getElementById("plansListContainer");
    if (plansListContainer) {
      savedPlansScrollPosition = plansListContainer.scrollTop;
    }
    currentPlanId = planId;
    currentPlanName = planName;
    currentPlanEditButton = triggerElement || null;
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
    if (planNameDisplay) {
      planNameDisplay.textContent = planName;
    }
    if (breadcrumbPlanName) {
      breadcrumbPlanName.textContent = planName;
    }
    modal.classList.remove("hidden");
    activateFocusTrap("planRunsModal");
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
    announceStatus(`Loading runs for ${planName}...`);
    try {
      const data = await requestJson(`/api/runs?plan=${planId}&project=1`);
      const runs = Array.isArray(data.runs) ? data.runs : [];
      if (loadingOverlay) {
        loadingOverlay.classList.add("hidden");
      }
      if (loadingState) {
        loadingState.classList.add("hidden");
      }
      if (runs.length === 0) {
        if (emptyState) {
          emptyState.classList.remove("hidden");
        }
        announceStatus("No runs found");
      } else {
        renderPlanRunsList(runs);
        announceStatus(`Loaded ${runs.length} run${runs.length !== 1 ? "s" : ""}`);
      }
    } catch (err) {
      if (loadingOverlay) {
        loadingOverlay.classList.add("hidden");
      }
      if (loadingState) {
        loadingState.classList.add("hidden");
      }
      if (errorState) {
        errorState.classList.remove("hidden");
        const errorMessage = document.getElementById("planRunsErrorMessage");
        if (errorMessage) {
          errorMessage.textContent = (err == null ? void 0 : err.message) || "An error occurred while loading runs.";
        }
      }
      showToast((err == null ? void 0 : err.message) || "Failed to load runs", "error");
      announceStatus("Failed to load runs");
    }
  }
  function renderPlanRunsList(runs) {
    const runsList = document.getElementById("planRunsList");
    const emptyState = document.getElementById("planRunsEmptyState");
    const errorState = document.getElementById("planRunsErrorState");
    if (!runsList) return;
    if (emptyState) emptyState.classList.add("hidden");
    if (errorState) errorState.classList.add("hidden");
    runsList.innerHTML = runs.map((run) => {
      const runName = escapeHtml(run.name || `Run ${run.id}`);
      const runId = run.id;
      const isCompleted = run.is_completed === true || run.is_completed === 1;
      const badgeClass = isCompleted ? "badge-completed" : "badge-active";
      const badgeText = isCompleted ? "Completed" : "Active";
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
              <span class="icon" aria-hidden="true">\u{1F194}</span> Run ID: ${runId}
            </span>
            ${suiteName ? `<span class="meta-item"><span class="icon" aria-hidden="true">\u{1F4E6}</span> Suite: ${suiteName}</span>` : ""}
          </div>
          <div class="entity-card-actions" role="group" aria-label="Actions for ${runName}">
            <button type="button" class="btn-edit edit-run-btn-modal" data-run-id="${runId}" data-run-name="${escapeHtml(run.name || "")}" aria-label="Edit run ${runName}" aria-describedby="run-title-${runId}">
              <span class="icon" aria-hidden="true">\u270F\uFE0F</span> Edit
            </button>
            <button type="button" class="btn-delete delete-run-btn-modal" data-run-id="${runId}" data-run-name="${escapeHtml(run.name || "")}" aria-label="Delete run ${runName}" aria-describedby="run-title-${runId}">
              <span class="icon" aria-hidden="true">\u{1F5D1}\uFE0F</span> Delete
            </button>
          </div>
        </div>
      `;
    }).join("");
    runsList.classList.remove("hidden");
    attachPlanRunsModalEventListeners();
  }
  function attachPlanRunsModalEventListeners() {
    document.querySelectorAll(".edit-run-btn-modal").forEach((btn) => {
      const handleEdit = (e) => {
        e.stopPropagation();
        const target = e.currentTarget;
        const runId = parseInt(target.dataset.runId || "0", 10);
        showRunDetailsModal(runId);
      };
      btn.addEventListener("click", handleEdit);
      btn.addEventListener("keydown", (e) => {
        const keyEvent = e;
        if (keyEvent.key === "Enter") {
          keyEvent.preventDefault();
          handleEdit(keyEvent);
        }
      });
    });
    document.querySelectorAll(".delete-run-btn-modal").forEach((btn) => {
      const handleDelete = (e) => {
        e.stopPropagation();
        const target = e.currentTarget;
        const runId = parseInt(target.dataset.runId || "0", 10);
        const runName = target.dataset.runName || `Run ${runId}`;
        showDeleteConfirmation("run", runName, runId, async () => {
          const success = await deleteRun(runId, runName);
          if (success && currentPlanId !== null) {
            showPlanRunsModal(currentPlanId, currentPlanName, currentPlanEditButton || void 0);
          }
        });
      };
      btn.addEventListener("click", handleDelete);
      btn.addEventListener("keydown", (e) => {
        const keyEvent = e;
        if (keyEvent.key === "Enter") {
          keyEvent.preventDefault();
          handleDelete(keyEvent);
        }
      });
    });
  }
  function hidePlanRunsModal() {
    const modal = document.getElementById("planRunsModal");
    if (!modal) return;
    modal.classList.add("hidden");
    deactivateFocusTrap("planRunsModal");
    restoreFocus("planRunsModal");
    const plansListContainer = document.getElementById("plansListContainer");
    if (plansListContainer) {
      requestAnimationFrame(() => {
        plansListContainer.scrollTop = savedPlansScrollPosition;
      });
    }
    currentPlanId = null;
    currentPlanName = "";
    currentPlanEditButton = null;
    announceStatus("Returned to plans list");
  }
  var currentRunId = null;
  var currentRunName = "";
  var currentRunIsDirty = false;
  async function showRunDetailsModal(runId) {
    currentRunId = runId;
    currentRunIsDirty = false;
    const activeElement = document.activeElement;
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
    modal.classList.remove("hidden");
    activateFocusTrap("runDetailsModal");
    if (loadingOverlay) {
      loadingOverlay.classList.remove("hidden");
    }
    if (formContainer) {
      formContainer.classList.add("hidden");
    }
    if (casesContainer) {
      casesContainer.classList.add("hidden");
    }
    if (breadcrumbPlanName) {
      breadcrumbPlanName.textContent = currentPlanName;
    }
    announceStatus("Loading run details...");
    try {
      const runData = await requestJson(`/api/run/${runId}`);
      const run = runData.run;
      if (!run) {
        throw new Error("Run not found");
      }
      currentRunName = run.name || `Run ${runId}`;
      if (runNameDisplay) {
        runNameDisplay.textContent = currentRunName;
      }
      if (breadcrumbRunName) {
        breadcrumbRunName.textContent = currentRunName;
      }
      const nameInput = document.getElementById("runDetailsName");
      const descInput = document.getElementById("runDetailsDescription");
      const refsInput = document.getElementById("runDetailsRefs");
      if (nameInput) {
        nameInput.value = run.name || "";
      }
      if (descInput) {
        descInput.value = run.description || "";
      }
      if (refsInput) {
        refsInput.value = run.refs || "";
      }
      if (formContainer) {
        formContainer.classList.remove("hidden");
      }
      await loadRunDetailsCases(runId);
      if (loadingOverlay) {
        loadingOverlay.classList.add("hidden");
      }
      if (casesContainer) {
        casesContainer.classList.remove("hidden");
      }
      announceStatus(`Loaded run details for ${currentRunName}`);
    } catch (err) {
      if (loadingOverlay) {
        loadingOverlay.classList.add("hidden");
      }
      showToast((err == null ? void 0 : err.message) || "Failed to load run details", "error");
      announceStatus("Failed to load run details");
      hideRunDetailsModal();
    }
  }
  async function loadRunDetailsCases(runId) {
    const loadingState = document.getElementById("runDetailsCasesLoadingState");
    const errorState = document.getElementById("runDetailsCasesErrorState");
    const emptyState = document.getElementById("runDetailsCasesEmptyState");
    const casesList = document.getElementById("runDetailsCasesList");
    if (!loadingState || !errorState || !emptyState || !casesList) return;
    loadingState.classList.remove("hidden");
    errorState.classList.add("hidden");
    emptyState.classList.add("hidden");
    casesList.classList.add("hidden");
    try {
      const data = await requestJson(`/api/tests/${runId}`);
      const tests = Array.isArray(data.tests) ? data.tests : [];
      loadingState.classList.add("hidden");
      if (tests.length === 0) {
        emptyState.classList.remove("hidden");
      } else {
        renderRunDetailsCases(tests);
      }
    } catch (err) {
      loadingState.classList.add("hidden");
      errorState.classList.remove("hidden");
      const errorMessage = document.getElementById("runDetailsCasesErrorMessage");
      if (errorMessage) {
        errorMessage.textContent = (err == null ? void 0 : err.message) || "An error occurred while loading test cases.";
      }
      showToast((err == null ? void 0 : err.message) || "Failed to load test cases", "error");
    }
  }
  var selectedCaseIds = /* @__PURE__ */ new Set();
  var selectedAddCaseIds = /* @__PURE__ */ new Set();
  var availableCasesData = [];
  var currentTestId = null;
  var currentTestTitle = "";
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
  function toggleCaseSelection(caseId, checked) {
    if (checked) {
      selectedCaseIds.add(caseId);
    } else {
      selectedCaseIds.delete(caseId);
    }
    updateBulkActionToolbar();
  }
  function selectAllCases() {
    const checkboxes = document.querySelectorAll(".case-checkbox");
    checkboxes.forEach((checkbox) => {
      checkbox.checked = true;
      const caseId = parseInt(checkbox.dataset.caseId || "0", 10);
      if (caseId > 0) {
        selectedCaseIds.add(caseId);
      }
    });
    updateBulkActionToolbar();
  }
  function deselectAllCases() {
    const checkboxes = document.querySelectorAll(".case-checkbox");
    checkboxes.forEach((checkbox) => {
      checkbox.checked = false;
    });
    selectedCaseIds.clear();
    updateBulkActionToolbar();
  }
  function showAddTestResultModal(testId, testTitle) {
    const modal = document.getElementById("addTestResultModal");
    const titleEl = document.getElementById("addResultTestTitle");
    const statusSelect = document.getElementById("resultStatus");
    const commentInput = document.getElementById("resultComment");
    const elapsedInput = document.getElementById("resultElapsed");
    const defectsInput = document.getElementById("resultDefects");
    const versionInput = document.getElementById("resultVersion");
    const attachmentsInput = document.getElementById("resultAttachments");
    if (!modal) return;
    currentTestId = testId;
    currentTestTitle = testTitle;
    if (titleEl) {
      titleEl.textContent = testTitle;
    }
    if (statusSelect) statusSelect.value = "";
    if (commentInput) commentInput.value = "";
    if (elapsedInput) elapsedInput.value = "";
    if (defectsInput) defectsInput.value = "";
    if (versionInput) versionInput.value = "";
    if (attachmentsInput) attachmentsInput.value = "";
    modal.classList.remove("hidden");
    activateFocusTrap("addTestResultModal");
    setTimeout(() => {
      if (statusSelect) statusSelect.focus();
    }, 100);
  }
  function hideAddTestResultModal() {
    const modal = document.getElementById("addTestResultModal");
    if (!modal) return;
    modal.classList.add("hidden");
    deactivateFocusTrap("addTestResultModal");
    currentTestId = null;
    currentTestTitle = "";
  }
  async function submitTestResult() {
    if (currentTestId === null) return;
    const statusSelect = document.getElementById("resultStatus");
    const commentInput = document.getElementById("resultComment");
    const elapsedInput = document.getElementById("resultElapsed");
    const defectsInput = document.getElementById("resultDefects");
    const versionInput = document.getElementById("resultVersion");
    const attachmentsInput = document.getElementById("resultAttachments");
    const loadingOverlay = document.getElementById("addResultLoadingOverlay");
    const submitBtn = document.getElementById("addResultSubmitBtn");
    if (!statusSelect || !statusSelect.value) {
      showToast("Please select a status", "error");
      if (statusSelect) statusSelect.focus();
      return;
    }
    const statusId = parseInt(statusSelect.value, 10);
    if (loadingOverlay) loadingOverlay.classList.remove("hidden");
    if (submitBtn) submitBtn.disabled = true;
    try {
      const resultPayload = {
        status_id: statusId
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
          "Content-Type": "application/json"
        },
        body: JSON.stringify(resultPayload)
      });
      if (!resultResponse.success) {
        throw new Error(resultResponse.message || "Failed to add result");
      }
      const resultId = resultResponse.result.id;
      if (attachmentsInput && attachmentsInput.files && attachmentsInput.files.length > 0) {
        const files = Array.from(attachmentsInput.files);
        let uploadedCount = 0;
        for (const file of files) {
          try {
            const formData = new FormData();
            formData.append("file", file);
            const attachResponse = await fetch(`/api/manage/result/${resultId}/attachment`, {
              method: "POST",
              body: formData
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
      hideAddTestResultModal();
      if (currentRunId !== null) {
        await loadRunDetailsCases(currentRunId);
      }
    } catch (err) {
      showToast((err == null ? void 0 : err.message) || "Failed to add test result", "error");
    } finally {
      if (loadingOverlay) loadingOverlay.classList.add("hidden");
      if (submitBtn) submitBtn.disabled = false;
    }
  }
  async function showAddCasesToRunModal() {
    if (currentRunId === null) return;
    const modal = document.getElementById("addCasesToRunModal");
    const loadingOverlay = document.getElementById("addCasesLoadingOverlay");
    const loadingState = document.getElementById("addCasesLoadingState");
    const errorState = document.getElementById("addCasesErrorState");
    const emptyState = document.getElementById("addCasesEmptyState");
    const casesList = document.getElementById("addCasesList");
    if (!modal) return;
    selectedAddCaseIds.clear();
    availableCasesData = [];
    updateAddCasesCount();
    modal.classList.remove("hidden");
    activateFocusTrap("addCasesToRunModal");
    if (loadingOverlay) loadingOverlay.classList.remove("hidden");
    if (loadingState) loadingState.classList.remove("hidden");
    if (errorState) errorState.classList.add("hidden");
    if (emptyState) emptyState.classList.add("hidden");
    if (casesList) casesList.classList.add("hidden");
    try {
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
    } catch (err) {
      if (loadingOverlay) loadingOverlay.classList.add("hidden");
      if (loadingState) loadingState.classList.add("hidden");
      if (errorState) {
        errorState.classList.remove("hidden");
        const errorMessage = document.getElementById("addCasesErrorMessage");
        if (errorMessage) {
          errorMessage.textContent = (err == null ? void 0 : err.message) || "Failed to load available cases";
        }
      }
      showToast((err == null ? void 0 : err.message) || "Failed to load available cases", "error");
    }
  }
  function hideAddCasesToRunModal() {
    const modal = document.getElementById("addCasesToRunModal");
    if (!modal) return;
    modal.classList.add("hidden");
    deactivateFocusTrap("addCasesToRunModal");
    selectedAddCaseIds.clear();
    availableCasesData = [];
    const searchInput = document.getElementById("addCasesSearch");
    if (searchInput) searchInput.value = "";
  }
  function renderAvailableCases(cases) {
    const casesList = document.getElementById("addCasesList");
    if (!casesList) return;
    casesList.innerHTML = cases.map((testCase) => {
      const caseId = testCase.id;
      const title = escapeHtml(testCase.title || `Case ${caseId}`);
      const refs = testCase.refs ? escapeHtml(String(testCase.refs)) : "";
      const sectionName = testCase.section_name ? escapeHtml(String(testCase.section_name)) : "";
      return `
        <div class="add-case-item" data-case-id="${caseId}" data-case-title="${escapeHtml(testCase.title || "")}" style="padding: 12px 16px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 12px; cursor: pointer; transition: background 0.15s ease;">
          <input 
            type="checkbox" 
            class="add-case-checkbox" 
            data-case-id="${caseId}"
            style="width: 18px; height: 18px; cursor: pointer; flex-shrink: 0;"
          />
          <div style="flex: 1; min-width: 0;">
            <div style="font-weight: 600; font-size: 14px; color: var(--text); margin-bottom: 4px;">${title}</div>
            <div style="font-size: 13px; color: var(--muted); display: flex; gap: 12px; flex-wrap: wrap;">
              <span><span class="icon" aria-hidden="true">\u{1F194}</span> C${caseId}</span>
              ${refs ? `<span><span class="icon" aria-hidden="true">\u{1F517}</span> ${refs}</span>` : ""}
              ${sectionName ? `<span><span class="icon" aria-hidden="true">\u{1F4C1}</span> ${sectionName}</span>` : ""}
            </div>
          </div>
        </div>
      `;
    }).join("");
    casesList.classList.remove("hidden");
    const checkboxes = casesList.querySelectorAll(".add-case-checkbox");
    checkboxes.forEach((checkbox) => {
      checkbox.addEventListener("change", (e) => {
        const target = e.target;
        const caseId = parseInt(target.dataset.caseId || "0", 10);
        toggleAddCaseSelection(caseId, target.checked);
      });
    });
    const items = casesList.querySelectorAll(".add-case-item");
    items.forEach((item) => {
      item.addEventListener("click", (e) => {
        if (e.target.classList.contains("add-case-checkbox")) return;
        const checkbox = item.querySelector(".add-case-checkbox");
        if (checkbox) {
          checkbox.checked = !checkbox.checked;
          const caseId = parseInt(checkbox.dataset.caseId || "0", 10);
          toggleAddCaseSelection(caseId, checkbox.checked);
        }
      });
    });
  }
  function toggleAddCaseSelection(caseId, checked) {
    if (checked) {
      selectedAddCaseIds.add(caseId);
    } else {
      selectedAddCaseIds.delete(caseId);
    }
    updateAddCasesCount();
  }
  function updateAddCasesCount() {
    const countEl = document.getElementById("addCasesSelectedCount");
    const confirmBtn = document.getElementById("addCasesConfirmBtn");
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
  function selectAllAddCases() {
    const checkboxes = document.querySelectorAll(".add-case-checkbox");
    checkboxes.forEach((checkbox) => {
      checkbox.checked = true;
      const caseId = parseInt(checkbox.dataset.caseId || "0", 10);
      if (caseId > 0) {
        selectedAddCaseIds.add(caseId);
      }
    });
    updateAddCasesCount();
  }
  function deselectAllAddCases() {
    const checkboxes = document.querySelectorAll(".add-case-checkbox");
    checkboxes.forEach((checkbox) => {
      checkbox.checked = false;
    });
    selectedAddCaseIds.clear();
    updateAddCasesCount();
  }
  function filterAvailableCases(searchTerm) {
    const term = searchTerm.toLowerCase().trim();
    if (!term) {
      renderAvailableCases(availableCasesData);
      return;
    }
    const filtered = availableCasesData.filter((testCase) => {
      const title = (testCase.title || "").toLowerCase();
      const id = String(testCase.id);
      const refs = (testCase.refs || "").toLowerCase();
      return title.includes(term) || id.includes(term) || refs.includes(term);
    });
    renderAvailableCases(filtered);
  }
  async function addSelectedCasesToRun() {
    if (selectedAddCaseIds.size === 0 || currentRunId === null) return;
    const count = selectedAddCaseIds.size;
    const caseIdsArray = Array.from(selectedAddCaseIds);
    const confirmBtn = document.getElementById("addCasesConfirmBtn");
    try {
      if (confirmBtn) confirmBtn.disabled = true;
      const response = await requestJson(`/api/manage/run/${currentRunId}/add_cases`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          case_ids: caseIdsArray
        })
      });
      if (response.success) {
        const message = response.skipped_count > 0 ? `Added ${response.added_count} case(s) (${response.skipped_count} already in run)` : `Added ${response.added_count} case(s) to run`;
        showToast(message, "success");
        hideAddCasesToRunModal();
        await loadRunDetailsCases(currentRunId);
      } else {
        throw new Error(response.message || "Failed to add cases to run");
      }
    } catch (err) {
      const errorMessage = (err == null ? void 0 : err.message) || "Failed to add cases to run";
      if (errorMessage.includes("403") || errorMessage.includes("test results")) {
        showToast("\u26A0\uFE0F Cannot modify this run - it has test results. TestRail doesn't allow adding cases to runs with results.", "error");
      } else {
        showToast(errorMessage, "error");
      }
    } finally {
      if (confirmBtn) confirmBtn.disabled = false;
    }
  }
  async function removeSelectedCasesFromRun() {
    if (selectedCaseIds.size === 0 || currentRunId === null) return;
    const count = selectedCaseIds.size;
    const caseIdsArray = Array.from(selectedCaseIds);
    const confirmed = confirm(`Remove ${count} test case${count > 1 ? "s" : ""} from this run?

Note: This will only remove them from the run, not delete them from the project.`);
    if (!confirmed) return;
    try {
      const toolbar = document.getElementById("runDetailsBulkToolbar");
      const removeBtn = document.getElementById("runDetailsBulkRemove");
      if (removeBtn) removeBtn.disabled = true;
      const response = await requestJson(`/api/manage/run/${currentRunId}/remove_cases`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          case_ids: caseIdsArray
        })
      });
      if (response.success) {
        showToast(`Removed ${response.removed_count} case(s) from run`, "success");
        selectedCaseIds.clear();
        updateBulkActionToolbar();
        await loadRunDetailsCases(currentRunId);
      } else {
        throw new Error(response.message || "Failed to remove cases from run");
      }
    } catch (err) {
      const errorMessage = (err == null ? void 0 : err.message) || "Failed to remove cases from run";
      if (errorMessage.includes("403") || errorMessage.includes("test results")) {
        showToast("\u26A0\uFE0F Cannot modify this run - it has test results. TestRail doesn't allow removing cases from runs with results.", "error");
      } else {
        showToast(errorMessage, "error");
      }
    } finally {
      const removeBtn = document.getElementById("runDetailsBulkRemove");
      if (removeBtn) removeBtn.disabled = false;
    }
  }
  function renderRunDetailsCases(tests) {
    const casesList = document.getElementById("runDetailsCasesList");
    const emptyState = document.getElementById("runDetailsCasesEmptyState");
    const errorState = document.getElementById("runDetailsCasesErrorState");
    if (!casesList) return;
    if (emptyState) emptyState.classList.add("hidden");
    if (errorState) errorState.classList.add("hidden");
    selectedCaseIds.clear();
    updateBulkActionToolbar();
    casesList.innerHTML = tests.map((test) => {
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
              <span class="icon" aria-hidden="true">\u{1F194}</span> Test ID: ${testId}
            </span>
            <span class="meta-item">
              <span class="icon" aria-hidden="true">\u{1F4CB}</span> Case ID: ${caseId}
            </span>
            ${refs ? `<span class="meta-item"><span class="icon" aria-hidden="true">\u{1F517}</span> Refs: ${refs}</span>` : ""}
          </div>
          <div class="entity-card-actions" role="group" aria-label="Actions for ${testTitle}">
            <button type="button" class="btn-edit add-result-btn-modal" data-test-id="${testId}" data-test-title="${escapeHtml(test.title || "")}" aria-label="Add result for ${testTitle}" aria-describedby="test-title-${testId}" style="background: var(--primary); color: white; border-color: var(--primary);">
              <span class="icon" aria-hidden="true">\u2705</span> Add Result
            </button>
            <button type="button" class="btn-edit edit-case-btn-modal" data-case-id="${caseId}" data-case-title="${escapeHtml(test.title || "")}" data-case-refs="${escapeHtml(test.refs || "")}" aria-label="Edit case ${testTitle}" aria-describedby="test-title-${testId}">
              <span class="icon" aria-hidden="true">\u270F\uFE0F</span> Edit
            </button>
          </div>
        </div>
      `;
    }).join("");
    casesList.classList.remove("hidden");
    const checkboxes = document.querySelectorAll(".case-checkbox");
    checkboxes.forEach((checkbox) => {
      checkbox.addEventListener("change", (e) => {
        const target = e.target;
        const caseId = parseInt(target.dataset.caseId || "0", 10);
        toggleCaseSelection(caseId, target.checked);
      });
    });
  }
  async function saveRunDetails() {
    const nameInput = document.getElementById("runDetailsName");
    const descInput = document.getElementById("runDetailsDescription");
    const refsInput = document.getElementById("runDetailsRefs");
    const saveBtn = document.getElementById("runDetailsSaveBtn");
    if (!nameInput || !descInput || !refsInput || currentRunId === null) {
      console.error("Run details form elements not found or no run selected");
      return;
    }
    const name = nameInput.value;
    const description = descInput.value;
    const refs = refsInput.value;
    if (!name.trim()) {
      showToast("Run name cannot be empty", "error");
      nameInput.focus();
      return;
    }
    if (saveBtn) {
      saveBtn.disabled = true;
    }
    try {
      const response = await requestJson(`/api/manage/run/${currentRunId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          name: name.trim(),
          description: description || null,
          refs: refs || null
        })
      });
      if (response.success) {
        showToast(`Run "${name.trim()}" updated successfully`, "success");
        currentRunName = name.trim();
        const runNameDisplay = document.getElementById("runDetailsModalRunName");
        const breadcrumbRunName = document.getElementById("runDetailsBreadcrumbRunName");
        if (runNameDisplay) {
          runNameDisplay.textContent = currentRunName;
        }
        if (breadcrumbRunName) {
          breadcrumbRunName.textContent = currentRunName;
        }
        currentRunIsDirty = false;
        await loadRunDetailsCases(currentRunId);
      } else {
        throw new Error(response.message || "Failed to update run");
      }
    } catch (err) {
      showToast((err == null ? void 0 : err.message) || "Failed to update run", "error");
    } finally {
      if (saveBtn) {
        saveBtn.disabled = false;
      }
    }
  }
  async function handleRunDetailsBack() {
    if (currentRunIsDirty) {
      await saveRunDetails();
    }
    hideRunDetailsModal();
    if (currentPlanId !== null) {
      showPlanRunsModal(currentPlanId, currentPlanName, currentPlanEditButton || void 0);
    }
  }
  function hideRunDetailsModal() {
    const modal = document.getElementById("runDetailsModal");
    if (!modal) return;
    modal.classList.add("hidden");
    deactivateFocusTrap("runDetailsModal");
    restoreFocus("runDetailsModal");
    currentRunId = null;
    currentRunName = "";
    currentRunIsDirty = false;
    announceStatus("Closed run details");
  }
  function attachPlanEventListeners() {
    document.querySelectorAll(".delete-plan-btn").forEach((btn) => {
      const handleDelete = (e) => {
        const target = e.currentTarget;
        const planId = parseInt(target.dataset.planId || "0", 10);
        const planName = target.dataset.planName || `Plan ${planId}`;
        showDeleteConfirmation("plan", planName, planId, () => {
          deletePlan(planId, planName);
        }, {
          cascadeWarning: "\u26A0\uFE0F Warning: Deleting this plan will also permanently delete all associated test runs."
        });
      };
      btn.addEventListener("click", handleDelete);
      btn.addEventListener("keydown", (e) => {
        const keyEvent = e;
        if (keyEvent.key === "Enter") {
          keyEvent.preventDefault();
          handleDelete(keyEvent);
        }
      });
    });
    document.querySelectorAll(".edit-plan-btn").forEach((btn) => {
      const handleEdit = (e) => {
        const target = e.currentTarget;
        const planId = parseInt(target.dataset.planId || "0", 10);
        const planName = target.dataset.planName || `Plan ${planId}`;
        showPlanRunsModal(planId, planName, target);
      };
      btn.addEventListener("click", handleEdit);
      btn.addEventListener("keydown", (e) => {
        const keyEvent = e;
        if (keyEvent.key === "Enter") {
          keyEvent.preventDefault();
          handleEdit(keyEvent);
        }
      });
    });
  }
  function debounce(func, wait) {
    let timeout = null;
    return () => {
      if (timeout !== null) {
        clearTimeout(timeout);
      }
      timeout = window.setTimeout(() => {
        func();
      }, wait);
    };
  }
  function initManagement() {
    var _a, _b, _c, _d, _e;
    (_a = document.getElementById("deleteConfirmCancel")) == null ? void 0 : _a.addEventListener("click", hideDeleteConfirmation);
    (_b = document.getElementById("deleteConfirmClose")) == null ? void 0 : _b.addEventListener("click", hideDeleteConfirmation);
    (_c = document.getElementById("deleteConfirmDelete")) == null ? void 0 : _c.addEventListener("click", executeDeleteConfirmation);
    (_d = document.getElementById("deleteConfirmModal")) == null ? void 0 : _d.addEventListener("click", (e) => {
      var _a2;
      if (((_a2 = e.target) == null ? void 0 : _a2.id) === "deleteConfirmModal") {
        hideDeleteConfirmation();
      }
    });
    const typeInputEl = document.getElementById("deleteConfirmTypeInput");
    const deleteBtn = document.getElementById("deleteConfirmDelete");
    const typeErrorEl = document.getElementById("deleteConfirmTypeError");
    if (typeInputEl && deleteBtn) {
      typeInputEl.addEventListener("input", () => {
        const typedValue = typeInputEl.value.trim();
        if (deleteConfirmRequireTyping) {
          if (typedValue === deleteConfirmExpectedName) {
            deleteBtn.disabled = false;
            deleteBtn.style.opacity = "1";
            deleteBtn.style.cursor = "pointer";
            typeInputEl.style.borderColor = "#10b981";
            if (typeErrorEl) {
              typeErrorEl.classList.add("hidden");
            }
          } else {
            deleteBtn.disabled = true;
            deleteBtn.style.opacity = "0.5";
            deleteBtn.style.cursor = "not-allowed";
            typeInputEl.style.borderColor = "var(--border)";
          }
        }
      });
      typeInputEl.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !deleteBtn.disabled) {
          e.preventDefault();
          executeDeleteConfirmation();
        }
      });
    }
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        const modal = document.getElementById("deleteConfirmModal");
        if (modal && !modal.classList.contains("hidden")) {
          hideDeleteConfirmation();
        }
      }
    });
    const createSectionToggle = document.querySelector(".create-section-toggle");
    const createSectionContent = document.getElementById("createSectionContent");
    if (createSectionToggle && createSectionContent) {
      createSectionToggle.addEventListener("click", () => {
        const isExpanded = createSectionToggle.getAttribute("aria-expanded") === "true";
        createSectionToggle.setAttribute("aria-expanded", isExpanded ? "false" : "true");
        if (isExpanded) {
          createSectionContent.classList.add("hidden");
        } else {
          createSectionContent.classList.remove("hidden");
        }
        const indicator = createSectionToggle.querySelector(".toggle-indicator");
        if (indicator) {
          indicator.textContent = isExpanded ? "\u25BC" : "\u25B2";
        }
      });
    }
    (_e = document.getElementById("refreshPlansBtn")) == null ? void 0 : _e.addEventListener("click", refreshPlanList);
    const plansSearchInput = document.getElementById("plansSearch");
    if (plansSearchInput) {
      const debouncedPlansFilter = debounce(() => {
        filterPlans(plansSearchInput.value);
      }, 300);
      plansSearchInput.addEventListener("input", debouncedPlansFilter);
    }
    initRunEditModal();
    initCaseEditModal();
    initTestCasesView();
    initPlanRunsModal();
    initRunDetailsModal();
    document.addEventListener("keydown", (e) => {
      const caseModal = document.getElementById("caseEditModal");
      if (!caseModal || caseModal.classList.contains("hidden")) return;
      if (e.key === "Escape") {
        e.preventDefault();
        hideCaseEditModal();
      }
      if (e.key === "Enter") {
        const activeElement = document.activeElement;
        if (activeElement && activeElement.tagName === "INPUT" && activeElement.type === "text") {
          e.preventDefault();
          saveCaseEdit();
        }
      }
    });
  }
  function initPlanRunsModal() {
    var _a, _b, _c, _d, _e;
    (_a = document.getElementById("planRunsModalClose")) == null ? void 0 : _a.addEventListener("click", hidePlanRunsModal);
    (_b = document.getElementById("planRunsCloseBtn")) == null ? void 0 : _b.addEventListener("click", hidePlanRunsModal);
    (_c = document.getElementById("planRunsModal")) == null ? void 0 : _c.addEventListener("click", (e) => {
      var _a2;
      if (((_a2 = e.target) == null ? void 0 : _a2.id) === "planRunsModal") {
        hidePlanRunsModal();
      }
    });
    (_d = document.getElementById("planRunsBreadcrumbPlans")) == null ? void 0 : _d.addEventListener("click", (e) => {
      e.preventDefault();
      const context = {
        level: "runs",
        planId: currentPlanId || void 0,
        planName: currentPlanName || void 0
      };
      navigateToBreadcrumbLevel("plans", context);
    });
    (_e = document.getElementById("planRunsRetryBtn")) == null ? void 0 : _e.addEventListener("click", () => {
      if (currentPlanId !== null) {
        showPlanRunsModal(currentPlanId, currentPlanName, currentPlanEditButton || void 0);
      }
    });
    document.addEventListener("keydown", (e) => {
      const modal = document.getElementById("planRunsModal");
      if (!modal || modal.classList.contains("hidden")) return;
      if (e.key === "Escape") {
        e.preventDefault();
        hidePlanRunsModal();
      }
    });
  }
  function initRunDetailsModal() {
    var _a, _b, _c, _d, _e, _f, _g, _h, _i, _j, _k, _l, _m, _n, _o, _p, _q, _r, _s, _t, _u, _v;
    (_a = document.getElementById("runDetailsModalClose")) == null ? void 0 : _a.addEventListener("click", () => {
      handleRunDetailsBack();
    });
    (_b = document.getElementById("runDetailsBackBtn")) == null ? void 0 : _b.addEventListener("click", () => {
      handleRunDetailsBack();
    });
    (_c = document.getElementById("runDetailsBackFooterBtn")) == null ? void 0 : _c.addEventListener("click", () => {
      handleRunDetailsBack();
    });
    (_d = document.getElementById("runDetailsSaveBtn")) == null ? void 0 : _d.addEventListener("click", saveRunDetails);
    (_e = document.getElementById("runDetailsModal")) == null ? void 0 : _e.addEventListener("click", (e) => {
      var _a2;
      if (((_a2 = e.target) == null ? void 0 : _a2.id) === "runDetailsModal") {
        handleRunDetailsBack();
      }
    });
    (_f = document.getElementById("runDetailsBreadcrumbPlans")) == null ? void 0 : _f.addEventListener("click", (e) => {
      e.preventDefault();
      const context = {
        level: "cases",
        planId: currentPlanId || void 0,
        planName: currentPlanName || void 0,
        runId: currentRunId || void 0,
        runName: currentRunName || void 0
      };
      navigateToBreadcrumbLevel("plans", context);
    });
    (_g = document.getElementById("runDetailsBreadcrumbPlanName")) == null ? void 0 : _g.addEventListener("click", (e) => {
      e.preventDefault();
      const context = {
        level: "cases",
        planId: currentPlanId || void 0,
        planName: currentPlanName || void 0,
        runId: currentRunId || void 0,
        runName: currentRunName || void 0
      };
      navigateToBreadcrumbLevel("runs", context);
    });
    (_h = document.getElementById("runDetailsCasesRetryBtn")) == null ? void 0 : _h.addEventListener("click", () => {
      if (currentRunId !== null) {
        loadRunDetailsCases(currentRunId);
      }
    });
    const nameInput = document.getElementById("runDetailsName");
    const descInput = document.getElementById("runDetailsDescription");
    const refsInput = document.getElementById("runDetailsRefs");
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
    document.addEventListener("keydown", (e) => {
      const modal = document.getElementById("runDetailsModal");
      if (!modal || modal.classList.contains("hidden")) return;
      if (e.key === "Escape") {
        e.preventDefault();
        handleRunDetailsBack();
      }
    });
    (_i = document.getElementById("runDetailsAddCases")) == null ? void 0 : _i.addEventListener("click", showAddCasesToRunModal);
    (_j = document.getElementById("runDetailsSelectAll")) == null ? void 0 : _j.addEventListener("click", selectAllCases);
    (_k = document.getElementById("runDetailsDeselectAll")) == null ? void 0 : _k.addEventListener("click", deselectAllCases);
    (_l = document.getElementById("runDetailsBulkRemove")) == null ? void 0 : _l.addEventListener("click", removeSelectedCasesFromRun);
    (_m = document.getElementById("addCasesToRunModalClose")) == null ? void 0 : _m.addEventListener("click", hideAddCasesToRunModal);
    (_n = document.getElementById("addCasesCancelBtn")) == null ? void 0 : _n.addEventListener("click", hideAddCasesToRunModal);
    (_o = document.getElementById("addCasesConfirmBtn")) == null ? void 0 : _o.addEventListener("click", addSelectedCasesToRun);
    (_p = document.getElementById("addCasesSelectAll")) == null ? void 0 : _p.addEventListener("click", selectAllAddCases);
    (_q = document.getElementById("addCasesDeselectAll")) == null ? void 0 : _q.addEventListener("click", deselectAllAddCases);
    const addCasesSearch = document.getElementById("addCasesSearch");
    if (addCasesSearch) {
      addCasesSearch.addEventListener("input", (e) => {
        const target = e.target;
        filterAvailableCases(target.value);
      });
    }
    (_r = document.getElementById("addCasesToRunModal")) == null ? void 0 : _r.addEventListener("click", (e) => {
      var _a2;
      if (((_a2 = e.target) == null ? void 0 : _a2.id) === "addCasesToRunModal") {
        hideAddCasesToRunModal();
      }
    });
    document.addEventListener("keydown", (e) => {
      const modal = document.getElementById("addCasesToRunModal");
      if (!modal || modal.classList.contains("hidden")) return;
      if (e.key === "Escape") {
        e.preventDefault();
        hideAddCasesToRunModal();
      }
    });
    (_s = document.getElementById("addTestResultModalClose")) == null ? void 0 : _s.addEventListener("click", hideAddTestResultModal);
    (_t = document.getElementById("addResultCancelBtn")) == null ? void 0 : _t.addEventListener("click", hideAddTestResultModal);
    (_u = document.getElementById("addResultSubmitBtn")) == null ? void 0 : _u.addEventListener("click", submitTestResult);
    (_v = document.getElementById("addTestResultModal")) == null ? void 0 : _v.addEventListener("click", (e) => {
      var _a2;
      if (((_a2 = e.target) == null ? void 0 : _a2.id) === "addTestResultModal") {
        hideAddTestResultModal();
      }
    });
    document.addEventListener("keydown", (e) => {
      const modal = document.getElementById("addTestResultModal");
      if (!modal || modal.classList.contains("hidden")) return;
      if (e.key === "Escape") {
        e.preventDefault();
        hideAddTestResultModal();
      }
    });
    const casesList = document.getElementById("runDetailsCasesList");
    if (casesList) {
      casesList.addEventListener("click", async (e) => {
        const target = e.target;
        if (target.closest(".add-result-btn-modal")) {
          e.stopPropagation();
          const btn = target.closest(".add-result-btn-modal");
          const testId = parseInt(btn.dataset.testId || "0", 10);
          const testTitle = btn.dataset.testTitle || "";
          showAddTestResultModal(testId, testTitle);
        }
        if (target.closest(".edit-case-btn-modal")) {
          e.stopPropagation();
          const btn = target.closest(".edit-case-btn-modal");
          const caseId = parseInt(btn.dataset.caseId || "0", 10);
          const caseTitle = btn.dataset.caseTitle || "";
          const refs = btn.dataset.caseRefs || null;
          const btnElement = btn;
          const originalText = btnElement.innerHTML;
          btnElement.disabled = true;
          btnElement.innerHTML = '<span class="icon" aria-hidden="true">\u23F3</span> Loading...';
          try {
            const response = await requestJson(`/api/manage/case/${caseId}`);
            const caseData = response.case;
            if (caseData) {
              showCaseEditModal(
                caseId,
                caseData.title || caseTitle,
                caseData.refs || refs,
                caseData.custom_bdd_scenario || null
              );
            } else {
              showCaseEditModal(caseId, caseTitle, refs, null);
            }
          } catch (err) {
            console.error("Failed to fetch case details:", err);
            showToast((err == null ? void 0 : err.message) || "Failed to load case details", "error");
            showCaseEditModal(caseId, caseTitle, refs, null);
          } finally {
            btnElement.disabled = false;
            btnElement.innerHTML = originalText;
          }
        }
      });
    }
  }
  function initRunEditModal() {
    var _a, _b, _c;
    (_a = document.getElementById("runEditCancel")) == null ? void 0 : _a.addEventListener("click", hideRunEditModal);
    (_b = document.getElementById("runEditModalClose")) == null ? void 0 : _b.addEventListener("click", hideRunEditModal);
    (_c = document.getElementById("runEditModal")) == null ? void 0 : _c.addEventListener("click", (e) => {
      var _a2;
      if (((_a2 = e.target) == null ? void 0 : _a2.id) === "runEditModal") {
        hideRunEditModal();
      }
    });
    const runEditForm = document.getElementById("runEditForm");
    if (runEditForm) {
      runEditForm.addEventListener("submit", (e) => {
        e.preventDefault();
        saveRunEdit();
      });
    }
    const nameInput = document.getElementById("runEditName");
    if (nameInput) {
      nameInput.addEventListener("input", () => {
        const nameError = document.getElementById("runEditNameError");
        if (nameError && !nameError.classList.contains("hidden")) {
          if (nameInput.value.trim().length > 0) {
            nameError.classList.add("hidden");
            nameInput.style.borderColor = "var(--border)";
          }
        }
      });
    }
    document.addEventListener("keydown", (e) => {
      const modal = document.getElementById("runEditModal");
      if (!modal || modal.classList.contains("hidden")) return;
      if (e.key === "Escape") {
        e.preventDefault();
        hideRunEditModal();
      }
      if (e.key === "Enter") {
        const activeElement = document.activeElement;
        if (activeElement && activeElement.tagName === "INPUT" && activeElement.type === "text") {
          e.preventDefault();
          saveRunEdit();
        }
      }
    });
  }
  var currentEditCaseId = null;
  var currentEditCaseAttachments = [];
  var ALLOWED_FILE_TYPES = [
    "image/png",
    "image/jpeg",
    "image/gif",
    "video/mp4",
    "video/webm",
    "application/pdf"
  ];
  var MAX_FILE_SIZE_MB = 25;
  var MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
  function showCaseEditModal(caseId, title, refs = null, bddScenarios = null) {
    const modal = document.getElementById("caseEditModal");
    const idInput = document.getElementById("caseEditId");
    const titleInput = document.getElementById("caseEditTitle");
    const refsInput = document.getElementById("caseEditRefs");
    const bddInput = document.getElementById("caseEditBddScenarios");
    const titleError = document.getElementById("caseEditTitleError");
    const fileError = document.getElementById("caseEditFileError");
    const loadingOverlay = document.getElementById("caseEditLoadingOverlay");
    const attachmentsList = document.getElementById("caseEditAttachmentsList");
    if (!modal || !idInput || !titleInput || !refsInput || !bddInput) {
      console.error("Case edit modal elements not found");
      return;
    }
    currentEditCaseId = caseId;
    currentEditCaseAttachments = [];
    const activeElement = document.activeElement;
    storeTriggerElement("caseEditModal", activeElement);
    idInput.value = String(caseId);
    titleInput.value = title || "";
    refsInput.value = refs || "";
    bddInput.value = bddScenarios || "";
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
    if (titleError) {
      titleError.classList.add("hidden");
    }
    if (fileError) {
      fileError.classList.add("hidden");
    }
    titleInput.style.borderColor = "var(--border)";
    if (loadingOverlay) {
      loadingOverlay.classList.add("hidden");
    }
    if (attachmentsList) {
      attachmentsList.innerHTML = "";
    }
    modal.classList.remove("hidden");
    modal.style.zIndex = "12000";
    activateFocusTrap("caseEditModal");
    setTimeout(() => {
      titleInput.focus();
      titleInput.select();
    }, 100);
    loadCaseAttachments(caseId);
  }
  function hideCaseEditModal() {
    const modal = document.getElementById("caseEditModal");
    const titleInput = document.getElementById("caseEditTitle");
    const refsInput = document.getElementById("caseEditRefs");
    const bddInput = document.getElementById("caseEditBddScenarios");
    const titleError = document.getElementById("caseEditTitleError");
    const fileError = document.getElementById("caseEditFileError");
    const loadingOverlay = document.getElementById("caseEditLoadingOverlay");
    const attachmentsList = document.getElementById("caseEditAttachmentsList");
    const uploadProgress = document.getElementById("caseEditUploadProgress");
    if (!modal) return;
    modal.classList.add("hidden");
    modal.style.zIndex = "";
    deactivateFocusTrap("caseEditModal");
    restoreFocus("caseEditModal");
    currentEditCaseId = null;
    currentEditCaseAttachments = [];
    if (titleInput) titleInput.value = "";
    if (refsInput) refsInput.value = "";
    if (bddInput) bddInput.value = "";
    if (titleError) {
      titleError.classList.add("hidden");
    }
    if (fileError) {
      fileError.classList.add("hidden");
    }
    if (titleInput) {
      titleInput.style.borderColor = "var(--border)";
    }
    if (loadingOverlay) {
      loadingOverlay.classList.add("hidden");
    }
    if (uploadProgress) {
      uploadProgress.classList.add("hidden");
    }
    if (attachmentsList) {
      attachmentsList.innerHTML = "";
    }
    if (currentRunId !== null) {
      const runDetailsModal = document.getElementById("runDetailsModal");
      if (runDetailsModal && runDetailsModal.classList.contains("hidden")) {
        showRunDetailsModal(currentRunId);
      } else {
        loadRunDetailsCases(currentRunId);
      }
    }
  }
  async function loadCaseAttachments(caseId) {
    const attachmentsList = document.getElementById("caseEditAttachmentsList");
    if (!attachmentsList) return;
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
    } catch (err) {
      console.error("Failed to load attachments:", err);
      attachmentsList.innerHTML = `
      <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 20px; text-align: center;">
        <div style="font-size: 32px; margin-bottom: 8px; opacity: 0.5;" aria-hidden="true">\u26A0\uFE0F</div>
        <p style="margin: 0 0 8px; font-size: 13px; color: var(--text);">Failed to load attachments</p>
        <p style="margin: 0 0 12px; font-size: 12px; color: var(--muted);">${escapeHtml((err == null ? void 0 : err.message) || "An error occurred")}</p>
        <button type="button" class="btn-secondary" onclick="window.retryLoadAttachments(${caseId})" style="padding: 6px 12px; font-size: 12px;">
          <span class="icon" aria-hidden="true">\u{1F504}</span> Retry
        </button>
      </div>
    `;
    }
  }
  window.retryLoadAttachments = (caseId) => {
    loadCaseAttachments(caseId);
  };
  function renderAttachmentsList(attachments) {
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
    attachmentsList.innerHTML = attachments.map((attachment) => {
      var _a;
      const isImage = (_a = attachment.content_type) == null ? void 0 : _a.startsWith("image/");
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
    }).join("");
  }
  function getFileIcon(contentType) {
    if (!contentType) return "\u{1F4C4}";
    if (contentType.startsWith("image/")) return "\u{1F5BC}\uFE0F";
    if (contentType.startsWith("video/")) return "\u{1F3AC}";
    if (contentType === "application/pdf") return "\u{1F4D5}";
    return "\u{1F4C4}";
  }
  function formatFileSize(bytes) {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  }
  function initCaseEditModal() {
    var _a, _b, _c, _d, _e, _f;
    (_a = document.getElementById("caseEditCancel")) == null ? void 0 : _a.addEventListener("click", hideCaseEditModal);
    (_b = document.getElementById("caseEditModalClose")) == null ? void 0 : _b.addEventListener("click", hideCaseEditModal);
    (_c = document.getElementById("caseEditModal")) == null ? void 0 : _c.addEventListener("click", (e) => {
      var _a2;
      if (((_a2 = e.target) == null ? void 0 : _a2.id) === "caseEditModal") {
        hideCaseEditModal();
      }
    });
    (_d = document.getElementById("caseEditBreadcrumbPlans")) == null ? void 0 : _d.addEventListener("click", (e) => {
      e.preventDefault();
      const titleInput2 = document.getElementById("caseEditTitle");
      const context = {
        level: "case-edit",
        planId: currentPlanId || void 0,
        planName: currentPlanName || void 0,
        runId: currentRunId || void 0,
        runName: currentRunName || void 0,
        caseId: currentEditCaseId || void 0,
        caseTitle: (titleInput2 == null ? void 0 : titleInput2.value) || void 0
      };
      navigateToBreadcrumbLevel("plans", context);
    });
    (_e = document.getElementById("caseEditBreadcrumbPlanName")) == null ? void 0 : _e.addEventListener("click", (e) => {
      e.preventDefault();
      const titleInput2 = document.getElementById("caseEditTitle");
      const context = {
        level: "case-edit",
        planId: currentPlanId || void 0,
        planName: currentPlanName || void 0,
        runId: currentRunId || void 0,
        runName: currentRunName || void 0,
        caseId: currentEditCaseId || void 0,
        caseTitle: (titleInput2 == null ? void 0 : titleInput2.value) || void 0
      };
      navigateToBreadcrumbLevel("runs", context);
    });
    (_f = document.getElementById("caseEditBreadcrumbRunName")) == null ? void 0 : _f.addEventListener("click", (e) => {
      e.preventDefault();
      const titleInput2 = document.getElementById("caseEditTitle");
      const context = {
        level: "case-edit",
        planId: currentPlanId || void 0,
        planName: currentPlanName || void 0,
        runId: currentRunId || void 0,
        runName: currentRunName || void 0,
        caseId: currentEditCaseId || void 0,
        caseTitle: (titleInput2 == null ? void 0 : titleInput2.value) || void 0
      };
      navigateToBreadcrumbLevel("cases", context);
    });
    const caseEditForm = document.getElementById("caseEditForm");
    if (caseEditForm) {
      caseEditForm.addEventListener("submit", (e) => {
        e.preventDefault();
        saveCaseEdit();
      });
    }
    const titleInput = document.getElementById("caseEditTitle");
    if (titleInput) {
      titleInput.addEventListener("input", () => {
        const titleError = document.getElementById("caseEditTitleError");
        if (titleError && !titleError.classList.contains("hidden")) {
          if (titleInput.value.trim().length > 0) {
            titleError.classList.add("hidden");
            titleInput.style.borderColor = "var(--border)";
          }
        }
      });
    }
    initFileUploadHandlers();
  }
  function initFileUploadHandlers() {
    const dropZone = document.getElementById("caseEditDropZone");
    const fileInput = document.getElementById("caseEditFileInput");
    if (!dropZone || !fileInput) return;
    dropZone.addEventListener("click", () => {
      fileInput.click();
    });
    dropZone.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        fileInput.click();
      }
    });
    fileInput.addEventListener("change", () => {
      var _a;
      const file = (_a = fileInput.files) == null ? void 0 : _a[0];
      if (file) {
        handleFileUpload(file);
      }
      fileInput.value = "";
    });
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
      var _a, _b;
      e.preventDefault();
      e.stopPropagation();
      dropZone.style.borderColor = "var(--border)";
      dropZone.style.background = "transparent";
      const file = (_b = (_a = e.dataTransfer) == null ? void 0 : _a.files) == null ? void 0 : _b[0];
      if (file) {
        handleFileUpload(file);
      }
    });
  }
  function validateCaseTitle(title) {
    return title.trim().length > 0;
  }
  function showCaseTitleValidationError() {
    const titleInput = document.getElementById("caseEditTitle");
    const titleError = document.getElementById("caseEditTitleError");
    if (titleInput) {
      titleInput.style.borderColor = "#ef4444";
    }
    if (titleError) {
      titleError.classList.remove("hidden");
    }
  }
  function clearCaseTitleValidationError() {
    const titleInput = document.getElementById("caseEditTitle");
    const titleError = document.getElementById("caseEditTitleError");
    if (titleInput) {
      titleInput.style.borderColor = "var(--border)";
    }
    if (titleError) {
      titleError.classList.add("hidden");
    }
  }
  async function saveCaseEdit() {
    const titleInput = document.getElementById("caseEditTitle");
    const refsInput = document.getElementById("caseEditRefs");
    const bddInput = document.getElementById("caseEditBddScenarios");
    const loadingOverlay = document.getElementById("caseEditLoadingOverlay");
    const saveBtn = document.getElementById("caseEditSave");
    if (!titleInput || !refsInput || !bddInput || currentEditCaseId === null) {
      console.error("Case edit form elements not found or no case selected");
      return;
    }
    const title = titleInput.value;
    const refs = refsInput.value;
    const bddScenarios = bddInput.value;
    if (!validateCaseTitle(title)) {
      showCaseTitleValidationError();
      titleInput.focus();
      return;
    }
    clearCaseTitleValidationError();
    if (loadingOverlay) {
      loadingOverlay.classList.remove("hidden");
    }
    if (saveBtn) {
      saveBtn.disabled = true;
    }
    try {
      const response = await requestJson(`/api/manage/case/${currentEditCaseId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          title: title.trim(),
          refs: refs || null,
          custom_bdd_scenario: bddScenarios || null
        })
      });
      if (response.success) {
        showToast(`Case "${title.trim()}" updated successfully`, "success");
        hideCaseEditModal();
      } else {
        throw new Error(response.message || "Failed to update case");
      }
    } catch (err) {
      showToast((err == null ? void 0 : err.message) || "Failed to update case", "error");
    } finally {
      if (loadingOverlay) {
        loadingOverlay.classList.add("hidden");
      }
      if (saveBtn) {
        saveBtn.disabled = false;
      }
    }
  }
  function validateFileType(file) {
    return ALLOWED_FILE_TYPES.includes(file.type);
  }
  function validateFileSize(file) {
    return file.size <= MAX_FILE_SIZE_BYTES;
  }
  function showFileValidationError(message) {
    const fileError = document.getElementById("caseEditFileError");
    if (fileError) {
      fileError.textContent = message;
      fileError.classList.remove("hidden");
    }
  }
  function clearFileValidationError() {
    const fileError = document.getElementById("caseEditFileError");
    if (fileError) {
      fileError.classList.add("hidden");
    }
  }
  async function handleFileUpload(file) {
    if (currentEditCaseId === null) {
      showToast("No case selected for attachment", "error");
      return;
    }
    clearFileValidationError();
    if (!validateFileType(file)) {
      showFileValidationError("File type not allowed. Accepted types: PNG, JPG, GIF, MP4, WebM, PDF");
      return;
    }
    if (!validateFileSize(file)) {
      showFileValidationError(`File size exceeds ${MAX_FILE_SIZE_MB}MB limit`);
      return;
    }
    const uploadProgress = document.getElementById("caseEditUploadProgress");
    const uploadFileName = document.getElementById("caseEditUploadFileName");
    if (uploadProgress) {
      uploadProgress.classList.remove("hidden");
    }
    if (uploadFileName) {
      uploadFileName.textContent = `Uploading ${file.name}...`;
    }
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`/api/manage/case/${currentEditCaseId}/attachment`, {
        method: "POST",
        body: formData
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Upload failed with status ${response.status}`);
      }
      const result = await response.json();
      if (result.attachment) {
        currentEditCaseAttachments.push(result.attachment);
        renderAttachmentsList(currentEditCaseAttachments);
      }
      showToast(`File "${file.name}" uploaded successfully`, "success");
    } catch (err) {
      showToast((err == null ? void 0 : err.message) || "Failed to upload file", "error");
    } finally {
      if (uploadProgress) {
        uploadProgress.classList.add("hidden");
      }
    }
  }
  async function initManageView() {
    try {
      plansCurrentPage = 0;
      await loadManagePlans2();
    } catch (err) {
      console.error("Error initializing manage view:", err);
      showToast("Failed to load management data", "error");
    }
  }
  var allPlans = [];
  var plansCurrentPage = 0;
  var PLANS_PAGE_SIZE = 10;
  async function loadManagePlans2() {
    const container = document.getElementById("plansListContainer");
    const loadingState = document.getElementById("plansLoadingState");
    const emptyState = document.getElementById("plansEmptyState");
    const countBadge = document.getElementById("plansCount");
    const refreshBtn = document.getElementById("refreshPlansBtn");
    const searchInput = document.getElementById("plansSearch");
    if (!container || !loadingState || !emptyState) return;
    const currentSearchValue = (searchInput == null ? void 0 : searchInput.value) || "";
    loadingState.classList.remove("hidden");
    emptyState.classList.add("hidden");
    container.classList.add("hidden");
    setSubsectionBusy("plans", true);
    announceStatus("Loading plans...");
    if (refreshBtn) refreshBtn.disabled = true;
    if (searchInput) searchInput.disabled = true;
    disableEntityButtons("plan");
    try {
      const projectInput = document.getElementById("planProject");
      const project = (projectInput == null ? void 0 : projectInput.value) || "1";
      const data = await requestJson(`/api/plans?project=${encodeURIComponent(project)}&is_completed=0`);
      const plans = Array.isArray(data.plans) ? data.plans : [];
      const plansWithRunData = await Promise.all(
        plans.map(async (plan) => {
          try {
            const runsData = await requestJson(`/api/runs?plan=${plan.id}&project=${encodeURIComponent(project)}`);
            const runs = Array.isArray(runsData.runs) ? runsData.runs : [];
            let latestRunUpdate = 0;
            runs.forEach((run) => {
              const runTime = run.updated_on || run.created_on || 0;
              if (runTime > latestRunUpdate) {
                latestRunUpdate = runTime;
              }
            });
            const effectiveUpdateTime = latestRunUpdate || plan.updated_on || plan.created_on || 0;
            return __spreadProps(__spreadValues({}, plan), {
              effective_updated_on: effectiveUpdateTime,
              latest_run_update: latestRunUpdate
            });
          } catch (err) {
            return __spreadProps(__spreadValues({}, plan), {
              effective_updated_on: plan.updated_on || plan.created_on || 0,
              latest_run_update: 0
            });
          }
        })
      );
      plansWithRunData.sort((a, b) => {
        return b.effective_updated_on - a.effective_updated_on;
      });
      allPlans = plansWithRunData;
      if (countBadge) {
        countBadge.textContent = String(plans.length);
      }
      if (currentSearchValue.trim()) {
        filterPlans(currentSearchValue);
      } else {
        renderPlansSubsection(plans);
      }
      setSubsectionBusy("plans", false);
      announceStatus(`Loaded ${plans.length} plan${plans.length !== 1 ? "s" : ""}`);
    } catch (err) {
      setSubsectionBusy("plans", false);
      announceStatus("Failed to load plans");
      showErrorState("plans", (err == null ? void 0 : err.message) || "Failed to load plans", refreshPlanList);
      showToast((err == null ? void 0 : err.message) || "Failed to load plans", "error");
    } finally {
      if (refreshBtn) refreshBtn.disabled = false;
      if (searchInput) searchInput.disabled = false;
    }
  }
  function renderPlansSubsection(plans) {
    var _a, _b;
    const container = document.getElementById("plansListContainer");
    const loadingState = document.getElementById("plansLoadingState");
    const emptyState = document.getElementById("plansEmptyState");
    if (!container || !loadingState || !emptyState) return;
    if (plans.length === 0) {
      loadingState.classList.add("hidden");
      emptyState.classList.remove("hidden");
      container.classList.add("hidden");
      return;
    }
    const startIndex = plansCurrentPage * PLANS_PAGE_SIZE;
    const endIndex = startIndex + PLANS_PAGE_SIZE;
    const displayPlans = plans.slice(startIndex, endIndex);
    const totalPages = Math.ceil(plans.length / PLANS_PAGE_SIZE);
    const hasPrev = plansCurrentPage > 0;
    const hasNext = plansCurrentPage < totalPages - 1;
    container.innerHTML = displayPlans.map((plan) => {
      const planName = escapeHtml(plan.name || `Plan ${plan.id}`);
      const planId = plan.id;
      const isCompleted = plan.is_completed === true || plan.is_completed === 1;
      const badgeClass = isCompleted ? "badge-completed" : "badge-active";
      const badgeText = isCompleted ? "Completed" : "Active";
      const updatedOn = plan.effective_updated_on || plan.updated_on || plan.created_on;
      let lastUpdatedText = "";
      if (updatedOn) {
        const date = new Date(updatedOn * 1e3);
        const now = /* @__PURE__ */ new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffDays = Math.floor(diffMs / (1e3 * 60 * 60 * 24));
        if (diffDays === 0) {
          lastUpdatedText = "Today";
        } else if (diffDays === 1) {
          lastUpdatedText = "Yesterday";
        } else if (diffDays < 7) {
          lastUpdatedText = `${diffDays} days ago`;
        } else if (diffDays < 30) {
          const weeks = Math.floor(diffDays / 7);
          lastUpdatedText = `${weeks} week${weeks > 1 ? "s" : ""} ago`;
        } else if (diffDays < 365) {
          const months = Math.floor(diffDays / 30);
          lastUpdatedText = `${months} month${months > 1 ? "s" : ""} ago`;
        } else {
          const years = Math.floor(diffDays / 365);
          lastUpdatedText = `${years} year${years > 1 ? "s" : ""} ago`;
        }
      }
      return `
        <div class="entity-card" role="listitem" data-entity-type="plan" data-entity-id="${planId}" data-plan-name="${escapeHtml(plan.name || "").toLowerCase()}" aria-label="Plan: ${planName}, Status: ${badgeText}">
          <div class="entity-card-header">
            <div class="entity-card-title" id="plan-title-${planId}">${planName}</div>
            <div class="entity-card-badges">
              <span class="badge ${badgeClass}" role="status">${badgeText}</span>
            </div>
          </div>
          <div class="entity-card-meta">
            <span class="meta-item">
              <span class="icon" aria-hidden="true">\u{1F194}</span> Plan ID: ${planId}
            </span>
            ${lastUpdatedText ? `<span class="meta-item">
              <span class="icon" aria-hidden="true">\u{1F552}</span> Updated: ${lastUpdatedText}
            </span>` : ""}
          </div>
          <div class="entity-card-actions" role="group" aria-label="Actions for ${planName}">
            <button type="button" class="btn-edit edit-plan-btn" data-plan-id="${planId}" data-plan-name="${escapeHtml(plan.name || "")}" aria-label="Edit plan ${planName}" aria-describedby="plan-title-${planId}">
              <span class="icon" aria-hidden="true">\u270F\uFE0F</span> Edit
            </button>
            <button type="button" class="btn-delete delete-plan-btn" data-plan-id="${planId}" data-plan-name="${escapeHtml(plan.name || "")}" aria-label="Delete plan ${planName}" aria-describedby="plan-title-${planId}">
              <span class="icon" aria-hidden="true">\u{1F5D1}\uFE0F</span> Delete
            </button>
          </div>
        </div>
      `;
    }).join("");
    container.innerHTML += `
    <div class="pagination-controls" style="display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border-top: 1px solid var(--border); margin-top: 8px;">
      <span style="font-size: 13px; color: var(--muted);">
        Showing ${startIndex + 1}-${Math.min(endIndex, plans.length)} of ${plans.length} plans
      </span>
      <div style="display: flex; gap: 8px;">
        <button type="button" class="refresh-btn plans-prev-btn" ${!hasPrev ? "disabled" : ""} aria-label="Previous page">
          \u2190 Prev
        </button>
        <span style="font-size: 13px; color: var(--muted); padding: 6px 12px;">
          Page ${plansCurrentPage + 1} of ${totalPages}
        </span>
        <button type="button" class="refresh-btn plans-next-btn" ${!hasNext ? "disabled" : ""} aria-label="Next page">
          Next \u2192
        </button>
      </div>
    </div>
  `;
    loadingState.classList.add("hidden");
    emptyState.classList.add("hidden");
    container.classList.remove("hidden");
    attachPlanEventListeners();
    (_a = container.querySelector(".plans-prev-btn")) == null ? void 0 : _a.addEventListener("click", () => {
      if (plansCurrentPage > 0) {
        plansCurrentPage--;
        renderPlansSubsection(plans);
      }
    });
    (_b = container.querySelector(".plans-next-btn")) == null ? void 0 : _b.addEventListener("click", () => {
      if (plansCurrentPage < totalPages - 1) {
        plansCurrentPage++;
        renderPlansSubsection(plans);
      }
    });
  }
  function filterPlans(searchQuery) {
    const query = searchQuery.toLowerCase().trim();
    plansCurrentPage = 0;
    if (!query) {
      renderPlansSubsection(allPlans);
      return;
    }
    const filteredPlans = allPlans.filter((plan) => {
      const planName = (plan.name || `Plan ${plan.id}`).toLowerCase();
      return planName.includes(query);
    });
    renderPlansSubsection(filteredPlans);
  }
  var currentTestCasesRunId = null;
  var currentTestCasesRunName = "";
  function getStatusBadgeClass(statusId) {
    switch (statusId) {
      case 1:
        return "badge-passed";
      // Green for Passed
      case 2:
        return "badge-blocked";
      // Orange for Blocked
      case 3:
        return "badge-untested";
      // Gray for Untested
      case 4:
        return "badge-retest";
      // Yellow for Retest
      case 5:
        return "badge-failed";
      // Red for Failed
      default:
        return "badge-untested";
    }
  }
  function hideTestCasesView() {
    const testCasesView = document.getElementById("testCasesView");
    if (testCasesView) {
      testCasesView.classList.add("hidden");
    }
    const container = document.getElementById("testCasesListContainer");
    if (container) {
      container.innerHTML = "";
      container.classList.add("hidden");
    }
    if (currentPlanId !== null && currentPlanName) {
      showPlanRunsModal(currentPlanId, currentPlanName, currentPlanEditButton || void 0);
      announceStatus(`Returned to runs for ${currentPlanName}`);
    } else {
      announceStatus("Returned to plans list");
    }
    currentTestCasesRunId = null;
    currentTestCasesRunName = "";
  }
  async function loadTestCases(runId) {
    const container = document.getElementById("testCasesListContainer");
    const loadingState = document.getElementById("testCasesLoadingState");
    const emptyState = document.getElementById("testCasesEmptyState");
    const errorState = document.getElementById("testCasesErrorState");
    const countBadge = document.getElementById("testCasesCount");
    const refreshBtn = document.getElementById("refreshTestCasesBtn");
    if (!container || !loadingState || !emptyState || !errorState) return;
    loadingState.classList.remove("hidden");
    emptyState.classList.add("hidden");
    errorState.classList.add("hidden");
    container.classList.add("hidden");
    if (refreshBtn) refreshBtn.disabled = true;
    announceStatus("Loading test cases...");
    try {
      const data = await requestJson(`/api/tests/${runId}`);
      const tests = Array.isArray(data.tests) ? data.tests : [];
      if (countBadge) {
        countBadge.textContent = String(tests.length);
      }
      loadingState.classList.add("hidden");
      if (tests.length === 0) {
        emptyState.classList.remove("hidden");
        container.classList.add("hidden");
        announceStatus("No test cases found");
      } else {
        renderTestCases(tests);
        announceStatus(`Loaded ${tests.length} test case${tests.length !== 1 ? "s" : ""}`);
      }
    } catch (err) {
      loadingState.classList.add("hidden");
      errorState.classList.remove("hidden");
      container.classList.add("hidden");
      const errorMessage = document.getElementById("testCasesErrorMessage");
      if (errorMessage) {
        errorMessage.textContent = (err == null ? void 0 : err.message) || "An error occurred while loading test cases.";
      }
      showToast((err == null ? void 0 : err.message) || "Failed to load test cases", "error");
      announceStatus("Failed to load test cases");
    } finally {
      if (refreshBtn) refreshBtn.disabled = false;
    }
  }
  function renderTestCases(tests) {
    const container = document.getElementById("testCasesListContainer");
    const emptyState = document.getElementById("testCasesEmptyState");
    const errorState = document.getElementById("testCasesErrorState");
    if (!container) return;
    if (emptyState) emptyState.classList.add("hidden");
    if (errorState) errorState.classList.add("hidden");
    container.innerHTML = tests.map((test) => {
      const testTitle = escapeHtml(test.title || `Test ${test.id}`);
      const testId = test.id;
      const caseId = test.case_id;
      const statusId = test.status_id || 3;
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
              <span class="icon" aria-hidden="true">\u{1F194}</span> Test ID: ${testId}
            </span>
            <span class="meta-item">
              <span class="icon" aria-hidden="true">\u{1F4CB}</span> Case ID: ${caseId}
            </span>
            ${refs ? `<span class="meta-item"><span class="icon" aria-hidden="true">\u{1F517}</span> Refs: ${refs}</span>` : ""}
          </div>
          <div class="entity-card-actions" role="group" aria-label="Actions for ${testTitle}">
            <button type="button" class="btn-edit edit-test-case-btn" data-case-id="${caseId}" data-case-title="${escapeHtml(test.title || "")}" data-case-refs="${escapeHtml(test.refs || "")}" aria-label="Edit case ${testTitle}" aria-describedby="test-title-${testId}">
              <span class="icon" aria-hidden="true">\u270F\uFE0F</span> Edit Case
            </button>
          </div>
        </div>
      `;
    }).join("");
    container.classList.remove("hidden");
    attachTestCaseEventListeners();
  }
  function attachTestCaseEventListeners() {
    document.querySelectorAll(".edit-test-case-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const target = e.currentTarget;
        const caseId = parseInt(target.dataset.caseId || "0", 10);
        const caseTitle = target.dataset.caseTitle || "";
        const refs = target.dataset.caseRefs || null;
        showCaseEditModal(caseId, caseTitle, refs, null);
      });
    });
  }
  function initTestCasesView() {
    var _a, _b, _c;
    (_a = document.getElementById("testCasesBackBtn")) == null ? void 0 : _a.addEventListener("click", hideTestCasesView);
    (_b = document.getElementById("refreshTestCasesBtn")) == null ? void 0 : _b.addEventListener("click", () => {
      if (currentTestCasesRunId !== null) {
        loadTestCases(currentTestCasesRunId);
      }
    });
    (_c = document.getElementById("testCasesRetryBtn")) == null ? void 0 : _c.addEventListener("click", () => {
      if (currentTestCasesRunId !== null) {
        loadTestCases(currentTestCasesRunId);
      }
    });
  }

  // src/app.ts
  function updateReportMeta(meta, params) {
    const container = document.getElementById("reportMeta");
    if (!container) {
      return;
    }
    if (!meta || Object.keys(meta).length === 0) {
      container.innerHTML = '<p class="report-meta-summary">No report generated yet.</p>';
      return;
    }
    const generated = meta.generated_at ? new Date(meta.generated_at).toLocaleString() : "just now";
    const durationText = typeof meta.duration_ms === "number" ? `${(meta.duration_ms / 1e3).toFixed(1)}s` : null;
    const callCount = typeof meta.api_call_count === "number" ? meta.api_call_count : null;
    const scopeLabel = (params == null ? void 0 : params.plan) ? `Plan ${params.plan}` : (params == null ? void 0 : params.run) ? `Run ${params.run}` : "";
    const summaryParts = [];
    if (scopeLabel) {
      summaryParts.push(scopeLabel);
    }
    summaryParts.push(`Generated ${generated}`);
    if (durationText) {
      summaryParts.push(`Duration ${durationText}`);
    }
    if (callCount !== null) {
      summaryParts.push(`${callCount} TestRail call${callCount === 1 ? "" : "s"}`);
    }
    const safeSummary = summaryParts.map((part) => escapeHtml(part)).join(" \xB7 ");
    let html = `<p class="report-meta-summary">${safeSummary}</p>`;
    const recentCalls = Array.isArray(meta.api_calls) ? meta.api_calls.slice(-10) : [];
    if (recentCalls.length) {
      const items = recentCalls.map((call) => {
        const kind = escapeHtml(String((call == null ? void 0 : call.kind) || "GET"));
        const endpoint = escapeHtml(String((call == null ? void 0 : call.endpoint) || ""));
        const elapsed = typeof (call == null ? void 0 : call.elapsed_ms) === "number" ? `${call.elapsed_ms.toFixed(1)} ms` : "";
        const status = (call == null ? void 0 : call.status) ? ` (${escapeHtml(String(call.status))})` : "";
        const durationLabel = elapsed ? ` \u2014 ${elapsed}` : "";
        return `<li><strong>${kind}</strong> ${endpoint}${durationLabel}${status}</li>`;
      }).join("");
      html += `<details class="report-meta-details">
          <summary>Recent TestRail calls</summary>
          <ul class="report-meta-calls">${items}</ul>
        </details>`;
    }
    container.innerHTML = html;
  }
  function formatStage(job) {
    const meta = (job == null ? void 0 : job.meta) || {};
    const stage = meta.stage;
    const payload = meta.stage_payload || {};
    if (!stage) return null;
    switch (stage) {
      case "processing_run":
        if (payload.run_id) {
          const idx = payload.index || 0;
          const total = payload.total || "?";
          return `Processing run ${payload.run_id} (${idx}/${total})\u2026`;
        }
        return "Processing runs\u2026";
      case "fetching_attachment_metadata":
        return `Fetching attachment metadata (${payload.count || 0})\u2026`;
      case "downloading_attachments":
        return `Downloading attachments (${payload.total || 0} items)\u2026`;
      case "downloading_attachment":
        if (payload.total) {
          return `Downloading attachment ${payload.current || 0}/${payload.total}\u2026`;
        }
        return "Downloading attachments\u2026";
      case "rendering_report":
        return "Rendering HTML report\u2026";
      case "initializing":
        return "Starting report job\u2026";
      default:
        return null;
    }
  }
  function jobStatusLabel(job) {
    if (!job || !job.status) {
      return "Generating report\u2026";
    }
    const stageMessage = formatStage(job);
    if (stageMessage) {
      return stageMessage;
    }
    if (job.status === "queued") {
      if (typeof job.queue_position === "number") {
        if (job.queue_position === 0) {
          return "Queued\u2026 almost ready";
        }
        return `Queued\u2026 ${job.queue_position} ahead of you`;
      }
      return "Queued\u2026";
    }
    if (job.status === "running") {
      return "Generating report\u2026";
    }
    return "Working\u2026";
  }
  function deriveProgress(job) {
    const meta = (job == null ? void 0 : job.meta) || {};
    const updates = Array.isArray(meta.progress_updates) ? meta.progress_updates : [];
    const fallbackStage = meta.stage ? { stage: meta.stage, payload: meta.stage_payload || {} } : null;
    const latest = updates.length ? updates[updates.length - 1] : fallbackStage;
    let totalRuns = 1;
    let currentRunIndex = 1;
    for (let i = updates.length - 1; i >= 0; i -= 1) {
      const upd = updates[i];
      if (upd && upd.stage === "processing_run") {
        const payload2 = upd.payload || {};
        const t = Number(payload2.total);
        const idx = Number(payload2.index);
        if (Number.isFinite(t) && t > 0) {
          totalRuns = t;
        }
        if (Number.isFinite(idx) && idx > 0) {
          currentRunIndex = idx;
        }
        break;
      }
    }
    if (latest && (!updates.length || currentRunIndex === 1)) {
      const p = latest.payload || {};
      const t = Number(p.total);
      const idx = Number(p.index);
      if (Number.isFinite(t) && t > 0) {
        totalRuns = t;
      }
      if (Number.isFinite(idx) && idx > 0) {
        currentRunIndex = idx;
      }
    }
    const stage = latest == null ? void 0 : latest.stage;
    const payload = (latest == null ? void 0 : latest.payload) || {};
    if ((job == null ? void 0 : job.status) === "queued") {
      const pct = typeof job.queue_position === "number" && job.queue_position === 0 ? 5 : 2;
      return { percent: pct, label: jobStatusLabel(job), etaMs: null };
    }
    if ((job == null ? void 0 : job.status) === "error") {
      return { percent: 100, label: jobStatusLabel(job), etaMs: null };
    }
    if ((job == null ? void 0 : job.status) === "success") {
      return { percent: 100, label: "Report ready", etaMs: 0 };
    }
    const basePerRun = 1 / Math.max(1, totalRuns);
    const completedRunsPortion = Math.max(0, currentRunIndex - 1) * basePerRun;
    let stageFractionWithinRun = 0.05;
    if (stage === "processing_run" || stage === "initializing") {
      stageFractionWithinRun = 0.05;
    } else if (stage === "fetching_attachment_metadata") {
      stageFractionWithinRun = 0.18;
    } else if (stage === "downloading_attachments") {
      const totalItems = Number(payload.total);
      if (Number.isFinite(totalItems) && totalItems > 0) {
        stageFractionWithinRun = 0.2;
      } else {
        stageFractionWithinRun = 0.25;
      }
    } else if (stage === "downloading_attachment") {
      const cur = Number(payload.current);
      const tot = Number(payload.total);
      if (Number.isFinite(cur) && Number.isFinite(tot) && tot > 0) {
        stageFractionWithinRun = 0.2 + Math.min(1, cur / tot) * 0.65;
      } else {
        stageFractionWithinRun = 0.3;
      }
    } else if (stage === "rendering_report") {
      stageFractionWithinRun = 0.95;
    }
    const progressFraction = Math.min(0.995, completedRunsPortion + stageFractionWithinRun * basePerRun);
    const percent = Math.round(progressFraction * 100);
    let etaMs = null;
    const startedAt = (job == null ? void 0 : job.started_at) ? Date.parse(job.started_at) : null;
    if (Number.isFinite(startedAt) && startedAt > 0) {
      const elapsedMs = Date.now() - startedAt;
      if (elapsedMs > 5e3 && progressFraction > 0.05) {
        const projectedTotal = elapsedMs / progressFraction;
        etaMs = Math.max(0, projectedTotal - elapsedMs);
      }
    }
    return { percent, label: jobStatusLabel(job), etaMs };
  }
  var startReportJob = (payload) => requestJson("/api/report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  var fetchJob = (jobId) => requestJson(`/api/report/${encodeURIComponent(jobId)}`);
  async function submitPlanForm(event) {
    var _a, _b, _c, _d, _e;
    event.preventDefault();
    const payload = {
      project: parseIntMaybe((_a = document.getElementById("planProject")) == null ? void 0 : _a.value) || 1,
      name: (_b = document.getElementById("planName")) == null ? void 0 : _b.value.trim(),
      description: ((_c = document.getElementById("planDesc")) == null ? void 0 : _c.value.trim()) || null,
      milestone_id: parseIntMaybe((_d = document.getElementById("planMilestone")) == null ? void 0 : _d.value)
    };
    if (!payload.name) {
      showToast("Plan name is required.", "error");
      return;
    }
    try {
      const data = await requestJson("/api/manage/plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const planId = (_e = data == null ? void 0 : data.plan) == null ? void 0 : _e.id;
      const planName = payload.name;
      showToast(`Plan "${planName}" created successfully`, "success");
      const nameEl = document.getElementById("planName");
      const descEl = document.getElementById("planDesc");
      const milestoneEl = document.getElementById("planMilestone");
      if (nameEl) nameEl.value = "";
      if (descEl) descEl.value = "";
      if (milestoneEl) milestoneEl.value = "";
      await refreshPlanList();
    } catch (err) {
      showToast((err == null ? void 0 : err.message) || "Failed to create plan", "error");
    }
  }
  async function submitRunForm(event) {
    var _a, _b, _c, _d, _e, _f, _g, _h, _i;
    event.preventDefault();
    const includeAll = (_b = (_a = document.getElementById("runIncludeAll")) == null ? void 0 : _a.checked) != null ? _b : true;
    const payload = {
      project: parseIntMaybe((_c = document.getElementById("runProject")) == null ? void 0 : _c.value) || 1,
      plan_id: parseIntMaybe((_d = document.getElementById("runPlanSelect")) == null ? void 0 : _d.value),
      name: (_e = document.getElementById("runName")) == null ? void 0 : _e.value.trim(),
      description: ((_f = document.getElementById("runDesc")) == null ? void 0 : _f.value.trim()) || null,
      refs: ((_g = document.getElementById("runRefs")) == null ? void 0 : _g.value.trim()) || null,
      include_all: includeAll
    };
    const manualCaseIds = parseIdList(((_h = document.getElementById("runCaseIds")) == null ? void 0 : _h.value) || "");
    const combinedCaseIds = Array.from(/* @__PURE__ */ new Set([...Array.from(getSelectedCases()), ...manualCaseIds])).filter(
      (id) => Number.isFinite(id)
    );
    if (!payload.name) {
      showToast("Run name is required.", "error");
      return;
    }
    if (combinedCaseIds.length) {
      payload.include_all = false;
      payload.case_ids = combinedCaseIds;
    }
    if (!payload.include_all && (!payload.case_ids || payload.case_ids.length === 0)) {
      showToast("Provide case IDs or select include all.", "error");
      return;
    }
    try {
      const data = await requestJson("/api/manage/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const runId = (_i = data == null ? void 0 : data.run) == null ? void 0 : _i.id;
      const runName = payload.name;
      showToast(`Run "${runName}" created successfully`, "success");
      const runNameEl = document.getElementById("runName");
      const runDesc = document.getElementById("runDesc");
      const runRefs = document.getElementById("runRefs");
      const runCaseIds = document.getElementById("runCaseIds");
      if (runNameEl) runNameEl.value = "";
      if (runDesc) runDesc.value = "";
      if (runRefs) runRefs.value = "";
      if (runCaseIds) runCaseIds.value = "";
      resetSelectedCases();
      updateCasePickerStatus();
      applySelectionToList();
    } catch (err) {
      showToast((err == null ? void 0 : err.message) || "Failed to create run", "error");
    }
  }
  async function submitCaseForm(event) {
    var _a, _b, _c, _d, _e;
    event.preventDefault();
    const payload = {
      project: parseIntMaybe((_a = document.getElementById("caseProject")) == null ? void 0 : _a.value) || 1,
      title: (_b = document.getElementById("caseTitle")) == null ? void 0 : _b.value.trim(),
      refs: ((_c = document.getElementById("caseRefs")) == null ? void 0 : _c.value.trim()) || null,
      bdd_scenarios: ((_d = document.getElementById("caseBdd")) == null ? void 0 : _d.value.trim()) || null
    };
    if (!payload.title) {
      showToast("Case title is required.", "error");
      return;
    }
    try {
      const data = await requestJson("/api/manage/case", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const caseId = (_e = data == null ? void 0 : data.case) == null ? void 0 : _e.id;
      const caseTitle = payload.title;
      showToast(`Case "${caseTitle}" created successfully`, "success");
      const caseTitleEl = document.getElementById("caseTitle");
      const caseRefs = document.getElementById("caseRefs");
      const caseBdd = document.getElementById("caseBdd");
      if (caseTitleEl) caseTitleEl.value = "";
      if (caseRefs) caseRefs.value = "";
      if (caseBdd) caseBdd.value = "";
    } catch (err) {
      showToast((err == null ? void 0 : err.message) || "Failed to create case", "error");
    }
  }
  var SmoothProgress = class {
    constructor(wrapEl, fillEl, valueEl) {
      __publicField(this, "wrapEl");
      __publicField(this, "fillEl");
      __publicField(this, "valueEl");
      __publicField(this, "current");
      __publicField(this, "target");
      __publicField(this, "_raf");
      this.wrapEl = wrapEl;
      this.fillEl = fillEl;
      this.valueEl = valueEl;
      this.current = 0;
      this.target = 0;
      this._raf = null;
    }
    _step() {
      const diff = this.target - this.current;
      const delta = Math.sign(diff) * Math.max(0.25, Math.abs(diff) * 0.18);
      this.current = this.current + delta;
      if (diff > 0 && this.current >= this.target || diff < 0 && this.current <= this.target) {
        this.current = this.target;
      }
      if (this.fillEl) {
        this.fillEl.style.width = `${Math.round(this.current)}%`;
      }
      if (this.valueEl) {
        this.valueEl.textContent = `${Math.round(this.current)}%`;
      }
      if (Math.abs(this.current - this.target) > 0.5) {
        this._raf = requestAnimationFrame(this._step.bind(this));
      }
    }
    set(pct) {
      if (!this.wrapEl || !this.fillEl || !this.valueEl) {
        return;
      }
      const clamped = Math.max(0, Math.min(100, pct));
      this.wrapEl.style.display = "flex";
      this.target = clamped;
      if (this._raf) {
        cancelAnimationFrame(this._raf);
      }
      this._raf = requestAnimationFrame(this._step.bind(this));
    }
    hide() {
      if (this._raf) {
        cancelAnimationFrame(this._raf);
      }
      this._raf = null;
      this.target = 0;
      this.current = 0;
      if (this.wrapEl) {
        this.wrapEl.style.display = "none";
      }
      if (this.fillEl) {
        this.fillEl.style.width = "0%";
      }
      if (this.valueEl) {
        this.valueEl.textContent = "";
      }
    }
  };
  function init() {
    var _a, _b, _c, _d, _e, _f, _g, _h, _i, _j, _k, _l, _m, _n, _o, _p, _q, _r, _s;
    setupThemeToggle();
    updateReportMeta(void 0);
    loadPlans().catch((err) => console.error("loadPlans error", err));
    loadManagePlans().catch((err) => console.error("loadManagePlans error", err));
    initManagement();
    window.initManageView = initManageView;
    const runSearch = document.getElementById("runSearch");
    if (runSearch) {
      runSearch.addEventListener("input", filterRuns);
    }
    const planSel = document.getElementById("plan");
    planSel == null ? void 0 : planSel.addEventListener("change", loadRuns);
    const projectInput = document.getElementById("project");
    projectInput == null ? void 0 : projectInput.addEventListener("input", () => loadPlans());
    const selectAllBtn = document.getElementById("runSelectAll");
    const clearAllBtn = document.getElementById("runClearAll");
    selectAllBtn == null ? void 0 : selectAllBtn.addEventListener("click", () => {
      setRunSelections(true);
      filterRuns();
    });
    clearAllBtn == null ? void 0 : clearAllBtn.addEventListener("click", () => {
      setRunSelections(false);
      filterRuns();
    });
    const refreshReportPlansBtn = document.getElementById("refreshReportPlansBtn");
    refreshReportPlansBtn == null ? void 0 : refreshReportPlansBtn.addEventListener("click", () => loadPlans(true));
    const refreshManagePlansBtn = document.getElementById("refreshManagePlansBtn");
    refreshManagePlansBtn == null ? void 0 : refreshManagePlansBtn.addEventListener("click", () => loadManagePlans(true));
    (_a = document.getElementById("casePickerToggle")) == null ? void 0 : _a.addEventListener("click", openCasePicker);
    (_b = document.getElementById("caseSearch")) == null ? void 0 : _b.addEventListener("input", filterCases);
    (_c = document.getElementById("caseRefreshBtn")) == null ? void 0 : _c.addEventListener("click", () => loadCases(true));
    (_d = document.getElementById("caseSelectVisibleBtn")) == null ? void 0 : _d.addEventListener("click", () => selectVisibleCases(true));
    (_e = document.getElementById("caseClearSelectionBtn")) == null ? void 0 : _e.addEventListener("click", clearCaseSelection);
    (_f = document.getElementById("caseList")) == null ? void 0 : _f.addEventListener("change", handleCaseCheckboxChange);
    (_g = document.getElementById("casePickerDone")) == null ? void 0 : _g.addEventListener("click", closeCasePicker);
    (_h = document.getElementById("casePickerClose")) == null ? void 0 : _h.addEventListener("click", closeCasePicker);
    (_i = document.getElementById("casePickerModal")) == null ? void 0 : _i.addEventListener("click", (e) => {
      var _a2;
      if (((_a2 = e.target) == null ? void 0 : _a2.id) === "casePickerModal") {
        closeCasePicker();
      }
    });
    (_j = document.getElementById("runCaseIds")) == null ? void 0 : _j.addEventListener("input", () => {
      var _a2;
      const text = ((_a2 = document.getElementById("runCaseIds")) == null ? void 0 : _a2.value) || "";
      resetSelectedCases();
      parseIdList(text).forEach((id) => getSelectedCases().add(id));
      updateCasePickerStatus();
      applySelectionToList();
    });
    (_k = document.getElementById("planCreateForm")) == null ? void 0 : _k.addEventListener("submit", submitPlanForm);
    (_l = document.getElementById("runCreateForm")) == null ? void 0 : _l.addEventListener("submit", submitRunForm);
    (_m = document.getElementById("caseCreateForm")) == null ? void 0 : _m.addEventListener("submit", submitCaseForm);
    (_n = document.getElementById("linkReporter")) == null ? void 0 : _n.addEventListener("click", (e) => {
      e.preventDefault();
      switchView("reporter");
    });
    (_o = document.getElementById("linkDashboard")) == null ? void 0 : _o.addEventListener("click", (e) => {
      e.preventDefault();
      switchView("dashboard");
    });
    (_p = document.getElementById("linkManage")) == null ? void 0 : _p.addEventListener("click", (e) => {
      e.preventDefault();
      switchView("manage");
    });
    (_q = document.getElementById("linkHowTo")) == null ? void 0 : _q.addEventListener("click", (e) => {
      e.preventDefault();
      switchView("howto");
    });
    (_r = document.getElementById("runProject")) == null ? void 0 : _r.addEventListener("change", () => {
      loadManagePlans();
    });
    (_s = document.getElementById("caseProject")) == null ? void 0 : _s.addEventListener("change", () => {
      loadManagePlans();
    });
    document.querySelectorAll(".panel-toggle").forEach((btn) => {
      const panelId = btn.getAttribute("data-panel");
      if (!panelId) return;
      btn.addEventListener("click", () => togglePanel(panelId));
      togglePanel(panelId, "close");
    });
    const form = document.querySelector("#reporterView .card form");
    const overlay = document.getElementById("loadingOverlay");
    const overlayText = document.getElementById("loadingOverlayText");
    const progressWrap = document.getElementById("loadingProgress");
    const progressFill = document.getElementById("loadingProgressFill");
    const progressValue = document.getElementById("loadingProgressValue");
    let activeJob = null;
    const progressBar = new SmoothProgress(progressWrap, progressFill, progressValue);
    const applyProgress = (progress) => {
      if (progress && typeof progress.percent === "number") {
        progressBar.set(progress.percent);
      } else {
        progressBar.hide();
      }
    };
    const setLoading = (state, message, progress) => {
      const btn = document.getElementById("previewReportBtn");
      if (!btn || !overlay || !overlayText) return;
      if (state) {
        overlay.style.display = "flex";
        let displayMessage = message || "Generating report\u2026";
        if (progress && typeof progress.etaMs === "number") {
          const etaLabel = formatDuration(progress.etaMs);
          if (etaLabel) {
            displayMessage += ` (~${etaLabel} remaining)`;
          }
        }
        overlayText.textContent = displayMessage;
        applyProgress(progress || null);
        btn.disabled = true;
        if (!btn.dataset.originalText) {
          btn.dataset.originalText = btn.textContent || "";
        }
        btn.textContent = "Generating\u2026";
      } else {
        overlay.style.display = "none";
        overlayText.textContent = "Generating report\u2026";
        applyProgress(null);
        btn.disabled = false;
        if (btn.dataset.originalText) {
          btn.textContent = btn.dataset.originalText;
          delete btn.dataset.originalText;
        }
      }
    };
    const pollJob = async (jobId) => {
      let attempt = 0;
      while (true) {
        const job = await fetchJob(jobId);
        activeJob = job;
        const progress = deriveProgress(job);
        if (job.status === "success" || job.status === "error") {
          return job;
        }
        setLoading(true, progress.label, progress);
        await new Promise((resolve) => setTimeout(resolve, Math.min(5e3, 1200 + attempt * 200)));
        attempt += 1;
      }
    };
    const openReportUrl = (reportUrl) => {
      try {
        const win = window.open(reportUrl, "_blank");
        if (!win) {
          window.location.href = reportUrl;
          showToast("Pop-up blocked by browser. Report opened in this tab instead.", "info");
        } else {
          win.focus();
        }
      } catch (err) {
        window.location.href = reportUrl;
        showToast("Browser blocked pop-ups. Report opened in this tab.", "info");
      }
    };
    const handleJobSuccess = (job) => {
      const reportUrl = job == null ? void 0 : job.url;
      if (!reportUrl) {
        throw new Error("Server response missing report URL.");
      }
      openReportUrl(reportUrl);
      const meta = (job == null ? void 0 : job.meta) || {};
      updateReportMeta(meta, (job == null ? void 0 : job.params) || {});
      const summaryBits = [];
      if (typeof meta.duration_ms === "number") {
        summaryBits.push(`${(meta.duration_ms / 1e3).toFixed(1)}s`);
      }
      if (typeof meta.api_call_count === "number") {
        summaryBits.push(`${meta.api_call_count} API call${meta.api_call_count === 1 ? "" : "s"}`);
      }
      if (meta.generated_at) {
        summaryBits.push(new Date(meta.generated_at).toLocaleString());
      }
      const suffix = summaryBits.length ? ` (${summaryBits.join(" \xB7 ")})` : "";
      showToast(`Report ready${suffix}.`, "success");
    };
    const handlePreviewSubmit = async (event) => {
      event.preventDefault();
      if (!ensurePlanSelected() || !ensureRunSelection()) {
        return;
      }
      const formData = new FormData(form || void 0);
      const projectValue = String(formData.get("project") || "").trim() || "1";
      const planValue = String(formData.get("plan") || "").trim();
      const selectedRuns = formData.getAll("run_ids").map((val) => String(val || "").trim()).filter(Boolean).map((val) => Number(val));
      const projectNumber = Number(projectValue);
      const planNumber = planValue ? Number(planValue) : null;
      const cleanedRuns = selectedRuns.filter((num) => Number.isFinite(num));
      const payload = {
        project: Number.isFinite(projectNumber) ? projectNumber : 1,
        plan: Number.isFinite(planNumber) ? planNumber : null,
        run: null,
        run_ids: cleanedRuns.length ? cleanedRuns : null
      };
      try {
        setLoading(true, "Submitting report request\u2026", { percent: 5 });
        const job = await startReportJob(payload);
        activeJob = job;
        if (job.status === "success") {
          setLoading(true, "Opening report\u2026", { percent: 100 });
          handleJobSuccess(job);
          return;
        }
        if (job.status === "error") {
          throw new Error(job.error || "Report job failed.");
        }
        if (!job.id) {
          throw new Error("Server did not provide a job id.");
        }
        showToast("Report queued. Large plans may take up to a minute.", "info");
        const initialProgress = deriveProgress(job);
        setLoading(true, initialProgress.label, initialProgress);
        const finalJob = await pollJob(job.id);
        if (finalJob.status === "error") {
          throw new Error(finalJob.error || "Report generation failed.");
        }
        setLoading(true, "Opening report\u2026", { percent: 100 });
        handleJobSuccess(finalJob);
      } catch (error) {
        const message = (error == null ? void 0 : error.message) || "Failed to generate report.";
        showToast(`Failed to generate report: ${message}`, "error");
      } finally {
        setLoading(false);
        activeJob = null;
      }
    };
    form == null ? void 0 : form.addEventListener("submit", handlePreviewSubmit);
    filterRuns();
    document.addEventListener("visibilitychange", function() {
      if (document.visibilityState === "visible" && activeJob && activeJob.status !== "success" && activeJob.status !== "error") {
        const progress = deriveProgress(activeJob);
        setLoading(true, progress.label, progress);
      }
    });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
