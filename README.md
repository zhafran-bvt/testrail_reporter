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
- Video attachments can be auto-transcoded via ffmpeg (resolution + bitrate caps) before embedding
- Streaming renderer keeps memory stable by writing run data to NDJSON and only snapshotting a few preview cards for tests
- Download button saves the rendered HTML directly (attachments are already inlined for offline use)
- Robust API handling (pagination, mixed payload shapes)
- **Dashboard view** for monitoring test plans and runs with real-time statistics, filtering, and visual indicators

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
- `TESTRAIL_HTTP_TIMEOUT`: Per-request timeout in seconds for TestRail API calls (default: `20`)
- `TESTRAIL_HTTP_RETRIES`: Retry attempts for API/attachment calls on 429/5xx/timeouts (default: `3`)
- `TESTRAIL_HTTP_BACKOFF`: Initial backoff in seconds between retries; grows exponentially (default: `1.6`)

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

### Management & CRUD Operations

The application provides full CRUD (Create, Read, Update, Delete) operations for test plans, runs, and cases:

**Management API endpoints:**
- `POST /api/manage/plan` → create a new test plan
- `PUT /api/manage/plan/{plan_id}` → update an existing plan
- `DELETE /api/manage/plan/{plan_id}` → delete a plan (with cascade)
- `POST /api/manage/run` → create a new test run
- `PUT /api/manage/run/{run_id}` → update an existing run
- `DELETE /api/manage/run/{run_id}` → delete a run
- `POST /api/manage/case` → create a new test case
- `PUT /api/manage/case/{case_id}` → update an existing case
- `DELETE /api/manage/case/{case_id}` → delete a case

**CRUD features:**
- Update operations support partial updates (only specified fields are changed)
- Delete operations support dry_run mode for safe preview
- Cascade deletion: deleting a plan deletes all its runs
- Automatic cache invalidation after updates/deletes
- UI provides edit and delete buttons with confirmation dialogs
- Form validation ensures data integrity

For detailed CRUD operation documentation, see [CRUD Operations Guide](docs/CRUD_OPERATIONS_GUIDE.md).

**BDD Scenarios Gherkin Formatting:**
- Automatic conversion of JSON stringify format to readable Gherkin
- Proper indentation for Given/When/Then/And/But keywords
- Real-time formatting when editing test cases
- No manual conversion needed - works automatically
- Backward compatible with existing TestRail data

For BDD scenarios documentation, see [Gherkin Parsing Guide](docs/GHERKIN_PARSING.md) and [User Guide](docs/USER_GUIDE_GHERKIN.md).

### Dashboard

The dashboard provides a real-time overview of test plans and runs with statistics, filtering, and visual indicators:

**Dashboard API endpoints:**
- `GET /api/dashboard/plans` → paginated list of plans with statistics
  - Query params: `project`, `is_completed`, `limit`, `offset`, `created_after`, `created_before`, `search`
- `GET /api/dashboard/plan/{plan_id}` → detailed plan info with all runs
- `GET /api/dashboard/runs/{plan_id}` → list of runs for a plan with statistics
- `GET /api/dashboard/config` → dashboard configuration values (thresholds, pagination)
- `POST /api/dashboard/cache/clear` → clear all dashboard caches for fresh data

**Dashboard features:**
- Paginated plan lists with search and filtering
- Real-time statistics (pass rate, completion rate, status distribution)
- Color-coded visual indicators based on pass rates
- Critical issue highlighting for high failure/block rates
- Sortable columns (name, date, pass rate, test count)
- Expandable plan details showing all runs
- Integrated report generation from dashboard
- Responsive design for mobile/tablet/desktop
- Configurable caching for performance

**Dashboard configuration:**

The dashboard behavior can be customized via environment variables:

