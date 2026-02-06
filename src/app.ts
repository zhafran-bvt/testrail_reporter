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

    resetCreateWizard("planCreateForm");
    
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

    resetCreateWizard("runCreateForm");
    
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

    resetCreateWizard("caseCreateForm");
    
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

function formatSummaryText(value: string) {
  const cleaned = value.trim().replace(/\s+/g, " ");
  if (!cleaned) return "—";
  if (cleaned.length <= 120) return cleaned;
  return `${cleaned.slice(0, 117)}...`;
}

function formatBddSummary(value: string) {
  const cleaned = value.trim();
  if (!cleaned) return "—";
  const lines = cleaned.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (lines.length > 3) return `${lines.length} steps`;
  return formatSummaryText(lines.join(" / "));
}

function getWizardSummaryValue(form: HTMLFormElement, key: string) {
  if (key === "runScope") {
    const includeAll = (document.getElementById("runIncludeAll") as HTMLInputElement | null)?.checked ?? false;
    const manualIds = parseIdList((document.getElementById("runCaseIds") as HTMLInputElement | null)?.value || "");
    const selectedCount = getSelectedCases().size;
    const manualCount = manualIds.filter((id) => Number.isFinite(id)).length + selectedCount;
    if (manualCount > 0) {
      return `Manual selection (${manualCount} case${manualCount === 1 ? "" : "s"})`;
    }
    return includeAll ? "All cases" : "Manual selection";
  }

  if (key === "caseBdd") {
    const bddField = document.getElementById("caseBdd") as HTMLTextAreaElement | null;
    return bddField ? formatBddSummary(bddField.value) : "—";
  }

  const field = form.querySelector<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>(`#${key}`);
  if (!field) return "—";
  if (field instanceof HTMLSelectElement) {
    const option = field.selectedOptions[0];
    return option?.textContent?.trim() || option?.value || "—";
  }
  if (field instanceof HTMLInputElement && field.type === "checkbox") {
    return field.checked ? "Yes" : "No";
  }
  return formatSummaryText(field.value || "");
}

function updateWizardSummary(form: HTMLFormElement) {
  const summaryEls = Array.from(form.querySelectorAll<HTMLElement>("[data-summary]"));
  summaryEls.forEach((el) => {
    const key = el.dataset.summary;
    if (!key) return;
    el.textContent = getWizardSummaryValue(form, key);
  });
}

function validateWizardStep(stepContent: HTMLElement) {
  const fields = Array.from(stepContent.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>(
    "input, select, textarea"
  ));
  let isValid = true;
  let firstInvalid: HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement | null = null;

  fields.forEach((field) => {
    const required = field.hasAttribute("required") || field.getAttribute("aria-required") === "true";
    if (!required || field.disabled) {
      field.classList.remove("input-invalid");
      return;
    }
    if (!field.checkValidity()) {
      isValid = false;
      field.classList.add("input-invalid");
      if (!firstInvalid) firstInvalid = field;
    } else {
      field.classList.remove("input-invalid");
    }
  });

  if (firstInvalid) {
    firstInvalid.reportValidity();
  }
  return isValid;
}

function applyWizardStep(form: HTMLFormElement, step: number) {
  const steps = Array.from(form.querySelectorAll<HTMLElement>(".create-step-content"));
  const chips = Array.from(form.querySelectorAll<HTMLButtonElement>(".create-step-chip"));
  if (!steps.length || !chips.length) return;

  const totalSteps = steps.length;
  const nextStep = Math.max(1, Math.min(totalSteps, step));
  form.dataset.currentStep = String(nextStep);
  form.dataset.totalSteps = String(totalSteps);

  steps.forEach((content) => {
    const contentStep = Number(content.dataset.step || "0");
    content.classList.toggle("is-active", contentStep === nextStep);
  });

  chips.forEach((chip) => {
    const chipStep = Number(chip.dataset.step || "0");
    const isActive = chipStep === nextStep;
    chip.classList.toggle("is-active", isActive);
    chip.classList.toggle("is-complete", chipStep < nextStep);
    chip.setAttribute("aria-selected", isActive ? "true" : "false");
  });

  updateWizardSummary(form);
}

