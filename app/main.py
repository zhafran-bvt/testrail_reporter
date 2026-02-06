"""Main FastAPI application with modular architecture."""

import os
import threading
from pathlib import Path

import requests
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.automation import router as automation_router
from app.api.dashboard import router as dashboard_router
from app.api.dataset import router as dataset_router
from app.api.general import router as general_router
from app.api.health import router as health_router
from app.api.management import router as management_router
from app.api.reports import router as reports_router
from app.core import bootstrap  # noqa: F401
from app.core.middleware import ErrorHandlingMiddleware, RequestLoggingMiddleware
from app.utils.helpers import report_worker_config, web_worker_count
from testrail_daily_report import generate_report, log_memory

app = FastAPI(title="TestRail Reporter", version="0.1.0")

# Add middleware
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RequestLoggingMiddleware)

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
# Ensure output directory exists and mount it
Path("output").mkdir(exist_ok=True)
app.mount("/output", NoCacheStaticFiles(directory="output"), name="output")
if Path("assets").exists():
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")

templates = Jinja2Templates(directory="templates")

# Include API routers
app.include_router(dashboard_router)
app.include_router(management_router)
app.include_router(reports_router)
app.include_router(health_router)
app.include_router(general_router)
app.include_router(dataset_router)
app.include_router(automation_router)

# Keepalive and memory logging threads
_keepalive_thread: threading.Thread | None = None
_keepalive_stop = threading.Event()
_memlog_thread: threading.Thread | None = None
_memlog_stop = threading.Event()


def _asset_cache_token() -> str:
    """Use latest static/template mtime as a stable cache token."""
    candidates = [
        Path("templates/index.html"),
        Path("assets/app.js"),
        Path("assets/dashboard.js"),
        Path("assets/dataset-nav.js"),
        Path("assets/dataset-nav.css"),
    ]
    latest_mtime = 0
    for path in candidates:
        try:
            if path.exists():
                latest_mtime = max(latest_mtime, int(path.stat().st_mtime))
        except OSError:
            continue
    return str(latest_mtime or 1)


ASSET_CACHE_TOKEN = _asset_cache_token()


def _start_keepalive():
    """Start keepalive thread if configured."""
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
    """Start memory logging thread."""
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
    """Stop keepalive thread."""
    global _keepalive_thread
    if not _keepalive_thread:
        return
    _keepalive_stop.set()
    _keepalive_thread.join(timeout=5)
    _keepalive_thread = None
    _keepalive_stop.clear()


def _stop_memlog():
    """Stop memory logging thread."""
    global _memlog_thread
    if not _memlog_thread:
        return
    _memlog_stop.set()
    _memlog_thread.join(timeout=5)
    _memlog_thread = None
    _memlog_stop.clear()


@app.on_event("startup")
def on_startup():
    """Application startup event handler."""
    report_worker_count, report_worker_requested, report_worker_max = report_worker_config()
    report_workers = f"{report_worker_count} (max {report_worker_max})"
    if report_worker_requested != report_worker_count:
        report_workers = f"{report_workers} (requested {report_worker_requested})"

    run_workers = os.getenv("RUN_WORKERS", "2")
    attachment_workers = os.getenv("ATTACHMENT_WORKERS", "2")
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
    """Application shutdown event handler."""
    _stop_keepalive()
    _stop_memlog()


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    """Main index page."""
    # Brand colors can be customized via environment variables
    brand = {
        "primary": os.getenv("BRAND_PRIMARY", "#1A8A85"),
        "primary_600": os.getenv("BRAND_PRIMARY_600", "#15736E"),
        "bg": os.getenv("BRAND_BG", "#F8F9FA"),
        "bg2": os.getenv("BRAND_BG2", "rgba(26,138,133,0.06)"),
    }
    logo_url = "/assets/Bvt.jpg"

    from app.core.config import config

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "default_project": 1,
            "default_suite_id": config.DEFAULT_SUITE_ID,
            "default_section_id": config.DEFAULT_SECTION_ID,
            "brand": brand,
            "logo_url": logo_url,
            "cache_bust": ASSET_CACHE_TOKEN,
        },
    )


@app.post("/generate")
def generate(
    project: int = Form(1),
    plan_param: str = Form(""),  # matches <input name="plan">
    run_param: str = Form(""),  # matches <input name="run">
    run_ids: list[str] | None = Form(default=None),
):
    """Legacy form-based report generation endpoint."""
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
    """Friendly redirect if someone visits /generate with GET."""
    return RedirectResponse(url="/", status_code=307)


@app.get("/ui", response_class=HTMLResponse)
def ui_alias(request: Request):
    """UI alias endpoint."""
    return index(request)
