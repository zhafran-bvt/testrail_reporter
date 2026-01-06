/* eslint-disable @typescript-eslint/no-explicit-any */
import { setupThemeToggle } from "./theme";
import { switchView, togglePanel } from "./views";
import {
  showToast,
  requestJson,
  parseIdList,
  parseIntMaybe,
  formatDuration,
  escapeHtml,
} from "./utils";
import {
  formatRelativeTime,
  formatAbsoluteTime,
  createTimeElement,
  updateAllTimeElements,
  startTimeUpdates,
  getStartOfToday,
  getStartOfWeek,
  getStartOfMonth,
} from "./timeUtils";
import { undoManager, createDeleteAction, createBulkDeleteAction, createUpdateAction, showUndoToast } from "./undoManager";
import { filterManager, applyFilter, createFilterFromState, getFilterDescription } from "./filterManager";
import {
  loadPlans,
  loadManagePlans,
  loadRuns,
  ensurePlanSelected,
  ensureRunSelection,
  setRunSelections,
  filterRuns,
} from "./plansRuns";
import {
  openCasePicker,
  closeCasePicker,
  filterCases,
  loadCases,
  handleCaseCheckboxChange,
  selectVisibleCases,
  clearCaseSelection,
  updateCasePickerStatus,
  applySelectionToList,
  updateCaseCount,
  resetSelectedCases,
  getSelectedCases,
} from "./casePicker";
import { ReportJob, ReportJobMeta } from "./types";
import { initManagement, initManageView, refreshPlanList } from "./manage";

function updateReportMeta(meta: ReportJobMeta | undefined, params?: any) {
  const container = document.getElementById("reportMeta");
  if (!container) {
    return;
  }
  if (!meta || Object.keys(meta).length === 0) {
    container.innerHTML = '<p class="report-meta-summary">No report generated yet.</p>';
    return;
  }
  const generated = meta.generated_at ? new Date(meta.generated_at).toLocaleString() : "just now";
  const durationText = typeof meta.duration_ms === "number" ? `${(meta.duration_ms / 1000).toFixed(1)}s` : null;
  const callCount = typeof meta.api_call_count === "number" ? meta.api_call_count : null;
  const scopeLabel = params?.plan ? `Plan ${params.plan}` : params?.run ? `Run ${params.run}` : "";
  const summaryParts: string[] = [];
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
  const safeSummary = summaryParts.map((part) => escapeHtml(part)).join(" · ");
  let html = `<p class="report-meta-summary">${safeSummary}</p>`;
  const recentCalls = Array.isArray(meta.api_calls) ? meta.api_calls.slice(-10) : [];
  if (recentCalls.length) {
    const items = recentCalls
      .map((call) => {
        const kind = escapeHtml(String(call?.kind || "GET"));
        const endpoint = escapeHtml(String(call?.endpoint || ""));
        const elapsed = typeof call?.elapsed_ms === "number" ? `${call.elapsed_ms.toFixed(1)} ms` : "";
        const status = call?.status ? ` (${escapeHtml(String(call.status))})` : "";
        const durationLabel = elapsed ? ` — ${elapsed}` : "";
        return `<li><strong>${kind}</strong> ${endpoint}${durationLabel}${status}</li>`;
      })
      .join("");
    html += `<details class="report-meta-details">
          <summary>Recent TestRail calls</summary>
          <ul class="report-meta-calls">${items}</ul>
        </details>`;
  }
  container.innerHTML = html;
}

