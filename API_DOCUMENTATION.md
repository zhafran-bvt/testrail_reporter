# TestRail Reporter API Documentation

## Overview

The TestRail Reporter provides a REST API for generating reports, managing TestRail content, and accessing dashboard statistics. All endpoints return JSON responses unless otherwise specified.

## Base URL

```
http://localhost:8080
```

(Replace with your deployment URL in production)

## Authentication

The API uses TestRail credentials configured via environment variables. No additional authentication is required for API endpoints.

## Common Response Formats

### Success Response
```json
{
  "data": { ... },
  "meta": {
    "cache": {
      "hit": true,
      "expires_at": "2024-12-04T10:30:00Z",
      "seconds_remaining": 120
    }
  }
}
```

### Error Response
```json
{
  "detail": "Error message describing what went wrong"
}
```

## Dashboard Endpoints

### GET /api/dashboard/plans

Fetch paginated list of test plans with statistics.

**Query Parameters:**
- `project` (int, default: 1): Project ID
- `is_completed` (int, optional): Filter by completion (0=active, 1=completed)
- `limit` (int, optional): Plans per page (default: 50, max: 200)
- `offset` (int, default: 0): Number of plans to skip
- `created_after` (int, optional): Unix timestamp filter
- `created_before` (int, optional): Unix timestamp filter
- `search` (string, optional): Search term for plan names

**Response:**
```json
{
  "plans": [
    {
      "plan_id": 123,
      "plan_name": "Sprint 42 Testing",
      "created_on": 1701388800,
      "is_completed": false,
      "updated_on": 1701475200,
      "total_runs": 5,
      "total_tests": 150,
      "status_distribution": {
        "Passed": 120,
        "Failed": 10,
        "Blocked": 5,
        "Retest": 3,
        "Untested": 12
      },
      "pass_rate": 85.5,
      "completion_rate": 92.0,
      "failed_count": 10,
      "blocked_count": 5,
      "untested_count": 12
    }
  ],
  "total_count": 47,
  "offset": 0,
  "limit": 50,
  "has_more": false,
  "meta": {
    "cache": {
      "hit": false,
      "expires_at": "2024-12-04T10:30:00Z",
      "seconds_remaining": 300
    }
  }
}
```

**Status Codes:**
- 200: Success
- 400: Invalid parameters
- 502: TestRail API error
- 504: TestRail API timeout
- 500: Server error

**Cache:** 5 minutes (configurable via `DASHBOARD_PLANS_CACHE_TTL`)

---

### GET /api/dashboard/plan/{plan_id}

Fetch detailed information for a specific plan including all runs.

**Path Parameters:**
- `plan_id` (int, required): TestRail plan ID

**Response:**
```json
{
  "plan": {
    "plan_id": 123,
    "plan_name": "Sprint 42 Testing",
    "created_on": 1701388800,
    "is_completed": false,
    "updated_on": 1701475200,
    "total_runs": 3,
    "total_tests": 150,
    "status_distribution": { ... },
    "pass_rate": 85.5,
    "completion_rate": 92.0,
    "failed_count": 10,
    "blocked_count": 5,
    "untested_count": 12
  },
  "runs": [
    {
      "run_id": 456,
      "run_name": "Smoke Tests",
      "suite_name": "Core Functionality",
      "is_completed": true,
      "total_tests": 50,
      "status_distribution": { ... },
      "pass_rate": 90.0,
      "completion_rate": 100.0,
      "updated_on": 1701475200
    }
  ],
  "meta": {
    "cache": {
      "hit": true,
      "expires_at": "2024-12-04T10:25:00Z",
      "seconds_remaining": 120
    }
  }
}
```

**Status Codes:**
- 200: Success
- 400: Invalid plan_id
- 404: Plan not found
- 502: TestRail API error
- 504: TestRail API timeout
- 500: Server error

**Cache:** 3 minutes (configurable via `DASHBOARD_PLAN_DETAIL_CACHE_TTL`)

---

### GET /api/dashboard/runs/{plan_id}

Fetch list of runs for a specific plan with statistics.

**Path Parameters:**
- `plan_id` (int, required): TestRail plan ID

