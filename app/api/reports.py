"""Reports API endpoints for report generation."""

import threading
import time
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import requests
from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.core.config import config
from app.core.dependencies import get_testrail_client
from app.models.requests import ReportRequest
from app.utils.helpers import report_worker_config
from testrail_client import capture_telemetry
from testrail_daily_report import generate_report

router = APIRouter(prefix="/api", tags=["reports"])


@dataclass(slots=True)
class ReportJob:
    """Report generation job."""

    id: str
    params: Dict[str, Any]
    status: str = "queued"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    path: str | None = None
    url: str | None = None
    error: str | None = None
    meta: Dict[str, Any] = field(default_factory=dict)

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
    """Manager for report generation jobs with streaming support."""

    def __init__(self, max_workers: int = 2, max_history: int = 50):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.jobs: Dict[str, ReportJob] = {}
        self.order: deque[str] = deque()
        self.lock = threading.Lock()
        self.max_history = max_history

    def enqueue(self, params: Dict[str, Any]) -> ReportJob:
        """Enqueue a new report generation job."""
        job_id = uuid.uuid4().hex
        job = ReportJob(id=job_id, params=params)
        with self.lock:
            self.jobs[job_id] = job
            self.order.append(job_id)
        self.executor.submit(self._run_job, job_id)
        return job

    def get(self, job_id: str) -> ReportJob | None:
        """Get job by ID."""
        with self.lock:
            return self.jobs.get(job_id)

    def serialize(self, job: ReportJob) -> Dict[str, Any]:
        """Serialize job to dict with queue position."""
        data: Dict[str, Any] = job.to_dict()
        data["queue_position"] = self.queue_position(job.id)
        return data

    def queue_position(self, job_id: str) -> int | None:
        """Get position in queue for queued jobs."""
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

    def stats(self) -> Dict[str, Any]:
        """Get job manager statistics."""
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
        """Trim job history to max_history limit."""
        with self.lock:
            while len(self.order) > self.max_history:
                oldest_id = self.order[0]
                job = self.jobs.get(oldest_id)
                if job and job.status not in {"success", "error"}:
                    break
                self.order.popleft()
                self.jobs.pop(oldest_id, None)

    def report_progress(self, job_id: str, stage: str, payload: Dict | None = None):
        """Report progress for a job."""
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
        """Execute a report generation job."""
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


# Initialize job manager with configuration
report_worker_count, _, _ = report_worker_config()
job_manager = ReportJobManager(max_workers=report_worker_count, max_history=config.REPORT_JOB_HISTORY)


@router.get("/report")
def report_sync(
    project: int = 1,
    plan: int | None = None,
    run: int | None = None,
    run_ids: list[int] | None = None,
    client=Depends(get_testrail_client),
):
    """Generate report synchronously (legacy endpoint)."""
    if run_ids and plan is None:
        raise HTTPException(status_code=400, detail="Run selection requires a plan")
    if (plan is None and run is None) or (plan is not None and run is not None):
        raise HTTPException(status_code=400, detail="Provide exactly one of plan or run")

    try:
        path = generate_report(project=project, plan=plan, run=run, run_ids=run_ids)
        url = "/reports/" + Path(path).name
        return {"path": path, "url": url}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {e}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


@router.post("/report", status_code=status.HTTP_202_ACCEPTED)
def report_async(payload: ReportRequest = Body(...)):
    """Generate report asynchronously with job tracking."""
    job = job_manager.enqueue(payload.model_dump())
    return job_manager.serialize(job)


@router.get("/report/{job_id}")
def report_status(job_id: str):
    """Get status of an async report generation job."""
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Report job not found")
    return job_manager.serialize(job)


@router.get("/report/queue/stats")
def report_queue_stats():
    """Get report queue statistics."""
    return job_manager.stats()
