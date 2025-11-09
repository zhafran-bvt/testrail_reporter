import threading
import time

from fastapi import FastAPI, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os
from dotenv import load_dotenv

from testrail_daily_report import generate_report, get_plans_for_project, get_plan, env_or_die
import requests
import glob

# Ensure local .env overrides host/env settings to avoid stale provider configs
load_dotenv(override=True)

app = FastAPI(title="TestRail Reporter", version="0.1.0")

# Serve generated reports and static assets
Path("out").mkdir(exist_ok=True)
app.mount("/reports", StaticFiles(directory="out"), name="reports")
if Path("assets").exists():
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")

templates = Jinja2Templates(directory="templates")

_keepalive_thread: threading.Thread | None = None
_keepalive_stop = threading.Event()

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

def _stop_keepalive():
    global _keepalive_thread
    if not _keepalive_thread:
        return
    _keepalive_stop.set()
    _keepalive_thread.join(timeout=5)
    _keepalive_thread = None
    _keepalive_stop.clear()

@app.on_event("startup")
def on_startup():
    _start_keepalive()

@app.on_event("shutdown")
def on_shutdown():
    _stop_keepalive()

@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    # Brand colors can be customized via environment variables
    brand = {
        "primary": os.getenv("BRAND_PRIMARY", "#2563eb"),
        "primary_600": os.getenv("BRAND_PRIMARY_600", "#1d4ed8"),
        "bg": os.getenv("BRAND_BG", "#0ea5e9"),
        "bg2": os.getenv("BRAND_BG2", "#0ea5e91a"),
    }
    # Detect latest image asset for logo dynamically
    logo_url = None
    try:
        candidates = []
        for ext in ("png", "jpg", "jpeg", "svg", "webp"):
            candidates.extend(glob.glob(str(Path("assets") / f"*.{ext}")))
        if candidates:
            latest = max(candidates, key=lambda p: Path(p).stat().st_mtime)
            logo_url = "/assets/" + Path(latest).name
    except Exception:
        logo_url = None

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "default_project": 1,
            "brand": brand,
            "logo_url": logo_url or "/assets/logo-bvt.png",
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
    # Alias for /api/report to avoid 404s from typos
    return api_report(project=project, plan=plan, run=run)


@app.get("/api/report")
def api_report(
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


@app.get("/api/plans")
def api_plans(project: int = 1, is_completed: int | None = None):
    """List plans for a project, optionally filter by completion (0 or 1)."""
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
    return {"count": len(slim), "plans": slim}

@app.get("/api/runs")
def api_runs(plan: int, project: int = 1):
    if not plan:
        raise HTTPException(status_code=400, detail="plan is required")
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
    return {"count": len(runs), "runs": runs}

@app.get("/ui", response_class=HTMLResponse)
def ui_alias(request: Request):
    return index(request)
