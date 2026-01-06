"""Management API endpoints for CRUD operations."""

import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, cast

import requests
from fastapi import APIRouter, Body, Depends, File, HTTPException, Request, UploadFile

import app.core.dependencies as dependencies
from app.core.config import config
from app.core.dependencies import require_write_enabled
from app.models.requests import AddTestResult, ManageCase, ManagePlan, ManageRun, UpdateCase, UpdatePlan, UpdateRun

router = APIRouter(prefix="/api/manage", tags=["management"])


def _resolve_testrail_client(request: Request):
    override = request.app.dependency_overrides.get(dependencies.get_testrail_client)
    if override:
        return override()
    return dependencies.get_testrail_client()


@router.post("/plan")
def create_plan(
    payload: ManagePlan, _write_enabled=Depends(require_write_enabled), client=Depends(_resolve_testrail_client)
):
    """Create a new test plan."""
    body: Dict[str, Any] = {
        "name": payload.name,
        "description": payload.description,
    }
    if payload.milestone_id is not None:
        body["milestone_id"] = cast(int, payload.milestone_id)

    if payload.dry_run:
        return {"dry_run": True, "payload": body, "project": payload.project}

    try:
        created = client.add_plan(payload.project, body)
        return {"plan": created}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"TestRail API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create plan: {str(e)}")


@router.post("/run")
def create_run(
    payload: ManageRun, _write_enabled=Depends(require_write_enabled), client=Depends(_resolve_testrail_client)
):
    """Create a new test run."""
    suite_id = config.DEFAULT_SUITE_ID
    if suite_id is None:
        raise HTTPException(
            status_code=400, detail="DEFAULT_SUITE_ID is required to create runs when suite_id is omitted"
        )

    body: Dict[str, Any] = {
        "suite_id": cast(int, suite_id),  # suite_id is guaranteed to be int here due to None check above
        "name": payload.name,
        "description": payload.description,
        "include_all": payload.include_all,
    }

    if payload.refs:
        body["refs"] = payload.refs
    if payload.case_ids:
        body["case_ids"] = payload.case_ids

    if payload.dry_run:
        target = "plan_entry" if payload.plan_id else "run"
        return {
            "dry_run": True,
            "target": target,
            "payload": body,
            "project": payload.project,
            "plan_id": payload.plan_id,
        }

    try:
        if payload.plan_id:
            created = client.add_plan_entry(payload.plan_id, body)
        else:
            created = client.add_run(payload.project, body)
        return {"run": created}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"TestRail API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create run: {str(e)}")


@router.post("/case")
def create_case(
    payload: ManageCase, _write_enabled=Depends(require_write_enabled), client=Depends(_resolve_testrail_client)
):
    """Create a new test case."""
    section_id = config.DEFAULT_SECTION_ID
    if section_id is None:
        raise HTTPException(status_code=400, detail="DEFAULT_SECTION_ID is required to create cases")

    body: Dict[str, Any] = {
        "title": payload.title,
        "refs": payload.refs,
    }

    # Add default template, type, and priority if configured
    if config.DEFAULT_TEMPLATE_ID is not None:
        body["template_id"] = config.DEFAULT_TEMPLATE_ID
    if config.DEFAULT_TYPE_ID is not None:
        body["type_id"] = config.DEFAULT_TYPE_ID
    if config.DEFAULT_PRIORITY_ID is not None:
        body["priority_id"] = config.DEFAULT_PRIORITY_ID

    # Convert BDD text into array of {content: ...}
    bdd_text = payload.bdd_scenarios or ""
    steps = [line.strip() for line in bdd_text.splitlines() if line.strip()]
    if steps:
        combined = "\n".join(steps)
        body["custom_testrail_bdd_scenario"] = [{"content": combined}]

    # Remove None fields
    body = {k: v for k, v in body.items() if v is not None}

    if payload.dry_run:
        return {"dry_run": True, "payload": body, "section_id": section_id}

    try:
        created = client.add_case(section_id, body)
        return {"case": created}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"TestRail API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create case: {str(e)}")


