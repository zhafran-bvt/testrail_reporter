from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

from testrail_daily_report import generate_report, get_plans_for_project, env_or_die
import requests
import glob
import base64
import mimetypes

# Ensure local .env overrides host/env settings to avoid stale provider configs
load_dotenv(override=True)

app = FastAPI(title="TestRail Reporter", version="0.1.0")

# Serve generated reports and static assets
Path("out").mkdir(exist_ok=True)
app.mount("/reports", StaticFiles(directory="out"), name="reports")
if Path("assets").exists():
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")

templates = Jinja2Templates(directory="templates")

def _parse_bool_env(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "on"}


def _humanize_smtp_error(e: Exception, server: str) -> str:
    msg = str(e)
    lower = msg.lower()
    # Office 365 common case
    if "smtpclientauthentication is disabled" in lower or "5.7.139" in lower:
        return (
            "SMTP AUTH is disabled for this mailbox or tenant. "
            "Enable 'Authenticated SMTP' for the mailbox in Exchange Admin Center, "
            "or allow SMTP AUTH org-wide if permitted."
        )
    # Gmail common case
    if "gmail" in server.lower() and ("authentication" in lower or "535" in lower):
        return (
            "Gmail authentication failed. If using Gmail, enable 2-Step Verification and "
            "create an App Password for SMTP. Use smtp.gmail.com:587 with STARTTLS."
        )
    return msg


def _send_email_via_smtp(sender_email: str, password: str, smtp_server: str, smtp_port: int, use_ssl: bool, use_starttls: bool,
                         recipient: str, subject: str, body: str, attachment_path: str):
    """Send using direct SMTP (STARTTLS or SSL)."""
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    with open(attachment_path, "rb") as attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())

    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f"attachment; filename= {os.path.basename(attachment_path)}",
    )
    msg.attach(part)

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=15) as server:
                server.login(sender_email, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as server:
                server.ehlo()
                if use_starttls:
                    server.starttls()
                    server.ehlo()
                server.login(sender_email, password)
                server.send_message(msg)
    except smtplib.SMTPAuthenticationError as auth_err:
        raise HTTPException(status_code=401, detail=_humanize_smtp_error(auth_err, smtp_server))
    except (smtplib.SMTPException, OSError) as smtp_err:
        # Network issues (e.g., [Errno 101] Network is unreachable) → likely provider egress block on SMTP
        detail = str(smtp_err)
        if isinstance(smtp_err, OSError) and getattr(smtp_err, 'errno', None) == 101:
            detail = (
                "Outbound SMTP appears blocked from this environment (Network is unreachable). "
                "On some PaaS (e.g., Render free tier), SMTP ports are restricted. "
                "Use an email API provider (e.g., SendGrid) or enable SMTP egress."
            )
        raise HTTPException(status_code=502, detail=detail)


def _send_email_via_sendgrid(sender_email: str, recipient: str, subject: str, body: str, attachment_path: str):
    api_key = env_or_die("SENDGRID_API_KEY")
    mime, _ = mimetypes.guess_type(attachment_path)
    if not mime:
        mime = "application/octet-stream"
    with open(attachment_path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode("ascii")
    payload = {
        "personalizations": [{"to": [{"email": recipient}]}],
        "from": {"email": sender_email},
        "subject": subject,
        "content": [{"type": "text/plain", "value": body}],
        "attachments": [{
            "content": content_b64,
            "filename": os.path.basename(attachment_path),
            "type": mime,
            "disposition": "attachment"
        }],
    }
    try:
        r = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20,
        )
        if r.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"SendGrid error {r.status_code}: {r.text}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"SendGrid network error: {e}")


def send_email(recipient: str, subject: str, body: str, attachment_path: str):
    sender_email = env_or_die("SMTP_USER")
    provider = os.getenv("EMAIL_PROVIDER", "smtp").strip().lower()
    if provider == "sendgrid":
        _send_email_via_sendgrid(sender_email, recipient, subject, body, attachment_path)
        return
    # default: SMTP
    password = env_or_die("SMTP_PASSWORD")
    smtp_server = env_or_die("SMTP_SERVER")
    smtp_port = int(env_or_die("SMTP_PORT"))
    use_ssl = _parse_bool_env("SMTP_USE_SSL", False)
    use_starttls = _parse_bool_env("SMTP_STARTTLS", True)
    _send_email_via_smtp(sender_email, password, smtp_server, smtp_port, use_ssl, use_starttls,
                         recipient, subject, body, attachment_path)

@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/debug/smtp")
def debug_smtp():
    """Return current SMTP config (masked) to verify which server is active."""
    def _mask_user(u: str | None) -> str | None:
        if not u:
            return None
        if "@" in u:
            name, domain = u.split("@", 1)
            return (name[:2] + "***@" + domain) if len(name) > 2 else ("***@" + domain)
        return u[:2] + "***"

    return {
        "server": os.getenv("SMTP_SERVER"),
        "port": os.getenv("SMTP_PORT"),
        "user": _mask_user(os.getenv("SMTP_USER")),
        "ssl": os.getenv("SMTP_USE_SSL"),
        "starttls": os.getenv("SMTP_STARTTLS"),
    }


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
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to TestRail API: {e}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Catch any other unexpected errors
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
    url = "/reports/" + Path(path).name
    return RedirectResponse(url=url, status_code=303)

@app.post("/send-report")
def send_report_endpoint(
    project: int = Form(1),
    plan: str = Form(""),
    run: str = Form(""),
    recipient: str = Form("")
):
    plan = int(plan) if str(plan).strip() else None
    run = int(run) if str(run).strip() else None
    if (plan is None and run is None) or (plan is not None and run is not None):
        raise HTTPException(status_code=400, detail="Provide exactly one of plan or run")
    
    try:
        path = generate_report(project=project, plan=plan, run=run)
        send_email(
            recipient=recipient,
            subject="TestRail Daily Report",
            body="Please find the attached TestRail daily report.",
            attachment_path=path,
        )
        return JSONResponse({
            "ok": True,
            "recipient": recipient,
            "path": path,
            "message": f"Report sent to {recipient}",
        }, status_code=200)
    except HTTPException as he:
        # Propagate known SMTP/report errors with their status code
        raise he
    except Exception as e:
        # Generic unexpected
        raise HTTPException(status_code=500, detail=str(e))


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