**Response:**
```json
{
  "plan_id": 123,
  "runs": [
    {
      "run_id": 456,
      "run_name": "Smoke Tests",
      "suite_name": "Core Functionality",
      "is_completed": true,
      "total_tests": 50,
      "status_distribution": {
        "Passed": 45,
        "Failed": 2,
        "Blocked": 1,
        "Retest": 0,
        "Untested": 2
      },
      "pass_rate": 90.0,
      "completion_rate": 96.0,
      "updated_on": 1701475200
    }
  ],
  "meta": {
    "cache": {
      "hit": false,
      "expires_at": "2024-12-04T10:22:00Z",
      "seconds_remaining": 120
    }
  }
}
```

**Status Codes:**
- 200: Success
- 400: Invalid plan_id
- 502: TestRail API error
- 504: TestRail API timeout
- 500: Server error

**Cache:** 2 minutes (configurable via `DASHBOARD_RUN_STATS_CACHE_TTL`)

---

### GET /api/dashboard/config

Fetch dashboard configuration values.

**Response:**
```json
{
  "cache": {
    "plans_ttl": 300,
    "plan_detail_ttl": 180,
    "stats_ttl": 120,
    "run_stats_ttl": 120
  },
  "pagination": {
    "default_page_size": 50,
    "max_page_size": 200
  },
  "visual_thresholds": {
    "pass_rate_high": 80,
    "pass_rate_medium": 50,
    "critical_fail_threshold": 20,
    "critical_block_threshold": 10
  }
}
```

**Status Codes:**
- 200: Success

**Cache:** No caching (always returns current configuration)

---

### POST /api/dashboard/cache/clear

Clear all dashboard caches to force fresh data fetch.

**Request Body:** None

**Response:**
```json
{
  "status": "success",
  "message": "All dashboard caches cleared",
  "cleared_caches": [
    "dashboard_plans",
    "dashboard_plan_detail",
    "dashboard_stats",
    "dashboard_run_stats"
  ]
}
```

**Status Codes:**
- 200: Success

---

## Report Generation Endpoints

### GET /api/report

Generate a test report synchronously (legacy endpoint).

**Query Parameters:**
- `project` (int, default: 1): Project ID
- `plan` (int, optional): Plan ID (mutually exclusive with `run`)
- `run` (int, optional): Run ID (mutually exclusive with `plan`)
- `run_ids` (list[int], optional): Specific run IDs to include (requires `plan`)

**Response:**
```json
{
  "path": "out/report_plan_123_20241204_103000.html",
  "url": "/reports/report_plan_123_20241204_103000.html"
}
```

**Status Codes:**
- 200: Success
- 400: Invalid parameters
- 502: TestRail API error
- 500: Server error

---

### POST /api/report

Generate a test report asynchronously (returns job ID).

**Request Body:**
```json
{
  "project": 1,
  "plan": 123,
  "run": null,
  "run_ids": [456, 789]
}
```

**Response:**
```json
{
  "id": "a1b2c3d4e5f6",
  "status": "queued",
  "created_at": "2024-12-04T10:30:00Z",
  "started_at": null,
  "completed_at": null,
  "path": null,
  "url": null,
  "error": null,
  "meta": {},
  "params": {
    "project": 1,
    "plan": 123,
    "run_ids": [456, 789]
  },
  "queue_position": 0
}
```

**Status Codes:**
- 202: Accepted (job queued)
- 400: Invalid parameters

---

### GET /api/report/{job_id}

Check status of an asynchronous report generation job.

**Path Parameters:**
- `job_id` (string, required): Job ID returned from POST /api/report

**Response (Queued):**
```json
{
  "id": "a1b2c3d4e5f6",
  "status": "queued",
  "queue_position": 2,
  ...
}
```

**Response (Running):**
```json
{
  "id": "a1b2c3d4e5f6",
  "status": "running",
  "started_at": "2024-12-04T10:30:05Z",
  "meta": {
    "stage": "fetching_tests",
    "stage_payload": {
      "run_id": 456,
      "progress": "50/100"
    }
  },
  ...
}
```

