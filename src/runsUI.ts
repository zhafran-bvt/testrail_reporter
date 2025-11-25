import { Run } from "./types";

export function renderRuns(runs: Run[]) {
  const runList = document.getElementById("run-list");
  const runEmpty = document.getElementById("run-empty");
  if (!runList || !runEmpty) return;
  if (!runs || runs.length === 0) {
    runList.innerHTML = "";
    runEmpty.textContent = "No runs found in this plan.";
    (runEmpty as HTMLElement).style.display = "block";
    return;
  }
  runList.innerHTML = runs
    .map((run) => {
      const name = run.name ? escapeHtml(run.name) : `Run ${run.id}`;
      const searchTokens = `${run.id} ${run.name || ""}`.toLowerCase();
      return `<label class=\"run-card\" data-text=\"${escapeHtml(searchTokens)}\">\n          <input type=\"checkbox\" name=\"run_ids\" value=\"${run.id}\" checked>\n          <div class=\"run-card-content\">\n            <span class=\"run-card-title\">${name}</span>\n            <span class=\"run-card-id\">Run ID: ${run.id}</span>\n            </div>\n        </label>`;
    })
    .join("");
  (runEmpty as HTMLElement).style.display = "none";
  runList.querySelectorAll('input[name="run_ids"]').forEach((cb) => {
    cb.addEventListener("change", updateRunSummary);
  });
}

export function filterRuns() {
  const runList = document.getElementById("run-list");
  const runEmpty = document.getElementById("run-empty");
  const runSearch = document.getElementById("runSearch") as HTMLInputElement | null;
  if (!runList || !runEmpty || !runSearch) return;
  const query = (runSearch.value || "").trim().toLowerCase();
  let visible = 0;
  runList.querySelectorAll<HTMLElement>(".run-card").forEach((card) => {
    const matches = !query || card.dataset.text?.includes(query);
    card.style.display = matches ? "" : "none";
    if (matches) visible++;
  });
  if (visible === 0) {
    runEmpty.textContent = query ? "No runs match your search." : "No runs found in this plan.";
    (runEmpty as HTMLElement).style.display = "block";
  } else {
    (runEmpty as HTMLElement).style.display = "none";
  }
  updateRunSummary();
}

export function updateRunSummary() {
  const runsSection = document.getElementById("runs-section") as HTMLElement | null;
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
  const visible = cards.filter((card) => (card as HTMLElement).style.display !== "none").length;
  const query = (document.getElementById("runSearch") as HTMLInputElement | null)?.value.trim() || "";
  let text = `Selected ${selected} of ${total} runs.`;
  if (query) {
    text += ` Showing ${visible} matching runs.`;
  }
  runsNote.textContent = text;
}

const escapeHtml = (s: any): string => String(s).replace(/[&<>\"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c] || c));
