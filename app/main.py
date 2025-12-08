# mypy: disable-error-code=assignment
import json
import os
import threading
import time
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from fastapi import (
    Body,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, field_validator, model_validator

from testrail_client import (
    DEFAULT_HTTP_BACKOFF,
    DEFAULT_HTTP_RETRIES,
    DEFAULT_HTTP_TIMEOUT,
    TestRailClient,
    capture_telemetry,
    get_plan,
    get_plans_for_project,
)
from testrail_daily_report import (
    env_or_die,
    generate_report,
    log_memory,
)

# Ensure local .env overrides host/env settings to avoid stale provider configs
load_dotenv(override=True)

app = FastAPI(title="TestRail Reporter", version="0.1.0")

# Serve generated reports and static assets
Path("out").mkdir(exist_ok=True)


class NoCacheStaticFiles(StaticFiles):
    """StaticFiles with no-cache headers to ensure refreshed report content."""

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


app.mount("/reports", NoCacheStaticFiles(directory="out"), name="reports")
if Path("assets").exists():
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")

templates = Jinja2Templates(directory="templates")


def _write_enabled() -> bool:
    return True


def _make_client() -> TestRailClient:
    base_url = env_or_die("TESTRAIL_BASE_URL").rstrip("/")
    user = env_or_die("TESTRAIL_USER")
    api_key = env_or_die("TESTRAIL_API_KEY")
    return TestRailClient(
        base_url=base_url,
        auth=(user, api_key),
        timeout=DEFAULT_HTTP_TIMEOUT,
        max_attempts=DEFAULT_HTTP_RETRIES,
        backoff=DEFAULT_HTTP_BACKOFF,
    )


def _default_suite_id() -> int | None:
    val = os.getenv("DEFAULT_SUITE_ID", "1")
    try:
        parsed = int(str(val).strip())
        return parsed
    except ValueError:
        return None


def _default_section_id() -> int | None:
    val = os.getenv("DEFAULT_SECTION_ID", "69")
    try:
        parsed = int(str(val).strip())
        return parsed
    except ValueError:
        return None


def _default_template_id() -> int | None:
    val = os.getenv("DEFAULT_TEMPLATE_ID", "4")
    try:
        return int(str(val).strip())
    except ValueError:
        return None


def _default_type_id() -> int | None:
    val = os.getenv("DEFAULT_TYPE_ID", "7")
    try:
        return int(str(val).strip())
    except ValueError:
        return None


def _default_priority_id() -> int | None:
    val = os.getenv("DEFAULT_PRIORITY_ID", "2")
    try:
        return int(str(val).strip())
    except ValueError:
        return None


class TTLCache:
    def __init__(self, ttl_seconds: int = 120, maxsize: int = 128):
        self.ttl = ttl_seconds
        self.maxsize = max(1, maxsize)
        self._store: dict[tuple, tuple[float, Any]] = {}
        self._order: deque[tuple] = deque()
        self._lock = threading.Lock()

    def _discard(self, key: tuple):
        self._store.pop(key, None)
        try:
            self._order.remove(key)
        except ValueError:
            pass

    def _record(self, key: tuple):
        try:
            self._order.remove(key)
        except ValueError:
            pass
        self._order.append(key)
        while len(self._order) > self.maxsize:
            oldest = self._order.popleft()
            self._store.pop(oldest, None)

    def get(self, key: tuple):
        now = time.time()
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            expires_at, value = entry
            if expires_at <= now:
                self._discard(key)
                return None
        return value.copy() if isinstance(value, dict) else value, expires_at

    def set(self, key: tuple, value: Any, ttl_seconds: int | None = None):
        ttl = ttl_seconds if ttl_seconds is not None else self.ttl
        expires_at = time.time() + max(1, ttl)
        with self._lock:
            self._store[key] = (
                expires_at,
                value.copy() if isinstance(value, dict) else value,
            )
            self._record(key)
        return expires_at

    def clear(self):
        with self._lock:
            self._store.clear()
            self._order.clear()


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


plans_cache_ttl = _int_env("PLANS_CACHE_TTL", 180)
plans_cache_maxsize = max(1, _int_env("PLANS_CACHE_MAXSIZE", 128))
runs_cache_ttl = _int_env("RUNS_CACHE_TTL", 60)
runs_cache_maxsize = max(1, _int_env("RUNS_CACHE_MAXSIZE", 128))
_plans_cache = TTLCache(ttl_seconds=plans_cache_ttl, maxsize=plans_cache_maxsize)
_runs_cache = TTLCache(ttl_seconds=runs_cache_ttl, maxsize=runs_cache_maxsize)


def _cache_meta(hit: bool, expires_at: float):
    return {
        "cache": {
            "hit": hit,
            "expires_at": datetime.fromtimestamp(expires_at, timezone.utc).isoformat(),
            "seconds_remaining": max(0, int(expires_at - time.time())),
        }
    }


@dataclass(slots=True)
class ReportJob:
    id: str
    params: dict[str, Any]
    status: str = "queued"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    path: str | None = None
    url: str | None = None
    error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "path": self.path,
            "url": self.url,
            "error": self.error,
            "meta": self.meta,
            "params": self.params,
        }


