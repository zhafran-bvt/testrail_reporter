(() => {
  var __defProp = Object.defineProperty;
  var __defNormalProp = (obj, key, value) => key in obj ? __defProp(obj, key, { enumerable: true, configurable: true, writable: true, value }) : obj[key] = value;
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
    const linkReporter = document.getElementById("linkReporter");
    const linkManage = document.getElementById("linkManage");
    const linkHowto = document.getElementById("linkHowTo");
    reporter == null ? void 0 : reporter.classList.add("hidden");
    manage == null ? void 0 : manage.classList.add("hidden");
    howto == null ? void 0 : howto.classList.add("hidden");
    linkReporter == null ? void 0 : linkReporter.classList.remove("active");
    linkManage == null ? void 0 : linkManage.classList.remove("active");
    linkHowto == null ? void 0 : linkHowto.classList.remove("active");
    if (target === "manage") {
      manage == null ? void 0 : manage.classList.remove("hidden");
      linkManage == null ? void 0 : linkManage.classList.add("active");
    } else if (target === "howto") {
      howto == null ? void 0 : howto.classList.remove("hidden");
      linkHowto == null ? void 0 : linkHowto.classList.add("active");
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
      showToast(planId ? `Plan created: #${planId}` : "Plan created", "success");
      const nameEl = document.getElementById("planName");
      const descEl = document.getElementById("planDesc");
      const milestoneEl = document.getElementById("planMilestone");
      if (nameEl) nameEl.value = "";
      if (descEl) descEl.value = "";
      if (milestoneEl) milestoneEl.value = "";
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
      showToast(runId ? `Run created: #${runId}` : "Run created", "success");
      const runName = document.getElementById("runName");
      const runDesc = document.getElementById("runDesc");
      const runRefs = document.getElementById("runRefs");
      const runCaseIds = document.getElementById("runCaseIds");
      if (runName) runName.value = "";
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
      const msg = caseId ? `Case created: #${caseId}` : "Case created";
      showToast(msg, "success");
      togglePanel("casePanel", "close");
      const caseTitle = document.getElementById("caseTitle");
      const caseRefs = document.getElementById("caseRefs");
      const caseBdd = document.getElementById("caseBdd");
      if (caseTitle) caseTitle.value = "";
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
    var _a, _b, _c, _d, _e, _f, _g, _h, _i, _j, _k, _l, _m, _n, _o, _p, _q, _r;
    setupThemeToggle();
    updateReportMeta(void 0);
    loadPlans().catch((err) => console.error("loadPlans error", err));
    loadManagePlans().catch((err) => console.error("loadManagePlans error", err));
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
    const refreshPlansBtn = document.getElementById("refreshPlansBtn");
    refreshPlansBtn == null ? void 0 : refreshPlansBtn.addEventListener("click", () => loadPlans(true));
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
    (_o = document.getElementById("linkManage")) == null ? void 0 : _o.addEventListener("click", (e) => {
      e.preventDefault();
      switchView("manage");
    });
    (_p = document.getElementById("linkHowTo")) == null ? void 0 : _p.addEventListener("click", (e) => {
      e.preventDefault();
      switchView("howto");
    });
    (_q = document.getElementById("runProject")) == null ? void 0 : _q.addEventListener("change", () => {
      loadManagePlans();
    });
    (_r = document.getElementById("caseProject")) == null ? void 0 : _r.addEventListener("change", () => {
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
