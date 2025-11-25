import { appConfig } from "./config";
import { CaseItem } from "./types";
import { escapeHtml, parseIdList, requestJson, showToast } from "./utils";

let selectedCases = new Set<number>();
let cachedCases: CaseItem[] = [];

export const getSelectedCases = () => selectedCases;
export const resetSelectedCases = () => {
  selectedCases = new Set<number>();
};

export function updateCasePickerStatus() {
  const status = document.getElementById("casePickerStatus");
  if (!status) return;
  const count = selectedCases.size;
  status.textContent = count ? `${count} case${count === 1 ? "" : "s"} selected` : "No cases selected.";
}

export function updateCaseCount(count: number | null) {
  const label = document.getElementById("caseCountLabel");
  if (!label) return;
  if (typeof count === "number" && count >= 0) {
    label.textContent = `${count} case${count === 1 ? "" : "s"} loaded`;
  } else {
    label.textContent = "Cases";
  }
}

export function syncCaseIdsInput() {
  const input = document.getElementById("runCaseIds") as HTMLInputElement | null;
  if (!input) return;
  const sorted = Array.from(selectedCases).sort((a, b) => a - b);
  input.value = sorted.join(", ");
  updateCasePickerStatus();
}

export function applySelectionToList() {
  document.querySelectorAll<HTMLInputElement>("#caseList input[type=\"checkbox\"]").forEach((cb) => {
    const id = parseInt(cb.value, 10);
    cb.checked = selectedCases.has(id);
  });
}

export function renderCases(cases: CaseItem[]) {
  const list = document.getElementById("caseList");
  const empty = document.getElementById("caseEmpty");
  if (!list || !empty) return;
  if (!cases || cases.length === 0) {
    list.innerHTML = "";
    empty.textContent = "No cases found.";
    (empty as HTMLElement).style.display = "block";
    return;
  }
  list.innerHTML = cases
    .map((c) => {
      const id = c.id;
      const title = escapeHtml(c.title || `Case ${id}`);
      const refs = c.refs ? escapeHtml(String(c.refs)) : "";
      const searchTokens = `${id} ${c.title || ""} ${c.refs || ""}`.toLowerCase();
      const refsLabel = refs ? `<span class="case-card-meta">Refs: ${refs}</span>` : "";
      return `<label class=\"case-card\" data-text=\"${escapeHtml(searchTokens)}\">\n          <input type=\"checkbox\" value=\"${id}\">\n          <div>\n            <div class=\"case-card-title\">${title}</div>\n            <div class=\"case-card-meta\">Case ${id}${refs ? " • " + refsLabel : ""}</div>\n          </div>\n        </label>`;
    })
    .join("");
  (empty as HTMLElement).style.display = "none";
  applySelectionToList();
}

export function filterCases() {
  const search = document.getElementById("caseSearch") as HTMLInputElement | null;
  const list = document.getElementById("caseList");
  const empty = document.getElementById("caseEmpty") as HTMLElement | null;
  if (!search || !list || !empty) return;
  const query = (search.value || "").trim().toLowerCase();
  let visible = 0;
  list.querySelectorAll<HTMLElement>(".case-card").forEach((card) => {
    const matches = !query || card.dataset.text?.includes(query);
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

export function loadCases(force = false) {
  const projectVal =
    (document.getElementById("runProject") as HTMLInputElement | null)?.value ||
    (document.getElementById("project") as HTMLInputElement | null)?.value ||
    "1";
  const refreshBtn = document.getElementById("caseRefreshBtn") as HTMLButtonElement | null;
  const empty = document.getElementById("caseEmpty") as HTMLElement | null;
  if (refreshBtn) {
    refreshBtn.disabled = true;
    refreshBtn.textContent = "Refreshing…";
  }
  if (empty) {
    empty.textContent = "Loading cases…";
    empty.style.display = "block";
  }
  const qs = new URLSearchParams({ project: projectVal });
  if (appConfig.defaultSuiteId !== null && appConfig.defaultSuiteId !== undefined) {
    qs.append("suite_id", String(appConfig.defaultSuiteId));
  }
  if (appConfig.defaultSectionId !== null && appConfig.defaultSectionId !== undefined) {
    qs.append("section_id", String(appConfig.defaultSectionId));
    const filterParam = JSON.stringify({
      mode: "1",
      filters: { "cases:section_id": { values: [String(appConfig.defaultSectionId)] } },
    });
    qs.append("filters", filterParam);
  }
  return requestJson<{ cases?: CaseItem[] }>(`/api/cases?${qs.toString()}`)
    .then((data) => {
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
    })
    .catch((err) => {
      showToast(err?.message || "Failed to load cases.", "error");
      if (empty) {
        empty.textContent = "Failed to load cases.";
        empty.style.display = "block";
      }
      updateCaseCount(null);
    })
    .finally(() => {
      if (refreshBtn) {
        refreshBtn.disabled = false;
        refreshBtn.textContent = "Refresh";
      }
    });
}

export function openCasePicker() {
  const modal = document.getElementById("casePickerModal");
  if (!modal) return;
  modal.classList.remove("hidden");
  const manual = parseIdList((document.getElementById("runCaseIds") as HTMLInputElement | null)?.value || "");
  manual.forEach((id) => selectedCases.add(id));
  updateCasePickerStatus();
  updateCaseCount(cachedCases.length || 0);
  loadCases().then(applySelectionToList);
}

export function closeCasePicker() {
  const modal = document.getElementById("casePickerModal");
  if (!modal) return;
  modal.classList.add("hidden");
}

export function handleCaseCheckboxChange(event: Event) {
  const target = event.target as HTMLInputElement | null;
  if (!target || target.type !== "checkbox") return;
  const id = parseInt(target.value, 10);
  if (!Number.isFinite(id)) return;
  if (target.checked) {
    selectedCases.add(id);
    const includeAll = document.getElementById("runIncludeAll") as HTMLInputElement | null;
    if (includeAll) {
      includeAll.checked = false;
    }
  } else {
    selectedCases.delete(id);
  }
  syncCaseIdsInput();
}

export function selectVisibleCases(state: boolean) {
  document.querySelectorAll<HTMLElement>("#caseList .case-card").forEach((card) => {
    if (card.style.display === "none") return;
    const cb = card.querySelector<HTMLInputElement>("input[type=\"checkbox\"]");
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

export function clearCaseSelection() {
  selectedCases.clear();
  document.querySelectorAll<HTMLInputElement>("#caseList input[type=\"checkbox\"]").forEach((cb) => (cb.checked = false));
  syncCaseIdsInput();
}
