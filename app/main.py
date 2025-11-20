import threading
import time
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Form, HTTPException, Query, Body, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from dotenv import load_dotenv
from pydantic import BaseModel, field_validator, model_validator

from testrail_daily_report import (
    generate_report,
    get_plans_for_project,
    get_plan,
    env_or_die,
    capture_telemetry,
    log_memory,
)
import requests
import glob

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
            self._store[key] = (expires_at, value.copy() if isinstance(value, dict) else value)
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


@dataclass
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
        data = job.to_dict()
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
            reporter = lambda stage, payload=None: self.report_progress(job_id, stage, payload or {})
            with capture_telemetry() as telemetry:
                path = generate_report(**job.params, progress=reporter)
            duration_ms = (time.perf_counter() - start) * 1000.0
            completed_at = datetime.now(timezone.utc)
            job.completed_at = completed_at
            job.path = path
            job.url = "/reports/" + Path(path).name
            api_calls = telemetry.get("api_calls", []) if isinstance(telemetry, dict) else []
            job.meta = {
                "generated_at": completed_at.isoformat(),
                "duration_ms": round(duration_ms, 2),
                "api_call_count": len(api_calls),
                "api_calls": api_calls,
            }
            job.status = "success"
            print(f"[report-job] {job_id} completed in {duration_ms:.0f}ms -> {job.url}", flush=True)
        except Exception as exc:
            job.error = str(exc)
            job.status = "error"
            job.completed_at = datetime.now(timezone.utc)
            print(f"[report-job] {job_id} failed: {exc}", flush=True)
        finally:
            self._trim_history()


def _sequential_report_worker_count() -> tuple[int, int]:
    try:
        requested = max(1, int(os.getenv("REPORT_WORKERS", "1")))
    except ValueError:
        requested = 1
    if requested > 1:
        print(
            "INFO: REPORT_WORKERS>1 requested but sequential execution is enforced to reduce memory usage.",
            flush=True,
        )
    return 1, requested


report_worker_count, report_worker_requested = _sequential_report_worker_count()
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
    report_workers = f"{report_worker_count} (sequential)"
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
        print("WARNING: WEB_CONCURRENCY > 1 will break async job polling; limit uvicorn workers (WEB_CONCURRENCY) to 1.", flush=True)

    _start_keepalive()
    _start_memlog()

@app.on_event("shutdown")
def on_shutdown():
    _stop_keepalive()
    _stop_memlog()

@app.get("/healthz")
def healthz():
    return {"ok": True}


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
            "brand": brand,
            "logo_url": logo_url,
        },
    )


@app.post("/generate")
def generate(
    project: int = Form(1),
    plan: str = Form(""),  # matches <input name="plan">
    run: str = Form(""),   # matches <input name="run">
    run_ids: list[str] | None = Form(default=None),
):
    # Convert blank strings to None, otherwise parse to int
    plan = int(plan) if str(plan).strip() else None
    run = int(run) if str(run).strip() else None
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
def api_runs(plan: int, project: int = 1):
    if not plan:
        raise HTTPException(status_code=400, detail="plan is required")
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
            runs.append({
                "id": rid,
                "name": r.get("name") or f"Run {rid}",
                "is_completed": r.get("is_completed"),
                "suite_name": suite_name,
            })
    runs.sort(key=lambda item: (item.get("is_completed", 0), item.get("name", "")))
    print(f"[api_runs] plan={plan} returned {len(runs)} runs", flush=True)
    base_payload = {"count": len(runs), "runs": runs}
    expires_at = _runs_cache.set(cache_key, base_payload)
    data = base_payload.copy()
    data["meta"] = _cache_meta(False, expires_at)
    return data

@app.get("/ui", response_class=HTMLResponse)
def ui_alias(request: Request):
    return index(request)
