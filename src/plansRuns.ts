import { Plan, Run } from "./types";
import { escapeHtml, requestJson, showToast } from "./utils";
import { filterRuns, renderRuns, updateRunSummary } from "./runsUI";

let cachedPlanOptionsHtml = "";

export async function loadRuns() {
  const planSel = document.getElementById("plan") as HTMLSelectElement | null;
  const projectInput = document.getElementById("project") as HTMLInputElement | null;
  const runsSection = document.getElementById("runs-section") as HTMLElement | null;
  const runList = document.getElementById("run-list");
  const runEmpty = document.getElementById("run-empty") as HTMLElement | null;
  const runSearch = document.getElementById("runSearch") as HTMLInputElement | null;
  const runsNote = document.getElementById("runs-note");
  const planVal = planSel?.value;
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
  runsNote.textContent = "Loading runs…";
  if (runEmpty) {
    runEmpty.textContent = "Loading runs…";
    runEmpty.style.display = "block";
  }
  if (runSearch) {
    runSearch.value = "";
  }
  try {
    const resp = await fetch(
      `/api/runs?project=${encodeURIComponent(projectInput?.value || "1")}&plan=${encodeURIComponent(planVal)}`
    );
    if (!resp.ok) {
      const text = await resp.text().catch(() => "");
      throw new Error(text || `Failed to fetch runs for plan ${planVal}`);
    }
    const data = await resp.json();
    const runs: Run[] = Array.isArray(data.runs) ? data.runs : [];
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

export async function loadPlans(force = false) {
  const projectInput = document.getElementById("project") as HTMLInputElement | null;
  const project = projectInput ? projectInput.value || "1" : "1";
  const planSel = document.getElementById("plan") as HTMLSelectElement | null;
  const note = document.getElementById("plan-note") as HTMLElement | null;
  const refreshBtn = document.getElementById("refreshPlansBtn") as HTMLButtonElement | null;
  if (!planSel) {
    return;
  }
  if (force) {
    cachedPlanOptionsHtml = "";
  }
  planSel.innerHTML = '<option value="" disabled selected>Loading plans…</option>';
  planSel.disabled = true;
  if (refreshBtn) {
    refreshBtn.disabled = true;
    refreshBtn.textContent = "Refreshing…";
  }

  async function fetchPlans(url: string): Promise<Plan[]> {
    const resp = await fetch(url);
    if (!resp.ok) {
      const text = await resp.text().catch(() => "");
      throw new Error(text || `Failed to fetch ${url}`);
    }
    const data = await resp.json();
    let plans: Plan[] = Array.isArray(data.plans) ? data.plans : [];
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
      const planOptions = plans
        .map((p) => `<option value="${p.id}">${escapeHtml(p.name || "Plan " + p.id)} (ID ${p.id})</option>`)
        .join("");
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

export function setManagePlanOptions(planOptions: string) {
  const runPlanSelect = document.getElementById("runPlanSelect") as HTMLSelectElement | null;
  if (runPlanSelect) {
    runPlanSelect.innerHTML = planOptions || `<option value=\"\">No plans found</option>`;
  }
}

export async function loadManagePlans(force = false) {
  const projectVal =
    (document.getElementById("runProject") as HTMLInputElement | null)?.value ||
    (document.getElementById("caseProject") as HTMLInputElement | null)?.value ||
    (document.getElementById("project") as HTMLInputElement | null)?.value ||
    "1";
  const refreshBtn = document.getElementById("refreshManagePlansBtn") as HTMLButtonElement | null;
  if (force) {
    cachedPlanOptionsHtml = "";
  }
  if (refreshBtn) {
    refreshBtn.disabled = true;
    refreshBtn.textContent = "Refreshing…";
  }
  if (cachedPlanOptionsHtml) {
    setManagePlanOptions(cachedPlanOptionsHtml);
  }
  try {
    const data = await requestJson<{ plans?: Plan[] }>(`/api/plans?project=${encodeURIComponent(projectVal)}&is_completed=0`);
    const plans = Array.isArray(data.plans) ? data.plans : [];
    plans.sort((a, b) => (b.created_on || 0) - (a.created_on || 0) || String(a.name || "").localeCompare(String(b.name || "")));
    const planOptions = plans
      .map((p) => `<option value="${p.id}">${escapeHtml(p.name || "Plan " + p.id)} (ID ${p.id})</option>`)
      .join("");
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

export function ensurePlanSelected(): boolean {
  const planSel = document.getElementById("plan") as HTMLSelectElement | null;
  if (!planSel?.value) {
    alert("Please select a Test Plan");
    return false;
  }
  return true;
}

export function ensureRunSelection(): boolean {
  const runsSection = document.getElementById("runs-section") as HTMLElement | null;
  if (!runsSection || runsSection.dataset.available !== "1") {
    return true;
  }
  const checked = document.querySelectorAll("#run-list input[name=\"run_ids\"]:checked").length;
  if (checked === 0) {
    alert("Please select at least one Test Run.");
    return false;
  }
  return true;
}

export function setRunSelections(state: boolean) {
  document.querySelectorAll<HTMLInputElement>("#run-list input[name=\"run_ids\"]").forEach((cb) => {
    cb.checked = state;
  });
  updateRunSummary();
}

export function getCachedPlanOptions() {
  return cachedPlanOptionsHtml;
}

export function setCachedPlanOptions(html: string) {
  cachedPlanOptionsHtml = html;
}

export { renderRuns, filterRuns, updateRunSummary };
