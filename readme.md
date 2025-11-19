# TestRail Reporter (HTML + API)

Generate and serve clean HTML summaries for TestRail plans or runs. The report includes per‑run breakdowns (Passed/Untested/Failed/Blocked/Obsolete/Retest), fixed‑width tables with Title and Assignee emphasized, assignee and priority names, and a project‑level donut chart. Project and plan names link back to TestRail (and Refs link to JIRA). Attachments are downloaded, lightly compressed, and embedded inline so the HTML works offline.

## Features
- Project + Plan context with links to TestRail
- Per-run totals and status breakdown (Passed, Untested, Failed, Blocked, Obsolete, Retest)
- Fixed-width table columns (Title widest, Assignee second)
- Assignee names resolved from TestRail users
- Priority names resolved from TestRail priorities
- Single project-level donut chart of status distribution
- Multi-run selection UI (filterable list, select-all/clear) with loading overlay while preview builds
- Attachments (screenshots/evidence) are compressed and embedded inline for offline viewing
- Robust API handling (pagination, mixed payload shapes)

## Requirements
- Python 3.9+
- A TestRail user with API access and an API key

Install dependencies:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Configuration
Set the following environment variables (e.g., in `.env`):

- `TESTRAIL_BASE_URL`: Base URL to your TestRail, e.g. `https://<subdomain>.testrail.io`
- `TESTRAIL_USER`: TestRail username or email
- `TESTRAIL_API_KEY`: TestRail API key

Load from `.env` is handled automatically via `python-dotenv`.

## CLI Usage

Run against a plan (aggregates all runs in the plan):

```bash
python3 testrail_daily_report.py --project 1 --plan 241
```

Limit to specific runs within the plan:

```bash
python3 testrail_daily_report.py --project 1 --plan 241 --runs 1001 1002 1003
```

Or a single run:

```bash
python3 testrail_daily_report.py --project 1 --run 1234
```

Output is saved to `out/Testing_Progress_Report_{plan_or_project}_ddmmyy.html` and can be opened in a browser.

## Web App Usage (API + UI)

Run a local server (serves UI + generated files):

```bash
uvicorn app.main:app --reload
```

Open UI: `http://127.0.0.1:8000/` (alias: `/ui`)

API endpoints:
- `GET /api/report?project=1&plan=241` → generates and returns `{ path, url }`
- `GET /api/report?project=1&run=1234` → generates and returns `{ path, url }`
- `GET /reports/<file.html>` → serves previously generated HTML
- `GET /healthz` → health check

Notes:
- Provide exactly one of `plan` or `run`.
- Project defaults to `1` in most flows, but can be passed explicitly.
- **Single web process:** the async job queue keeps its state in-process, so production deployments must run FastAPI with a single uvicorn worker (this repo’s `Procfile`/`Dockerfile` already enforce `--workers 1`). `REPORT_WORKERS_*` controls report generation parallelism.
- **Long reports need long timeouts:** generating big plans with attachments can easily exceed 30 s, so the provided commands set `--timeout-keep-alive 120`. If your host injects its own run command, match or exceed those keep-alive/timeouts so the worker isn’t restarted mid-report.
- UI behavior:
  - Preview button opens the generated HTML in a new tab and shows a modal spinner until the file downloads.
  - Plans list auto-loads open plans first; if none, it falls back to all plans.
  - Runs list appears after picking a plan; you can search/filter, select-all, or clear selections.

## Debugging

- Health: `GET /healthz` returns `{ "ok": true }` when the app is up.
- Warm ping: set `KEEPALIVE_URL` (and optional `KEEPALIVE_INTERVAL`) so the server self-pings even when idle (useful on Render free tier).
- Plans fetching:
  - The UI first calls `/api/plans?project=ID&is_completed=0` (open plans).
  - If none are found, it retries `/api/plans?project=ID` and shows a note.
  - If errors persist, check server logs and verify `TESTRAIL_*` env values.

## How it works (data sources)
- Runs in a plan are enumerated via `get_plan/<plan_id>`.
- Test status comes from `get_tests/<run_id>` (field `status_id`) to match TestRail run page counts exactly. The script maps IDs to names via `get_statuses` and shows “Untested” for tests without a result.
- Latest results per test are fetched via `get_results_for_run/<run_id>` only for enrichment (e.g., comments/attachments if needed), but do not affect the status shown.
- Assignee names come from `get_users` (with `get_user/<id>` fallback).
- Priority names come from `get_priorities`.
- Refs link to JIRA with base `https://bvarta-project.atlassian.net/browse/{REF}`.
- Screenshots are downloaded, compressed (configurable max dimension + JPEG quality), and embedded inline (data URLs) so offline HTML still shows evidence.

## Columns and layout
- Columns (default): `ID | Title | Status | Assignee | Priority | Attachments`
- Fixed widths for consistent readability:
  - Title is the widest; Assignee is second widest.
  - Table uses `table-layout: fixed` and wraps long text.
- Sorting: non‑Passed appear first (Failed → Blocked → Retest → Untested → Passed).
- Pagination: 25 rows per page, with Prev/Next controls per run.

## Template customization
The HTML is rendered with Jinja2 using `templates/daily_report.html.j2`. You can:
- Change column order or widths (update the `<colgroup>` and headers)
- Add or remove fields shown per test
- Adjust colors for the donut chart or status pills
- Customize attachment cards/inline evidence in `templates/daily_report.html.j2`.

## CI/CD and Automation
- GitHub Actions
  - CI: `.github/workflows/ci.yml` — installs deps, compiles, and checks CLI help. Pair this with Render's auto‑deploy on push to build and deploy the Docker image.
    - Recommended: enable auto‑deploy on Render for your Web Service so every push to `main` triggers a deploy.

## Troubleshooting
- Empty report: ensure API credentials and base URL are correct, and the plan/run IDs exist for the given project.
- Count mismatches: this script uses `get_tests` for status to match TestRail’s own counts. If you customize it to use results, deduplicate to the latest per `test_id`.
- Missing names: if a user or priority is missing, the script falls back to the raw ID.
- 404 on UI: confirm you started the server in the repo root with `uvicorn app.main:app --reload`, then open `http://127.0.0.1:8000/`.
- Attachments not visible after download: ensure you regenerated the report after upgrading (older HTML lacked inline images). Inline rendering requires modern browsers that support data URLs.
- Slow generation: adjust worker/attachment env vars:
  - `RUN_WORKERS` / `RUN_WORKERS_MAX` – concurrent runs fetched (defaults 2/4, hard cap 8)
  - `ATTACHMENT_WORKERS` – concurrent attachment downloads (default 2, max 4)
  - `ATTACHMENT_IMAGE_MAX_DIM` and `ATTACHMENT_JPEG_QUALITY` – controls compression
  - `ATTACHMENT_INLINE_MAX_BYTES` (default 250000) – inline small images; set 0 to disable
  - `ATTACHMENT_VIDEO_INLINE_MAX_BYTES` (defaults to image inline limit) – inline small videos for offline playback
  - `ATTACHMENT_MAX_BYTES` – skip attachments above this size

## Roadmap ideas
- Optional per-run donut charts
- CSV/Excel export
- Filters (e.g., hide Untested)

## License
Internal/Private unless specified otherwise.