class ReportJobManager:
    def __init__(self, max_workers: int = 2, max_history: int = 50):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.jobs: dict[str, ReportJob] = {}
        self.order: deque[str] = deque()
        self.lock = threading.Lock()
        self.max_history = max_history

    def enqueue(self, params: dict[str, Any]) -> ReportJob:
        job_id = uuid.uuid4().hex
        job = ReportJob(id=job_id, params=params)
        with self.lock:
            self.jobs[job_id] = job
            self.order.append(job_id)
        self.executor.submit(self._run_job, job_id)
        return job

    def get(self, job_id: str) -> ReportJob | None:
        with self.lock:
            return self.jobs.get(job_id)

    def serialize(self, job: ReportJob) -> dict[str, Any]:
        data: dict[str, Any] = job.to_dict()
        data["queue_position"] = self.queue_position(job.id)
        return data

    def queue_position(self, job_id: str) -> int | None:
        with self.lock:
            position = 0
            for jid in self.order:
                job = self.jobs.get(jid)
                if not job:
                    continue
                if jid == job_id:
                    return position if job.status == "queued" else None
                if job.status == "queued":
                    position += 1
        return None

    def stats(self) -> dict[str, Any]:
        with self.lock:
            total = len(self.order)
            running = 0
            queued = 0
            recent_status = None
            recent_id = None
            for jid in self.order:
                job = self.jobs.get(jid)
                if not job:
                    continue
                if job.status == "running":
                    running += 1
                elif job.status == "queued":
                    queued += 1
            if self.order:
                latest = self.jobs.get(self.order[-1])
                if latest:
                    recent_status = latest.status
                    recent_id = latest.id
        return {
            "size": total,
            "running": running,
            "queued": queued,
            "history_limit": self.max_history,
            "latest_job": {"id": recent_id, "status": recent_status} if recent_id else None,
        }

    def _trim_history(self):
        with self.lock:
            while len(self.order) > self.max_history:
                oldest_id = self.order[0]
                job = self.jobs.get(oldest_id)
                if job and job.status not in {"success", "error"}:
                    break
                self.order.popleft()
                self.jobs.pop(oldest_id, None)

    def report_progress(self, job_id: str, stage: str, payload: dict | None = None):
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return
            job.meta.setdefault("progress_updates", [])
            update = {
                "stage": stage,
                "payload": payload or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            job.meta["stage"] = stage
            job.meta["stage_payload"] = payload or {}
            job.meta["updated_at"] = update["timestamp"]
            job.meta["progress_updates"].append(update)
            # keep only recent few entries
            if len(job.meta["progress_updates"]) > 25:
                job.meta["progress_updates"] = job.meta["progress_updates"][-25:]

    def _run_job(self, job_id: str):
        job = self.get(job_id)
        if not job:
            return
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        start = time.perf_counter()
        print(f"[report-job] {job_id} started with params={job.params}", flush=True)
        try:

            def reporter(stage, payload=None):
                self.report_progress(job_id, stage, payload or {})

            with capture_telemetry() as telemetry:
                path = generate_report(**job.params, progress=reporter)
            duration_ms = (time.perf_counter() - start) * 1000.0
            completed_at = datetime.now(timezone.utc)
            job.completed_at = completed_at
            job.path = str(path)
            job.url = "/reports/" + Path(path).name
            api_calls = telemetry.get("api_calls", []) if isinstance(telemetry, dict) else []
            job.meta = {
                "generated_at": completed_at.isoformat(),
                "duration_ms": round(duration_ms, 2),
                "api_call_count": len(api_calls),
                "api_calls": api_calls,
            }
            job.status = "success"
            print(
                f"[report-job] {job_id} completed in {duration_ms:.0f}ms -> {job.url}",
                flush=True,
            )
        except Exception as exc:
            job.error = str(exc)
            job.status = "error"
            job.completed_at = datetime.now(timezone.utc)
            print(f"[report-job] {job_id} failed: {exc}", flush=True)
        finally:
            self._trim_history()


def _report_worker_config() -> tuple[int, int, int]:
    try:
        requested = max(1, int(os.getenv("REPORT_WORKERS", "1")))
    except ValueError:
        requested = 1
    try:
        configured_max = max(1, int(os.getenv("REPORT_WORKERS_MAX", "4")))
    except ValueError:
        configured_max = 4
    resolved = max(1, min(requested, configured_max))
    if resolved != requested:
        print(
            f"INFO: REPORT_WORKERS limited to {resolved} " f"(requested {requested}, max {configured_max}).",
            flush=True,
        )
    return resolved, requested, configured_max


report_worker_count, report_worker_requested, report_worker_max = _report_worker_config()
job_history_limit = max(10, int(os.getenv("REPORT_JOB_HISTORY", "60")))
_job_manager = ReportJobManager(max_workers=report_worker_count, max_history=job_history_limit)


class ReportRequest(BaseModel):
    project: int = 1
    plan: int | None = None
    run: int | None = None
    run_ids: list[int] | None = None

    @field_validator("run_ids", mode="before")
    @classmethod
    def _coerce_run_ids(cls, value):
        if value is None:
            return None
        if isinstance(value, (str, int)):
            value = [value]
        if isinstance(value, tuple):
            value = list(value)
        cleaned: list[int] = []
        for item in value:
            if item is None:
                continue
            text = str(item).strip()
            if not text:
                continue
            cleaned.append(int(text))
        return cleaned or None

    @model_validator(mode="after")
    def _validate_constraints(self):
        if (self.plan is None and self.run is None) or (self.plan is not None and self.run is not None):
            raise ValueError("Provide exactly one of plan or run")
        if self.run_ids and self.plan is None:
            raise ValueError("Run selection requires a plan")
        return self


class ManagePlan(BaseModel):
    project: int = 1
    name: str
    description: str | None = None
    milestone_id: int | None = None
    dry_run: bool = False


class ManageRun(BaseModel):
    project: int = 1
    plan_id: int | None = None
    name: str
    description: str | None = None
    refs: str | None = None
    include_all: bool = True
    case_ids: list[int] | None = None
    dry_run: bool = False

    @model_validator(mode="after")
    def _validate_cases(self):
        if not self.include_all and not self.case_ids:
            raise ValueError("Provide case_ids when include_all is false")
        return self


class ManageCase(BaseModel):
    project: int = 1
    title: str
    refs: str | None = None
    bdd_scenarios: str | None = None
    dry_run: bool = False


class UpdatePlan(BaseModel):
    name: str | None = None
    description: str | None = None
    milestone_id: int | None = None
    dry_run: bool = False

    @model_validator(mode="after")
    def _validate_not_all_empty(self):
        if self.name is not None and not self.name.strip():
            raise ValueError("Plan name cannot be empty")
        return self


class UpdateRun(BaseModel):
    name: str | None = None
    description: str | None = None
    refs: str | None = None
    dry_run: bool = False

    @model_validator(mode="after")
    def _validate_not_all_empty(self):
        if self.name is not None and not self.name.strip():
            raise ValueError("Run name cannot be empty")
        return self


class UpdateCase(BaseModel):
    title: str | None = None
    refs: str | None = None
    bdd_scenarios: str | None = None
    dry_run: bool = False

    @model_validator(mode="after")
    def _validate_not_all_empty(self):
        if self.title is not None and not self.title.strip():
            raise ValueError("Case title cannot be empty")
        return self


class DashboardPlansResponse(BaseModel):
    """Response model for paginated plan lists."""

    plans: list[dict[str, Any]]
    total_count: int
    offset: int
    limit: int
    has_more: bool
    meta: dict[str, Any]


class DashboardPlanDetail(BaseModel):
    """Response model for plan details with runs."""

    plan: dict[str, Any]
    runs: list[dict[str, Any]]
    meta: dict[str, Any]


class DashboardRunsResponse(BaseModel):
    """Response model for run lists."""

    plan_id: int
    runs: list[dict[str, Any]]
    meta: dict[str, Any]


_keepalive_thread: threading.Thread | None = None
_keepalive_stop = threading.Event()
_memlog_thread: threading.Thread | None = None
_memlog_stop = threading.Event()


def _start_keepalive():
    url = os.getenv("KEEPALIVE_URL")
    if not url:
        return
    try:
        interval = max(60, int(os.getenv("KEEPALIVE_INTERVAL", "240")))
    except ValueError:
        interval = 240

    def _loop():
        while not _keepalive_stop.is_set():
            try:
                requests.get(url, timeout=10)
            except Exception:
                pass
            _keepalive_stop.wait(interval)

    global _keepalive_thread
    if _keepalive_thread and _keepalive_thread.is_alive():
        return
    _keepalive_thread = threading.Thread(target=_loop, name="keepalive-thread", daemon=True)
    _keepalive_thread.start()


def _start_memlog():
    try:
        interval = max(30, int(os.getenv("MEM_LOG_INTERVAL", "60")))
    except ValueError:
        interval = 60

    def _loop():
        while not _memlog_stop.is_set():
            try:
                log_memory("heartbeat")
            except Exception:
                pass
            _memlog_stop.wait(interval)

    global _memlog_thread
    if _memlog_thread and _memlog_thread.is_alive():
        return
    _memlog_thread = threading.Thread(target=_loop, name="memlog-thread", daemon=True)
    _memlog_thread.start()


def _stop_keepalive():
    global _keepalive_thread
    if not _keepalive_thread:
        return
    _keepalive_stop.set()
    _keepalive_thread.join(timeout=5)
    _keepalive_thread = None
    _keepalive_stop.clear()


def _stop_memlog():
    global _memlog_thread
    if not _memlog_thread:
        return
    _memlog_stop.set()
    _memlog_thread.join(timeout=5)
    _memlog_thread = None
    _memlog_stop.clear()


@app.on_event("startup")
def on_startup():
    report_workers = f"{report_worker_count} (max {report_worker_max})"
    if report_worker_requested != report_worker_count:
        report_workers = f"{report_workers} (requested {report_worker_requested})"
    run_workers = os.getenv("RUN_WORKERS", "2")
    attachment_workers = os.getenv("ATTACHMENT_WORKERS", "2")

    def web_worker_count() -> int:
        candidates = [
            os.getenv("WEB_CONCURRENCY"),
            os.getenv("UVICORN_WORKERS"),
            os.getenv("GUNICORN_WORKERS"),
        ]
        for value in candidates:
            if value is None:
                continue
            try:
                parsed = int(str(value).strip())
                if parsed > 0:
                    return parsed
            except ValueError:
                continue
        return 1

    web_workers = web_worker_count()

    print("--- Worker Configuration ---")
    print(f"Report Workers:     {report_workers}")
    print(f"Run Workers:          {run_workers}")
    print(f"Attachment Workers:   {attachment_workers}")
    print(f"Web Workers:          {web_workers}")
    print("--------------------------")
    if web_workers > 1:
        print(
            "WARNING: WEB_CONCURRENCY > 1 will break async job polling; "
            "limit uvicorn workers (WEB_CONCURRENCY) to 1.",
            flush=True,
        )

    _start_keepalive()
    _start_memlog()


@app.on_event("shutdown")
def on_shutdown():
    _stop_keepalive()
    _stop_memlog()


@app.get("/healthz")
def healthz():
    return {
        "ok": True,
        "queue": _job_manager.stats(),
        "http": {
            "timeout_seconds": DEFAULT_HTTP_TIMEOUT,
            "retries": DEFAULT_HTTP_RETRIES,
            "backoff_seconds": DEFAULT_HTTP_BACKOFF,
        },
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    # Brand colors can be customized via environment variables
    brand = {
        "primary": os.getenv("BRAND_PRIMARY", "#1A8A85"),
        "primary_600": os.getenv("BRAND_PRIMARY_600", "#15736E"),
        "bg": os.getenv("BRAND_BG", "#F8F9FA"),
        "bg2": os.getenv("BRAND_BG2", "rgba(26,138,133,0.06)"),
    }
    logo_url = "/assets/Bvt.jpg"

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "default_project": 1,
            "default_suite_id": _default_suite_id(),
            "default_section_id": _default_section_id(),
            "brand": brand,
            "logo_url": logo_url,
            "cache_bust": int(time.time()),  # Cache-busting for JS/CSS files
        },
    )