```bash
# Cache TTL (seconds) - how long to cache dashboard data
DASHBOARD_PLANS_CACHE_TTL=300          # Plan list cache (5 minutes)
DASHBOARD_PLAN_DETAIL_CACHE_TTL=180   # Plan detail cache (3 minutes)
DASHBOARD_STATS_CACHE_TTL=120         # Statistics cache (2 minutes)
DASHBOARD_RUN_STATS_CACHE_TTL=120     # Run statistics cache (2 minutes)

# Pagination
DASHBOARD_DEFAULT_PAGE_SIZE=25        # Default number of plans per page
DASHBOARD_MAX_PAGE_SIZE=25            # Maximum allowed page size

# Visual thresholds (percentages)
DASHBOARD_PASS_RATE_HIGH=80           # Green color threshold (>= 80%)
DASHBOARD_PASS_RATE_MEDIUM=50         # Yellow color threshold (>= 50%)
DASHBOARD_CRITICAL_FAIL_THRESHOLD=20  # Highlight if failed > 20%
DASHBOARD_CRITICAL_BLOCK_THRESHOLD=10 # Highlight if blocked > 10%
```

All dashboard configuration values have sensible defaults and can be adjusted based on your needs.

Notes:
- Provide exactly one of `plan` or `run`.
- Project defaults to `1` in most flows, but can be passed explicitly.
- **Single web process:** the async job queue keeps its state in-process, so production deployments must run FastAPI with a single uvicorn worker (this repo’s `Procfile`/`Dockerfile` already enforce `--workers 1`). `REPORT_WORKERS_*` controls report generation parallelism.
- **Long reports need long timeouts:** generating big plans with attachments can easily exceed 30 s, so the provided commands set `--timeout-keep-alive 120`. If your host injects its own run command, match or exceed those keep-alive/timeouts so the worker isn’t restarted mid-report.
- UI behavior:
  - Preview button opens the generated HTML in a new tab and shows a modal spinner until the file downloads.
  - Plans list auto-loads open plans first; if none, it falls back to all plans.
  - Runs list appears after picking a plan; you can search/filter, select-all, or clear selections.
  - The Download button saves the HTML that is already loaded (all attachments are embedded as data URLs).

## Report output & streaming

- **Streaming renderer:** each run is serialized to a temp NDJSON file and streamed into the template. Only a small snapshot (`TABLE_SNAPSHOT_LIMIT`, default 3) is kept in memory for unit tests and preview cards.
- **Self-contained HTML:** attachments are compressed/encoded as data URLs, so the HTML alone contains every inline asset without leaving disk artifacts behind.
- **Snapshots:** set `REPORT_TABLE_SNAPSHOT=0` to disable in-memory preview tables entirely (useful in production), or adjust `TABLE_SNAPSHOT_LIMIT` when running tests that need more preview rows.
- **Attachment directories:** attachment downloads stay in temp files only while the report is rendering; nothing persists under `out/attachments` once the HTML is written.

## Environment knobs (beyond credentials)

