# TestRail CRUD Operations Guide

## Overview

The TestRail Reporter application provides full CRUD (Create, Read, Update, Delete) operations for managing test plans, runs, and cases. This guide covers both API usage and UI interactions for performing these operations safely and effectively.

## Table of Contents

1. [Update Operations](#update-operations)
2. [Delete Operations](#delete-operations)
3. [Dry Run Mode](#dry-run-mode)
4. [UI Guide](#ui-guide)
5. [Best Practices](#best-practices)
6. [Error Handling](#error-handling)
7. [Common Workflows](#common-workflows)

---

## Update Operations

Update operations allow you to modify existing TestRail entities without recreating them. All update operations support partial updates—only the fields you provide will be changed, and all other fields remain unchanged.

### Update a Test Plan

**API Endpoint:** `PUT /api/manage/plan/{plan_id}`

**Updatable Fields:**
- `name` (string): Plan name (must not be empty)
- `description` (string): Plan description (can be empty)
- `milestone_id` (int): Associated milestone ID

**Example Request:**

```bash
curl -X PUT "http://localhost:8080/api/manage/plan/123" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sprint 42 Testing - Updated",
    "description": "Updated description for Sprint 42",
    "milestone_id": 11
  }'
```

**Example Response:**

```json
{
  "plan": {
    "id": 123,
    "name": "Sprint 42 Testing - Updated",
    "description": "Updated description for Sprint 42",
    "milestone_id": 11,
    "created_on": 1701388800,
    "is_completed": false
  },
  "updated_fields": ["name", "description", "milestone_id"]
}
```

**Validation Rules:**
- Plan name cannot be empty
- Plan ID must exist in TestRail
- Milestone ID must be valid if provided

---

### Update a Test Run

**API Endpoint:** `PUT /api/manage/run/{run_id}`

**Updatable Fields:**
- `name` (string): Run name (must not be empty)
- `description` (string): Run description (can be empty)
- `refs` (string): Comma-separated reference IDs (e.g., "JIRA-123,JIRA-456")

**Example Request:**

```bash
curl -X PUT "http://localhost:8080/api/manage/run/456" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Smoke Tests - Updated",
    "description": "Updated smoke test suite",
    "refs": "JIRA-123,JIRA-456,JIRA-789"
  }'
```

**Example Response:**

```json
{
  "run": {
    "id": 456,
    "name": "Smoke Tests - Updated",
    "description": "Updated smoke test suite",
    "refs": "JIRA-123,JIRA-456,JIRA-789",
    "suite_id": 1,
    "is_completed": false
  },
  "updated_fields": ["name", "description", "refs"]
}
```

**Validation Rules:**
- Run name cannot be empty
- Run ID must exist in TestRail
- References can be empty or null

---

### Update a Test Case

**API Endpoint:** `PUT /api/manage/case/{case_id}`

**Updatable Fields:**
- `title` (string): Case title (must not be empty)
- `refs` (string): Comma-separated reference IDs
- `bdd_scenarios` (string): BDD-style test scenarios (stored in custom_preconds field)

**Example Request:**

```bash
curl -X PUT "http://localhost:8080/api/manage/case/789" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Verify login with 2FA",
    "refs": "JIRA-789,JIRA-790",
    "bdd_scenarios": "Given user is on login page\nWhen user enters valid credentials\nAnd 2FA is enabled\nThen user is prompted for 2FA code"
  }'
```

**Example Response:**

```json
{
  "case": {
    "id": 789,
    "title": "Verify login with 2FA",
    "refs": "JIRA-789,JIRA-790",
    "custom_preconds": "Given user is on login page\nWhen user enters valid credentials\nAnd 2FA is enabled\nThen user is prompted for 2FA code",
    "section_id": 69,
    "priority_id": 2
  },
  "updated_fields": ["title", "refs", "custom_preconds"]
}
```

**Validation Rules:**
- Case title cannot be empty
- Case ID must exist in TestRail
- BDD scenarios can be empty or null

---

## Delete Operations

Delete operations permanently remove entities from TestRail. These operations cannot be undone, so always use dry run mode first to verify what will be deleted.

### Delete a Test Plan

**API Endpoint:** `DELETE /api/manage/plan/{plan_id}`

**Query Parameters:**
- `dry_run` (bool, optional): Preview deletion without executing

**Important:** Deleting a plan also deletes all runs within that plan (cascade deletion).

**Example Request (Dry Run):**

```bash
curl -X DELETE "http://localhost:8080/api/manage/plan/123?dry_run=true"
```

**Example Response (Dry Run):**

```json
{
  "status": "dry_run",
  "message": "Would delete plan 123",
  "plan_id": 123,
  "plan_name": "Sprint 42 Testing",
  "warning": "This plan contains 5 runs that will also be deleted"
}
```

**Example Request (Execute):**

```bash
curl -X DELETE "http://localhost:8080/api/manage/plan/123"
```

**Example Response (Success):**

```json
{
  "status": "success",
  "message": "Plan 123 deleted successfully",
  "plan_id": 123,
  "plan_name": "Sprint 42 Testing"
}
```

**Side Effects:**
- All runs in the plan are deleted
- All test results in those runs are deleted
- Cache entries for the plan are cleared
- Dashboard will no longer show the plan

---

### Delete a Test Run

**API Endpoint:** `DELETE /api/manage/run/{run_id}`

**Query Parameters:**
- `dry_run` (bool, optional): Preview deletion without executing

**Important:** Deleting a run also deletes all test results within that run.

**Example Request (Dry Run):**

```bash
curl -X DELETE "http://localhost:8080/api/manage/run/456?dry_run=true"
```

**Example Response (Dry Run):**

```json
{
  "status": "dry_run",
  "message": "Would delete run 456",
  "run_id": 456,
  "run_name": "Smoke Tests",
  "warning": "This run contains 50 test cases with results"
}
```

**Example Request (Execute):**

```bash
curl -X DELETE "http://localhost:8080/api/manage/run/456"
```

**Example Response (Success):**

```json
{
  "status": "success",
  "message": "Run 456 deleted successfully",
  "run_id": 456,
  "run_name": "Smoke Tests"
}
```

**Side Effects:**
- All test results in the run are deleted
- Cache entries for the run are cleared
- Plan statistics are updated (if run was part of a plan)

---

### Delete a Test Case

**API Endpoint:** `DELETE /api/manage/case/{case_id}`

**Query Parameters:**
- `dry_run` (bool, optional): Preview deletion without executing

**Important:** Deleting a case removes it from all test runs and suites.

**Example Request (Dry Run):**

```bash
curl -X DELETE "http://localhost:8080/api/manage/case/789?dry_run=true"
```

**Example Response (Dry Run):**

```json
{
  "status": "dry_run",
  "message": "Would delete case 789",
  "case_id": 789,
  "case_title": "Verify login functionality",
  "warning": "This case is used in 3 active test runs"
}
```

**Example Request (Execute):**

```bash
curl -X DELETE "http://localhost:8080/api/manage/case/789"
```

**Example Response (Success):**

```json
{
  "status": "success",
  "message": "Case 789 deleted successfully",
  "case_id": 789,
  "case_title": "Verify login functionality"
}
```

**Side Effects:**
- Case is removed from all test runs
- Case is removed from the test suite
- Historical results for this case remain in completed runs

---

## Dry Run Mode

Dry run mode allows you to preview the effects of an operation without actually executing it. This is especially important for delete operations, which cannot be undone.

### How Dry Run Works

1. **Update Operations**: Shows what fields would be changed and their new values
2. **Delete Operations**: Shows what would be deleted and any cascade effects

### When to Use Dry Run

- **Always** before deleting plans, runs, or cases
- When updating multiple entities in a batch
- When testing automation scripts
- When training new team members
- When unsure about the impact of an operation

### Example: Dry Run Workflow

```bash
# Step 1: Preview the deletion
curl -X DELETE "http://localhost:8080/api/manage/plan/123?dry_run=true"

# Step 2: Review the response
# {
#   "status": "dry_run",
#   "message": "Would delete plan 123",
#   "warning": "This plan contains 5 runs that will also be deleted"
# }

# Step 3: If everything looks correct, execute the deletion
curl -X DELETE "http://localhost:8080/api/manage/plan/123"
```

---

## UI Guide

The TestRail Reporter UI provides intuitive interfaces for CRUD operations in the Management view.

### Accessing the Management View

1. Open the TestRail Reporter application
2. Click the "Management" icon in the side navigation
3. Select your project from the dropdown

### Editing Entities

#### Edit a Test Plan

1. Navigate to the Management view
2. Find the plan you want to edit in the plans list
3. Click the "Edit" button (pencil icon) on the plan card
4. A modal form will appear with the current plan details
5. Modify the fields you want to change:
   - Plan Name
   - Description
   - Milestone
6. Click "Save Changes" to update the plan
7. A success message will appear, and the plan card will refresh with new data

**Form Validation:**
- Plan name is required and cannot be empty
- Description is optional
- Milestone is optional

#### Edit a Test Run

1. Navigate to the Management view
2. Select a plan to view its runs
3. Find the run you want to edit
4. Click the "Edit" button on the run card
5. Modify the fields in the modal form:
   - Run Name
   - Description
   - References (comma-separated)
6. Click "Save Changes"
7. The run card will refresh with updated data

#### Edit a Test Case

1. Navigate to the Management view
2. Select a suite and section to view cases
3. Find the case you want to edit
4. Click the "Edit" button on the case card
5. Modify the fields in the modal form:
   - Case Title
   - References
   - BDD Scenarios
6. Click "Save Changes"
7. The case card will refresh with updated data

### Deleting Entities

#### Delete a Test Plan

1. Navigate to the Management view
2. Find the plan you want to delete
3. Click the "Delete" button (trash icon) on the plan card
4. A confirmation dialog will appear showing:
   - Plan name
   - Number of runs that will be deleted
   - Warning about cascade deletion
5. Review the information carefully
6. Click "Confirm Delete" to proceed or "Cancel" to abort
7. If confirmed, the plan will be deleted and removed from the display
8. A success message will appear

**Visual Indicators:**
- Delete button is styled in red to indicate danger
- Confirmation dialog has a warning icon
- Plan name is highlighted in the confirmation message

#### Delete a Test Run

1. Navigate to the Management view
2. Select a plan to view its runs
3. Find the run you want to delete
4. Click the "Delete" button on the run card
5. A confirmation dialog will appear showing:
   - Run name and suite
   - Number of test cases with results
6. Review the information carefully
7. Click "Confirm Delete" to proceed or "Cancel" to abort
8. The run will be deleted and removed from the display

#### Delete a Test Case

1. Navigate to the Management view
2. Select a suite and section to view cases
3. Find the case you want to delete
4. Click the "Delete" button on the case card
5. A confirmation dialog will appear showing:
   - Case title
   - Warning about removal from all runs
6. Review the information carefully
7. Click "Confirm Delete" to proceed or "Cancel" to abort
8. The case will be deleted and removed from the display

### Error Handling in UI

If an operation fails, the UI will:

1. Display an error message with details
2. Retain the form data (for updates) so you can correct and retry
3. Keep the entity in the display (for deletes)
4. Log the error to the browser console for debugging

**Common Error Messages:**
- "Plan not found" - The plan may have been deleted by another user
- "Validation error: name cannot be empty" - Required field is missing
- "Failed to connect to TestRail" - Network or API issue
- "Permission denied" - User lacks necessary permissions

---

## Best Practices

### General Best Practices

1. **Always Use Dry Run First**
   - Preview all delete operations before executing
   - Test update operations on non-critical entities first
   - Use dry run when automating CRUD operations

2. **Validate Before Updating**
   - Ensure required fields are not empty
   - Verify IDs exist before attempting operations
   - Check permissions before bulk operations

3. **Handle Errors Gracefully**
   - Always check HTTP status codes
   - Parse error messages for user-friendly display
   - Implement retry logic for transient failures

4. **Clear Cache After Changes**
   - Dashboard cache is automatically cleared for affected entities
   - Consider manually refreshing dashboard after bulk operations
   - Be aware of cache TTL when verifying changes

5. **Document Changes**
   - Keep a log of significant deletions
   - Document reasons for bulk updates
   - Maintain audit trail for compliance

### Update Best Practices

1. **Partial Updates**
   - Only include fields you want to change
   - Omit fields that should remain unchanged
   - This prevents accidental overwrites

2. **Batch Updates**
   - Use scripts for updating multiple entities
   - Include error handling and logging
   - Consider rate limiting to avoid API throttling

3. **Validation**
   - Validate data before sending to API
   - Use dry run to verify changes
   - Test on non-production data first

### Delete Best Practices

1. **Confirmation**
   - Always require explicit confirmation
   - Show what will be deleted (including cascades)
   - Provide clear warnings about irreversibility

2. **Cascade Awareness**
   - Understand cascade deletion rules:
     - Deleting a plan deletes all its runs
     - Deleting a run deletes all its results
     - Deleting a case removes it from all runs
   - Use dry run to see cascade effects

3. **Backup Strategy**
   - Export important data before deletion
   - Keep TestRail backups up to date
   - Document deletion procedures

4. **Timing**
   - Avoid deleting during active testing
   - Coordinate with team before major deletions
   - Consider archiving instead of deleting

---

## Error Handling

### Common Error Scenarios

#### 400 Bad Request

**Cause:** Invalid parameters or validation error

**Examples:**
- Empty required field (name, title)
- Invalid data type (string instead of int)
- Malformed JSON

**Solution:**
- Validate input before sending
- Check API documentation for required fields
- Ensure JSON is properly formatted

#### 404 Not Found

**Cause:** Entity doesn't exist in TestRail

**Examples:**
- Plan/run/case was already deleted
- Wrong ID provided
- Entity belongs to different project

**Solution:**
- Verify the ID exists in TestRail
- Check if entity was deleted by another user
- Ensure you're querying the correct project

#### 502 Bad Gateway

**Cause:** TestRail API connection error

**Examples:**
- TestRail server is down
- Network connectivity issues
- Invalid TestRail credentials

**Solution:**
- Check TestRail server status
- Verify network connectivity
- Confirm TESTRAIL_* environment variables are correct

#### 500 Internal Server Error

**Cause:** Server-side error in Reporter application

**Examples:**
- Unexpected data format from TestRail
- Database connection issue
- Code bug

**Solution:**
- Check server logs for details
- Report bug to development team
- Try again after server restart

### Error Response Format

All errors follow a consistent format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Handling Errors in Code

**Python Example:**

```python
import requests

def update_plan(plan_id, data):
    url = f"http://localhost:8080/api/manage/plan/{plan_id}"
    
    try:
        response = requests.put(url, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"Plan {plan_id} not found")
        elif e.response.status_code == 400:
            print(f"Validation error: {e.response.json()['detail']}")
        else:
            print(f"Error: {e.response.json()['detail']}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return None
```

**JavaScript Example:**

```javascript
async function updatePlan(planId, data) {
  const url = `http://localhost:8080/api/manage/plan/${planId}`;
  
  try {
    const response = await fetch(url, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Failed to update plan:', error.message);
    return null;
  }
}
```

---

## Common Workflows

### Workflow 1: Update Plan Milestone for Sprint

**Scenario:** Update all plans for Sprint 42 to use the new milestone.

```bash
#!/bin/bash

# Configuration
MILESTONE_ID=11
PLAN_IDS=(123 124 125 126)

# Update each plan
for plan_id in "${PLAN_IDS[@]}"; do
  echo "Updating plan $plan_id..."
  
  # Dry run first
  response=$(curl -s -X PUT "http://localhost:8080/api/manage/plan/$plan_id" \
    -H "Content-Type: application/json" \
    -d "{\"milestone_id\": $MILESTONE_ID, \"dry_run\": true}")
  
  echo "Dry run result: $response"
  
  # Execute update
  curl -X PUT "http://localhost:8080/api/manage/plan/$plan_id" \
    -H "Content-Type: application/json" \
    -d "{\"milestone_id\": $MILESTONE_ID}"
  
  echo "Plan $plan_id updated"
  echo "---"
done

echo "All plans updated successfully"
```

### Workflow 2: Clean Up Old Test Plans

**Scenario:** Delete completed plans older than 90 days.

```bash
#!/bin/bash

# Get list of old completed plans
plans=$(curl -s "http://localhost:8080/api/dashboard/plans?project=1&is_completed=1&limit=200")

# Parse plan IDs (requires jq)
plan_ids=$(echo "$plans" | jq -r '.plans[] | select(.created_on < (now - 7776000)) | .plan_id')

# Delete each plan
for plan_id in $plan_ids; do
  echo "Checking plan $plan_id..."
  
  # Dry run to see what would be deleted
  dry_run=$(curl -s -X DELETE "http://localhost:8080/api/manage/plan/$plan_id?dry_run=true")
  echo "Would delete: $dry_run"
  
  # Prompt for confirmation
  read -p "Delete plan $plan_id? (y/n) " -n 1 -r
  echo
  
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    curl -X DELETE "http://localhost:8080/api/manage/plan/$plan_id"
    echo "Plan $plan_id deleted"
  else
    echo "Skipped plan $plan_id"
  fi
  
  echo "---"
done
```

### Workflow 3: Bulk Update Run References

**Scenario:** Add a JIRA ticket reference to all runs in a plan.

```bash
#!/bin/bash

PLAN_ID=123
JIRA_REF="JIRA-999"

# Get all runs for the plan
runs=$(curl -s "http://localhost:8080/api/dashboard/runs/$PLAN_ID")

# Parse run IDs (requires jq)
run_ids=$(echo "$runs" | jq -r '.runs[].run_id')

# Update each run
for run_id in $run_ids; do
  echo "Updating run $run_id..."
  
  # Get current refs (would need to fetch run details first in real scenario)
  # For simplicity, we'll just append the new ref
  
  curl -X PUT "http://localhost:8080/api/manage/run/$run_id" \
    -H "Content-Type: application/json" \
    -d "{\"refs\": \"$JIRA_REF\"}"
  
  echo "Run $run_id updated"
done

echo "All runs updated with reference $JIRA_REF"
```

### Workflow 4: Safe Deletion with Backup

**Scenario:** Delete a plan but export its data first.

```bash
#!/bin/bash

PLAN_ID=123

# Step 1: Generate a report (backup)
echo "Generating backup report..."
report=$(curl -s -X POST "http://localhost:8080/api/report" \
  -H "Content-Type: application/json" \
  -d "{\"project\": 1, \"plan\": $PLAN_ID}")

report_path=$(echo "$report" | jq -r '.path')
echo "Backup saved to: $report_path"

# Step 2: Dry run deletion
echo "Previewing deletion..."
dry_run=$(curl -s -X DELETE "http://localhost:8080/api/manage/plan/$PLAN_ID?dry_run=true")
echo "$dry_run"

# Step 3: Confirm with user
read -p "Proceed with deletion? (y/n) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
  # Step 4: Execute deletion
  result=$(curl -s -X DELETE "http://localhost:8080/api/manage/plan/$PLAN_ID")
  echo "$result"
  echo "Plan deleted. Backup available at: $report_path"
else
  echo "Deletion cancelled"
fi
```

### Workflow 5: Update Case Titles in Bulk

**Scenario:** Add a prefix to all case titles in a section.

```python
import requests

BASE_URL = "http://localhost:8080"
PROJECT_ID = 1
SECTION_ID = 69
PREFIX = "[Automated] "

# Get all cases in the section
response = requests.get(f"{BASE_URL}/api/cases", params={
    "project": PROJECT_ID,
    "section_id": SECTION_ID
})
cases = response.json()["cases"]

# Update each case
for case in cases:
    case_id = case["id"]
    current_title = case["title"]
    
    # Skip if already has prefix
    if current_title.startswith(PREFIX):
        print(f"Skipping case {case_id}: already has prefix")
        continue
    
    new_title = PREFIX + current_title
    
    # Dry run first
    dry_run_response = requests.put(
        f"{BASE_URL}/api/manage/case/{case_id}",
        json={"title": new_title, "dry_run": True}
    )
    print(f"Dry run for case {case_id}: {dry_run_response.json()}")
    
    # Execute update
    update_response = requests.put(
        f"{BASE_URL}/api/manage/case/{case_id}",
        json={"title": new_title}
    )
    
    if update_response.status_code == 200:
        print(f"Updated case {case_id}: {current_title} -> {new_title}")
    else:
        print(f"Failed to update case {case_id}: {update_response.json()}")

print("Bulk update complete")
```

---

## Security Considerations

1. **Authentication**
   - CRUD operations use TestRail credentials configured in environment variables
   - Ensure credentials have appropriate permissions
   - Never expose credentials in client-side code

2. **Authorization**
   - TestRail enforces user permissions
   - Users can only modify entities they have access to
   - 403 errors indicate insufficient permissions

3. **Audit Trail**
   - TestRail maintains its own audit log
   - Consider logging CRUD operations in your application
   - Keep records of bulk operations

4. **Rate Limiting**
   - Be mindful of TestRail API rate limits
   - Implement delays in bulk operations
   - Use batch operations when available

---

## Troubleshooting

### Updates Not Appearing in Dashboard

**Problem:** Updated entity doesn't show changes in dashboard

**Solutions:**
1. Click the Refresh button to clear cache
2. Wait for cache TTL to expire (up to 5 minutes)
3. Check if update actually succeeded (check API response)
4. Verify you're viewing the correct project

### Deletion Fails with "Entity Not Found"

**Problem:** Delete operation returns 404

**Solutions:**
1. Verify the entity ID is correct
2. Check if entity was already deleted
3. Ensure you're using the correct project
4. Refresh the page to get latest data

### Form Validation Errors

**Problem:** UI form shows validation errors

**Solutions:**
1. Ensure required fields are not empty
2. Check field length limits
3. Verify data types (numbers vs strings)
4. Review error message for specific field

### Cascade Deletion Concerns

**Problem:** Worried about accidentally deleting too much

**Solutions:**
1. Always use dry run first
2. Review the warning messages carefully
3. Export/backup data before deletion
4. Start with smaller entities (cases, then runs, then plans)

---

## Additional Resources

- [API Documentation](API_DOCUMENTATION.md) - Complete API reference
- [Dashboard Guide](DASHBOARD_GUIDE.md) - Dashboard usage instructions
- [Configuration Guide](CONFIGURATION.md) - Environment variable reference
- TestRail API Documentation - Official TestRail API docs

---

## Support

For issues or questions:

1. Check this guide and API documentation
2. Review server logs for error details
3. Check browser console for client-side errors
4. Contact your TestRail administrator for permission issues
5. Report bugs to the development team

---

**Last Updated:** December 4, 2024