function formatStage(job: ReportJob) {
  const meta: any = job?.meta || {};
  const stage = meta.stage;
  const payload = meta.stage_payload || {};
  if (!stage) return null;
  switch (stage) {
    case "processing_run":
      if (payload.run_id) {
        const idx = payload.index || 0;
        const total = payload.total || "?";
        return `Processing run ${payload.run_id} (${idx}/${total})…`;
      }
      return "Processing runs…";
    case "fetching_attachment_metadata":
      return `Fetching attachment metadata (${payload.count || 0})…`;
    case "downloading_attachments":
      return `Downloading attachments (${payload.total || 0} items)…`;
    case "downloading_attachment":
      if (payload.total) {
        return `Downloading attachment ${payload.current || 0}/${payload.total}…`;
      }
      return "Downloading attachments…";
    case "rendering_report":
      return "Rendering HTML report…";
    case "initializing":
      return "Starting report job…";
    default:
      return null;
  }
}

function jobStatusLabel(job: ReportJob): string {
  if (!job || !job.status) {
    return "Generating report…";
  }
  const stageMessage = formatStage(job);
  if (stageMessage) {
    return stageMessage;
  }
  if (job.status === "queued") {
    if (typeof job.queue_position === "number") {
      if (job.queue_position === 0) {
        return "Queued… almost ready";
      }
      return `Queued… ${job.queue_position} ahead of you`;
    }
    return "Queued…";
  }
  if (job.status === "running") {
    return "Generating report…";
  }
  return "Working…";
}