**Response (Success):**
```json
{
  "id": "a1b2c3d4e5f6",
  "status": "success",
  "started_at": "2024-12-04T10:30:05Z",
  "completed_at": "2024-12-04T10:30:45Z",
  "path": "out/report_plan_123_20241204_103000.html",
  "url": "/reports/report_plan_123_20241204_103000.html",
  "meta": {
    "generated_at": "2024-12-04T10:30:45Z",
    "duration_ms": 40000,
    "api_call_count": 15,
    "api_calls": [...]
  },
  ...
}
```

**Response (Error):**
```json
{
  "id": "a1b2c3d4e5f6",
  "status": "error",
  "error": "Failed to fetch plan: Plan not found",
  "completed_at": "2024-12-04T10:30:10Z",
  ...
}
```

**Status Codes:**
- 200: Success
- 404: Job not found

---

## Management Endpoints

### POST /api/manage/plan

Create a new test plan.

**Request Body:**
```json
{
  "project": 1,
  "name": "Sprint 42 Testing",
  "description": "Testing for Sprint 42 features",
  "milestone_id": 10,
  "dry_run": false
}
```

**Response:**
```json
{
  "plan": {
    "id": 123,
    "name": "Sprint 42 Testing",
    "description": "Testing for Sprint 42 features",
    ...
  }
}
```

**Status Codes:**
- 200: Success
- 400: Invalid parameters
- 502: TestRail API error
- 500: Server error

---

### PUT /api/manage/plan/{plan_id}

Update an existing test plan.

**Path Parameters:**
- `plan_id` (int, required): TestRail plan ID

**Request Body:**
```json
{
  "name": "Sprint 42 Testing - Updated",
  "description": "Updated description for Sprint 42",
  "milestone_id": 11,
  "dry_run": false
}
```

All fields are optional. Only provided fields will be updated; omitted fields remain unchanged.

**Dry Run Mode:**
Set `dry_run: true` to preview changes without actually updating TestRail. The response will show what would be changed.

**Response:**
```json
{
  "plan": {
    "id": 123,
    "name": "Sprint 42 Testing - Updated",
    "description": "Updated description for Sprint 42",
    "milestone_id": 11,
    ...
  },
  "updated_fields": ["name", "description", "milestone_id"]
}
```

**Status Codes:**
- 200: Success
- 400: Invalid parameters or validation error
- 404: Plan not found
- 502: TestRail API error
- 500: Server error

**Validation Rules:**
- `name` must not be empty if provided
- `description` can be empty or null
- `milestone_id` must be a valid milestone ID if provided

---

### DELETE /api/manage/plan/{plan_id}

Delete a test plan from TestRail.

**Path Parameters:**
- `plan_id` (int, required): TestRail plan ID

**Query Parameters:**
- `dry_run` (bool, optional, default: false): Preview deletion without executing

**Dry Run Mode:**
Set `dry_run=true` to preview what would be deleted without actually deleting. Useful for validation.

**Response (Success):**
```json
{
  "status": "success",
  "message": "Plan 123 deleted successfully",
  "plan_id": 123,
  "plan_name": "Sprint 42 Testing"
}
```

**Response (Dry Run):**
```json
{
  "status": "dry_run",
  "message": "Would delete plan 123",
  "plan_id": 123,
  "plan_name": "Sprint 42 Testing",
  "warning": "This plan contains 5 runs that will also be deleted"
}
```

**Status Codes:**
- 200: Success
- 400: Invalid parameters
- 404: Plan not found
- 502: TestRail API error
- 500: Server error

**Important Notes:**
- Deleting a plan also deletes all runs within that plan (cascade deletion)
- This operation cannot be undone
- Always use dry_run first to verify what will be deleted
- Cache entries for the deleted plan are automatically cleared

---

### POST /api/manage/run

Create a new test run.

**Request Body:**
```json
{
  "project": 1,
  "plan_id": 123,
  "name": "Smoke Tests",
  "description": "Quick smoke test suite",
  "refs": "JIRA-123,JIRA-456",
  "include_all": true,
  "case_ids": null,
  "dry_run": false
}
```

**Response:**
```json
{
  "run": {
    "id": 456,
    "name": "Smoke Tests",
    "suite_id": 1,
    ...
  }
}
```

**Status Codes:**
- 200: Success
- 400: Invalid parameters
- 502: TestRail API error
- 500: Server error

---

### PUT /api/manage/run/{run_id}

Update an existing test run.

**Path Parameters:**
- `run_id` (int, required): TestRail run ID

