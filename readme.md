# TestRail Daily HTML Report

Generate a clean HTML summary for a TestRail project’s plan or run. The report includes per-run breakdowns (Passed/Untested/Failed/Blocked/Obsolete/Retest), fixed-width tables with Title and Assignee emphasized, assignee and priority names, and a project-level donut chart. Project and plan names link back to TestRail.

## Features
- Project + Plan context with links to TestRail
- Per-run totals and status breakdown (Passed, Untested, Failed, Blocked, Obsolete, Retest)
- Fixed-width table columns (Title widest, Assignee second)
- Assignee names resolved from TestRail users
- Priority names resolved from TestRail priorities
- Single project-level donut chart of status distribution
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

## Usage

Run against a plan (aggregates all runs inside the plan):

```bash
python3 testrail_daily_report.py --project 1 --plan 241
```

Or run against a single run:

```bash
python3 testrail_daily_report.py --project 1 --run 1234
```

Output is saved to `out/report_YYYY-MM-DD.html` and can be opened in a browser.

## How it works (data sources)
- Runs in a plan are enumerated via `get_plan/<plan_id>`.
- Test status comes from `get_tests/<run_id>` (field `status_id`) to match TestRail run page counts exactly. The script maps IDs to names via `get_statuses` and shows “Untested” for tests without a result.
- Latest results per test are fetched via `get_results_for_run/<run_id>` only for enrichment (e.g., comments/attachments if needed), but do not affect the status shown.
- Assignee names come from `get_users` (with `get_user/<id>` fallback).
- Priority names come from `get_priorities`.

## Columns and layout
- Columns: `ID | Title | Status | Assignee | Refs | Priority`
- Fixed widths for consistent readability:
  - Title is the widest; Assignee is second widest.
  - Table uses `table-layout: fixed` and wraps long text.

## Template customization
The HTML is rendered with Jinja2 using `templates/daily_report.html.j2`. You can:
- Change column order or widths (update the `<colgroup>` and headers)
- Add or remove fields shown per test
- Adjust colors for the donut chart or status pills

## Troubleshooting
- Empty report: ensure API credentials and base URL are correct, and the plan/run IDs exist for the given project.
- Count mismatches: this script uses `get_tests` for status to match TestRail’s own counts. If you customize it to use results, deduplicate to the latest per `test_id`.
- Missing names: if a user or priority is missing, the script falls back to the raw ID.

## Roadmap ideas
- Optional per-run donut charts
- CSV/Excel export
- Filters (e.g., hide Untested)

## License
Internal/Private unless specified otherwise.