@router.put("/plan/{plan_id}")
def update_plan(
    plan_id: int,
    payload: UpdatePlan,
    _write_enabled=Depends(require_write_enabled),
    client=Depends(_resolve_testrail_client),
):
    """Update an existing test plan."""
    # Validate plan_id
    if plan_id < 1:
        raise HTTPException(status_code=400, detail="Plan ID must be positive")

    # Build update payload with only non-None fields
    body: Dict[str, Any] = {}
    if payload.name is not None:
        body["name"] = payload.name
    if payload.description is not None:
        body["description"] = payload.description
    if payload.milestone_id is not None:
        body["milestone_id"] = cast(int, payload.milestone_id)

    # If no fields to update, return error
    if not body:
        raise HTTPException(status_code=400, detail="At least one field must be provided for update")

    if payload.dry_run:
        return {
            "dry_run": True,
            "plan_id": plan_id,
            "payload": body,
        }

    try:
        updated = client.update_plan(plan_id, body)
        return {"plan": updated}
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
        raise HTTPException(status_code=502, detail=f"TestRail API error: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update plan: {str(e)}")


@router.put("/run/{run_id}")
def update_run(
    run_id: int,
    payload: UpdateRun,
    _write_enabled=Depends(require_write_enabled),
    client=Depends(_resolve_testrail_client),
):
    """Update an existing test run."""
    # Validate run_id
    if run_id < 1:
        raise HTTPException(status_code=400, detail="Run ID must be positive")

    # Build update payload with only non-None fields
    body: Dict[str, Any] = {}
    if payload.name is not None:
        body["name"] = payload.name
    if payload.description is not None:
        body["description"] = payload.description
    if payload.refs is not None:
        body["refs"] = payload.refs

    # If no fields to update, return error
    if not body:
        raise HTTPException(status_code=400, detail="At least one field must be provided for update")

    if payload.dry_run:
        return {
            "dry_run": True,
            "run_id": run_id,
            "payload": body,
        }

    try:
        # Get run details to check if it's part of a plan
        try:
            run_data = client.get_run(run_id)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 400:
                raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
            raise

        plan_id = run_data.get("plan_id")

        # If run is part of a plan, we need to use update_plan_entry
        if plan_id:
            # Get plan details to find entry_id
            plan_data = client.get_plan(plan_id)
            entry_id = None

            # Find the entry that contains this run
            for entry in plan_data.get("entries", []):
                for run in entry.get("runs", []):
                    if run.get("id") == run_id:
                        entry_id = entry.get("id")
                        break
                if entry_id:
                    break

            if not entry_id:
                raise HTTPException(status_code=500, detail="Could not find plan entry for this run")

            # Update plan entry
            updated = client.update_plan_entry(plan_id, entry_id, body)

            # Extract the updated run from the entry
            updated_run = None
            for run in updated.get("runs", []):
                if run.get("id") == run_id:
                    updated_run = run
                    break

            return {"success": True, "run": updated_run or updated}
        else:
            # Standalone run, use update_run
            updated = client.update_run(run_id, body)
            return {"success": True, "run": updated}
    except HTTPException:
        raise
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        if e.response is not None and e.response.status_code == 403:
            raise HTTPException(
                status_code=403, detail="Cannot update this run. It may have restrictions or be locked."
            )
        raise HTTPException(status_code=502, detail=f"TestRail API error: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update run: {str(e)}")


@router.get("/case/{case_id}")
def get_case(case_id: int, client=Depends(_resolve_testrail_client)):
    """Get details for a specific test case."""
    # Validate case_id
    if case_id < 1:
        raise HTTPException(status_code=400, detail="Case ID must be positive")

    try:
        with client.make_session() as session:
            base_url = client.base_url

            # Fetch case details from TestRail
            response = session.get(f"{base_url}/index.php?/api/v2/get_case/{case_id}")
            response.raise_for_status()
            case_data = response.json()

            # Extract BDD scenarios if present
            bdd_scenario = None
            try:
                if "custom_testrail_bdd_scenario" in case_data:
                    bdd_field = case_data["custom_testrail_bdd_scenario"]
                    if isinstance(bdd_field, list) and len(bdd_field) > 0:
                        bdd_scenario = bdd_field[0].get("content", "")
                    elif isinstance(bdd_field, str):
                        bdd_scenario = bdd_field
            except Exception:
                # If there's any issue extracting BDD scenario, just set it to None
                pass

            return {
                "success": True,
                "case": {
                    "id": case_data.get("id"),
                    "title": case_data.get("title"),
                    "refs": case_data.get("refs"),
                    "custom_bdd_scenario": bdd_scenario,
                },
            }
    except requests.exceptions.HTTPError as e:
        if e.response and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
        raise HTTPException(status_code=502, detail=f"TestRail API error: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch case: {str(e)}")