**Request Body:**
```json
{
  "name": "Smoke Tests - Updated",
  "description": "Updated smoke test suite",
  "refs": "JIRA-123,JIRA-456,JIRA-789",
  "dry_run": false
}
```

All fields are optional. Only provided fields will be updated; omitted fields remain unchanged.

**Dry Run Mode:**
Set `dry_run: true` to preview changes without actually updating TestRail.

**Response:**
```json
{
  "run": {
    "id": 456,
    "name": "Smoke Tests - Updated",
    "description": "Updated smoke test suite",
    "refs": "JIRA-123,JIRA-456,JIRA-789",
    ...
  },
  "updated_fields": ["name", "description", "refs"]
}
```

**Status Codes:**
- 200: Success
- 400: Invalid parameters or validation error
- 404: Run not found
- 502: TestRail API error
- 500: Server error

**Validation Rules:**
- `name` must not be empty if provided
- `description` can be empty or null
- `refs` can be empty or null

---

### DELETE /api/manage/run/{run_id}

Delete a test run from TestRail.

**Path Parameters:**
- `run_id` (int, required): TestRail run ID

**Query Parameters:**
- `dry_run` (bool, optional, default: false): Preview deletion without executing

**Dry Run Mode:**
Set `dry_run=true` to preview what would be deleted without actually deleting.

**Response (Success):**
```json
{
  "status": "success",
  "message": "Run 456 deleted successfully",
  "run_id": 456,
  "run_name": "Smoke Tests"
}
```

**Response (Dry Run):**
```json
{
  "status": "dry_run",
  "message": "Would delete run 456",
  "run_id": 456,
  "run_name": "Smoke Tests",
  "warning": "This run contains 50 test cases with results"
}
```

**Status Codes:**
- 200: Success
- 400: Invalid parameters
- 404: Run not found
- 502: TestRail API error
- 500: Server error

**Important Notes:**
- Deleting a run also deletes all test results within that run
- This operation cannot be undone
- Always use dry_run first to verify what will be deleted
- Cache entries for the deleted run are automatically cleared

---

### POST /api/manage/case

Create a new test case.

**Request Body:**
```json
{
  "project": 1,
  "title": "Verify login functionality",
  "refs": "JIRA-789",
  "bdd_scenarios": "Given user is on login page\nWhen user enters valid credentials\nThen user is logged in",
  "dry_run": false
}
```

**Response:**
```json
{
  "case": {
    "id": 789,
    "title": "Verify login functionality",
    "section_id": 69,
    ...
  }
}
```

**Status Codes:**
- 200: Success
- 400: Invalid parameters
- 502: TestRail API error
- 500: Server error

---

### PUT /api/manage/case/{case_id}

Update an existing test case.

**Path Parameters:**
- `case_id` (int, required): TestRail case ID

**Request Body:**
```json
{
  "title": "Verify login functionality - Updated",
  "refs": "JIRA-789,JIRA-790",
  "bdd_scenarios": "Given user is on login page\nWhen user enters valid credentials\nAnd 2FA is enabled\nThen user is prompted for 2FA code",
  "dry_run": false
}
```

All fields are optional. Only provided fields will be updated; omitted fields remain unchanged.

**Dry Run Mode:**
Set `dry_run: true` to preview changes without actually updating TestRail.

**Response:**
```json
{
  "case": {
    "id": 789,
    "title": "Verify login functionality - Updated",
    "refs": "JIRA-789,JIRA-790",
    "custom_preconds": "Given user is on login page\nWhen user enters valid credentials\nAnd 2FA is enabled\nThen user is prompted for 2FA code",
    ...
  },
  "updated_fields": ["title", "refs", "custom_preconds"]
}
```

**Status Codes:**
- 200: Success
- 400: Invalid parameters or validation error
- 404: Case not found
- 502: TestRail API error
- 500: Server error

**Validation Rules:**
- `title` must not be empty if provided
- `refs` can be empty or null
- `bdd_scenarios` can be empty or null

---

### DELETE /api/manage/case/{case_id}

Delete a test case from TestRail.

**Path Parameters:**
- `case_id` (int, required): TestRail case ID

**Query Parameters:**
- `dry_run` (bool, optional, default: false): Preview deletion without executing

