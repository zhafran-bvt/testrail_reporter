from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os

from testrail_daily_report import generate_report, get_plans_for_project, env_or_die
import requests
import glob

app = FastAPI(title="TestRail Reporter", version="0.1.0")

# Serve generated reports and static assets
Path("out").mkdir(exist_ok=True)
app.mount("/reports", StaticFiles(directory="out"), name="reports")
if Path("assets").exists():
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")

templates = Jinja2Templates(directory="templates")


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
):
    # Convert blank strings to None, otherwise parse to int
    plan = int(plan) if str(plan).strip() else None
    run = int(run) if str(run).strip() else None
    if (plan is None and run is None) or (plan is not None and run is not None):
        raise HTTPException(status_code=400, detail="Provide exactly one of plan or run")
    try:
        path = generate_report(project=project, plan=plan, run=run)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
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
def api_report(project: int = 1, plan: int | None = None, run: int | None = None):
    if (plan is None and run is None) or (plan is not None and run is not None):
        raise HTTPException(status_code=400, detail="Provide exactly one of plan or run")
    path = generate_report(project=project, plan=plan, run=run)
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
@app.get("/ui", response_class=HTMLResponse)
def ui_alias(request: Request):
    return index(request)