@router.put("/case/{case_id}")
def update_case(
    case_id: int,
    payload: UpdateCase,
    _write_enabled=Depends(require_write_enabled),
    client=Depends(_resolve_testrail_client),
):
    """Update an existing test case."""
    # Validate case_id
    if case_id < 1:
        raise HTTPException(status_code=400, detail="Case ID must be positive")

    # Build update payload with only non-None fields
    body: Dict[str, Any] = {}
    if payload.title is not None:
        body["title"] = payload.title
    if payload.refs is not None:
        body["refs"] = payload.refs

    # Handle BDD scenarios if provided
    if payload.bdd_scenarios is not None:
        bdd_text = payload.bdd_scenarios
        steps = [line.strip() for line in bdd_text.splitlines() if line.strip()]
        if steps:
            combined = "\n".join(steps)
            body["custom_testrail_bdd_scenario"] = [{"content": combined}]

    # If no fields to update, return error
    if not body:
        raise HTTPException(status_code=400, detail="At least one field must be provided for update")

    if payload.dry_run:
        return {
            "dry_run": True,
            "case_id": case_id,
            "payload": body,
        }

    try:
        updated = client.update_case(case_id, body)
        return {"success": True, "case": updated}
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
        raise HTTPException(status_code=502, detail=f"TestRail API error: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update case: {str(e)}")