function initCreateWizards() {
  const forms = Array.from(document.querySelectorAll<HTMLFormElement>("form[data-wizard]"));
  forms.forEach((form) => {
    const steps = Array.from(form.querySelectorAll<HTMLElement>(".create-step-content"));
    const chips = Array.from(form.querySelectorAll<HTMLButtonElement>(".create-step-chip"));
    if (!steps.length || !chips.length) return;

    const getCurrentStep = () => Number(form.dataset.currentStep || "1");

    const goToStep = (step: number) => {
      applyWizardStep(form, step);
    };

    const goNext = () => {
      const currentStep = getCurrentStep();
      const currentContent = steps[currentStep - 1];
      if (!currentContent || !validateWizardStep(currentContent)) return;
      goToStep(currentStep + 1);
    };

    const goPrev = () => {
      const currentStep = getCurrentStep();
      goToStep(currentStep - 1);
    };

    form.querySelectorAll<HTMLElement>("[data-step-next]").forEach((btn) => {
      btn.addEventListener("click", (event) => {
        event.preventDefault();
        goNext();
      });
    });

    form.querySelectorAll<HTMLElement>("[data-step-prev]").forEach((btn) => {
      btn.addEventListener("click", (event) => {
        event.preventDefault();
        goPrev();
      });
    });

    chips.forEach((chip) => {
      chip.addEventListener("click", () => {
        const targetStep = Number(chip.dataset.step || "1");
        const currentStep = getCurrentStep();
        if (targetStep === currentStep) return;
        if (targetStep < currentStep) {
          goToStep(targetStep);
          return;
        }
        let canAdvance = true;
        for (let i = 0; i < targetStep - 1; i += 1) {
          if (!validateWizardStep(steps[i])) {
            canAdvance = false;
            break;
          }
        }
        if (canAdvance) {
          goToStep(targetStep);
        }
      });
    });

    form.addEventListener("submit", (event) => {
      const currentStep = getCurrentStep();
      if (currentStep < steps.length) {
        event.preventDefault();
        event.stopImmediatePropagation();
        goNext();
      }
    });

    form.addEventListener("input", (event) => {
      const target = event.target as HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement | null;
      if (target && "checkValidity" in target && target.classList.contains("input-invalid")) {
        if (target.checkValidity()) {
          target.classList.remove("input-invalid");
        }
      }
      updateWizardSummary(form);
    });

    form.addEventListener("change", () => updateWizardSummary(form));

    applyWizardStep(form, 1);
  });
}

function resetCreateWizard(formId: string) {
  const form = document.getElementById(formId) as HTMLFormElement | null;
  if (!form) return;
  form.querySelectorAll(".input-invalid").forEach((el) => el.classList.remove("input-invalid"));
  applyWizardStep(form, 1);
}

function initScopedTabs(container: Element | null) {
  if (!container) return;
  const tabButtons = Array.from(container.querySelectorAll<HTMLButtonElement>(".manage-tab"));
  const panels = Array.from(container.querySelectorAll<HTMLElement>(".manage-tab-panel"));
  if (!tabButtons.length || !panels.length) return;

  const activateTab = (button: HTMLButtonElement) => {
    const targetId = button.getAttribute("aria-controls");
    tabButtons.forEach((btn) => {
      const active = btn === button;
      btn.classList.toggle("is-active", active);
      btn.setAttribute("aria-selected", active ? "true" : "false");
    });
    panels.forEach((panel) => {
      panel.classList.toggle("is-active", panel.id === targetId);
    });
  };

  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => activateTab(btn));
  });
}

function focusCreateTabs() {
  const container = document.querySelector(".manage-create-tabs");
  if (!container) return;
  const planTab = container.querySelector<HTMLButtonElement>("#tabCreatePlan");
  if (planTab) {
    planTab.click();
    planTab.focus();
  }
  container.scrollIntoView({ behavior: "smooth", block: "start" });
}

function initManageTabs() {
  initScopedTabs(document.querySelector(".manage-create-tabs"));
  initScopedTabs(document.querySelector(".automation-tabs"));
}

function stripAutomationHtml(value: string) {
  const lowered = value.toLowerCase();
  if (!lowered.includes("<p") && !lowered.includes("<br") && !lowered.includes("</")) {
    return value;
  }
  let text = value.replace(/<br\s*\/?>/gi, "\n").replace(/<\/p>/gi, "\n").replace(/<\/div>/gi, "\n");
  text = text.replace(/<[^>]+>/g, "");
  const textarea = document.createElement("textarea");
  textarea.innerHTML = text;
  return textarea.value;
}

function stripJsonFence(value: string) {
  const trimmed = value.trim();
  const match = trimmed.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/i);
  if (match) {
    return match[1].trim();
  }
  return value;
}

function normalizeAutomationPayload(value: string, stripHtml: boolean) {
  let text = value;
  if (stripHtml) {
    text = stripAutomationHtml(text);
  }
  text = stripJsonFence(text);
  return text.trim();
}