| Variable | Purpose | Notes |
| --- | --- | --- |
| `REPORT_WORKERS`, `REPORT_WORKERS_MAX`, `REPORT_WORKERS_MIN` | concurrent jobs in the internal queue | Keep low (1–2) unless you have plenty of RAM; each job downloads attachments + renders HTML. |
| `RUN_WORKERS`, `RUN_WORKERS_MAX` | number of TestRail runs processed simultaneously per job | Higher values speed up plans with many runs but increase peak memory. |
| `ATTACHMENT_WORKERS`, `ATTACHMENT_WORKERS_MAX` | attachment download threads per run | Useful for hiding network latency; combine with `ATTACHMENT_BATCH_SIZE` to cap concurrent files. |
| `ATTACHMENT_BATCH_SIZE` | split attachment downloads into batches | `0` disables batching; otherwise the size of each batch submitted to the thread pool. |
| `ATTACHMENT_MAX_BYTES`, `ATTACHMENT_INLINE_MAX_BYTES`, `ATTACHMENT_VIDEO_INLINE_MAX_BYTES`, `ATTACHMENT_IMAGE_MAX_DIM`, `ATTACHMENT_JPEG_QUALITY`, `ATTACHMENT_MIN_JPEG_QUALITY` | governs compression + skip rules | Set `ATTACHMENT_MAX_BYTES` lower to avoid enormous blobs; inline limits control when we embed base64 payloads. |
| `ATTACHMENT_VIDEO_TRANSCODE`, `ATTACHMENT_VIDEO_MAX_DIM`, `ATTACHMENT_VIDEO_TARGET_KBPS`, `ATTACHMENT_VIDEO_FFMPEG_PRESET`, `FFMPEG_BIN` | video compression controls | When enabled, ffmpeg transcodes videos to H.264/AAC using these limits before embedding inline. |
| `REPORT_TABLE_SNAPSHOT`, `TABLE_SNAPSHOT_LIMIT` | controls preview tables used by tests/UI | Disable snapshots in production or shrink the limit to reduce memory. |
| `REPORT_JOB_HISTORY` | number of completed jobs retained in memory | Default 60; keep modest to avoid unbounded metadata. |
| `MEM_LOG_INTERVAL` | seconds between `[mem-log]` heartbeat lines | Helps observe allocator behavior in production. |
| `TESTRAIL_HTTP_TIMEOUT`, `TESTRAIL_HTTP_RETRIES`, `TESTRAIL_HTTP_BACKOFF` | request timeout/retry/backoff for all TestRail calls (including attachments) | Retries on 429, 5xx, timeouts, and connection errors; backoff grows each attempt. |
| `DASHBOARD_PLANS_CACHE_TTL`, `DASHBOARD_PLAN_DETAIL_CACHE_TTL`, `DASHBOARD_STATS_CACHE_TTL`, `DASHBOARD_RUN_STATS_CACHE_TTL` | cache TTL in seconds for dashboard data | Controls how long dashboard data is cached before refreshing. Defaults: 300, 180, 120, 120. |
| `DASHBOARD_DEFAULT_PAGE_SIZE`, `DASHBOARD_MAX_PAGE_SIZE` | pagination limits for dashboard plan lists | Default page size is 25, maximum is 25. |
| `DASHBOARD_PASS_RATE_HIGH`, `DASHBOARD_PASS_RATE_MEDIUM` | pass rate thresholds for color coding (percentages) | Green for >= high (80), yellow for >= medium (50), red for < medium. |
| `DASHBOARD_CRITICAL_FAIL_THRESHOLD`, `DASHBOARD_CRITICAL_BLOCK_THRESHOLD` | thresholds for highlighting critical issues (percentages) | Plans/runs with failed > 20% or blocked > 10% get prominent highlighting. |

All env variables can live in `.env` for local work; deployments (Railway, Render, etc.) can override them per environment.

## Automation Management (Docker)

The Automation Management UI reads `.feature` files and can run Cypress locally. In Docker, the container needs access to the `orbis-test-automation` repo.

Required env vars:
- `AUTOMATION_REPO_ROOT` → absolute path to the repo inside the container
- `AUTOMATION_FEATURES_ROOT` → absolute path to `apps/<app>/cypress` inside the container

By default, the Dockerfile now **bakes the orbis-test-automation repo into the image** (`testrail-automation-management` branch). You can override the repo or ref at build time:

```bash
docker build \
  --build-arg ORBIS_AUTOMATION_REPO=https://github.com/bvarta-tech/orbis-test-automation.git \
  --build-arg ORBIS_AUTOMATION_REF=testrail-automation-management \
  -t testrail-daily-report:latest .
```

If you use `docker compose`, set `ORBIS_AUTOMATION_REPO` / `ORBIS_AUTOMATION_REF` in `.env` and the build args are applied automatically.

Runtime sync (no rebuild):
- Set `AUTOMATION_GIT_SYNC=1` to `git fetch` + reset to `ORBIS_AUTOMATION_REF` on container start.
- Use `AUTOMATION_APP_PATH` if the Cypress app path is not `apps/lokasi_intelligence`.
- `AUTOMATION_NPM_INSTALL=1` installs deps when `node_modules` is missing (default on).

Example Docker run (host path `/opt/orbis-test-automation`), if you want to **override** the baked repo with a local checkout:

```bash
docker run \
  -v /opt/orbis-test-automation:/opt/orbis-test-automation \
  -e AUTOMATION_REPO_ROOT=/opt/orbis-test-automation \
  -e AUTOMATION_FEATURES_ROOT=/opt/orbis-test-automation/apps/lokasi_intelligence/cypress \
  -p 8080:8080 \
  <your-image>
```

