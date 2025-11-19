import threading
import time
import uuid
from collections import deque
import queue
from dataclasses import dataclass, field
from datetime import datetime, timezone
import importlib
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Form, HTTPException, Query, Body, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from dotenv import load_dotenv
from pydantic import BaseModel, field_validator, model_validator

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


_report_module = None
_report_module_lock = threading.Lock()


def _get_report_module():
    global _report_module
    if _report_module is None:
        with _report_module_lock:
            if _report_module is None:
                _report_module = importlib.import_module("testrail_daily_report")
    return _report_module


def _maybe_log_memory(label: str):
    module = _report_module
    if not module:
        return
    try:
        module.log_memory(label)
    except Exception:
        pass


class TTLCache:
    def __init__(self, ttl_seconds: int = 120):
        self.ttl = ttl_seconds
        self._store: dict[tuple, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: tuple):
        now = time.time()
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            expires_at, value = entry
            if expires_at <= now:
                self._store.pop(key, None)
                return None
        return value.copy() if isinstance(value, dict) else value, expires_at

    def set(self, key: tuple, value: Any, ttl_seconds: int | None = None):
        ttl = ttl_seconds if ttl_seconds is not None else self.ttl
        expires_at = time.time() + max(1, ttl)
        with self._lock:
            self._store[key] = (expires_at, value.copy() if isinstance(value, dict) else value)
        return expires_at

    def clear(self):
        with self._lock:
            self._store.clear()


plans_cache_ttl = int(os.getenv("PLANS_CACHE_TTL", "180"))
runs_cache_ttl = int(os.getenv("RUNS_CACHE_TTL", "60"))
_plans_cache = TTLCache(ttl_seconds=plans_cache_ttl)
_runs_cache = TTLCache(ttl_seconds=runs_cache_ttl)


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
    def __init__(self, max_workers: int = 2, max_history: int = 50, min_workers: int | None = None, idle_seconds: int = 60):
        self.max_workers = max(1, max_workers)
        min_workers = min_workers if min_workers is not None else 1
        self.min_workers = max(1, min(self.max_workers, min_workers))
        self.idle_seconds = max(5, idle_seconds)
        self.jobs: dict[str, ReportJob] = {}
        self.order: deque[str] = deque()
        self.lock = threading.Lock()
        self.max_history = max_history
        self._job_queue: queue.Queue[str] = queue.Queue()
        self._worker_states: dict[str, dict[str, Any]] = {}
        for _ in range(self.min_workers):
            self._spawn_worker()

    def enqueue(self, params: dict[str, Any]) -> ReportJob:
        job_id = uuid.uuid4().hex
        job = ReportJob(id=job_id, params=params)
        with self.lock:
            self.jobs[job_id] = job
            self.order.append(job_id)
        self._job_queue.put(job_id)
        self._scale_up_if_needed()
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

    def _spawn_worker(self):
        worker_name = f"report-worker-{uuid.uuid4().hex[:6]}"
        thread = threading.Thread(target=self._worker_loop, args=(worker_name,), name=worker_name, daemon=True)
        with self.lock:
            self._worker_states[worker_name] = {"idle": True, "thread": thread}
        thread.start()

    def _worker_loop(self, worker_name: str):
        while True:
            try:
                job_id = self._job_queue.get(timeout=self.idle_seconds)
            except queue.Empty:
                with self.lock:
                    if len(self._worker_states) > self.min_workers:
                        self._worker_states.pop(worker_name, None)
                        return
                continue
            with self.lock:
                state = self._worker_states.get(worker_name)
                if state is not None:
                    state["idle"] = False
            try:
                self._run_job(job_id)
            finally:
                with self.lock:
                    state = self._worker_states.get(worker_name)
                    if state is not None:
                        state["idle"] = True
                self._job_queue.task_done()

    def _scale_up_if_needed(self):
        spawn = 0
        with self.lock:
            idle_workers = sum(1 for state in self._worker_states.values() if state.get("idle"))
            queued = self._job_queue.qsize()
            available = self.max_workers - len(self._worker_states)
            needed = queued - idle_workers
            if needed > 0 and available > 0:
                spawn = min(needed, available)
        for _ in range(spawn):
            self._spawn_worker()

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
            report_module = _get_report_module()
            reporter = lambda stage, payload=None: self.report_progress(job_id, stage, payload or {})
            with report_module.capture_telemetry() as telemetry:
                path = report_module.generate_report(**job.params, progress=reporter)
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


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