function formatAutomationPayload(value: any) {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") {
    const normalized = normalizeAutomationPayload(value, true);
    if (!normalized) return "";
    try {
      return JSON.stringify(JSON.parse(normalized), null, 2);
    } catch {
      return normalized;
    }
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function parseAutomationPayload(text: string) {
  const normalized = normalizeAutomationPayload(text, false);
  if (!normalized) return "";
  try {
    return JSON.parse(normalized);
  } catch {
    return normalized;
  }
}

function initAutomationManagement() {
  type AutomationCaseListItem = {
    id: number;
    title: string;
    feature?: string;
    feature_path?: string;
    feature_group?: string;
    tags?: string[];
    method?: string;
    endpoint?: string;
  };

  const casesByType: Record<"api" | "web", AutomationCaseListItem[]> = { api: [], web: [] };
  const caseMaps: Record<"api" | "web", Map<number, AutomationCaseListItem>> = {
    api: new Map(),
    web: new Map(),
  };

  const apiSearch = document.getElementById("automationApiSearch") as HTMLInputElement | null;
  const webSearch = document.getElementById("automationWebSearch") as HTMLInputElement | null;
  const apiList = document.getElementById("automationApiCaseList");
  const webList = document.getElementById("automationWebCaseList");
  const apiRefreshBtn = document.getElementById("automationApiRefreshBtn") as HTMLButtonElement | null;
  const webRefreshBtn = document.getElementById("automationWebRefreshBtn") as HTMLButtonElement | null;

  const runApp = document.getElementById("automationRunApp") as HTMLSelectElement | null;
  const runType = document.getElementById("automationRunType") as HTMLSelectElement | null;
  const runEnv = document.getElementById("automationRunEnv") as HTMLSelectElement | null;
  const runTag = document.getElementById("automationRunTag") as HTMLInputElement | null;
  const allureLabel = document.getElementById("automationAllureLabel") as HTMLInputElement | null;
  const runParallel = document.getElementById("automationRunParallel") as HTMLSelectElement | null;
  const runHeaded = document.getElementById("automationRunHeaded") as HTMLSelectElement | null;
  const runUseSelected = document.getElementById("automationRunUseSelectedBtn") as HTMLButtonElement | null;
  const runBtn = document.getElementById("automationRunBtn") as HTMLButtonElement | null;
  const runStopBtn = document.getElementById("automationRunStopBtn") as HTMLButtonElement | null;
  const runCopyCmdBtn = document.getElementById("automationRunCopyCmdBtn") as HTMLButtonElement | null;
  const runDownloadLogBtn = document.getElementById("automationRunDownloadLogBtn") as HTMLButtonElement | null;
  const runCopyLogBtn = document.getElementById("automationRunCopyLogBtn") as HTMLButtonElement | null;
  const runErrorsOnlyToggle = document.getElementById("automationRunErrorsOnly") as HTMLInputElement | null;
  const runStatus = document.getElementById("automationRunStatus");
  const runProgressBar = document.getElementById("automationRunProgressBar") as HTMLElement | null;
  const runLog = document.getElementById("automationRunLog");
  const runHistoryList = document.getElementById("automationRunHistory");
  const runHistoryRefreshBtn = document.getElementById("automationRunHistoryRefreshBtn") as HTMLButtonElement | null;
  const runStorageKey = "automationRunId";
  let runPoller: number | null = null;
  let lastRunId: string | null = null;
  let lastRunCommand: string | null = null;
  let lastRunLogLines: string[] = [];

  const allureBtn = document.getElementById("automationAllureBtn") as HTMLButtonElement | null;
  const allureStatus = document.getElementById("automationAllureStatus");
  const allureLink = document.getElementById("automationAllureLink") as HTMLAnchorElement | null;
  const repoWarning = document.getElementById("automationRepoWarning");

  let canLoadCases = true;

  const apiCaseInput = document.getElementById("automationApiCaseId") as HTMLInputElement | null;
  const apiLoadBtn = document.getElementById("automationApiLoadBtn") as HTMLButtonElement | null;
  const apiSaveBtn = document.getElementById("automationApiSaveBtn") as HTMLButtonElement | null;
  const apiEditor = document.getElementById("automationApiPayloadEditor") as HTMLTextAreaElement | null;
  const apiTitle = document.getElementById("automationApiCaseTitle");
  const apiTags = document.getElementById("automationApiTags");
  const apiFeaturePath = document.getElementById("automationApiFeaturePath");

  const webCaseInput = document.getElementById("automationWebCaseId") as HTMLInputElement | null;
  const webLoadBtn = document.getElementById("automationWebLoadBtn") as HTMLButtonElement | null;
  const webSaveBtn = document.getElementById("automationWebSaveBtn") as HTMLButtonElement | null;
  const webEditor = document.getElementById("automationWebInputsEditor") as HTMLTextAreaElement | null;
  const webTitle = document.getElementById("automationWebCaseTitle");
  const webTags = document.getElementById("automationWebTags");
  const webFeaturePath = document.getElementById("automationWebFeaturePath");
  const webPreview = document.getElementById("automationWebPreview");

  let selectedCase: { id: number; kind: "api" | "web" } | null = null;
  const logErrorRegex = /(error|failed|exception|traceback|cypresserror)/i;

  const renderTags = (container: HTMLElement | null, kind: "api" | "web", item: AutomationCaseListItem) => {
    if (!container) return;
    const tags = new Set<string>();
    tags.add(kind === "api" ? "@api" : "@e2e");
    tags.add(`@C${item.id}`);
    (item.tags || []).forEach((tag) => {
      if (!tag.startsWith("@C")) tags.add(tag);
    });
    if (item.feature_group) {
      tags.add(item.feature_group);
    }
    container.innerHTML = "";
    Array.from(tags).forEach((tag) => {
      const span = document.createElement("span");
      span.className = "automation-tag";
      span.textContent = tag;
      container.appendChild(span);
    });
  };

  const applyCaseMeta = (kind: "api" | "web", item: AutomationCaseListItem) => {
    const titleText = `C${item.id} — ${item.title || "Untitled case"}`;
    if (kind === "api") {
      if (apiTitle) apiTitle.textContent = titleText;
      if (apiFeaturePath) apiFeaturePath.textContent = item.feature_path || "—";
      renderTags(apiTags, "api", item);
    } else {
      if (webTitle) webTitle.textContent = titleText;
      if (webFeaturePath) webFeaturePath.textContent = item.feature_path || "—";
      renderTags(webTags, "web", item);
    }
  };

  const ensureSelectedCard = (listEl: HTMLElement | null, card: HTMLElement | null) => {
    if (!listEl || !card) return;
    listEl.querySelectorAll(".automation-case-card").forEach((el) => {
      el.classList.remove("is-active");
    });
    card.classList.add("is-active");
  };

  const renderCaseList = (kind: "api" | "web", list: AutomationCaseListItem[]) => {
    const listEl = kind === "api" ? apiList : webList;
    if (!listEl) return;
    listEl.innerHTML = "";
    if (!list.length) {
      const empty = document.createElement("div");
      empty.className = "automation-case-card";
      empty.textContent = "No cases found.";
      listEl.appendChild(empty);
      return;
    }
    list.forEach((item) => {
      const card = document.createElement("div");
      card.className = "automation-case-card";
      card.dataset.automationCase = "true";
      card.dataset.caseId = String(item.id);
      card.dataset.caseType = kind;
      card.dataset.caseTitle = item.title || "";
      card.dataset.featurePath = item.feature_path || "";
      card.dataset.feature = item.feature || "";
      card.dataset.featureGroup = item.feature_group || "";
      card.dataset.method = item.method || "";
      card.dataset.endpoint = item.endpoint || "";
      card.dataset.tags = JSON.stringify(item.tags || []);

      const title = document.createElement("div");
      title.className = "automation-case-title";
      title.textContent = `C${item.id} — ${item.title || "Untitled case"}`;

      const featureLine = document.createElement("div");
      featureLine.className = "automation-case-meta-line";
      featureLine.textContent = `Feature: ${item.feature || item.feature_group || "—"}`;

      const detailLine = document.createElement("div");
      detailLine.className = "automation-case-meta-line";
      if (kind === "api") {
        const endpointLabel = item.endpoint
          ? `${item.method ? `${item.method} ` : ""}${item.endpoint}`
          : item.feature_path || "—";
        detailLine.textContent = `Endpoint: ${endpointLabel}`;
      } else {
        detailLine.textContent = `File: ${item.feature_path || "—"}`;
      }

      const actions = document.createElement("div");
      actions.className = "automation-case-actions";
      const openBtn = document.createElement("button");
      openBtn.type = "button";
      openBtn.className = "refresh-btn";
      openBtn.dataset.action = "open";
      openBtn.textContent = kind === "api" ? "Open Payload" : "Open Inputs";
      const copyBtn = document.createElement("button");
      copyBtn.type = "button";
      copyBtn.className = "refresh-btn";
      copyBtn.dataset.action = "copy";
      copyBtn.textContent = "Copy Case ID";
      actions.appendChild(openBtn);
      actions.appendChild(copyBtn);

      card.appendChild(title);
      card.appendChild(featureLine);
      card.appendChild(detailLine);
      card.appendChild(actions);
      listEl.appendChild(card);
    });
  };

  const updateMetaFromId = (kind: "api" | "web", caseId: number) => {
    const item = caseMaps[kind].get(caseId);
    if (!item) {
      const fallback = { id: caseId, title: `Case ${caseId}` };
      applyCaseMeta(kind, fallback);
      return;
    }
    applyCaseMeta(kind, item);
  };

  const loadCase = async (kind: "api" | "web") => {
    const input = kind === "api" ? apiCaseInput : webCaseInput;
    if (!input) return;
    const caseId = parseIntMaybe(input.value);
    if (!caseId) {
      showToast("Provide a valid case ID.", "error");
      return;
    }
    try {
      const data = await requestJson(`/api/automation/case/${caseId}`);
      if (kind === "api") {
        updateMetaFromId("api", caseId);
        if (apiEditor) apiEditor.value = formatAutomationPayload(data?.api_payload || "");
      } else {
        updateMetaFromId("web", caseId);
        if (webEditor) webEditor.value = formatAutomationPayload(data?.web_inputs || "");
        if (webPreview && webEditor) {
          webPreview.textContent = webEditor.value || "{}";
        }
      }
      selectedCase = { id: caseId, kind };
      showToast(`Loaded case C${caseId}`, "success");
    } catch (err: any) {
      showToast(err?.message || "Failed to load case", "error");
    }
  };

  const saveCase = async (kind: "api" | "web") => {
    const input = kind === "api" ? apiCaseInput : webCaseInput;
    const editor = kind === "api" ? apiEditor : webEditor;
    if (!input || !editor) return;
    const caseId = parseIntMaybe(input.value);
    if (!caseId) {
      showToast("Provide a valid case ID.", "error");
      return;
    }
    const payloadValue = parseAutomationPayload(editor.value);
    const body = kind === "api" ? { api_payload: payloadValue } : { web_inputs: payloadValue };
    try {
      await requestJson(`/api/automation/case/${caseId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (kind === "web" && webPreview) {
        webPreview.textContent = editor.value || "{}";
      }
      showToast(`Saved automation data for C${caseId}`, "success");
    } catch (err: any) {
      showToast(err?.message || "Failed to save automation data", "error");
    }
  };

  apiLoadBtn?.addEventListener("click", () => loadCase("api"));
  webLoadBtn?.addEventListener("click", () => loadCase("web"));
  apiSaveBtn?.addEventListener("click", () => saveCase("api"));
  webSaveBtn?.addEventListener("click", () => saveCase("web"));

  const handleCaseListClick = (kind: "api" | "web", event: Event) => {
    const target = event.target as HTMLElement | null;
    const listEl = kind === "api" ? apiList : webList;
    if (!target || !listEl) return;
    const card = target.closest<HTMLElement>(".automation-case-card");
    if (!card || !listEl.contains(card)) return;
    const caseId = parseIntMaybe(card.dataset.caseId || "");
    if (!caseId) return;

    const action = target.closest<HTMLElement>("[data-action]")?.dataset.action;
    if (action === "copy") {
      event.stopPropagation();
      if (!navigator.clipboard) {
        showToast("Clipboard not available", "error");
        return;
      }
      navigator.clipboard
        .writeText(String(caseId))
        .then(() => showToast(`Copied C${caseId}`, "success"))
        .catch(() => showToast("Failed to copy case ID", "error"));
      return;
    }

    if (kind === "api" && apiCaseInput) apiCaseInput.value = String(caseId);
    if (kind === "web" && webCaseInput) webCaseInput.value = String(caseId);
    updateMetaFromId(kind, caseId);
    ensureSelectedCard(listEl, card);
    selectedCase = { id: caseId, kind };
    loadCase(kind);
  };

  apiList?.addEventListener("click", (event) => handleCaseListClick("api", event));
  webList?.addEventListener("click", (event) => handleCaseListClick("web", event));

  const fetchCaseList = async (kind: "api" | "web") => {
    if (!canLoadCases) {
      const listEl = kind === "api" ? apiList : webList;
      if (listEl) {
        listEl.innerHTML = "";
        const warning = document.createElement("div");
        warning.className = "automation-case-card";
        warning.textContent = "Feature files are not available on this host.";
        listEl.appendChild(warning);
      }
      return;
    }
    try {
      const data = await requestJson<{ cases: AutomationCaseListItem[] }>(
        `/api/automation/cases?case_type=${kind}`
      );
      const list = Array.isArray(data?.cases) ? data.cases : [];
      casesByType[kind] = list;
      caseMaps[kind] = new Map(list.map((item) => [item.id, item]));
      renderCaseList(kind, list);
    } catch (err: any) {
      const listEl = kind === "api" ? apiList : webList;
      if (listEl) {
        listEl.innerHTML = "";
        const errorCard = document.createElement("div");
        errorCard.className = "automation-case-card";
        errorCard.textContent = err?.message || "Failed to load cases.";
        listEl.appendChild(errorCard);
      }
    }
  };

  const filterCasesByQuery = (kind: "api" | "web", query: string) => {
    const normalized = query.trim().toLowerCase();
    const list = casesByType[kind];
    if (!normalized) {
      renderCaseList(kind, list);
      return;
    }
    const filtered = list.filter((item) => {
      const idMatch = String(item.id).includes(normalized);
      const titleMatch = (item.title || "").toLowerCase().includes(normalized);
      const featureMatch = (item.feature || "").toLowerCase().includes(normalized);
      return idMatch || titleMatch || featureMatch;
    });
    renderCaseList(kind, filtered);
  };

  apiSearch?.addEventListener("input", () => {
    filterCasesByQuery("api", apiSearch.value);
  });
  webSearch?.addEventListener("input", () => {
    filterCasesByQuery("web", webSearch.value);
  });

  apiRefreshBtn?.addEventListener("click", () => fetchCaseList("api"));
  webRefreshBtn?.addEventListener("click", () => fetchCaseList("web"));

  const applyAutomationStatus = (status: any) => {
    const warnings: string[] = [];
    const repoOk = Boolean(status?.repo_root_ok);
    const featuresOk = Boolean(status?.features_root_ok);
    const appOk = Boolean(status?.app_root_ok);
    const npmOk = Boolean(status?.npm_available);

    if (!repoOk) {
      warnings.push("Automation repo not found. Set AUTOMATION_REPO_ROOT and mount the repo.");
    }
    if (!appOk) {
      warnings.push("Automation app path not found inside the repo.");
    }
    if (!featuresOk) {
      warnings.push("Feature files not found. Set AUTOMATION_FEATURES_ROOT.");
    }
    if (!npmOk) {
      warnings.push("npm is not available in this environment.");
    }

    canLoadCases = featuresOk;
    if (repoWarning) {
      if (warnings.length) {
        repoWarning.textContent = warnings.join(" ");
        repoWarning.style.display = "block";
      } else {
        repoWarning.textContent = "";
        repoWarning.style.display = "none";
      }
    }

    const canRun = repoOk && appOk && npmOk;
    if (runBtn) runBtn.disabled = !canRun;
    if (allureBtn) allureBtn.disabled = !canRun;
    if (!canRun && runStatus) {
      runStatus.textContent = "Automation runner is unavailable on this host.";
    }
    if (!featuresOk) {
      fetchCaseList("api");
      fetchCaseList("web");
    }
  };

  const loadAutomationStatus = async () => {
    try {
      const status = await requestJson("/api/automation/status");
      applyAutomationStatus(status);
    } catch (err: any) {
      if (repoWarning) {
        repoWarning.textContent = err?.message || "Failed to load automation status.";
        repoWarning.style.display = "block";
      }
    }
  };

  loadAutomationStatus();
  const filterLogLines = (lines: string[], errorsOnly: boolean) => {
    if (!errorsOnly) return lines;
    return lines.filter((line) => logErrorRegex.test(line));
  };

  const updateLogView = () => {
    if (!runLog) return;
    const errorsOnly = runErrorsOnlyToggle?.checked ?? false;
    const lines = filterLogLines(lastRunLogLines, errorsOnly);
    runLog.textContent = lines.join("\n") || "No logs yet.";
  };

  const updateRunActions = (status: string | undefined, runId?: string | null) => {
    const active = status === "running" || status === "stopping";
    if (runStopBtn) runStopBtn.disabled = !active || !runId;
    if (runCopyCmdBtn) runCopyCmdBtn.disabled = !lastRunCommand;
    if (runDownloadLogBtn) runDownloadLogBtn.disabled = !runId;
    if (runCopyLogBtn) runCopyLogBtn.disabled = !lastRunLogLines.length;
  };

  const renderRunHistory = (runs: any[]) => {
    if (!runHistoryList) return;
    runHistoryList.innerHTML = "";
    if (!runs.length) {
      const empty = document.createElement("div");
      empty.className = "automation-case-card";
      empty.textContent = "No runs yet.";
      runHistoryList.appendChild(empty);
      return;
    }
    runs.forEach((run) => {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "automation-case-card automation-run-card";
      card.dataset.runId = run.run_id;
      if (run.run_id === lastRunId) {
        card.classList.add("is-active");
      }

      const title = document.createElement("div");
      title.className = "automation-case-title";
      title.textContent = `${(run.test_type || "run").toUpperCase()} · ${run.environment || "env"} · ${run.app || "app"}`;

      const meta = document.createElement("div");
      meta.className = "automation-case-meta-line";
      const tagLabel = run.test_tag ? `Tag: ${run.test_tag}` : "Tag: all";
      const startedAt = run.started_at ? formatRelativeTime(new Date(run.started_at)) : "unknown";
      meta.textContent = `${tagLabel} · ${startedAt}`;

      const detail = document.createElement("div");
      detail.className = "automation-case-meta-line";
      const progress = run.progress_percent != null ? `${run.progress_percent}%` : "n/a";
      detail.textContent = `Status: ${run.status || "unknown"} · Progress: ${progress}`;

      card.appendChild(title);
      card.appendChild(meta);
      card.appendChild(detail);
      runHistoryList.appendChild(card);
    });
  };

  const fetchRunHistory = async () => {
    try {
      const data = await requestJson("/api/automation/runs");
      renderRunHistory(data?.runs || []);
    } catch {
      renderRunHistory([]);
    }
  };

  updateRunActions("idle", null);

  runUseSelected?.addEventListener("click", () => {
    if (!selectedCase) {
      showToast("Select a case first.", "error");
      return;
    }
    if (runTag) {
      runTag.value = `@C${selectedCase.id}`;
    }
    if (runType) {
      runType.value = selectedCase.kind === "api" ? "api" : "e2e";
    }
    if (runStatus) {
      runStatus.textContent = `Ready to run C${selectedCase.id}.`;
    }
  });

  const syncHeadedToggle = () => {
    if (!runHeaded) return;
    const typeValue = (runType?.value || "api").toLowerCase();
    const enableHeaded = typeValue === "e2e" || typeValue === "all";
    runHeaded.disabled = !enableHeaded;
    if (!enableHeaded) {
      runHeaded.value = "false";
    }
  };

  runType?.addEventListener("change", syncHeadedToggle);
  runType?.addEventListener("input", syncHeadedToggle);
  document.addEventListener("change", (event) => {
    const target = event.target as HTMLElement | null;
    if (target?.id === "automationRunType") {
      syncHeadedToggle();
    }
  });
  syncHeadedToggle();

  runBtn?.addEventListener("click", async () => {
    const wantsParallel = (runParallel?.value || "false") === "true";
    if (wantsParallel) {
      showToast("Parallel runs are not supported locally yet.", "error");
      return;
    }
    const wantsHeaded = (runHeaded?.value || "false") === "true";
    const payload = {
      app_name: runApp?.value || "lokasi_intelligence",
      test_type: runType?.value || "api",
      test_tag: runTag?.value.trim() || "",
      environment: runEnv?.value || "staging",
      parallel: wantsParallel,
      headed: wantsHeaded,
    };

    if (runStatus) {
      runStatus.textContent = "Dispatching workflow...";
    }
    try {
      const response = await requestJson("/api/automation/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const runId = response?.run_id || "";
      lastRunCommand = response?.command || null;
      if (runId) {
        localStorage.setItem(runStorageKey, runId);
      }
      if (runStatus) {
        const logPath = response?.log_path ? ` Logs: ${response.log_path}` : "";
        const envPath = response?.env_path ? ` Env: ${response.env_path}` : "";
        runStatus.textContent = `Run started (PID ${response?.pid || "?"}).${logPath}${envPath}`;
      }
      if (runProgressBar) {
        runProgressBar.style.width = "0%";
      }
      if (runLog) {
        runLog.textContent = "Waiting for logs...";
      }
      if (runId) {
        startRunPolling(runId);
      }
      fetchRunHistory();
      showToast("Automation run started.", "success");
    } catch (err: any) {
      if (runStatus) {
        runStatus.textContent = err?.message || "Dispatch failed.";
      }
      showToast(err?.message || "Failed to dispatch workflow.", "error");
    }
  });

  runStopBtn?.addEventListener("click", async () => {
    if (!lastRunId) {
      showToast("No active run selected.", "error");
      return;
    }
    try {
      await requestJson(`/api/automation/run/${encodeURIComponent(lastRunId)}/stop`, {
        method: "POST",
      });
      showToast("Stop requested.", "info");
      pollRunStatus(lastRunId);
      fetchRunHistory();
    } catch (err: any) {
      showToast(err?.message || "Failed to stop run.", "error");
    }
  });

  runCopyCmdBtn?.addEventListener("click", async () => {
    if (!lastRunCommand) {
      showToast("No command available.", "error");
      return;
    }
    try {
      await navigator.clipboard.writeText(lastRunCommand);
      showToast("Command copied.", "success");
    } catch {
      showToast("Failed to copy command.", "error");
    }
  });

  runDownloadLogBtn?.addEventListener("click", () => {
    if (!lastRunId) {
      showToast("No run selected.", "error");
      return;
    }
    const url = `/api/automation/run/${encodeURIComponent(lastRunId)}/log?download=1`;
    window.open(url, "_blank", "noopener");
  });

  runCopyLogBtn?.addEventListener("click", async () => {
    if (!runLog?.textContent) {
      showToast("No log output available.", "error");
      return;
    }
    try {
      await navigator.clipboard.writeText(runLog.textContent);
      showToast("Log copied.", "success");
    } catch {
      showToast("Failed to copy log.", "error");
    }
  });

  allureBtn?.addEventListener("click", async () => {
    const payload = {
      app_name: runApp?.value || "lokasi_intelligence",
      output_label: allureLabel?.value.trim() || "",
    };
    if (allureStatus) {
      allureStatus.textContent = "Generating Allure report...";
    }
    if (allureLink) {
      allureLink.style.display = "none";
      allureLink.removeAttribute("href");
    }
    try {
      const response = await requestJson("/api/automation/allure-report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const url = response?.url || "";
      if (allureStatus) {
        allureStatus.textContent = "Allure report generated.";
      }
      if (allureLink && url) {
        allureLink.href = url;
        allureLink.style.display = "inline-flex";
        allureLink.textContent = "Open Allure Report";
      }
      showToast("Allure report generated.", "success");
    } catch (err: any) {
      if (allureStatus) {
        allureStatus.textContent = err?.message || "Allure report failed.";
      }
      showToast(err?.message || "Failed to generate Allure report.", "error");
    }
  });

  const stopRunPolling = () => {
    if (runPoller !== null) {
      window.clearInterval(runPoller);
      runPoller = null;
    }
  };

  const updateRunUI = (data: any) => {
    const status = data?.status || "unknown";
    const statusLabel = status.replace(/_/g, " ");
    const completed = data?.completed_cases ?? 0;
    const total = data?.total_cases;
    const progress = data?.progress_percent;
    const summaryParts = [`Status: ${statusLabel}`];
    if (typeof total === "number") {
      summaryParts.push(`Progress: ${completed}/${total}`);
    } else {
      summaryParts.push("Progress: n/a");
    }
    if (typeof progress === "number") {
      summaryParts.push(`${progress}%`);
    }
    if (data?.last_log_line) {
      summaryParts.push(`Last: ${data.last_log_line}`);
    }
    if (runStatus) {
      runStatus.textContent = summaryParts.join(" · ");
    }
    if (runProgressBar) {
      runProgressBar.style.width = typeof progress === "number" ? `${progress}%` : "0%";
    }
    lastRunCommand = data?.command || lastRunCommand;
    lastRunLogLines = Array.isArray(data?.log_tail) ? data.log_tail : [];
    updateLogView();
    updateRunActions(status, lastRunId);
  };

  const pollRunStatus = async (runId: string) => {
    try {
      const errorsOnly = runErrorsOnlyToggle?.checked ? "true" : "false";
      const data = await requestJson(
        `/api/automation/run/${encodeURIComponent(runId)}?errors_only=${errorsOnly}`
      );
      updateRunUI(data);
      fetchRunHistory();
      if (data?.status === "success" || data?.status === "failed" || data?.status === "completed_with_failures" || data?.status === "stopped") {
        stopRunPolling();
      }
    } catch (err: any) {
      if (runStatus) {
        runStatus.textContent = err?.message || "Failed to fetch run status.";
      }
      localStorage.removeItem(runStorageKey);
      stopRunPolling();
    }
  };

  const startRunPolling = (runId: string) => {
    stopRunPolling();
    lastRunId = runId;
    pollRunStatus(runId);
    runPoller = window.setInterval(() => pollRunStatus(runId), 5000);
  };

  const existingRunId = localStorage.getItem(runStorageKey);
  if (existingRunId) {
    startRunPolling(existingRunId);
  }

  runErrorsOnlyToggle?.addEventListener("change", () => {
    if (lastRunId) {
      pollRunStatus(lastRunId);
    } else {
      updateLogView();
    }
  });

  runHistoryRefreshBtn?.addEventListener("click", fetchRunHistory);

  runHistoryList?.addEventListener("click", (event) => {
    const target = event.target as HTMLElement | null;
    const card = target?.closest<HTMLElement>(".automation-run-card");
    const runId = card?.dataset.runId;
    if (!runId) return;
    localStorage.setItem(runStorageKey, runId);
    startRunPolling(runId);
    fetchRunHistory();
  });

  fetchCaseList("api");
  fetchCaseList("web");
  fetchRunHistory();
}

function init() {
  setupThemeToggle();
  updateReportMeta(undefined);
  initManageTabs();
  (window as any).focusCreateTabs = focusCreateTabs;
  loadPlans().catch((err) => console.error("loadPlans error", err));
  loadManagePlans().catch((err) => console.error("loadManagePlans error", err));
  initManagement();
  initCreateWizards();
  initAutomationManagement();
  
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
  document.getElementById("linkAutomation")?.addEventListener("click", (e) => {
    e.preventDefault();
    switchView("automation");
  });
  document.getElementById("linkDataset")?.addEventListener("click", (e) => {
    e.preventDefault();
    switchView("dataset");
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