function deriveProgress(job: ReportJob) {
  const meta: any = job?.meta || {};
  const updates = Array.isArray(meta.progress_updates) ? meta.progress_updates : [];
  const fallbackStage = meta.stage ? { stage: meta.stage, payload: meta.stage_payload || {} } : null;
  const latest = updates.length ? updates[updates.length - 1] : fallbackStage;
  let totalRuns = 1;
  let currentRunIndex = 1;

  for (let i = updates.length - 1; i >= 0; i -= 1) {
    const upd = updates[i];
    if (upd && upd.stage === "processing_run") {
      const payload = upd.payload || {};
      const t = Number(payload.total);
      const idx = Number(payload.index);
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
    const p = (latest as any).payload || {};
    const t = Number(p.total);
    const idx = Number(p.index);
    if (Number.isFinite(t) && t > 0) {
      totalRuns = t;
    }
    if (Number.isFinite(idx) && idx > 0) {
      currentRunIndex = idx;
    }
  }

  const stage = (latest as any)?.stage;
  const payload = (latest as any)?.payload || {};
  if (job?.status === "queued") {
    const pct = typeof job.queue_position === "number" && job.queue_position === 0 ? 5 : 2;
    return { percent: pct, label: jobStatusLabel(job), etaMs: null };
  }
  if (job?.status === "error") {
    return { percent: 100, label: jobStatusLabel(job), etaMs: null };
  }
  if (job?.status === "success") {
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

  let etaMs: number | null = null;
  const startedAt = job?.started_at ? Date.parse(job.started_at) : null;
  if (Number.isFinite(startedAt) && (startedAt as number) > 0) {
    const elapsedMs = Date.now() - (startedAt as number);
    if (elapsedMs > 5000 && progressFraction > 0.05) {
      const projectedTotal = elapsedMs / progressFraction;
      etaMs = Math.max(0, projectedTotal - elapsedMs);
    }
  }

  return { percent, label: jobStatusLabel(job), etaMs };
}

const startReportJob = (payload: any) =>
  requestJson<ReportJob>("/api/report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

const fetchJob = (jobId: string) => requestJson<ReportJob>(`/api/report/${encodeURIComponent(jobId)}`);

async function submitPlanForm(event: Event) {
  event.preventDefault();
  const payload = {
    project: parseIntMaybe((document.getElementById("planProject") as HTMLInputElement | null)?.value) || 1,
    name: (document.getElementById("planName") as HTMLInputElement | null)?.value.trim(),
    description: (document.getElementById("planDesc") as HTMLTextAreaElement | null)?.value.trim() || null,
    milestone_id: parseIntMaybe((document.getElementById("planMilestone") as HTMLInputElement | null)?.value),
  };
  if (!payload.name) {
    showToast("Plan name is required.", "error");
    return;
  }
  try {
    const data = await requestJson<{ plan?: { id?: number } }>("/api/manage/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const planId = data?.plan?.id;
    const planName = payload.name;
    
    // Show success toast with entity name (Requirement 6.4)
    showToast(`Plan "${planName}" created successfully`, "success");
    
    // Clear form fields (Requirement 6.4)
    const nameEl = document.getElementById("planName") as HTMLInputElement | null;
    const descEl = document.getElementById("planDesc") as HTMLTextAreaElement | null;
    const milestoneEl = document.getElementById("planMilestone") as HTMLInputElement | null;
    if (nameEl) nameEl.value = "";
    if (descEl) descEl.value = "";
    if (milestoneEl) milestoneEl.value = "";
    
    // Refresh corresponding Manage subsection (Requirement 6.4)
    await refreshPlanList();
    
    // Keep Create section expanded for additional creations (Requirement 6.5)
    // The section is already expanded if the user is submitting the form
    // No action needed - it stays expanded by default
  } catch (err: any) {
    showToast(err?.message || "Failed to create plan", "error");
  }
}

async function submitRunForm(event: Event) {
  event.preventDefault();
  const includeAll = (document.getElementById("runIncludeAll") as HTMLInputElement | null)?.checked ?? true;
  const payload: any = {
    project: parseIntMaybe((document.getElementById("runProject") as HTMLInputElement | null)?.value) || 1,
    plan_id: parseIntMaybe((document.getElementById("runPlanSelect") as HTMLSelectElement | null)?.value),
    name: (document.getElementById("runName") as HTMLInputElement | null)?.value.trim(),
    description: (document.getElementById("runDesc") as HTMLTextAreaElement | null)?.value.trim() || null,
    refs: (document.getElementById("runRefs") as HTMLInputElement | null)?.value.trim() || null,
    include_all: includeAll,
  };
  const manualCaseIds = parseIdList((document.getElementById("runCaseIds") as HTMLInputElement | null)?.value || "");
  const combinedCaseIds = Array.from(new Set<number>([...Array.from(getSelectedCases()), ...manualCaseIds])).filter((id) =>
    Number.isFinite(id)
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
    const data = await requestJson<{ run?: { id?: number } }>("/api/manage/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const runId = data?.run?.id;
    const runName = payload.name;
    
    // Show success toast with entity name (Requirement 6.4)
    showToast(`Run "${runName}" created successfully`, "success");
    
    // Clear form fields (Requirement 6.4)
    const runNameEl = document.getElementById("runName") as HTMLInputElement | null;
    const runDesc = document.getElementById("runDesc") as HTMLTextAreaElement | null;
    const runRefs = document.getElementById("runRefs") as HTMLInputElement | null;
    const runCaseIds = document.getElementById("runCaseIds") as HTMLInputElement | null;
    if (runNameEl) runNameEl.value = "";
    if (runDesc) runDesc.value = "";
    if (runRefs) runRefs.value = "";
    if (runCaseIds) runCaseIds.value = "";
    resetSelectedCases();
    updateCasePickerStatus();
    applySelectionToList();
    
    // Refresh removed - runs subsection no longer exists in hierarchical navigation
    
    // Keep Create section expanded for additional creations (Requirement 6.5)
    // The section is already expanded if the user is submitting the form
    // No action needed - it stays expanded by default
  } catch (err: any) {
    showToast(err?.message || "Failed to create run", "error");
  }
}

async function submitCaseForm(event: Event) {
  event.preventDefault();
  const payload = {
    project: parseIntMaybe((document.getElementById("caseProject") as HTMLInputElement | null)?.value) || 1,
    title: (document.getElementById("caseTitle") as HTMLInputElement | null)?.value.trim(),
    refs: (document.getElementById("caseRefs") as HTMLInputElement | null)?.value.trim() || null,
    bdd_scenarios: (document.getElementById("caseBdd") as HTMLTextAreaElement | null)?.value.trim() || null,
  };
  if (!payload.title) {
    showToast("Case title is required.", "error");
    return;
  }
  try {
    const data = await requestJson<{ case?: { id?: number } }>("/api/manage/case", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const caseId = data?.case?.id;
    const caseTitle = payload.title;
    
    // Show success toast with entity name (Requirement 6.4)
    showToast(`Case "${caseTitle}" created successfully`, "success");
    
    // Clear form fields (Requirement 6.4)
    const caseTitleEl = document.getElementById("caseTitle") as HTMLInputElement | null;
    const caseRefs = document.getElementById("caseRefs") as HTMLInputElement | null;
    const caseBdd = document.getElementById("caseBdd") as HTMLTextAreaElement | null;
    if (caseTitleEl) caseTitleEl.value = "";
    if (caseRefs) caseRefs.value = "";
    if (caseBdd) caseBdd.value = "";
    
    // Refresh removed - cases subsection no longer exists in hierarchical navigation
    
    // Keep Create section expanded for additional creations (Requirement 6.5)
    // The section is already expanded if the user is submitting the form
    // No action needed - it stays expanded by default
  } catch (err: any) {
    showToast(err?.message || "Failed to create case", "error");
  }
}

class SmoothProgress {
  wrapEl: HTMLElement | null;
  fillEl: HTMLElement | null;
  valueEl: HTMLElement | null;
  current: number;
  target: number;
  _raf: number | null;
  constructor(wrapEl: HTMLElement | null, fillEl: HTMLElement | null, valueEl: HTMLElement | null) {
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
    if ((diff > 0 && this.current >= this.target) || (diff < 0 && this.current <= this.target)) {
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
  set(pct: number) {
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
}

function init() {
  setupThemeToggle();
  updateReportMeta(undefined);
  loadPlans().catch((err) => console.error("loadPlans error", err));
  loadManagePlans().catch((err) => console.error("loadManagePlans error", err));
  initManagement();
  
  // Expose initManageView globally for views.ts
  (window as any).initManageView = initManageView;

  const runSearch = document.getElementById("runSearch") as HTMLInputElement | null;
  if (runSearch) {
    runSearch.addEventListener("input", filterRuns);
  }
  const planSel = document.getElementById("plan") as HTMLSelectElement | null;
  planSel?.addEventListener("change", loadRuns);
  const projectInput = document.getElementById("project") as HTMLInputElement | null;
  projectInput?.addEventListener("input", () => loadPlans());

  const selectAllBtn = document.getElementById("runSelectAll");
  const clearAllBtn = document.getElementById("runClearAll");
  selectAllBtn?.addEventListener("click", () => {
    setRunSelections(true);
    filterRuns();
  });
  clearAllBtn?.addEventListener("click", () => {
    setRunSelections(false);
    filterRuns();
  });
  const refreshReportPlansBtn = document.getElementById("refreshReportPlansBtn");
  refreshReportPlansBtn?.addEventListener("click", () => loadPlans(true));
  const refreshManagePlansBtn = document.getElementById("refreshManagePlansBtn");
  refreshManagePlansBtn?.addEventListener("click", () => loadManagePlans(true));
  document.getElementById("casePickerToggle")?.addEventListener("click", openCasePicker);
  document.getElementById("caseSearch")?.addEventListener("input", filterCases);
  document.getElementById("caseRefreshBtn")?.addEventListener("click", () => loadCases(true));
  document.getElementById("caseSelectVisibleBtn")?.addEventListener("click", () => selectVisibleCases(true));
  document.getElementById("caseClearSelectionBtn")?.addEventListener("click", clearCaseSelection);
  document.getElementById("caseList")?.addEventListener("change", handleCaseCheckboxChange);
  document.getElementById("casePickerDone")?.addEventListener("click", closeCasePicker);
  document.getElementById("casePickerClose")?.addEventListener("click", closeCasePicker);
  document.getElementById("casePickerModal")?.addEventListener("click", (e) => {
    if ((e.target as HTMLElement)?.id === "casePickerModal") {
      closeCasePicker();
    }
  });
  document.getElementById("runCaseIds")?.addEventListener("input", () => {
    const text = (document.getElementById("runCaseIds") as HTMLInputElement | null)?.value || "";
    resetSelectedCases();
    parseIdList(text).forEach((id) => getSelectedCases().add(id));
    updateCasePickerStatus();
    applySelectionToList();
  });
  document.getElementById("planCreateForm")?.addEventListener("submit", submitPlanForm);
  document.getElementById("runCreateForm")?.addEventListener("submit", submitRunForm);
  document.getElementById("caseCreateForm")?.addEventListener("submit", submitCaseForm);
  document.getElementById("linkReporter")?.addEventListener("click", (e) => {
    e.preventDefault();
    switchView("reporter");
  });
  document.getElementById("linkDashboard")?.addEventListener("click", (e) => {
    e.preventDefault();
    switchView("dashboard");
  });
  document.getElementById("linkManage")?.addEventListener("click", (e) => {
    e.preventDefault();
    switchView("manage");
  });
  document.getElementById("linkHowTo")?.addEventListener("click", (e) => {
    e.preventDefault();
    switchView("howto");
  });
  document.getElementById("runProject")?.addEventListener("change", () => {
    loadManagePlans();
  });
  document.getElementById("caseProject")?.addEventListener("change", () => {
    loadManagePlans();
  });

  document.querySelectorAll<HTMLElement>(".panel-toggle").forEach((btn) => {
    const panelId = btn.getAttribute("data-panel");
    if (!panelId) return;
    btn.addEventListener("click", () => togglePanel(panelId));
    togglePanel(panelId, "close");
  });

  const form = document.querySelector<HTMLFormElement>("#reporterView .card form");
  const overlay = document.getElementById("loadingOverlay") as HTMLElement | null;
  const overlayText = document.getElementById("loadingOverlayText") as HTMLElement | null;
  const progressWrap = document.getElementById("loadingProgress") as HTMLElement | null;
  const progressFill = document.getElementById("loadingProgressFill") as HTMLElement | null;
  const progressValue = document.getElementById("loadingProgressValue") as HTMLElement | null;
  let activeJob: ReportJob | null = null;
  const progressBar = new SmoothProgress(progressWrap, progressFill, progressValue);

  const applyProgress = (progress: { percent?: number } | null) => {
    if (progress && typeof progress.percent === "number") {
      progressBar.set(progress.percent);
    } else {
      progressBar.hide();
    }
  };

  const setLoading = (state: boolean, message?: string, progress?: { percent?: number; etaMs?: number | null }) => {
    const btn = document.getElementById("previewReportBtn") as HTMLButtonElement | null;
    if (!btn || !overlay || !overlayText) return;
    if (state) {
      overlay.style.display = "flex";
      let displayMessage = message || "Generating report…";
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
      btn.textContent = "Generating…";
    } else {
      overlay.style.display = "none";
      overlayText.textContent = "Generating report…";
      applyProgress(null);
      btn.disabled = false;
      if (btn.dataset.originalText) {
        btn.textContent = btn.dataset.originalText;
        delete btn.dataset.originalText;
      }
    }
  };

  const pollJob = async (jobId: string): Promise<ReportJob> => {
    let attempt = 0;
    while (true) {
      const job = await fetchJob(jobId);
      activeJob = job;
      const progress = deriveProgress(job);
      if (job.status === "success" || job.status === "error") {
        return job;
      }
      setLoading(true, progress.label, progress as any);
      await new Promise((resolve) => setTimeout(resolve, Math.min(5000, 1200 + attempt * 200)));
      attempt += 1;
    }
  };

  const openReportUrl = (reportUrl: string) => {
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

  const handleJobSuccess = (job: ReportJob) => {
    const reportUrl = job?.url;
    if (!reportUrl) {
      throw new Error("Server response missing report URL.");
    }
    openReportUrl(reportUrl);
    const meta = job?.meta || {};
    updateReportMeta(meta, job?.params || {});
    const summaryBits: string[] = [];
    if (typeof meta.duration_ms === "number") {
      summaryBits.push(`${(meta.duration_ms / 1000).toFixed(1)}s`);
    }
    if (typeof meta.api_call_count === "number") {
      summaryBits.push(`${meta.api_call_count} API call${meta.api_call_count === 1 ? "" : "s"}`);
    }
    if (meta.generated_at) {
      summaryBits.push(new Date(meta.generated_at).toLocaleString());
    }
    const suffix = summaryBits.length ? ` (${summaryBits.join(" · ")})` : "";
    showToast(`Report ready${suffix}.`, "success");
  };

  const handlePreviewSubmit = async (event: Event) => {
    event.preventDefault();
    if (!ensurePlanSelected() || !ensureRunSelection()) {
      return;
    }
    const formData = new FormData(form || undefined);
    const projectValue = String(formData.get("project") || "").trim() || "1";
    const planValue = String(formData.get("plan") || "").trim();
    const selectedRuns = formData
      .getAll("run_ids")
      .map((val) => String(val || "").trim())
      .filter(Boolean)
      .map((val) => Number(val));
    const projectNumber = Number(projectValue);
    const planNumber = planValue ? Number(planValue) : null;
    const cleanedRuns = selectedRuns.filter((num) => Number.isFinite(num));
    const payload: any = {
      project: Number.isFinite(projectNumber) ? projectNumber : 1,
      plan: Number.isFinite(planNumber) ? planNumber : null,
      run: null,
      run_ids: cleanedRuns.length ? cleanedRuns : null,
    };

    try {
      setLoading(true, "Submitting report request…", { percent: 5 });
      const job = await startReportJob(payload);
      activeJob = job;
      if (job.status === "success") {
        setLoading(true, "Opening report…", { percent: 100 });
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
      setLoading(true, initialProgress.label, initialProgress as any);
      const finalJob = await pollJob(job.id);
      if (finalJob.status === "error") {
        throw new Error(finalJob.error || "Report generation failed.");
      }
      setLoading(true, "Opening report…", { percent: 100 });
      handleJobSuccess(finalJob);
    } catch (error: any) {
      const message = error?.message || "Failed to generate report.";
      showToast(`Failed to generate report: ${message}`, "error");
    } finally {
      setLoading(false);
      activeJob = null;
    }
  };

  form?.addEventListener("submit", handlePreviewSubmit);
  filterRuns();

  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible" && activeJob && activeJob.status !== "success" && activeJob.status !== "error") {
      const progress = deriveProgress(activeJob);
      setLoading(true, progress.label, progress as any);
    }
  });
}

// Export utilities globally for use in dashboard.js and other vanilla JS files
if (typeof window !== 'undefined') {
  (window as any).formatRelativeTime = formatRelativeTime;
  (window as any).formatAbsoluteTime = formatAbsoluteTime;
  (window as any).createTimeElement = createTimeElement;
  (window as any).updateAllTimeElements = updateAllTimeElements;
  (window as any).startTimeUpdates = startTimeUpdates;
  (window as any).getStartOfToday = getStartOfToday;
  (window as any).getStartOfWeek = getStartOfWeek;
  (window as any).getStartOfMonth = getStartOfMonth;
  (window as any).undoManager = undoManager;
  (window as any).createDeleteAction = createDeleteAction;
  (window as any).createBulkDeleteAction = createBulkDeleteAction;
  (window as any).createUpdateAction = createUpdateAction;
  (window as any).showUndoToast = showUndoToast;
  (window as any).filterManager = filterManager;
  (window as any).applyFilter = applyFilter;
  (window as any).createFilterFromState = createFilterFromState;
  (window as any).getFilterDescription = getFilterDescription;
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