@router.post("/case/{case_id}/attachment")
async def add_case_attachment(
    case_id: int,
    file: UploadFile = File(...),
    _write_enabled=Depends(require_write_enabled),
    client=Depends(_resolve_testrail_client),
):
    """Upload a file attachment to a test case."""
    # Validate case_id
    if case_id < 1:
        raise HTTPException(status_code=400, detail="Case ID must be positive")

    # Validate file type
    content_type = file.content_type or ""
    if content_type not in config.ALLOWED_FILE_TYPES:
        allowed_types = ", ".join(config.ALLOWED_FILE_TYPES.values())
        raise HTTPException(status_code=400, detail=f"File type not allowed. Accepted types: {allowed_types}")

    # Read file content and validate size
    content = await file.read()
    file_size = len(content)

    if file_size > config.MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail=f"File size exceeds {config.MAX_FILE_SIZE_MB}MB limit")

    # Save to temporary file for upload
    filename = file.filename or "attachment"

    try:
        suffix = Path(filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            result = client.add_attachment_to_case(case_id, tmp_path, filename)

            # Build response with attachment metadata
            attachment = {
                "id": result.get("attachment_id"),
                "name": filename,
                "filename": filename,
                "size": file_size,
                "content_type": content_type,
                "created_on": int(time.time()),
            }

            return {"attachment": attachment}
        finally:
            # Clean up temp file
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass

    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
        raise HTTPException(status_code=502, detail=f"TestRail API error: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload attachment: {str(e)}")


@router.get("/case/{case_id}/attachments")
def get_case_attachments(case_id: int, client=Depends(_resolve_testrail_client)):
    """Get list of attachments for a test case."""
    # Validate case_id
    if case_id < 1:
        raise HTTPException(status_code=400, detail="Case ID must be positive")

    try:
        attachments = client.get_attachments_for_case(case_id)

        # Map attachments to response format and deduplicate by ID
        seen_ids = set()
        attachment_list = []
        for att in attachments:
            att_id = att.get("id")
            if att_id is None or att_id in seen_ids:
                continue

            seen_ids.add(att_id)

            att_name = att.get("name") or att.get("filename") or f"Attachment {att_id}"
            att_fname = att.get("filename") or att.get("name") or f"attachment_{att_id}"
            attachment_list.append(
                {
                    "id": att_id,
                    "name": att_name,
                    "filename": att_fname,
                    "size": att.get("size") or 0,
                    "content_type": att.get("content_type") or "application/octet-stream",
                    "created_on": att.get("created_on") or 0,
                }
            )

        return {
            "attachments": attachment_list,
            "count": len(attachment_list),
        }

    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
        raise HTTPException(status_code=502, detail=f"TestRail API error: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch attachments: {str(e)}")


@router.delete("/plan/{plan_id}")
def delete_plan(
    plan_id: int,
    dry_run: bool = False,
    _write_enabled=Depends(require_write_enabled),
    client=Depends(_resolve_testrail_client),
):
    """Delete a test plan from TestRail."""
    # Validate plan_id
    if plan_id < 1:
        raise HTTPException(status_code=400, detail="Plan ID must be positive")

    if dry_run:
        return {"dry_run": True, "plan_id": plan_id, "action": "delete_plan", "message": f"Would delete plan {plan_id}"}

    try:
        # Attempt to delete the plan
        client.delete_plan(plan_id)

        return {"success": True, "plan_id": plan_id, "message": f"Plan {plan_id} deleted successfully"}
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
        raise HTTPException(status_code=502, detail=f"TestRail API error: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete plan: {str(e)}")


@router.delete("/run/{run_id}")
def delete_run(
    run_id: int,
    dry_run: bool = False,
    _write_enabled=Depends(require_write_enabled),
    client=Depends(_resolve_testrail_client),
):
    """Delete a test run from TestRail."""
    # Validate run_id
    if run_id < 1:
        raise HTTPException(status_code=400, detail="Run ID must be positive")

    if dry_run:
        return {"dry_run": True, "run_id": run_id, "action": "delete_run", "message": f"Would delete run {run_id}"}

    try:
        # Get run details to check if it's part of a plan
        try:
            run_data = client.get_run(run_id)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 400:
                raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
            raise

        plan_id = run_data.get("plan_id")

        # If run is part of a plan, we need to delete the plan entry
        if plan_id:
            # Get plan details to find entry_id
            plan_data = client.get_plan(plan_id)
            entry_id = None

            # Find the entry that contains this run
            for entry in plan_data.get("entries", []):
                for run in entry.get("runs", []):
                    if run.get("id") == run_id:
                        entry_id = entry.get("id")
                        break
                if entry_id:
                    break

            if not entry_id:
                raise HTTPException(status_code=500, detail="Could not find plan entry for this run")

            # Delete plan entry (which deletes the run)
            client.delete_plan_entry(plan_id, entry_id)
        else:
            # Standalone run, use delete_run
            client.delete_run(run_id)

        return {"success": True, "run_id": run_id, "message": f"Run {run_id} deleted successfully"}
    except HTTPException:
        raise
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        if e.response is not None and e.response.status_code == 403:
            raise HTTPException(
                status_code=403, detail="Cannot delete this run. It may be part of a plan or have restrictions."
            )
        raise HTTPException(status_code=502, detail=f"TestRail API error: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete run: {str(e)}")


@router.delete("/case/{case_id}")
def delete_case(
    case_id: int,
    dry_run: bool = False,
    _write_enabled=Depends(require_write_enabled),
    client=Depends(_resolve_testrail_client),
):
    """Delete a test case from TestRail."""
    # Validate case_id
    if case_id < 1:
        raise HTTPException(status_code=400, detail="Case ID must be positive")

    if dry_run:
        return {"dry_run": True, "case_id": case_id, "action": "delete_case", "message": f"Would delete case {case_id}"}

    try:
        # Attempt to delete the case
        client.delete_case(case_id)

        return {"success": True, "case_id": case_id, "message": f"Case {case_id} deleted successfully"}
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
        raise HTTPException(status_code=502, detail=f"TestRail API error: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete case: {str(e)}")


@router.post("/test/{test_id}/result")
async def add_test_result(
    test_id: int,
    payload: AddTestResult,
    _write_enabled=Depends(require_write_enabled),
    client=Depends(_resolve_testrail_client),
):
    """Add a test result for a test."""
    # Validate test_id
    if test_id < 1:
        raise HTTPException(status_code=400, detail="Test ID must be positive")

    # Validate status_id (1=Passed, 2=Blocked, 3=Untested, 4=Retest, 5=Failed)
    if payload.status_id not in [1, 2, 3, 4, 5]:
        raise HTTPException(status_code=400, detail="Invalid status_id. Must be 1-5")

    # Build result payload
    body: Dict[str, Any] = {"status_id": payload.status_id}

    if payload.comment is not None:
        body["comment"] = payload.comment
    if payload.elapsed is not None:
        body["elapsed"] = payload.elapsed
    if payload.defects is not None:
        body["defects"] = payload.defects
    if payload.version is not None:
        body["version"] = payload.version
    if payload.assignedto_id is not None:
        body["assignedto_id"] = payload.assignedto_id

    try:
        result = client.add_result_for_test(test_id, body)
        return {"success": True, "result": result}
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Test {test_id} not found")
        raise HTTPException(status_code=502, detail=f"TestRail API error: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add result: {str(e)}")


@router.post("/result/{result_id}/attachment")
async def add_result_attachment(
    result_id: int,
    file: UploadFile = File(...),
    _write_enabled=Depends(require_write_enabled),
    client=Depends(_resolve_testrail_client),
):
    """Upload a file attachment to a test result."""
    # Validate result_id
    if result_id < 1:
        raise HTTPException(status_code=400, detail="Result ID must be positive")

    # Validate file type
    content_type = file.content_type or ""
    if content_type not in config.ALLOWED_FILE_TYPES:
        allowed_types = ", ".join(config.ALLOWED_FILE_TYPES.values())
        raise HTTPException(status_code=400, detail=f"File type not allowed. Accepted types: {allowed_types}")

    # Read file content and validate size
    content = await file.read()
    file_size = len(content)

    if file_size > config.MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail=f"File size exceeds {config.MAX_FILE_SIZE_MB}MB limit")

    # Save to temporary file for upload
    filename = file.filename or "attachment"

    try:
        suffix = Path(filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            result = client.add_attachment_to_result(result_id, tmp_path, filename)

            # Build response with attachment metadata
            attachment = {
                "id": result.get("attachment_id"),
                "name": filename,
                "filename": filename,
                "size": file_size,
                "content_type": content_type,
                "created_on": int(time.time()),
            }

            return {"success": True, "attachment": attachment}
        finally:
            # Clean up temp file
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass

    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Result {result_id} not found")
        raise HTTPException(status_code=502, detail=f"TestRail API error: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload attachment: {str(e)}")


@router.post("/run/{run_id}/remove_cases")
def remove_cases_from_run(
    run_id: int,
    case_ids: List[int] = Body(..., embed=True),
    _write_enabled=Depends(require_write_enabled),
    client=Depends(_resolve_testrail_client),
):
    """Remove test cases from a test run."""
    # Validate run_id
    if run_id < 1:
        raise HTTPException(status_code=400, detail="Run ID must be positive")

    # Validate case_ids
    if not case_ids:
        raise HTTPException(status_code=400, detail="case_ids cannot be empty")

    if any(cid < 1 for cid in case_ids):
        raise HTTPException(status_code=400, detail="All case IDs must be positive")

    try:
        # Get run details to check if it's part of a plan
        run_data = client.get_run(run_id)
        plan_id = run_data.get("plan_id")

        # Get current tests in the run
        current_tests = client.get_tests_for_run(run_id)

        if not isinstance(current_tests, list):
            raise HTTPException(status_code=500, detail="Invalid response from TestRail API")

        # Extract current case IDs
        current_case_ids = [test.get("case_id") for test in current_tests if test.get("case_id")]

        # Remove the specified case IDs
        remaining_case_ids = [cid for cid in current_case_ids if cid not in case_ids]

        # Update the run with remaining case IDs
        try:
            if plan_id:
                # Get plan details to find entry_id
                plan_data = client.get_plan(plan_id)
                entry_id = None

                # Find the entry that contains this run
                for entry in plan_data.get("entries", []):
                    for run in entry.get("runs", []):
                        if run.get("id") == run_id:
                            entry_id = entry.get("id")
                            break
                    if entry_id:
                        break

                if not entry_id:
                    raise HTTPException(status_code=500, detail="Could not find plan entry for this run")

                # Update plan entry with remaining case_ids
                client.update_plan_entry(plan_id, entry_id, {"case_ids": remaining_case_ids})
            else:
                # Standalone run, use update_run
                client.update_run(run_id, {"case_ids": remaining_case_ids})
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 403:
                raise HTTPException(
                    status_code=403,
                    detail="Cannot remove cases from this run. TestRail does not allow modifying runs that have test results.",
                )
            raise

        removed_count = len([cid for cid in case_ids if cid in current_case_ids])

        return {
            "success": True,
            "run_id": run_id,
            "removed_count": removed_count,
            "remaining_count": len(remaining_case_ids),
            "message": f"Removed {removed_count} case(s) from run {run_id}",
        }
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        raise HTTPException(status_code=502, detail=f"TestRail API error: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove cases from run: {str(e)}")


@router.post("/run/{run_id}/add_cases")
def add_cases_to_run(
    run_id: int,
    case_ids: List[int] = Body(..., embed=True),
    _write_enabled=Depends(require_write_enabled),
    client=Depends(_resolve_testrail_client),
):
    """Add test cases to an existing test run."""
    # Validate run_id
    if run_id < 1:
        raise HTTPException(status_code=400, detail="Run ID must be positive")

    # Validate case_ids
    if not case_ids:
        raise HTTPException(status_code=400, detail="case_ids cannot be empty")

    if any(cid < 1 for cid in case_ids):
        raise HTTPException(status_code=400, detail="All case IDs must be positive")

    try:
        # Get run details to check if it's part of a plan
        run_data = client.get_run(run_id)
        plan_id = run_data.get("plan_id")

        # Get current tests in the run
        current_tests = client.get_tests_for_run(run_id)

        if not isinstance(current_tests, list):
            raise HTTPException(status_code=500, detail="Invalid response from TestRail API")

        # Extract current case IDs
        current_case_ids = [test.get("case_id") for test in current_tests if test.get("case_id")]

        # Add new case IDs (avoid duplicates)
        new_case_ids = [cid for cid in case_ids if cid not in current_case_ids]

        if not new_case_ids:
            return {
                "success": True,
                "run_id": run_id,
                "added_count": 0,
                "total_count": len(current_case_ids),
                "skipped_count": len(case_ids),
                "message": "All selected cases are already in the run",
            }

        updated_case_ids = current_case_ids + new_case_ids

        # Try to update the run with combined case IDs
        try:
            if plan_id:
                # Get plan details to find entry_id
                plan_data = client.get_plan(plan_id)
                entry_id = None

                # Find the entry that contains this run
                for entry in plan_data.get("entries", []):
                    for run in entry.get("runs", []):
                        if run.get("id") == run_id:
                            entry_id = entry.get("id")
                            break
                    if entry_id:
                        break

                if not entry_id:
                    raise HTTPException(status_code=500, detail="Could not find plan entry for this run")

                # Update plan entry with new case_ids
                client.update_plan_entry(plan_id, entry_id, {"case_ids": updated_case_ids})
            else:
                # Standalone run, use update_run
                client.update_run(run_id, {"case_ids": updated_case_ids})
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 403:
                raise HTTPException(
                    status_code=403,
                    detail="Cannot add cases to this run. TestRail does not allow modifying runs that have test results. Please create a new run instead.",
                )
            raise

        return {
            "success": True,
            "run_id": run_id,
            "added_count": len(new_case_ids),
            "total_count": len(updated_case_ids),
            "skipped_count": len(case_ids) - len(new_case_ids),
            "message": f"Added {len(new_case_ids)} case(s) to run {run_id}",
        }
    except HTTPException:
        raise
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        if e.response is not None and e.response.status_code == 403:
            raise HTTPException(
                status_code=403,
                detail="Cannot add cases to this run. TestRail does not allow modifying runs that have test results. Please create a new run instead.",
            )
        raise HTTPException(status_code=502, detail=f"TestRail API error: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add cases to run: {str(e)}")


@router.get("/run/{run_id}/available_cases")
def get_available_cases_for_run(
    run_id: int, project: int = 1, suite_id: int | None = None, client=Depends(_resolve_testrail_client)
):
    """Get test cases that are available to add to a run (not already in the run)."""
    # Validate run_id
    if run_id < 1:
        raise HTTPException(status_code=400, detail="Run ID must be positive")

    try:
        # Get current tests in the run
        current_tests = client.get_tests_for_run(run_id)
        current_case_ids = set(test.get("case_id") for test in current_tests if test.get("case_id"))

        # Get all cases from the project/suite
        all_cases = client.get_cases(project, suite_id=suite_id)

        # Filter out cases that are already in the run
        available_cases = [case for case in all_cases if case.get("id") not in current_case_ids]

        return {
            "success": True,
            "run_id": run_id,
            "available_cases": available_cases,
            "total_available": len(available_cases),
        }
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        raise HTTPException(status_code=502, detail=f"TestRail API error: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get available cases: {str(e)}")