@app.post("/generate")
def generate(
    project: int = Form(1),
    plan_param: str = Form(""),  # matches <input name="plan">
    run_param: str = Form(""),  # matches <input name="run">
    run_ids: list[str] | None = Form(default=None),
):
    # Convert blank strings to None, otherwise parse to int
    plan: int | None = int(plan_param) if plan_param.strip() else None
    run: int | None = int(run_param) if run_param.strip() else None
    selected_run_ids = [int(x) for x in run_ids] if run_ids else None
    if selected_run_ids and plan is None:
        raise HTTPException(status_code=400, detail="Run selection requires a plan")
    if (plan is None and run is None) or (plan is not None and run is not None):
        raise HTTPException(status_code=400, detail="Provide exactly one of plan or run")
    try:
        path = generate_report(project=project, plan=plan, run=run, run_ids=selected_run_ids)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {e}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Catch any other unexpected errors
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
    url = "/reports/" + Path(path).name
    return RedirectResponse(url=url, status_code=303)


@app.get("/generate")
def generate_get():
    # Friendly redirect if someone visits /generate with GET
    return RedirectResponse(url="/", status_code=307)


@app.get("/report")
def report_alias(project: int = 1, plan: int | None = None, run: int | None = None):
    # Alias for /api/report (synchronous legacy endpoint)
    return api_report_sync(project=project, plan=plan, run=run)


@app.get("/api/report")
def api_report_sync(
    project: int = 1,
    plan: int | None = None,
    run: int | None = None,
    run_ids: list[int] | None = Query(None),
):
    if run_ids and plan is None:
        raise HTTPException(status_code=400, detail="Run selection requires a plan")
    if (plan is None and run is None) or (plan is not None and run is not None):
        raise HTTPException(status_code=400, detail="Provide exactly one of plan or run")
    path = generate_report(project=project, plan=plan, run=run, run_ids=run_ids)
    url = "/reports/" + Path(path).name
    return {"path": path, "url": url}


@app.post("/api/report", status_code=status.HTTP_202_ACCEPTED)
def api_report_async(payload: ReportRequest = Body(...)):
    job = _job_manager.enqueue(payload.model_dump())
    return _job_manager.serialize(job)


@app.get("/api/report/{job_id}")
def api_report_status(job_id: str):
    job = _job_manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Report job not found")
    return _job_manager.serialize(job)


def _require_write_enabled():
    return


@app.post("/api/manage/plan")
def api_manage_plan(payload: ManagePlan):
    _require_write_enabled()
    client = _make_client()
    body = {
        "name": payload.name,
        "description": payload.description,
    }
    if payload.milestone_id is not None:
        body["milestone_id"] = payload.milestone_id
    if payload.dry_run:
        return {"dry_run": True, "payload": body, "project": payload.project}
    created = client.add_plan(payload.project, body)
    return {"plan": created}


@app.post("/api/manage/run")
def api_manage_run(payload: ManageRun):
    _require_write_enabled()
    client = _make_client()
    suite_id = _default_suite_id()
    if suite_id is None:
        raise HTTPException(
            status_code=400,
            detail=("DEFAULT_SUITE_ID is required to create runs when suite_id is omitted"),
        )
    assert suite_id is not None
    body: dict[str, Any] = {}
    body["suite_id"] = suite_id
    body["name"] = payload.name
    body["description"] = payload.description
    body["include_all"] = payload.include_all
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
    if payload.plan_id:
        created = client.add_plan_entry(payload.plan_id, body)
    else:
        created = client.add_run(payload.project, body)
    return {"run": created}


@app.post("/api/manage/case")
def api_manage_case(payload: ManageCase):
    _require_write_enabled()
    client = _make_client()
    section_id = _default_section_id()
    if section_id is None:
        raise HTTPException(status_code=400, detail="DEFAULT_SECTION_ID is required to create cases")
    assert section_id is not None
    body: dict[str, Any] = {
        "title": payload.title,
        "refs": payload.refs,
    }
    tmpl = _default_template_id()
    if tmpl is not None:
        body["template_id"] = tmpl  # type: ignore
    typ = _default_type_id()
    if typ is not None:
        body["type_id"] = typ  # type: ignore
    prio = _default_priority_id()
    if prio is not None:
        body["priority_id"] = prio  # type: ignore
    # Convert BDD text into array of {content: ...}
    bdd_text = payload.bdd_scenarios or ""
    steps = [line.strip() for line in bdd_text.splitlines() if line.strip()]
    if steps:
        combined = "\n".join(steps)
        body["custom_testrail_bdd_scenario"] = [{"content": combined}]  # type: ignore
    # Remove None fields
    body = {k: v for k, v in body.items() if v is not None}
    if payload.dry_run:
        return {"dry_run": True, "payload": body, "section_id": section_id}
    created = client.add_case(section_id, body)
    return {"case": created}


@app.put("/api/manage/plan/{plan_id}")
def api_update_plan(plan_id: int, payload: UpdatePlan):
    """
    Update an existing test plan.

    Args:
        plan_id: TestRail plan ID to update
        payload: UpdatePlan model with fields to update

    Returns:
        Updated plan data or dry_run preview

    Raises:
        HTTPException 400: Invalid plan_id or validation error
        HTTPException 404: Plan not found
        HTTPException 502: TestRail API error
    """
    _require_write_enabled()

    # Validate plan_id
    if plan_id < 1:
        raise HTTPException(status_code=400, detail="Plan ID must be positive")

    # Build update payload with only non-None fields
    body: dict[str, Any] = {}
    if payload.name is not None:
        body["name"] = payload.name
    if payload.description is not None:
        body["description"] = payload.description
    if payload.milestone_id is not None:
        body["milestone_id"] = payload.milestone_id

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
        client = _make_client()
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


@app.put("/api/manage/run/{run_id}")
def api_update_run(run_id: int, payload: UpdateRun):
    """
    Update an existing test run.

    Args:
        run_id: TestRail run ID to update
        payload: UpdateRun model with fields to update

    Returns:
        Updated run data or dry_run preview

    Raises:
        HTTPException 400: Invalid run_id or validation error
        HTTPException 404: Run not found
        HTTPException 502: TestRail API error
    """
    _require_write_enabled()

    # Validate run_id
    if run_id < 1:
        raise HTTPException(status_code=400, detail="Run ID must be positive")

    # Build update payload with only non-None fields
    body: dict[str, Any] = {}
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
        client = _make_client()
        updated = client.update_run(run_id, body)
        return {"run": updated}
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        raise HTTPException(status_code=502, detail=f"TestRail API error: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update run: {str(e)}")


@app.get("/api/manage/case/{case_id}")
def api_get_case(case_id: int):
    """
    Get details for a specific test case.

    Args:
        case_id: TestRail case ID to fetch

    Returns:
        Case data including title, refs, and custom fields

    Raises:
        HTTPException 400: Invalid case_id
        HTTPException 404: Case not found
        HTTPException 502: TestRail API error
    """
    # Validate case_id
    if case_id < 1:
        raise HTTPException(status_code=400, detail="Case ID must be positive")

    try:
        client = _make_client()
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
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch case: {str(e)}")


@app.put("/api/manage/case/{case_id}")
def api_update_case(case_id: int, payload: UpdateCase):
    """
    Update an existing test case.

    Args:
        case_id: TestRail case ID to update
        payload: UpdateCase model with fields to update

    Returns:
        Updated case data or dry_run preview

    Raises:
        HTTPException 400: Invalid case_id or validation error
        HTTPException 404: Case not found
        HTTPException 502: TestRail API error
    """
    _require_write_enabled()

    # Validate case_id
    if case_id < 1:
        raise HTTPException(status_code=400, detail="Case ID must be positive")

    # Build update payload with only non-None fields
    body: dict[str, Any] = {}
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
        client = _make_client()
        updated = client.update_case(case_id, body)
        return {"case": updated}
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
        raise HTTPException(status_code=502, detail=f"TestRail API error: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update case: {str(e)}")


# File attachment constants
ALLOWED_FILE_TYPES = {
    "image/png": "PNG",
    "image/jpeg": "JPG",
    "image/gif": "GIF",
    "video/mp4": "MP4",
    "video/webm": "WebM",
    "application/pdf": "PDF",
}
MAX_FILE_SIZE_MB = 25
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


