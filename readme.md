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
- Streaming renderer keeps memory stable by writing run data to NDJSON and only snapshotting a few preview cards for tests
- Download button returns a `.zip` bundle (HTML + `/out/attachments/run_*`) so offline reports still include evidence
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
  - The Download button fetches the `.zip` bundle next to each HTML (`Testing_Progress_Report_*.zip`) so attachments are available offline.

## Report output & streaming

- **Streaming renderer:** each run is serialized to a temp NDJSON file and streamed into the template. Only a small snapshot (`TABLE_SNAPSHOT_LIMIT`, default 3) is kept in memory for unit tests and preview cards.
- **Bundles:** every successful job produces both the HTML (`out/*.html`) and a bundle (`out/*.zip`) containing that HTML plus `out/attachments/run_*`. The UI already downloads the `.zip`.
- **Snapshots:** set `REPORT_TABLE_SNAPSHOT=0` to disable in-memory preview tables entirely (useful in production), or adjust `TABLE_SNAPSHOT_LIMIT` when running tests that need more preview rows.
- **Attachment directories:** attachments live under `out/attachments/run_<id>/...`; the bundle logic now works with absolute paths (important when `WORKDIR=/app` in Docker).

## Environment knobs (beyond credentials)

| Variable | Purpose | Notes |
| --- | --- | --- |
| `REPORT_WORKERS`, `REPORT_WORKERS_MAX`, `REPORT_WORKERS_MIN` | concurrent jobs in the internal queue | Keep low (1–2) unless you have plenty of RAM; each job downloads attachments + renders HTML. |
| `RUN_WORKERS`, `RUN_WORKERS_MAX` | number of TestRail runs processed simultaneously per job | Higher values speed up plans with many runs but increase peak memory. |
| `ATTACHMENT_WORKERS`, `ATTACHMENT_WORKERS_MAX` | attachment download threads per run | Useful for hiding network latency; combine with `ATTACHMENT_BATCH_SIZE` to cap concurrent files. |
| `ATTACHMENT_BATCH_SIZE` | split attachment downloads into batches | `0` disables batching; otherwise the size of each batch submitted to the thread pool. |
| `ATTACHMENT_MAX_BYTES`, `ATTACHMENT_INLINE_MAX_BYTES`, `ATTACHMENT_VIDEO_INLINE_MAX_BYTES`, `ATTACHMENT_IMAGE_MAX_DIM`, `ATTACHMENT_JPEG_QUALITY`, `ATTACHMENT_MIN_JPEG_QUALITY` | governs compression + skip rules | Set `ATTACHMENT_MAX_BYTES` lower to avoid enormous blobs; inline limits control when we embed base64 payloads. |
| `REPORT_TABLE_SNAPSHOT`, `TABLE_SNAPSHOT_LIMIT` | controls preview tables used by tests/UI | Disable snapshots in production or shrink the limit to reduce memory. |
| `REPORT_JOB_HISTORY` | number of completed jobs retained in memory | Default 60; keep modest to avoid unbounded metadata. |
| `MEM_LOG_INTERVAL` | seconds between `[mem-log]` heartbeat lines | Helps observe allocator behavior in production. |

All env variables can live in `.env` for local work; deployments (Railway, Render, etc.) can override them per environment.

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
- Slow generation or high memory: tune the worker env vars listed above, lower `ATTACHMENT_MAX_BYTES`, or raise `ATTACHMENT_BATCH_SIZE` to reduce concurrent files.
- Bundle missing attachments: confirm `out/attachments/run_*` exists and that the download button grabs the `.zip` (HTML-only downloads no longer embed files).
- Memory stuck high in Docker: the Dockerfile now ships with `libjemalloc` and `MALLOC_CONF="background_thread:true,dirty_decay_ms:200,muzzy_decay_ms:200,narenas:2,oversize_threshold:131072"` so RSS drops after jobs. If you fork the image, keep those settings or expect glibc to hold the high-water mark.

## Roadmap ideas
- Optional per-run donut charts
- CSV/Excel export
- Filters (e.g., hide Untested)

## License
Internal/Private unless specified otherwise.