**Dry Run Mode:**
Set `dry_run=true` to preview what would be deleted without actually deleting.

**Response (Success):**
```json
{
  "status": "success",
  "message": "Case 789 deleted successfully",
  "case_id": 789,
  "case_title": "Verify login functionality"
}
```

**Response (Dry Run):**
```json
{
  "status": "dry_run",
  "message": "Would delete case 789",
  "case_id": 789,
  "case_title": "Verify login functionality",
  "warning": "This case is used in 3 active test runs"
}
```

**Status Codes:**
- 200: Success
- 400: Invalid parameters
- 404: Case not found
- 502: TestRail API error
- 500: Server error

**Important Notes:**
- Deleting a case removes it from all test runs and suites
- This operation cannot be undone
- Always use dry_run first to verify what will be deleted
- Consider the impact on active test runs before deletion

---

## Utility Endpoints

### GET /api/plans

List plans for a project (legacy endpoint, used by Reporter view).

**Query Parameters:**
- `project` (int, default: 1): Project ID
- `is_completed` (int, optional): Filter by completion (0 or 1)

**Response:**
```json
{
  "count": 10,
  "plans": [
    {
      "id": 123,
      "name": "Sprint 42 Testing",
      "is_completed": false,
      "created_on": 1701388800
    }
  ],
  "meta": {
    "cache": {
      "hit": true,
      "expires_at": "2024-12-04T10:33:00Z",
      "seconds_remaining": 180
    }
  }
}
```

**Cache:** 3 minutes (configurable via `PLANS_CACHE_TTL`)

---

### GET /api/runs

List runs for a plan (legacy endpoint, used by Reporter view).

**Query Parameters:**
- `plan` (int, required): Plan ID
- `project` (int, default: 1): Project ID

**Response:**
```json
{
  "count": 5,
  "runs": [
    {
      "id": 456,
      "name": "Smoke Tests",
      "is_completed": true,
      "suite_name": "Core Functionality"
    }
  ],
  "meta": {
    "cache": {
      "hit": false,
      "expires_at": "2024-12-04T10:31:00Z",
      "seconds_remaining": 60
    }
  }
}
```

**Cache:** 1 minute (configurable via `RUNS_CACHE_TTL`)

---

### GET /api/cases

List test cases for a project/suite/section.

**Query Parameters:**
- `project` (int, default: 1): Project ID
- `suite_id` (int, optional): Suite ID
- `section_id` (int, optional): Section ID
- `filters` (string, optional): JSON-encoded filter object

**Response:**
```json
{
  "count": 50,
  "cases": [
    {
      "id": 789,
      "title": "Verify login functionality",
      "refs": "JIRA-789",
      "updated_on": 1701388800,
      "priority_id": 2,
      "section_id": 69
    }
  ]
}
```

---

### GET /api/users

List users for the project.

**Query Parameters:**
- `project` (int, default: 1): Project ID

**Response:**
```json
{
  "count": 10,
  "users": [
    {
      "id": 1,
      "name": "John Doe"
    }
  ]
}
```

---

### GET /healthz

Health check endpoint.

**Response:**
```json
{
  "ok": true,
  "queue": {
    "size": 5,
    "running": 1,
    "queued": 4,
    "history_limit": 60,
    "latest_job": {
      "id": "a1b2c3d4",
      "status": "running"
    }
  },
  "http": {
    "timeout_seconds": 20,
    "retries": 3,
    "backoff_seconds": 2
  }
}
```

---

## Rate Limiting

Currently, no rate limiting is implemented. Consider adding rate limiting in production environments, especially for:
- Cache clearing endpoints
- Report generation endpoints
- Management endpoints (create operations)

## Error Handling

All endpoints follow consistent error response format:

```json
{
  "detail": "Error message"
}
```

Common error scenarios:
- 400: Invalid request parameters
- 404: Resource not found
- 502: TestRail API connection error
- 504: TestRail API timeout
- 500: Internal server error

## Caching Strategy

The API uses TTL-based caching with the following defaults:

| Cache Type | TTL | Environment Variable |
|------------|-----|---------------------|
| Dashboard Plans | 5 min | DASHBOARD_PLANS_CACHE_TTL |
| Dashboard Plan Detail | 3 min | DASHBOARD_PLAN_DETAIL_CACHE_TTL |
| Dashboard Statistics | 2 min | DASHBOARD_STATS_CACHE_TTL |
| Dashboard Run Statistics | 2 min | DASHBOARD_RUN_STATS_CACHE_TTL |
| Plans List | 3 min | PLANS_CACHE_TTL |
| Runs List | 1 min | RUNS_CACHE_TTL |

Cache keys include all query parameters, so different filter combinations have separate cache entries.

## Best Practices

1. **Use Pagination**: Always use `limit` and `offset` for large datasets
2. **Cache Awareness**: Understand that data may be cached; use refresh when needed
3. **Error Handling**: Always handle error responses appropriately
4. **Async Reports**: Use async endpoint for large reports to avoid timeouts
5. **Filter Early**: Apply filters at API level rather than client-side
6. **Monitor Health**: Check `/healthz` endpoint for system status

## Examples

### Dashboard Examples

#### Fetch Active Plans with High Failure Rate

```bash
curl "http://localhost:8080/api/dashboard/plans?project=1&is_completed=0&limit=25"
```

Then filter client-side for plans with `pass_rate < 50`.

#### Clear Dashboard Cache

```bash
curl -X POST "http://localhost:8080/api/dashboard/cache/clear"
```

---

### Report Generation Examples

#### Generate Report for Specific Runs

```bash
curl -X POST "http://localhost:8080/api/report" \
  -H "Content-Type: application/json" \
  -d '{
    "project": 1,
    "plan": 123,
    "run_ids": [456, 789]
  }'
```

#### Check Report Job Status

```bash
curl "http://localhost:8080/api/report/a1b2c3d4e5f6"
```

---

### CRUD Operation Examples

#### Update a Test Plan

Update plan name and description:

```bash
curl -X PUT "http://localhost:8080/api/manage/plan/123" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sprint 42 Testing - Updated",
    "description": "Updated description for Sprint 42"
  }'
```

Preview update without applying (dry run):

```bash
curl -X PUT "http://localhost:8080/api/manage/plan/123" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sprint 42 Testing - Updated",
    "dry_run": true
  }'
```

#### Update a Test Run

Update run name and add references:

```bash
curl -X PUT "http://localhost:8080/api/manage/run/456" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Smoke Tests - Updated",
    "refs": "JIRA-123,JIRA-456,JIRA-789"
  }'
```

#### Update a Test Case

Update case title and BDD scenarios:

```bash
curl -X PUT "http://localhost:8080/api/manage/case/789" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Verify login with 2FA",
    "bdd_scenarios": "Given user is on login page\nWhen user enters valid credentials\nAnd 2FA is enabled\nThen user is prompted for 2FA code"
  }'
```

#### Delete a Test Plan (with dry run)

First, preview what would be deleted:

```bash
curl -X DELETE "http://localhost:8080/api/manage/plan/123?dry_run=true"
```

If the preview looks correct, execute the deletion:

```bash
curl -X DELETE "http://localhost:8080/api/manage/plan/123"
```

#### Delete a Test Run

Preview deletion:

```bash
curl -X DELETE "http://localhost:8080/api/manage/run/456?dry_run=true"
```

Execute deletion:

```bash
curl -X DELETE "http://localhost:8080/api/manage/run/456"
```

#### Delete a Test Case

Preview deletion:

```bash
curl -X DELETE "http://localhost:8080/api/manage/case/789?dry_run=true"
```

Execute deletion:

```bash
curl -X DELETE "http://localhost:8080/api/manage/case/789"
```

#### Batch Update Multiple Plans

Use a script to update multiple plans:

```bash
#!/bin/bash
PLAN_IDS=(123 124 125)
for plan_id in "${PLAN_IDS[@]}"; do
  curl -X PUT "http://localhost:8080/api/manage/plan/$plan_id" \
    -H "Content-Type: application/json" \
    -d '{
      "milestone_id": 11
    }'
done
```

#### Update with Error Handling

```bash
response=$(curl -s -w "\n%{http_code}" -X PUT "http://localhost:8080/api/manage/plan/123" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Plan Name"
  }')

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" -eq 200 ]; then
  echo "Success: $body"
else
  echo "Error ($http_code): $body"
fi
```