report_workers_env = _int_env("REPORT_WORKERS", 1)
report_workers_max = max(1, _int_env("REPORT_WORKERS_MAX", report_workers_env))
report_workers_min = max(1, min(report_workers_max, _int_env("REPORT_WORKERS_MIN", 1)))
report_worker_idle_secs = max(5, _int_env("REPORT_WORKER_IDLE_SECS", 60))
job_history_limit = max(10, _int_env("REPORT_JOB_HISTORY", 60))
_job_manager = ReportJobManager(
    min_workers=report_workers_min,
    max_workers=report_workers_max,
    idle_seconds=report_worker_idle_secs,
    max_history=job_history_limit,
)


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
_idle_thread: threading.Thread | None = None
_idle_stop = threading.Event()

_last_request_ts = time.time()
_active_requests = 0

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
                _maybe_log_memory("heartbeat")
            except Exception:
                pass
            _memlog_stop.wait(interval)

    global _memlog_thread
    if _memlog_thread and _memlog_thread.is_alive():
        return
    _memlog_thread = threading.Thread(target=_loop, name="memlog-thread", daemon=True)
    _memlog_thread.start()


def _start_idle_monitor():
    try:
        idle_seconds = int(os.getenv("IDLE_RESTART_SECONDS", "0"))
    except ValueError:
        idle_seconds = 0
    if idle_seconds <= 0:
        return

    # Check roughly a few times during the idle window.
    interval = max(30, min(idle_seconds, max(30, idle_seconds // 2)))

    def _loop():
        while not _idle_stop.is_set():
            now = time.time()
            idle_for = now - _last_request_ts
            # Only restart when no requests are in-flight and we've been idle long enough.
            if _active_requests == 0 and idle_for >= idle_seconds:
                print(
                    f"[idle-restart] No requests for {idle_for:.0f}s "
                    f"(threshold={idle_seconds}s); exiting for restart.",
                    flush=True,
                )
                os._exit(0)
            _idle_stop.wait(interval)

    global _idle_thread
    if _idle_thread and _idle_thread.is_alive():
        return
    _idle_thread = threading.Thread(target=_loop, name="idle-restart-thread", daemon=True)
    _idle_thread.start()

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


def _stop_idle_monitor():
    global _idle_thread
    if not _idle_thread:
        return
    _idle_stop.set()
    _idle_thread.join(timeout=5)
    _idle_thread = None
    _idle_stop.clear()


@app.middleware("http")
async def _track_activity(request: Request, call_next):
    global _last_request_ts, _active_requests
    now = time.time()
    _last_request_ts = now
    _active_requests += 1
    try:
        response = await call_next(request)
    finally:
        _active_requests -= 1
        _last_request_ts = time.time()
    return response

@app.on_event("startup")
def on_startup():
    run_workers = os.getenv("RUN_WORKERS", "2")
    run_workers_max = os.getenv("RUN_WORKERS_MAX", run_workers)
    run_workers_autoscale = os.getenv("RUN_WORKERS_AUTOSCALE", "0")
    attachment_workers = os.getenv("ATTACHMENT_WORKERS", "2")
    
    print("--- Worker Configuration ---")
    print(f"Report Workers:     min={_job_manager.min_workers} max={_job_manager.max_workers} idle={_job_manager.idle_seconds}s")
    print(f"Run Workers:          base={run_workers} max={run_workers_max} autoscale={run_workers_autoscale}")
    print(f"Attachment Workers:   {attachment_workers}")
    print("--------------------------")

    _start_keepalive()
    _start_memlog()
    _start_idle_monitor()

@app.on_event("shutdown")
def on_shutdown():
    _stop_keepalive()
    _stop_memlog()
    _stop_idle_monitor()

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
    report_module = _get_report_module()
    try:
        path = report_module.generate_report(project=project, plan=plan, run=run, run_ids=selected_run_ids)
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
    report_module = _get_report_module()
    path = report_module.generate_report(project=project, plan=plan, run=run, run_ids=run_ids)
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
    report_module = _get_report_module()
    try:
        base_url = report_module.env_or_die("TESTRAIL_BASE_URL").rstrip("/")
        user = report_module.env_or_die("TESTRAIL_USER")
        api_key = report_module.env_or_die("TESTRAIL_API_KEY")
    except SystemExit:
        raise HTTPException(status_code=500, detail="Server missing TestRail credentials")
    session = requests.Session()
    session.auth = (user, api_key)
    plans = report_module.get_plans_for_project(session, base_url, project_id=project, is_completed=is_completed)
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
    report_module = _get_report_module()
    try:
        base_url = report_module.env_or_die("TESTRAIL_BASE_URL").rstrip("/")
        user = report_module.env_or_die("TESTRAIL_USER")
        api_key = report_module.env_or_die("TESTRAIL_API_KEY")
    except SystemExit:
        raise HTTPException(status_code=500, detail="Server missing TestRail credentials")
    session = requests.Session()
    session.auth = (user, api_key)
    try:
        plan_obj = report_module.get_plan(session, base_url, plan)
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
