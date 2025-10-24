from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os

from testrail_daily_report import generate_report

app = FastAPI(title="TestRail Reporter", version="0.1.0")

# Serve generated reports
Path("out").mkdir(exist_ok=True)
app.mount("/reports", StaticFiles(directory="out"), name="reports")

templates = Jinja2Templates(directory="templates")


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "default_project": 1,
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
@app.get("/ui", response_class=HTMLResponse)
def ui_alias(request: Request):
    return index(request)