@app.post("/api/manage/case/{case_id}/attachment")
async def api_add_case_attachment(case_id: int, file: UploadFile = File(...)):
    """
    Upload a file attachment to a test case.

    Args:
        case_id: TestRail case ID
        file: File to upload (multipart/form-data)

    Returns:
        Attachment metadata on success

    Raises:
        HTTPException 400: Invalid case_id, file type, or file size
        HTTPException 404: Case not found
        HTTPException 502: TestRail API error
    """
    _require_write_enabled()

    # Validate case_id
    if case_id < 1:
        raise HTTPException(status_code=400, detail="Case ID must be positive")

    # Validate file type
    content_type = file.content_type or ""
    if content_type not in ALLOWED_FILE_TYPES:
        allowed_types = ", ".join(ALLOWED_FILE_TYPES.values())
        raise HTTPException(status_code=400, detail=f"File type not allowed. Accepted types: {allowed_types}")

    # Read file content and validate size
    content = await file.read()
    file_size = len(content)

    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail=f"File size exceeds {MAX_FILE_SIZE_MB}MB limit")

    # Save to temporary file for upload
    import tempfile

    filename = file.filename or "attachment"

    try:
        suffix = Path(filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            client = _make_client()
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


@app.get("/api/manage/case/{case_id}/attachments")
def api_get_case_attachments(case_id: int):
    """
    Get list of attachments for a test case.

    Args:
        case_id: TestRail case ID

    Returns:
        List of attachment metadata

    Raises:
        HTTPException 400: Invalid case_id
        HTTPException 404: Case not found
        HTTPException 502: TestRail API error
    """
    # Validate case_id
    if case_id < 1:
        raise HTTPException(status_code=400, detail="Case ID must be positive")

    try:
        client = _make_client()
        attachments = client.get_attachments_for_case(case_id)

        # Map attachments to response format
        attachment_list = []
        for att in attachments:
            att_id = att.get("id")
            if att_id is None:
                continue

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


@app.delete("/api/manage/plan/{plan_id}")
def api_delete_plan(plan_id: int, dry_run: bool = False):
    """
    Delete a test plan from TestRail.

    Args:
        plan_id: TestRail plan ID to delete
        dry_run: If True, return preview without actually deleting

    Returns:
        Success message with deleted plan ID or dry_run preview

    Raises:
        HTTPException 400: Invalid plan_id
        HTTPException 404: Plan not found
        HTTPException 502: TestRail API error
    """
    _require_write_enabled()

    # Validate plan_id
    if plan_id < 1:
        raise HTTPException(status_code=400, detail="Plan ID must be positive")

    if dry_run:
        return {"dry_run": True, "plan_id": plan_id, "action": "delete_plan", "message": f"Would delete plan {plan_id}"}

    try:
        client = _make_client()

        # Attempt to delete the plan
        client.delete_plan(plan_id)

        # Clear relevant cache entries after successful deletion
        _plans_cache.clear()
        _dashboard_plans_cache.clear()
        _dashboard_plan_detail_cache.clear()
        _dashboard_stats_cache.clear()

        return {"success": True, "plan_id": plan_id, "message": f"Plan {plan_id} deleted successfully"}
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
        raise HTTPException(status_code=502, detail=f"TestRail API error: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete plan: {str(e)}")


@app.delete("/api/manage/run/{run_id}")
def api_delete_run(run_id: int, dry_run: bool = False):
    """
    Delete a test run from TestRail.

    Args:
        run_id: TestRail run ID to delete
        dry_run: If True, return preview without actually deleting

    Returns:
        Success message with deleted run ID or dry_run preview

    Raises:
        HTTPException 400: Invalid run_id
        HTTPException 404: Run not found
        HTTPException 502: TestRail API error
    """
    _require_write_enabled()

    # Validate run_id
    if run_id < 1:
        raise HTTPException(status_code=400, detail="Run ID must be positive")

    if dry_run:
        return {"dry_run": True, "run_id": run_id, "action": "delete_run", "message": f"Would delete run {run_id}"}

    try:
        client = _make_client()

        # Attempt to delete the run
        client.delete_run(run_id)

        # Clear relevant cache entries after successful deletion
        _runs_cache.clear()
        _dashboard_plans_cache.clear()
        _dashboard_plan_detail_cache.clear()
        _dashboard_stats_cache.clear()
        _dashboard_run_stats_cache.clear()

        return {"success": True, "run_id": run_id, "message": f"Run {run_id} deleted successfully"}
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        raise HTTPException(status_code=502, detail=f"TestRail API error: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete run: {str(e)}")


@app.delete("/api/manage/case/{case_id}")
def api_delete_case(case_id: int, dry_run: bool = False):
    """
    Delete a test case from TestRail.

    Args:
        case_id: TestRail case ID to delete
        dry_run: If True, return preview without actually deleting

    Returns:
        Success message with deleted case ID or dry_run preview

    Raises:
        HTTPException 400: Invalid case_id
        HTTPException 404: Case not found
        HTTPException 502: TestRail API error
    """
    _require_write_enabled()

    # Validate case_id
    if case_id < 1:
        raise HTTPException(status_code=400, detail="Case ID must be positive")

    if dry_run:
        return {"dry_run": True, "case_id": case_id, "action": "delete_case", "message": f"Would delete case {case_id}"}

    try:
        client = _make_client()

        # Attempt to delete the case
        client.delete_case(case_id)

        # Clear relevant cache entries after successful deletion
        # Cases don't have dedicated cache, but clear dashboard caches
        # in case the case was part of a run being displayed
        _dashboard_plans_cache.clear()
        _dashboard_plan_detail_cache.clear()
        _dashboard_stats_cache.clear()
        _dashboard_run_stats_cache.clear()

        return {"success": True, "case_id": case_id, "message": f"Case {case_id} deleted successfully"}
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
        raise HTTPException(status_code=502, detail=f"TestRail API error: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete case: {str(e)}")


@app.get("/api/plans")
def api_plans(project: int = 1, is_completed: int | None = None):
    """List plans for a project, optionally filter by completion (0 or 1)."""
    cache_key = ("plans", project, is_completed)
    cached = _plans_cache.get(cache_key)
    if cached:
        payload, expires_at = cached
        data = payload.copy()
        data["meta"] = _cache_meta(True, expires_at)
        return data
    try:
        base_url = env_or_die("TESTRAIL_BASE_URL").rstrip("/")
        user = env_or_die("TESTRAIL_USER")
        api_key = env_or_die("TESTRAIL_API_KEY")
    except SystemExit:
        raise HTTPException(status_code=500, detail="Server missing TestRail credentials")
    session = requests.Session()
    session.auth = (user, api_key)
    plans = get_plans_for_project(session, base_url, project_id=project, is_completed=is_completed)
    # return concise info
    slim = [
        {
            "id": p.get("id"),
            "name": p.get("name"),
            "is_completed": p.get("is_completed"),
            "created_on": p.get("created_on"),
        }
        for p in plans
    ]
    base_payload = {"count": len(slim), "plans": slim}
    expires_at = _plans_cache.set(cache_key, base_payload)
    resp = base_payload.copy()
    resp["meta"] = _cache_meta(False, expires_at)
    return resp


@app.get("/api/runs")
def api_runs(plan: int | None = None, project: int = 1):
    """
    Return runs for a plan. If no plan is provided, return an empty list instead of 422.
    """
    # Gracefully handle missing plan so client-side refreshes don't 422
    if plan is None:
        return {
            "count": 0,
            "runs": [],
            "meta": {
                "cache": {
                    "hit": False,
                    "expires_at": None,
                    "seconds_remaining": 0,
                }
            },
        }
    if plan < 1:
        raise HTTPException(status_code=400, detail="plan must be positive")

    cache_key = ("runs", project, plan)
    cached = _runs_cache.get(cache_key)
    if cached:
        payload, expires_at = cached
        data = payload.copy()
        data["meta"] = _cache_meta(True, expires_at)
        return data
    try:
        base_url = env_or_die("TESTRAIL_BASE_URL").rstrip("/")
        user = env_or_die("TESTRAIL_USER")
        api_key = env_or_die("TESTRAIL_API_KEY")
    except SystemExit:
        raise HTTPException(status_code=500, detail="Server missing TestRail credentials")
    session = requests.Session()
    session.auth = (user, api_key)
    try:
        plan_obj = get_plan(session, base_url, plan)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error fetching plan runs: {e}")
    runs = []
    for entry in plan_obj.get("entries", []):
        suite_name = entry.get("name")
        for r in entry.get("runs", []):
            rid = r.get("id")
            if rid is None:
                continue
            runs.append(
                {
                    "id": rid,
                    "name": r.get("name") or f"Run {rid}",
                    "is_completed": r.get("is_completed"),
                    "suite_name": suite_name,
                }
            )
    runs.sort(key=lambda item: (item.get("is_completed", 0), item.get("name", "")))
    print(f"[api_runs] plan={plan} returned {len(runs)} runs", flush=True)
    base_payload = {"count": len(runs), "runs": runs}
    expires_at = _runs_cache.set(cache_key, base_payload)
    data = base_payload.copy()
    data["meta"] = _cache_meta(False, expires_at)
    return data


# Default status mapping for test cases
DEFAULT_STATUS_MAP = {
    1: "Passed",
    2: "Blocked",
    3: "Untested",
    4: "Retest",
    5: "Failed",
}


@app.get("/api/run/{run_id}")
def api_get_run(run_id: int):
    """
    Fetch details for a specific run.
    """
    try:
        base_url = env_or_die("TESTRAIL_BASE_URL").rstrip("/")
        user = env_or_die("TESTRAIL_USER")
        api_key = env_or_die("TESTRAIL_API_KEY")
    except SystemExit:
        raise HTTPException(status_code=500, detail="Server missing TestRail credentials")

    session = requests.Session()
    session.auth = (user, api_key)

    try:
        # Fetch run details from TestRail
        response = session.get(f"{base_url}/index.php?/api/v2/get_run/{run_id}")
        response.raise_for_status()
        run_data = response.json()

        return {
            "run": {
                "id": run_data.get("id"),
                "name": run_data.get("name"),
                "description": run_data.get("description"),
                "refs": run_data.get("refs"),
                "is_completed": run_data.get("is_completed"),
                "plan_id": run_data.get("plan_id"),
            }
        }
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error fetching run: {e}")


@app.get("/api/tests/{run_id}")
def api_tests_for_run(run_id: int):
    """
    Fetch test cases for a specific run.

    Args:
        run_id: TestRail run ID

    Returns:
        JSON response containing:
        - run_id: The run ID
        - run_name: Name of the run
        - tests: List of test cases with id, case_id, title, status_id, status_name, refs
        - count: Number of tests

    Raises:
        HTTPException 400: Invalid run_id
        HTTPException 404: Run not found
        HTTPException 502: TestRail API error
    """
    # Validate run_id
    if run_id < 1:
        raise HTTPException(status_code=400, detail="Run ID must be positive")

    try:
        client = _make_client()

        # Fetch run details for the run name
        run_data = client.get_run(run_id)
        run_name = run_data.get("name") or f"Run {run_id}"

        # Fetch tests for the run
        tests = client.get_tests_for_run(run_id)

        # Get status mapping (use defaults if API fails)
        try:
            statuses = client.get_statuses_map(defaults=DEFAULT_STATUS_MAP)
        except Exception:
            statuses = DEFAULT_STATUS_MAP.copy()

        # Map tests to response format
        test_list = []
        for test in tests:
            test_id = test.get("id")
            if test_id is None:
                continue

            status_id = test.get("status_id")
            status_name = statuses.get(status_id, f"Status {status_id}") if status_id else "Unknown"

            test_list.append(
                {
                    "id": test_id,
                    "case_id": test.get("case_id"),
                    "title": test.get("title") or f"Test {test_id}",
                    "status_id": status_id,
                    "status_name": status_name,
                    "refs": test.get("refs"),
                }
            )

        return {
            "run_id": run_id,
            "run_name": run_name,
            "tests": test_list,
            "count": len(test_list),
        }

    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        raise HTTPException(status_code=502, detail=f"TestRail API error: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tests: {str(e)}")


@app.post("/api/cache/clear")
def api_cache_clear():
    """
    Clear the plans and runs cache for the reporter page.

    This endpoint clears the server-side cache for plans and runs,
    forcing fresh data to be fetched from TestRail on the next request.

    Use this when:
    - Plans have been added/removed in TestRail
    - Runs have been modified in TestRail
    - You want to ensure you're seeing the latest data

    Returns:
        dict: Success message with timestamp
    """
    _plans_cache.clear()
    _runs_cache.clear()

    return {"success": True, "message": "Cache cleared successfully", "cleared_at": datetime.now().isoformat()}


@app.get("/api/cases")
def api_cases(
    project: int = 1,
    suite_id: int | None = None,
    section_id: int | None = None,
    filters: str | None = None,
):
    try:
        client = _make_client()
        filter_section_id = None
        if not section_id and filters:
            try:
                parsed = json.loads(filters)
                section_vals = parsed.get("filters", {}).get("cases:section_id", {}).get("values")
                if isinstance(section_vals, list) and section_vals:
                    try:
                        filter_section_id = int(str(section_vals[0]).strip())
                    except (TypeError, ValueError):
                        filter_section_id = None
            except Exception:
                filter_section_id = None
        effective_section = section_id or filter_section_id
        cases = client.get_cases(project, suite_id=suite_id, section_id=effective_section)
    except HTTPException:
        raise
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error fetching cases: {e}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load cases: {exc}")
    slim = []
    for c in cases:
        cid = c.get("id")
        if cid is None:
            continue
        slim.append(
            {
                "id": cid,
                "title": c.get("title") or f"Case {cid}",
                "refs": c.get("refs"),
                "updated_on": c.get("updated_on"),
                "priority_id": c.get("priority_id"),
                "section_id": c.get("section_id"),
            }
        )
    return {"count": len(slim), "cases": slim}


@app.get("/api/users")
def api_users(project: int = 1):
    """Return list of users for dropdowns."""
    try:
        client = _make_client()
        users = client.get_users_map()
        items = [{"id": uid, "name": name} for uid, name in sorted(users.items(), key=lambda kv: kv[1])]
        return {"count": len(items), "users": items}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load users: {exc}")


@app.get("/ui", response_class=HTMLResponse)
def ui_alias(request: Request):
    return index(request)


# Dashboard cache configuration (TTL in seconds)
dashboard_plans_cache_ttl = _int_env("DASHBOARD_PLANS_CACHE_TTL", 300)
dashboard_plan_detail_cache_ttl = _int_env("DASHBOARD_PLAN_DETAIL_CACHE_TTL", 180)
dashboard_stats_cache_ttl = _int_env("DASHBOARD_STATS_CACHE_TTL", 120)
dashboard_run_stats_cache_ttl = _int_env("DASHBOARD_RUN_STATS_CACHE_TTL", 120)

# Dashboard pagination configuration
dashboard_default_page_size = _int_env("DASHBOARD_DEFAULT_PAGE_SIZE", 25)
dashboard_max_page_size = _int_env("DASHBOARD_MAX_PAGE_SIZE", 25)

# Dashboard visual threshold configuration (percentages)
dashboard_pass_rate_high = _int_env("DASHBOARD_PASS_RATE_HIGH", 80)
dashboard_pass_rate_medium = _int_env("DASHBOARD_PASS_RATE_MEDIUM", 50)
dashboard_critical_fail_threshold = _int_env("DASHBOARD_CRITICAL_FAIL_THRESHOLD", 20)
dashboard_critical_block_threshold = _int_env("DASHBOARD_CRITICAL_BLOCK_THRESHOLD", 10)

# Separate caches for different dashboard data types
_dashboard_plans_cache = TTLCache(ttl_seconds=dashboard_plans_cache_ttl, maxsize=128)
_dashboard_plan_detail_cache = TTLCache(ttl_seconds=dashboard_plan_detail_cache_ttl, maxsize=64)
_dashboard_stats_cache = TTLCache(ttl_seconds=dashboard_stats_cache_ttl, maxsize=128)
_dashboard_run_stats_cache = TTLCache(ttl_seconds=dashboard_run_stats_cache_ttl, maxsize=256)


@app.get("/api/dashboard/plans", response_model=DashboardPlansResponse)
def api_dashboard_plans(
    project: int = 1,
    is_completed: int | None = None,
    limit: int | None = None,
    offset: int = 0,
    created_after: int | None = None,
    created_before: int | None = None,
    search: str | None = None,
):
    """
    Get paginated list of test plans with aggregated statistics for the dashboard.

    This endpoint fetches test plans from TestRail and calculates comprehensive statistics
    for each plan, including pass rates, completion rates, and status distributions.
    Results are cached for performance (default: 5 minutes).

    Query Parameters:
        project (int): TestRail project ID (default: 1)
            - Must be a positive integer
            - Identifies which project's plans to fetch

        is_completed (int, optional): Filter by completion status
            - 0: Show only active (incomplete) plans
            - 1: Show only completed plans
            - None: Show all plans (default)

        limit (int, optional): Maximum number of plans to return per page
            - Default: 25 (configured via DASHBOARD_DEFAULT_PAGE_SIZE)
            - Maximum: 25 (configured via DASHBOARD_MAX_PAGE_SIZE)
            - Automatically clamped to valid range
            - Note: Statistics calculation is parallelized (2 workers) for better performance

        offset (int): Number of plans to skip for pagination (default: 0)
            - Must be non-negative
            - Used with limit for pagination (e.g., offset=50, limit=50 for page 2)

        created_after (int, optional): Unix timestamp filter
            - Only return plans created after this timestamp
            - Must be non-negative
            - Can be combined with created_before for date range

        created_before (int, optional): Unix timestamp filter
            - Only return plans created before this timestamp
            - Must be non-negative
            - Must be >= created_after if both specified

        search (str, optional): Search term for filtering by plan name
            - Case-insensitive substring match
            - Applied after other filters
            - Searches in plan name field only

    Returns:
        DashboardPlansResponse: JSON response containing:
            - plans (list): Array of plan objects with statistics
                Each plan includes:
                - plan_id: TestRail plan ID
                - plan_name: Plan name
                - created_on: Unix timestamp of creation
                - is_completed: Boolean completion status
                - updated_on: Unix timestamp of last update (may be null)
                - total_runs: Number of test runs in the plan
                - total_tests: Total test cases across all runs
                - status_distribution: Dict mapping status names to counts
                - pass_rate: Percentage of passed tests (0.0-100.0)
                - completion_rate: Percentage of executed tests (0.0-100.0)
                - failed_count: Number of failed tests
                - blocked_count: Number of blocked tests
                - untested_count: Number of untested tests

            - total_count (int): Total number of plans matching filters (before pagination)
            - offset (int): Current offset value
            - limit (int): Current limit value
            - has_more (bool): Whether more pages are available
            - meta (dict): Cache metadata
                - cache.hit: Whether response came from cache
                - cache.expires_at: ISO timestamp when cache expires
                - cache.seconds_remaining: Seconds until cache expiration

    Raises:
        HTTPException 400: Invalid parameters (negative values, invalid date range, etc.)
        HTTPException 502: TestRail API connection error
        HTTPException 504: TestRail API timeout
        HTTPException 500: Unexpected server error

    Example:
        GET /api/dashboard/plans?project=1&is_completed=0&limit=25&offset=0

        Response:
        {
            "plans": [
                {
                    "plan_id": 123,
                    "plan_name": "Sprint 42 Testing",
                    "created_on": 1701388800,
                    "is_completed": false,
                    "total_runs": 5,
                    "total_tests": 150,
                    "pass_rate": 85.5,
                    "completion_rate": 92.0,
                    ...
                }
            ],
            "total_count": 47,
            "offset": 0,
            "limit": 25,
            "has_more": true,
            "meta": {
                "cache": {
                    "hit": false,
                    "expires_at": "2024-12-04T10:30:00Z",
                    "seconds_remaining": 300
                }
            }
        }

    Performance Notes:
        - Results are cached for DASHBOARD_PLANS_CACHE_TTL seconds (default: 300)
        - Statistics calculation involves multiple API calls to TestRail
        - Large plans with many runs may take several seconds to process
        - Use pagination and filters to improve response times

    Cache Behavior:
        - Cache key includes all query parameters
        - Different filter combinations have separate cache entries
        - Use POST /api/dashboard/cache/clear to force refresh
        - Cache metadata in response indicates hit/miss status
    """
    # Validate parameters
    if project < 1:
        raise HTTPException(status_code=400, detail="Project ID must be positive")

    if offset < 0:
        raise HTTPException(status_code=400, detail="Offset must be non-negative")

    if is_completed is not None and is_completed not in (0, 1):
        raise HTTPException(status_code=400, detail="is_completed must be 0 or 1")

    # Validate date range
    if created_after is not None and created_after < 0:
        raise HTTPException(status_code=400, detail="created_after must be non-negative timestamp")

    if created_before is not None and created_before < 0:
        raise HTTPException(status_code=400, detail="created_before must be non-negative timestamp")

    if created_after is not None and created_before is not None and created_after > created_before:
        raise HTTPException(status_code=400, detail="created_after must be less than or equal to created_before")

    # Validate and normalize limit using configured defaults
    if limit is None:
        limit = dashboard_default_page_size
    limit = max(1, min(limit, dashboard_max_page_size))

    # Check cache
    cache_key = ("dashboard_plans", project, is_completed, offset, limit, created_after, created_before, search)
    cached = _dashboard_plans_cache.get(cache_key)
    if cached:
        payload, expires_at = cached
        data = payload.copy()
        estimated_flag = data.pop("_estimated_total", False)
        data["meta"] = _cache_meta(True, expires_at)
        data["meta"]["estimated_total"] = estimated_flag
        return data

    try:
        client = _make_client()

        def _apply_search_and_date(plans: list[dict]) -> list[dict]:
            filtered = []
            search_term = search.strip().lower() if search else None
            for plan in plans:
                if not isinstance(plan, dict):
                    continue
                if created_after is not None or created_before is not None:
                    created_on = plan.get("created_on")
                    if created_on is None:
                        created_on = 0
                    elif not isinstance(created_on, (int, float)):
                        try:
                            created_on = int(created_on)
                        except (ValueError, TypeError):
                            created_on = 0
                    if created_after is not None and created_on < created_after:
                        continue
                    if created_before is not None and created_on > created_before:
                        continue
                if search_term:
                    plan_name = plan.get("name", "")
                    if not isinstance(plan_name, str):
                        plan_name = str(plan_name) if plan_name is not None else ""
                    if search_term not in plan_name.lower():
                        continue
                filtered.append(plan)
            return filtered

        # Fetch only the window we need (plus one extra to detect has_more)
        page_batch_size = max(limit * 2, 50)
        needed = limit + 1
        cursor = offset
        collected: list[dict] = []
        source_exhausted = False

        while len(collected) < needed:
            try:
                batch = client.get_plans_for_project(
                    project,
                    is_completed=is_completed,
                    created_after=created_after,
                    created_before=created_before,
                    start_offset=cursor,
                    max_plans=page_batch_size,
                    page_limit=page_batch_size,
                )
            except requests.exceptions.Timeout as e:
                print(f"Error: TestRail API timeout for project {project}: {e}", flush=True)
                raise HTTPException(status_code=504, detail="TestRail API request timed out. Please try again.")
            except requests.exceptions.ConnectionError as e:
                print(f"Error: TestRail API connection error for project {project}: {e}", flush=True)
                raise HTTPException(
                    status_code=502, detail="Unable to connect to TestRail API. Please check your connection."
                )

            if not batch:
                source_exhausted = True
                break

            if not isinstance(batch, list):
                print(f"Error: Invalid plans data type: {type(batch)}", flush=True)
                raise HTTPException(status_code=500, detail="Invalid response from TestRail API")

            cursor += len(batch)
            filtered_batch = _apply_search_and_date(batch)
            collected.extend(filtered_batch)

            if len(batch) < page_batch_size:
                source_exhausted = True
                break

        total_count = offset + len(collected)
        if not source_exhausted or len(collected) > limit:
            # Indicate at least one more plan may be available
            total_count += 1

        paginated_plans = collected[:limit]

        # Calculate statistics for each plan using parallel processing
        from app.dashboard_stats import calculate_plan_statistics

        def calculate_stats_for_plan(plan):
            """Helper function to calculate stats for a single plan."""
            if not isinstance(plan, dict):
                print(f"Warning: Skipping invalid plan data: {plan}", flush=True)
                return None

            plan_id = plan.get("id")
            if not plan_id:
                print(f"Warning: Skipping plan with missing ID: {plan}", flush=True)
                return None

            try:
                # Create a new client for this thread
                thread_client = _make_client()
                stats = calculate_plan_statistics(plan_id, thread_client)

                # Convert to dict format
                return {
                    "plan_id": stats.plan_id,
                    "plan_name": stats.plan_name,
                    "created_on": stats.created_on,
                    "is_completed": stats.is_completed,
                    "updated_on": stats.updated_on,
                    "total_runs": stats.total_runs,
                    "total_tests": stats.total_tests,
                    "status_distribution": stats.status_distribution,
                    "pass_rate": stats.pass_rate,
                    "completion_rate": stats.completion_rate,
                    "failed_count": stats.failed_count,
                    "blocked_count": stats.blocked_count,
                    "untested_count": stats.untested_count,
                }
            except requests.exceptions.RequestException as e:
                print(f"Warning: API error calculating stats for plan {plan_id}: {e}", flush=True)
                # Include plan with minimal info if stats calculation fails
                return {
                    "plan_id": plan_id,
                    "plan_name": plan.get("name", f"Plan {plan_id}"),
                    "created_on": plan.get("created_on", 0),
                    "is_completed": plan.get("is_completed", False),
                    "updated_on": plan.get("updated_on"),
                    "total_runs": 0,
                    "total_tests": 0,
                    "status_distribution": {},
                    "pass_rate": 0.0,
                    "completion_rate": 0.0,
                    "failed_count": 0,
                    "blocked_count": 0,
                    "untested_count": 0,
                }
            except Exception as e:
                print(f"Warning: Failed to calculate stats for plan {plan_id}: {e}", flush=True)
                # Include plan with minimal info if stats calculation fails
                return {
                    "plan_id": plan_id,
                    "plan_name": plan.get("name", f"Plan {plan_id}"),
                    "created_on": plan.get("created_on", 0),
                    "is_completed": plan.get("is_completed", False),
                    "updated_on": plan.get("updated_on"),
                    "total_runs": 0,
                    "total_tests": 0,
                    "status_distribution": {},
                    "pass_rate": 0.0,
                    "completion_rate": 0.0,
                    "failed_count": 0,
                    "blocked_count": 0,
                    "untested_count": 0,
                }

        # Use ThreadPoolExecutor to calculate stats in parallel
        # Limit to 2 workers to avoid TestRail API rate limits
        max_workers = min(2, len(paginated_plans))
        plans_with_stats = []

        if paginated_plans:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_plan = {executor.submit(calculate_stats_for_plan, plan): plan for plan in paginated_plans}

                # Collect results as they complete
                for future in future_to_plan:
                    try:
                        result = future.result(timeout=30)  # 30 second timeout per plan
                        if result is not None:
                            plans_with_stats.append(result)
                    except Exception as e:
                        plan = future_to_plan[future]
                        plan_id = plan.get("id") if isinstance(plan, dict) else "unknown"
                        print(f"Warning: Failed to get stats for plan {plan_id}: {e}", flush=True)

        has_more = (len(collected) > limit) or (not source_exhausted)
        estimated_total = not source_exhausted or len(collected) > limit

        response_data = {
            "plans": plans_with_stats,
            "total_count": total_count,
            "offset": offset,
            "limit": limit,
            "has_more": has_more,
            "meta": {},
            "_estimated_total": estimated_total,
        }

        # Cache the response
        expires_at = _dashboard_plans_cache.set(cache_key, response_data, ttl_seconds=dashboard_plans_cache_ttl)
        meta_dict = _cache_meta(False, expires_at)
        meta_dict["estimated_total"] = estimated_total
        response_data["meta"] = meta_dict

        return response_data

    except HTTPException:
        raise
    except requests.exceptions.RequestException as e:
        print(f"Error: TestRail API error in dashboard plans: {e}", flush=True)
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {str(e)}")
    except Exception as e:
        print(f"Error: Unexpected error in dashboard plans: {e}", flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard plans: {str(e)}")


@app.get("/api/dashboard/plan/{plan_id}", response_model=DashboardPlanDetail)
def api_dashboard_plan_detail(plan_id: int):
    """
    Get detailed information for a specific test plan including all runs and their statistics.

    This endpoint fetches comprehensive details for a single plan, including aggregated
    plan-level statistics and individual statistics for each run within the plan.
    Results are cached for performance (default: 3 minutes).

    Path Parameters:
        plan_id (int): TestRail plan ID
            - Must be a positive integer
            - Plan must exist and be accessible

    Returns:
        DashboardPlanDetail: JSON response containing:
            - plan (dict): Plan object with aggregated statistics
                - plan_id: TestRail plan ID
                - plan_name: Plan name
                - created_on: Unix timestamp of creation
                - is_completed: Boolean completion status
                - updated_on: Unix timestamp of last update (may be null)
                - total_runs: Number of test runs in the plan
                - total_tests: Total test cases across all runs
                - status_distribution: Dict mapping status names to counts
                - pass_rate: Percentage of passed tests (0.0-100.0)
                - completion_rate: Percentage of executed tests (0.0-100.0)
                - failed_count: Number of failed tests
                - blocked_count: Number of blocked tests
                - untested_count: Number of untested tests

            - runs (list): Array of run objects with statistics
                Each run includes:
                - run_id: TestRail run ID
                - run_name: Run name
                - suite_name: Test suite name (may be null)
                - is_completed: Boolean completion status
                - total_tests: Number of test cases in run
                - status_distribution: Dict mapping status names to counts
                - pass_rate: Percentage of passed tests (0.0-100.0)
                - completion_rate: Percentage of executed tests (0.0-100.0)
                - updated_on: Unix timestamp of last update (may be null)

            - meta (dict): Cache metadata
                - cache.hit: Whether response came from cache
                - cache.expires_at: ISO timestamp when cache expires
                - cache.seconds_remaining: Seconds until cache expiration

    Raises:
        HTTPException 400: Invalid plan_id (not positive integer)
        HTTPException 404: Plan not found or contains invalid data
        HTTPException 502: TestRail API connection error
        HTTPException 504: TestRail API timeout
        HTTPException 500: Unexpected server error

    Example:
        GET /api/dashboard/plan/123

        Response:
        {
            "plan": {
                "plan_id": 123,
                "plan_name": "Sprint 42 Testing",
                "total_runs": 3,
                "total_tests": 150,
                "pass_rate": 85.5,
                ...
            },
            "runs": [
                {
                    "run_id": 456,
                    "run_name": "Smoke Tests",
                    "suite_name": "Core Functionality",
                    "total_tests": 50,
                    "pass_rate": 90.0,
                    ...
                },
                ...
            ],
            "meta": {
                "cache": {
                    "hit": true,
                    "expires_at": "2024-12-04T10:25:00Z",
                    "seconds_remaining": 120
                }
            }
        }

    Performance Notes:
        - Results are cached for DASHBOARD_PLAN_DETAIL_CACHE_TTL seconds (default: 180)
        - Fetches statistics for all runs in the plan
        - May involve many API calls for plans with numerous runs
        - Failed run statistics are logged but don't fail the entire request

    Use Cases:
        - Expanding a plan card in the dashboard UI
        - Viewing detailed run-level statistics
        - Identifying which runs need attention
        - Drilling down from plan-level to run-level metrics
    """
    # Validate plan_id
    if plan_id < 1:
        raise HTTPException(status_code=400, detail="Plan ID must be positive")

    # Check cache
    cache_key = ("dashboard_plan_detail", plan_id)
    cached = _dashboard_plan_detail_cache.get(cache_key)
    if cached:
        payload, expires_at = cached
        data = payload.copy()
        data["meta"] = _cache_meta(True, expires_at)
        return data

    try:
        client = _make_client()

        # Calculate plan statistics
        from app.dashboard_stats import (
            calculate_plan_statistics,
            calculate_run_statistics,
        )

        try:
            plan_stats = calculate_plan_statistics(plan_id, client)
        except requests.exceptions.Timeout as e:
            print(f"Error: TestRail API timeout for plan {plan_id}: {e}", flush=True)
            raise HTTPException(status_code=504, detail="TestRail API request timed out. Please try again.")
        except requests.exceptions.ConnectionError as e:
            print(f"Error: TestRail API connection error for plan {plan_id}: {e}", flush=True)
            raise HTTPException(
                status_code=502, detail="Unable to connect to TestRail API. Please check your connection."
            )
        except ValueError as e:
            print(f"Error: Invalid data for plan {plan_id}: {e}", flush=True)
            raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found or contains invalid data")

        # Convert plan stats to dict
        plan_dict = {
            "plan_id": plan_stats.plan_id,
            "plan_name": plan_stats.plan_name,
            "created_on": plan_stats.created_on,
            "is_completed": plan_stats.is_completed,
            "updated_on": plan_stats.updated_on,
            "total_runs": plan_stats.total_runs,
            "total_tests": plan_stats.total_tests,
            "status_distribution": plan_stats.status_distribution,
            "pass_rate": plan_stats.pass_rate,
            "completion_rate": plan_stats.completion_rate,
            "failed_count": plan_stats.failed_count,
            "blocked_count": plan_stats.blocked_count,
            "untested_count": plan_stats.untested_count,
        }

        # Get all runs for the plan
        try:
            plan_data = client.get_plan(plan_id)
        except requests.exceptions.RequestException as e:
            print(f"Error: Failed to fetch plan data for {plan_id}: {e}", flush=True)
            raise HTTPException(status_code=502, detail=f"Error fetching plan data from TestRail API: {str(e)}")

        # Validate plan data
        if not isinstance(plan_data, dict):
            print(f"Error: Invalid plan data type for {plan_id}: {type(plan_data)}", flush=True)
            raise HTTPException(status_code=500, detail="Invalid response from TestRail API")

        run_ids = []
        entries = plan_data.get("entries", [])
        if not isinstance(entries, list):
            print(f"Warning: Invalid entries type for plan {plan_id}: {type(entries)}", flush=True)
            entries = []

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            runs = entry.get("runs", [])
            if not isinstance(runs, list):
                continue
            for run in runs:
                if not isinstance(run, dict):
                    continue
                run_id = run.get("id")
                if run_id:
                    run_ids.append(run_id)

        # Calculate statistics for each run
        runs_with_stats = []
        for run_id in run_ids:
            try:
                run_stats = calculate_run_statistics(run_id, client)

                # Convert to dict format
                run_dict = {
                    "run_id": run_stats.run_id,
                    "run_name": run_stats.run_name,
                    "suite_name": run_stats.suite_name,
                    "is_completed": run_stats.is_completed,
                    "total_tests": run_stats.total_tests,
                    "status_distribution": run_stats.status_distribution,
                    "pass_rate": run_stats.pass_rate,
                    "completion_rate": run_stats.completion_rate,
                    "updated_on": run_stats.updated_on,
                }
                runs_with_stats.append(run_dict)
            except requests.exceptions.RequestException as e:
                print(f"Warning: API error calculating stats for run {run_id}: {e}", flush=True)
            except Exception as e:
                print(f"Warning: Failed to calculate stats for run {run_id}: {e}", flush=True)

        response_data = {
            "plan": plan_dict,
            "runs": runs_with_stats,
            "meta": {},
        }

        # Cache the response
        expires_at = _dashboard_plan_detail_cache.set(
            cache_key, response_data, ttl_seconds=dashboard_plan_detail_cache_ttl
        )
        response_data["meta"] = _cache_meta(False, expires_at)

        return response_data

    except HTTPException:
        raise
    except requests.exceptions.RequestException as e:
        print(f"Error: TestRail API error in plan detail: {e}", flush=True)
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {str(e)}")
    except Exception as e:
        print(f"Error: Unexpected error in plan detail: {e}", flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch plan details: {str(e)}")


@app.get("/api/dashboard/config")
def api_dashboard_config():
    """
    Get dashboard configuration values for client-side use.

    This endpoint returns the server-side configuration values that control
    dashboard behavior, allowing the frontend to apply consistent thresholds,
    pagination limits, and cache TTLs.

    Returns:
        dict: Configuration object containing:
            - cache (dict): Cache TTL values in seconds
                - plans_ttl: Plans list cache duration (default: 300)
                - plan_detail_ttl: Plan details cache duration (default: 180)
                - stats_ttl: Statistics cache duration (default: 120)
                - run_stats_ttl: Run statistics cache duration (default: 120)

            - pagination (dict): Pagination configuration
                - default_page_size: Default plans per page (default: 50)
                - max_page_size: Maximum plans per page (default: 200)

            - visual_thresholds (dict): Thresholds for visual indicators (percentages)
                - pass_rate_high: Green threshold (default: 80)
                - pass_rate_medium: Yellow threshold (default: 50)
                - critical_fail_threshold: Critical failure rate (default: 20)
                - critical_block_threshold: Critical block rate (default: 10)

    Example:
        GET /api/dashboard/config

        Response:
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

    Configuration Sources:
        All values can be customized via environment variables:
        - DASHBOARD_PLANS_CACHE_TTL
        - DASHBOARD_PLAN_DETAIL_CACHE_TTL
        - DASHBOARD_STATS_CACHE_TTL
        - DASHBOARD_RUN_STATS_CACHE_TTL
        - DASHBOARD_DEFAULT_PAGE_SIZE
        - DASHBOARD_MAX_PAGE_SIZE
        - DASHBOARD_PASS_RATE_HIGH
        - DASHBOARD_PASS_RATE_MEDIUM
        - DASHBOARD_CRITICAL_FAIL_THRESHOLD
        - DASHBOARD_CRITICAL_BLOCK_THRESHOLD

    Use Cases:
        - Frontend initialization to match server configuration
        - Displaying cache expiration information to users
        - Applying consistent color coding across UI
        - Validating pagination parameters before API calls
    """
    return {
        "cache": {
            "plans_ttl": dashboard_plans_cache_ttl,
            "plan_detail_ttl": dashboard_plan_detail_cache_ttl,
            "stats_ttl": dashboard_stats_cache_ttl,
            "run_stats_ttl": dashboard_run_stats_cache_ttl,
        },
        "pagination": {
            "default_page_size": dashboard_default_page_size,
            "max_page_size": dashboard_max_page_size,
        },
        "visual_thresholds": {
            "pass_rate_high": dashboard_pass_rate_high,
            "pass_rate_medium": dashboard_pass_rate_medium,
            "critical_fail_threshold": dashboard_critical_fail_threshold,
            "critical_block_threshold": dashboard_critical_block_threshold,
        },
    }


@app.post("/api/dashboard/cache/clear")
def api_dashboard_cache_clear():
    """
    Clear all dashboard caches to force fresh data fetch from TestRail.

    This endpoint clears all server-side caches used by the dashboard,
    ensuring that the next request fetches fresh data from TestRail.
    Used by the dashboard refresh functionality.

    Method: POST (to prevent accidental cache clearing from GET requests)

    Returns:
        dict: Status response containing:
            - status: "success" if caches were cleared
            - message: Human-readable confirmation message
            - cleared_caches: List of cache names that were cleared

    Example:
        POST /api/dashboard/cache/clear

        Response:
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

    Caches Cleared:
        - dashboard_plans: Plans list cache (all filter combinations)
        - dashboard_plan_detail: Individual plan details cache
        - dashboard_stats: Plan statistics cache
        - dashboard_run_stats: Run statistics cache

    Side Effects:
        - All cached dashboard data is immediately invalidated
        - Next dashboard request will fetch fresh data from TestRail
        - May cause temporary performance impact as caches rebuild
        - Does not affect other application caches (plans, runs, etc.)

    Use Cases:
        - User clicks "Refresh" button in dashboard
        - After creating/updating plans or runs in TestRail
        - When immediate data accuracy is required
        - Troubleshooting stale data issues

    Performance Notes:
        - Cache clearing is instantaneous (< 1ms)
        - Subsequent requests will be slower until caches rebuild
        - Consider rate limiting this endpoint in production
        - Multiple concurrent clears are safe (thread-safe implementation)
    """
    _dashboard_plans_cache.clear()
    _dashboard_plan_detail_cache.clear()
    _dashboard_stats_cache.clear()
    _dashboard_run_stats_cache.clear()

    return {
        "status": "success",
        "message": "All dashboard caches cleared",
        "cleared_caches": ["dashboard_plans", "dashboard_plan_detail", "dashboard_stats", "dashboard_run_stats"],
    }


@app.get("/api/dashboard/runs/{plan_id}", response_model=DashboardRunsResponse)
def api_dashboard_runs(plan_id: int):
    """
    Get list of runs for a specific plan with statistics.

    Args:
        plan_id: TestRail plan ID

    Returns:
        DashboardRunsResponse with run statistics
    """
    # Validate plan_id
    if plan_id < 1:
        raise HTTPException(status_code=400, detail="Plan ID must be positive")

    # Check cache
    cache_key = ("dashboard_runs", plan_id)
    cached = _dashboard_stats_cache.get(cache_key)
    if cached:
        payload, expires_at = cached
        data = payload.copy()
        data["meta"] = _cache_meta(True, expires_at)
        return data

    try:
        client = _make_client()

        # Get all runs for the plan
        try:
            plan_data = client.get_plan(plan_id)
        except requests.exceptions.Timeout as e:
            print(f"Error: TestRail API timeout for plan {plan_id}: {e}", flush=True)
            raise HTTPException(status_code=504, detail="TestRail API request timed out. Please try again.")
        except requests.exceptions.ConnectionError as e:
            print(f"Error: TestRail API connection error for plan {plan_id}: {e}", flush=True)
            raise HTTPException(
                status_code=502, detail="Unable to connect to TestRail API. Please check your connection."
            )
        except requests.exceptions.RequestException as e:
            print(f"Error: Failed to fetch plan data for {plan_id}: {e}", flush=True)
            raise HTTPException(status_code=502, detail=f"Error fetching plan data from TestRail API: {str(e)}")

        # Validate plan data
        if not isinstance(plan_data, dict):
            print(f"Error: Invalid plan data type for {plan_id}: {type(plan_data)}", flush=True)
            raise HTTPException(status_code=500, detail="Invalid response from TestRail API")

        run_ids = []
        entries = plan_data.get("entries", [])
        if not isinstance(entries, list):
            print(f"Warning: Invalid entries type for plan {plan_id}: {type(entries)}", flush=True)
            entries = []

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            runs = entry.get("runs", [])
            if not isinstance(runs, list):
                continue
            for run in runs:
                if not isinstance(run, dict):
                    continue
                run_id = run.get("id")
                if run_id:
                    run_ids.append(run_id)

        # Calculate statistics for each run
        from app.dashboard_stats import calculate_run_statistics

        runs_with_stats = []
        for run_id in run_ids:
            try:
                run_stats = calculate_run_statistics(run_id, client)

                # Convert to dict format
                run_dict = {
                    "run_id": run_stats.run_id,
                    "run_name": run_stats.run_name,
                    "suite_name": run_stats.suite_name,
                    "is_completed": run_stats.is_completed,
                    "total_tests": run_stats.total_tests,
                    "status_distribution": run_stats.status_distribution,
                    "pass_rate": run_stats.pass_rate,
                    "completion_rate": run_stats.completion_rate,
                    "updated_on": run_stats.updated_on,
                }
                runs_with_stats.append(run_dict)
            except requests.exceptions.RequestException as e:
                print(f"Warning: API error calculating stats for run {run_id}: {e}", flush=True)
            except Exception as e:
                print(f"Warning: Failed to calculate stats for run {run_id}: {e}", flush=True)

        response_data = {
            "plan_id": plan_id,
            "runs": runs_with_stats,
            "meta": {},
        }

        # Cache the response
        expires_at = _dashboard_stats_cache.set(cache_key, response_data, ttl_seconds=dashboard_run_stats_cache_ttl)
        response_data["meta"] = _cache_meta(False, expires_at)

        return response_data

    except HTTPException:
        raise
    except requests.exceptions.RequestException as e:
        print(f"Error: TestRail API error in dashboard runs: {e}", flush=True)
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {str(e)}")
    except Exception as e:
        print(f"Error: Unexpected error in dashboard runs: {e}", flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch runs: {str(e)}")