Notes:
- The container must have `node`/`npm` available and the automation repo dependencies installed (`npm ci` in the repo).
- If the repo path is missing, the UI shows a warning and disables automation actions.
 - A host volume mount will override the baked-in repo path.

## Suggested environment profiles

**Memory-conscious (≤4 GB)**
- `REPORT_WORKERS=1`, `RUN_WORKERS=2`, `ATTACHMENT_WORKERS=3`
- `ATTACHMENT_BATCH_SIZE=10`, `ATTACHMENT_MAX_BYTES=75000000`
- `REPORT_TABLE_SNAPSHOT=0` (skip preview tables) and `TABLE_SNAPSHOT_LIMIT=1`
- Favor `ATTACHMENT_INLINE_MAX_BYTES=200000` to keep embedded blobs small
- Set `REPORT_WORKER_IDLE_SECS=60` so idle threads release memory sooner

**Throughput-focused (≥8 GB)**
- `REPORT_WORKERS=3`, `RUN_WORKERS=4`, `ATTACHMENT_WORKERS=8`
- `ATTACHMENT_BATCH_SIZE=0` (no batching) for maximum parallel downloads
- Keep `REPORT_TABLE_SNAPSHOT=1` with `TABLE_SNAPSHOT_LIMIT=3` for UI previews
- Increase `ATTACHMENT_MAX_BYTES` if your plans require large media
- Ensure `MEM_LOG_INTERVAL=30` so you can monitor peaks during load tests

Use these as starting points—mix and match depending on your SLA (e.g., bump `ATTACHMENT_WORKERS` only when TestRail rate limits allow it).

## Debugging

- Health: `GET /healthz` returns `{ "ok": true }` plus queue stats and the active HTTP timeout/retry settings.
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
- Missing attachments: confirm `ATTACHMENT_INLINE_MAX_BYTES` and video/image limits are high enough for your evidence. Oversized files are marked as skipped instead of being written next to the HTML.
- Memory stuck high in Docker: the Dockerfile now ships with `libjemalloc` and `MALLOC_CONF="background_thread:true,dirty_decay_ms:600,muzzy_decay_ms:600"` so RSS drops after jobs. If you fork the image, keep those settings or expect glibc to hold the high-water mark.

## Documentation

Comprehensive documentation is available for all features:

- **[API Documentation](docs/API_DOCUMENTATION.md)** - Complete API reference with examples
  - Dashboard endpoints
  - Report generation endpoints
  - Management/CRUD endpoints
  - Error handling and status codes
  - Caching strategy

- **[CRUD Operations Guide](docs/CRUD_OPERATIONS_GUIDE.md)** - Detailed guide for managing TestRail entities
  - Update operations (plans, runs, cases)
  - Delete operations with cascade rules
  - Dry run mode usage
  - UI workflow instructions
  - Best practices and common workflows
  - Error handling and troubleshooting

- **[Dashboard Guide](docs/DASHBOARD_GUIDE.md)** - Dashboard usage instructions
  - Features overview
  - Filtering and sorting
  - Visual indicators
  - Report generation
  - Responsive design
  - Configuration options

- **[Configuration Guide](docs/CONFIGURATION.md)** - Environment variable reference
  - TestRail connection settings
  - Performance tuning
  - Cache configuration
  - Dashboard thresholds

- **[Gherkin Parsing Guide](docs/GHERKIN_PARSING.md)** - BDD scenarios formatting
  - Automatic JSON stringify to Gherkin conversion
  - Technical implementation details
  - Supported formats and edge cases
  - Troubleshooting guide

- **[User Guide: Gherkin](docs/USER_GUIDE_GHERKIN.md)** - How to use BDD scenarios
  - Step-by-step usage instructions
  - Before/after examples
  - Writing good BDD scenarios
  - Tips and best practices

- **[Gherkin Examples](docs/GHERKIN_EXAMPLES.md)** - Real-world BDD scenario examples
  - 8 practical examples with transformations
  - Login flows, API testing, error handling
  - Mobile app and integration test scenarios

## Roadmap ideas
- Optional per-run donut charts
- CSV/Excel export
- Filters (e.g., hide Untested)

## License
Internal/Private unless specified otherwise.
