"""Automation management endpoints for dynamic payloads and web inputs."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel

import app.core.dependencies as dependencies
from app.core.config import config
from app.core.dependencies import require_write_enabled

router = APIRouter(prefix="/api/automation", tags=["automation"])
_CASE_TAG_RE = re.compile(r"@C(\d+)", re.IGNORECASE)
_SCENARIO_RE = re.compile(r"^Scenario(?: Outline)?:\s*(.+)$", re.IGNORECASE)
_FEATURE_RE = re.compile(r"^Feature:\s*(.+)$", re.IGNORECASE)
_REQUEST_RE = re.compile(
    r"\b(?:send|sends)\s+(GET|POST|PUT|PATCH|DELETE)\s+request\s+to\s+\"([^\"]+)\"",
    re.IGNORECASE,
)
_ENV_LINE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
_LOG_SCENARIO_RE = re.compile(r"^\s*Scenario(?: Outline)?:", re.IGNORECASE | re.MULTILINE)
_RUNS: dict[str, dict[str, Any]] = {}
_RUN_LOCK = threading.Lock()


def _resolve_testrail_client(request: Request):
    override = request.app.dependency_overrides.get(dependencies.get_testrail_client)
    if override:
        return override()
    return dependencies.get_testrail_client()


def _automation_field_keys() -> tuple[str, str]:
    api_field = (config.AUTOMATION_API_PAYLOAD_FIELD or "").strip()
    web_field = (config.AUTOMATION_WEB_INPUT_FIELD or "").strip()
    if not api_field or not web_field:
        raise HTTPException(
            status_code=400,
            detail="AUTOMATION_API_PAYLOAD_FIELD and AUTOMATION_WEB_INPUT_FIELD must be configured.",
        )
    return api_field, web_field


def _is_within(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
    except ValueError:
        return False
    return True


def _resolve_features_root(root_override: str | None = None) -> Path:
    if root_override:
        root = Path(root_override).expanduser().resolve()
        if not root.is_dir():
            raise HTTPException(status_code=400, detail="Automation root path not found.")
        allowed_bases = [Path.cwd().resolve(), Path.home().resolve()]
        if not any(_is_within(root, base) for base in allowed_bases):
            raise HTTPException(
                status_code=400,
                detail="Automation root must be within the workspace or home directory.",
            )
        return root

    configured = (config.AUTOMATION_FEATURES_ROOT or "").strip()
    if configured:
        root = Path(configured).expanduser()
        if root.is_dir():
            return root
    cwd = Path.cwd()
    candidates = [
        cwd / "orbis-test-automation" / "apps" / "lokasi_intelligence" / "cypress",
        cwd.parent / "orbis-test-automation" / "apps" / "lokasi_intelligence" / "cypress",
        Path.home() / "orbis-test-automation" / "apps" / "lokasi_intelligence" / "cypress",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise HTTPException(
        status_code=500,
        detail="Automation features root not found. Set AUTOMATION_FEATURES_ROOT.",
    )


def _extract_feature_group(relative_path: Path) -> str:
    parts = list(relative_path.parts)
    if "features" in parts:
        idx = parts.index("features")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return ""


def _is_repo_root(path: Path) -> bool:
    return (path / "package.json").is_file() and (path / "apps").is_dir()


def _resolve_repo_root() -> Path:
    configured = (config.AUTOMATION_REPO_ROOT or "").strip()
    if configured:
        root = Path(configured).expanduser().resolve()
        if root.is_dir() and _is_repo_root(root):
            return root
        raise HTTPException(status_code=400, detail="AUTOMATION_REPO_ROOT is invalid.")

    try:
        features_root = _resolve_features_root()
    except HTTPException:
        features_root = None

    if features_root:
        for parent in [features_root] + list(features_root.parents):
            if _is_repo_root(parent):
                return parent

    candidates = [
        Path.cwd(),
        Path.cwd().parent,
        Path.home() / "orbis-test-automation",
    ]
    for candidate in candidates:
        if candidate.is_dir() and _is_repo_root(candidate):
            return candidate

    raise HTTPException(status_code=500, detail="Automation repo root not found.")


def _parse_feature_file(path: Path, relative_path: Path) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    feature_name = ""
    feature_tags: list[str] = []
    pending_tags: list[str] = []
    scenarios: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("@"):
            pending_tags.extend(line.split())
            continue

        feature_match = _FEATURE_RE.match(line)
        if feature_match:
            feature_name = feature_match.group(1).strip()
            if pending_tags:
                feature_tags = pending_tags
                pending_tags = []
            continue

        scenario_match = _SCENARIO_RE.match(line)
        if scenario_match:
            title = scenario_match.group(1).strip()
            current = {"title": title, "tags": feature_tags + pending_tags, "steps": []}
            scenarios.append(current)
            pending_tags = []
            continue

        if current is not None:
            current["steps"].append(line)

    cases: list[dict[str, Any]] = []
    for scenario in scenarios:
        tags = scenario.get("tags") or []
        case_ids: list[str] = []
        for tag in tags:
            match = _CASE_TAG_RE.search(tag)
            if match:
                case_ids.append(match.group(1))
        if not case_ids:
            continue

        endpoint = None
        method = None
        for step in scenario.get("steps", []):
            req_match = _REQUEST_RE.search(step)
            if req_match:
                method = req_match.group(1).upper()
                endpoint = req_match.group(2)
                break

        for case_id in case_ids:
            cases.append(
                {
                    "id": int(case_id),
                    "title": scenario.get("title") or f"Case {case_id}",
                    "feature": feature_name,
                    "feature_path": str(relative_path),
                    "feature_group": _extract_feature_group(relative_path),
                    "tags": tags,
                    "method": method,
                    "endpoint": endpoint,
                }
            )
    return cases


def _load_feature_cases(kind: str, root_override: str | None = None) -> list[dict[str, Any]]:
    if kind not in {"api", "web"}:
        raise HTTPException(status_code=400, detail="case type must be api or web.")

    root = _resolve_features_root(root_override)
    features_root = root / kind / "features"
    if not features_root.is_dir():
        raise HTTPException(
            status_code=500,
            detail=f"Feature directory not found: {features_root}",
        )

    cases: list[dict[str, Any]] = []
    seen: set[int] = set()
    for feature_path in sorted(features_root.rglob("*.feature")):
        relative_path = feature_path.relative_to(root)
        for entry in _parse_feature_file(feature_path, relative_path):
            case_id = entry.get("id")
            if isinstance(case_id, int) and case_id in seen:
                continue
            if isinstance(case_id, int):
                seen.add(case_id)
            cases.append(entry)

    cases.sort(key=lambda item: item.get("id", 0))
    return cases


def _normalize_payload(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return f"```json\n{json.dumps(value, indent=2)}\n```"
    if isinstance(value, (int, float, bool)):
        return f"```json\n{json.dumps(value)}\n```"
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return ""
        if trimmed.startswith("```") and trimmed.endswith("```"):
            return trimmed
        try:
            parsed = json.loads(trimmed)
        except Exception:
            return value
        return f"```json\n{json.dumps(parsed, indent=2)}\n```"
    return str(value)


def _build_run_commands(payload: AutomationRunRequest) -> list[tuple[str, str]]:
    tag = (payload.test_tag or "").strip()
    if payload.test_type == "all":
        if tag:
            return [("api", "npm run test:tag"), ("e2e", "npm run test:tag")]
        return [("api", "npm run test:api"), ("e2e", "npm run test:e2e")]
    if payload.test_type == "api":
        return [("api", "npm run test:tag" if tag else "npm run test:api")]
    return [("e2e", "npm run test:tag" if tag else "npm run test:e2e")]


def _load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return values
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = _ENV_LINE_RE.match(line)
        if not match:
            continue
        key, value = match.groups()
        value = value.strip()
        if len(value) >= 2 and (
            (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'"))
        ):
            value = value[1:-1]
        values[key] = value
    return values


def _resolve_env_file(repo_root: Path, app_name: str) -> tuple[Path | None, dict[str, str]]:
    candidates = [
        repo_root / "apps" / app_name / ".env",
        repo_root / ".env",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate, _load_env_file(candidate)
    return None, {}


def _resolve_app_root(repo_root: Path, app_name: str) -> Path:
    app_root = repo_root / "apps" / app_name
    if not app_root.is_dir():
        raise HTTPException(status_code=400, detail=f"App not found: {app_name}")
    return app_root


def _sanitize_label(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned


def _copy_allure_report(source_dir: Path, label: str | None = None) -> dict[str, str]:
    run_id = uuid4().hex
    safe_label = _sanitize_label(label or "")
    target_name = f"{safe_label}-{run_id}" if safe_label else run_id
    output_root = Path("output") / "allure"
    output_root.mkdir(parents=True, exist_ok=True)
    target_dir = output_root / target_name
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(source_dir, target_dir)
    return {
        "run_id": run_id,
        "target_dir": str(target_dir),
        "url": f"/output/allure/{target_name}/index.html",
    }


def _read_log_tail(path: Path, max_bytes: int = 20000, max_lines: int = 200) -> list[str]:
    if not path.exists():
        return []
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            if size > max_bytes:
                handle.seek(-max_bytes, os.SEEK_END)
            data = handle.read()
    except Exception:
        return []
    text = data.decode("utf-8", errors="ignore")
    lines = text.splitlines()
    if max_lines and len(lines) > max_lines:
        lines = lines[-max_lines:]
    return lines


def _estimate_total_cases(payload: AutomationRunRequest, repo_root: Path) -> tuple[int | None, str | None]:
    features_root = repo_root / "apps" / payload.app_name / "cypress"
    try:
        tag = (payload.test_tag or "").strip()
        if tag:
            if " " in tag or any(token in tag for token in (" and ", " or ", " not ")):
                return None, None
            tag_value = tag if tag.startswith("@") else f"@{tag}"
        else:
            tag_value = None

        if payload.test_type == "all":
            api_cases = _load_feature_cases("api", str(features_root))
            web_cases = _load_feature_cases("web", str(features_root))
            if tag_value:
                count = sum(1 for case in api_cases if tag_value in (case.get("tags") or []))
                count += sum(1 for case in web_cases if tag_value in (case.get("tags") or []))
            else:
                count = len(api_cases) + len(web_cases)
        else:
            kind = "api" if payload.test_type == "api" else "web"
            cases = _load_feature_cases(kind, str(features_root))
            if tag_value:
                count = sum(1 for case in cases if tag_value in (case.get("tags") or []))
            else:
                count = len(cases)
    except HTTPException:
        return None, None
    return count, tag_value


def _update_run_progress(run: dict[str, Any]) -> None:
    log_path = Path(run.get("log_path", ""))
    if not log_path.exists():
        return
    try:
        size = log_path.stat().st_size
    except Exception:
        return
    offset = int(run.get("log_offset", 0))
    if offset > size:
        offset = 0
    try:
        with log_path.open("rb") as handle:
            handle.seek(offset)
            chunk = handle.read()
            new_offset = handle.tell()
    except Exception:
        return
    if not chunk:
        return
    text = chunk.decode("utf-8", errors="ignore")
    new_count = len(_LOG_SCENARIO_RE.findall(text))
    run["completed_cases"] = int(run.get("completed_cases", 0)) + new_count
    run["log_offset"] = new_offset
    lines = text.splitlines()
    if lines:
        run["last_log_line"] = lines[-1]
    run["updated_at"] = datetime.now(timezone.utc).isoformat()


def _watch_run(run_id: str, process: subprocess.Popen) -> None:
    exit_code = process.wait()
    status = "success" if exit_code == 0 else "failed"
    with _RUN_LOCK:
        run = _RUNS.get(run_id)
        if run is None:
            return
        run["status"] = status
        run["exit_code"] = exit_code
        run["finished_at"] = datetime.now(timezone.utc).isoformat()
        run["updated_at"] = run["finished_at"]


class AutomationCaseUpdate(BaseModel):
    api_payload: Any | None = None
    web_inputs: Any | None = None


class AutomationRunRequest(BaseModel):
    app_name: str = "lokasi_intelligence"
    test_type: str = "api"
    test_tag: str | None = None
    environment: str = "staging"
    parallel: bool = False


class AllureReportRequest(BaseModel):
    app_name: str = "lokasi_intelligence"
    output_label: str | None = None


@router.get("/case/{case_id}")
def get_automation_case(case_id: int, client=Depends(_resolve_testrail_client)):
    """Load a single case with automation payload fields."""
    if case_id < 1:
        raise HTTPException(status_code=400, detail="Case ID must be positive")

    api_field, web_field = _automation_field_keys()

    try:
        case_data = client.get_case(case_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load case: {exc}")

    return {
        "id": case_data.get("id", case_id),
        "title": case_data.get("title") or f"Case {case_id}",
        "refs": case_data.get("refs"),
        "section_id": case_data.get("section_id"),
        "api_payload": case_data.get(api_field),
        "web_inputs": case_data.get(web_field),
        "api_field": api_field,
        "web_field": web_field,
    }


@router.get("/status")
def get_automation_status(app_name: str = "lokasi_intelligence"):
    """Report whether automation repo and feature paths are available."""
    status: dict[str, Any] = {
        "repo_root_config": config.AUTOMATION_REPO_ROOT,
        "features_root_config": config.AUTOMATION_FEATURES_ROOT,
        "repo_root_ok": False,
        "features_root_ok": False,
        "app_root_ok": False,
        "repo_root": None,
        "features_root": None,
        "npm_available": bool(shutil.which("npm")),
        "errors": {},
    }

    try:
        repo_root = _resolve_repo_root()
        status["repo_root_ok"] = True
        status["repo_root"] = str(repo_root)
        app_root = repo_root / "apps" / app_name
        if app_root.is_dir():
            status["app_root_ok"] = True
            status["app_root"] = str(app_root)
        else:
            status["errors"]["app_root"] = f"App not found: {app_name}"
    except HTTPException as exc:
        status["errors"]["repo_root"] = exc.detail

    try:
        features_root = _resolve_features_root()
        status["features_root_ok"] = True
        status["features_root"] = str(features_root)
        api_features = features_root / "api" / "features"
        web_features = features_root / "web" / "features"
        status["api_features_ok"] = api_features.is_dir()
        status["web_features_ok"] = web_features.is_dir()
    except HTTPException as exc:
        status["errors"]["features_root"] = exc.detail

    return status


@router.get("/cases")
def list_automation_cases(case_type: str = "api", root: str | None = None):
    """List automation cases from feature files for API or web suites."""
    return {"cases": _load_feature_cases(case_type, root)}


@router.put("/case/{case_id}")
def update_automation_case(
    case_id: int,
    payload: AutomationCaseUpdate = Body(...),
    _write_enabled=Depends(require_write_enabled),
    client=Depends(_resolve_testrail_client),
):
    """Update automation payload fields for a case."""
    if case_id < 1:
        raise HTTPException(status_code=400, detail="Case ID must be positive")

    api_field, web_field = _automation_field_keys()
    update_body: Dict[str, Any] = {}

    if payload.api_payload is not None:
        update_body[api_field] = _normalize_payload(payload.api_payload)
    if payload.web_inputs is not None:
        update_body[web_field] = _normalize_payload(payload.web_inputs)

    if not update_body:
        raise HTTPException(status_code=400, detail="No automation fields provided.")

    try:
        updated = client.update_case(case_id, update_body)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to update case: {exc}")

    return {
        "success": True,
        "case": {
            "id": updated.get("id", case_id),
            "title": updated.get("title"),
            "refs": updated.get("refs"),
            "api_payload": updated.get(api_field),
            "web_inputs": updated.get(web_field),
        },
    }


@router.post("/run")
def run_automation(
    payload: AutomationRunRequest,
    _write_enabled=Depends(require_write_enabled),
):
    """Run automation locally by invoking the orbis-test-automation workspace."""
    if payload.test_type not in {"api", "e2e", "all"}:
        raise HTTPException(status_code=400, detail="Invalid test_type.")
    if payload.environment not in {"staging", "preproduction", "production"}:
        raise HTTPException(status_code=400, detail="Invalid environment.")
    if payload.parallel:
        raise HTTPException(status_code=400, detail="Parallel runs are not supported locally yet.")
    if not shutil.which("npm"):
        raise HTTPException(status_code=400, detail="npm is not available on this host.")

    repo_root = _resolve_repo_root()
    commands = _build_run_commands(payload)
    if not commands:
        raise HTTPException(status_code=400, detail="No command to run.")

    tag = (payload.test_tag or "").strip()
    env = os.environ.copy()
    env_path, env_values = _resolve_env_file(repo_root, payload.app_name)
    if env_values:
        env.update(env_values)
    env["APP"] = payload.app_name
    env["NODE_ENV"] = payload.environment
    if tag:
        env["TAGS"] = tag

    command_parts = [f"NODE_ENV_TEST_TYPE={test_type} {cmd}" for test_type, cmd in commands]
    command = " && ".join(command_parts)

    runs_dir = Path("logs") / "automation_runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_id = uuid4().hex
    log_path = runs_dir / f"{run_id}.log"

    with log_path.open("ab") as log_file:
        process = subprocess.Popen(
            ["/bin/bash", "-lc", command],
            cwd=repo_root,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )

    total_cases, normalized_tag = _estimate_total_cases(payload, repo_root)
    with _RUN_LOCK:
        _RUNS[run_id] = {
            "pid": process.pid,
            "command": command,
            "log_path": str(log_path),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "app": payload.app_name,
            "test_type": payload.test_type,
            "test_tag": tag,
            "environment": payload.environment,
            "env_path": str(env_path) if env_path else None,
            "status": "running",
            "exit_code": None,
            "completed_cases": 0,
            "total_cases": total_cases,
            "normalized_tag": normalized_tag,
            "log_offset": 0,
            "last_log_line": "",
        }

    thread = threading.Thread(target=_watch_run, args=(run_id, process), daemon=True)
    thread.start()

    return {
        "success": True,
        "message": "Automation run started.",
        "run_id": run_id,
        "pid": process.pid,
        "log_path": str(log_path),
        "command": command,
        "env_path": str(env_path) if env_path else None,
    }


@router.post("/allure-report")
def generate_allure_report(
    payload: AllureReportRequest,
    _write_enabled=Depends(require_write_enabled),
):
    """Generate an Allure HTML report from existing results."""
    if not shutil.which("npm"):
        raise HTTPException(status_code=400, detail="npm is not available on this host.")
    repo_root = _resolve_repo_root()
    app_root = _resolve_app_root(repo_root, payload.app_name)
    results_dir = app_root / "cypress" / "reports" / "allure-results"
    if not results_dir.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Allure results not found: {results_dir}",
        )

    env = os.environ.copy()
    env_path, env_values = _resolve_env_file(repo_root, payload.app_name)
    if env_values:
        env.update(env_values)
    env["APP"] = payload.app_name

    command = "npm run allure:report"
    result = subprocess.run(
        ["/bin/bash", "-lc", command],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        detail = stderr or stdout or "Allure report generation failed."
        raise HTTPException(status_code=500, detail=detail[:2000])

    report_dir = app_root / "cypress" / "reports" / "allure-report"
    if not report_dir.is_dir():
        raise HTTPException(status_code=500, detail="Allure report output not found.")

    copied = _copy_allure_report(report_dir, payload.output_label)
    return {
        "success": True,
        "message": "Allure report generated.",
        "app": payload.app_name,
        "env_path": str(env_path) if env_path else None,
        "report_dir": str(report_dir),
        **copied,
    }


@router.get("/run/{run_id}")
def get_automation_run(run_id: str):
    """Get status and recent logs for a run."""
    with _RUN_LOCK:
        run = _RUNS.get(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found.")
        _update_run_progress(run)
        status = run.get("status", "running")
        total_cases = run.get("total_cases")
        completed_cases = run.get("completed_cases", 0)
        progress_percent = None
        if isinstance(total_cases, int) and total_cases > 0:
            progress_percent = min(100, int((completed_cases / total_cases) * 100))
        log_path = Path(run.get("log_path", ""))
        log_tail = _read_log_tail(log_path)

    return {
        "run_id": run_id,
        "status": status,
        "exit_code": run.get("exit_code"),
        "started_at": run.get("started_at"),
        "updated_at": run.get("updated_at"),
        "finished_at": run.get("finished_at"),
        "pid": run.get("pid"),
        "command": run.get("command"),
        "log_path": run.get("log_path"),
        "last_log_line": run.get("last_log_line"),
        "completed_cases": completed_cases,
        "total_cases": total_cases,
        "progress_percent": progress_percent,
        "log_tail": log_tail,
    }
