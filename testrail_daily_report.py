#!/usr/bin/env python3
"""
TestRail Daily Report → HTML
Fetches test results from TestRail (run or plan) and generates an HTML summary.
Usage:
    python testrail_daily_report.py --project 1 --plan 241
Requires env vars:
    TESTRAIL_BASE_URL, TESTRAIL_USER, TESTRAIL_API_KEY
"""

import os, sys, argparse, requests, pandas as pd, mimetypes, base64, math
import time
import contextvars
import contextlib
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
from io import BytesIO
import tempfile
import shutil
from dotenv import load_dotenv
from PIL import Image

try:
    import resource  # type: ignore
except ImportError:  # pragma: no cover - resource not available on all platforms
    resource = None  # type: ignore

try:
    import psutil  # type: ignore
except ImportError:  # pragma: no cover - psutil optional
    psutil = None  # type: ignore

# Ensure .env overrides any existing env so local config is honored
load_dotenv(override=True)


# --- Telemetry helpers ---
_telemetry_ctx: contextvars.ContextVar[dict | None] = contextvars.ContextVar("testrail_reporter_telemetry", default=None)

@contextlib.contextmanager
def capture_telemetry():
    """Capture API call telemetry for the current thread."""
    data = {"api_calls": []}
    token = _telemetry_ctx.set(data)
    try:
        yield data
    finally:
        _telemetry_ctx.reset(token)


def record_api_call(kind: str, endpoint: str, elapsed_ms: float, status: str, error: str | None = None):
    telemetry = _telemetry_ctx.get()
    if not telemetry:
        return
    telemetry.setdefault("api_calls", []).append({
        "kind": kind,
        "endpoint": endpoint,
        "elapsed_ms": round(elapsed_ms, 2),
        "status": status,
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


# --- Default status mapping ---
DEFAULT_STATUS_MAP = {
    1: "Passed",
    2: "Blocked",
    3: "Untested",
    4: "Retest",
    5: "Failed",
}


def env_or_die(key: str) -> str:
    v = os.getenv(key)
    if not v:
        print(f"Missing env var: {key}", file=sys.stderr)
        sys.exit(2)
    return v


def _memory_usage_mb() -> float | None:
    """Return current RSS memory usage in MB if detectable."""
    if psutil:
        try:
            proc = psutil.Process(os.getpid())
            return proc.memory_info().rss / (1024 * 1024)
        except Exception:
            pass
    if resource:
        try:
            usage = resource.getrusage(resource.RUSAGE_SELF)
            # ru_maxrss is KB on Linux, bytes on macOS. Detect large values to adjust.
            rss = float(getattr(usage, "ru_maxrss", 0.0))
            if rss <= 0:
                return None
            if rss > 10 * (1024 ** 2):  # looks like bytes
                return rss / (1024 * 1024)
            return rss / 1024.0  # assume KB
        except Exception:
            return None
    return None


def log_memory(label: str):
    """Log current memory usage to stderr with a consistent prefix."""
    mem_mb = _memory_usage_mb()
    if mem_mb is None:
        return
    print(f"[mem-log] stage={label} rss_mb={mem_mb:.2f}", file=sys.stderr, flush=True)


def api_get(session: requests.Session, base_url: str, endpoint: str):
    url = f"{base_url}/index.php?/api/v2/{endpoint}"
    start = time.perf_counter()
    try:
        r = session.get(url)
        r.raise_for_status()
        data = r.json()
        # Surface TestRail API error payloads early
        if isinstance(data, dict) and any(k in data for k in ("error", "message")):
            msg = data.get("error") or data.get("message") or str(data)
            raise RuntimeError(f"API error for '{endpoint}': {msg}")
        record_api_call("GET", endpoint, (time.perf_counter() - start) * 1000.0, "ok")
        return data
    except Exception as exc:
        record_api_call("GET", endpoint, (time.perf_counter() - start) * 1000.0, "error", str(exc))
        raise


def get_project(session, base_url, project_id: int):
    return api_get(session, base_url, f"get_project/{project_id}")


def get_plan(session, base_url, plan_id: int):
    return api_get(session, base_url, f"get_plan/{plan_id}")


class UserLookupForbidden(Exception):
    """Raised when TestRail denies access to user lookup endpoints."""


def get_users_map(session, base_url):
    try:
        users = api_get(session, base_url, "get_users")
        mapping = {}
        if isinstance(users, list):
            for u in users:
                uid = u.get("id")
                try:
                    uid = int(uid) if uid is not None else None
                except Exception:
                    pass
                if uid is not None:
                    mapping[uid] = u.get("name") or u.get("email") or str(uid)
        return mapping
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 403:
            raise UserLookupForbidden("TestRail denied access to get_users") from e
        print(f"Warning: could not load users: {e}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"Warning: could not load users: {e}", file=sys.stderr)
        return {}


## Removed get_run helper as time-based trend was dropped


def get_user(session, base_url, user_id: int):
    try:
        return api_get(session, base_url, f"get_user/{user_id}")
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 403:
            raise UserLookupForbidden("TestRail denied access to get_user") from e
        print(f"Warning: get_user({user_id}) failed: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Warning: get_user({user_id}) failed: {e}", file=sys.stderr)
        return None


def get_priorities_map(session, base_url):
    """Return {priority_id: priority_name} mapping.
    Falls back to short_name if available, else name, else the id as string.
    """
    try:
        items = api_get(session, base_url, "get_priorities")
        mapping = {}
        if isinstance(items, list):
            for p in items:
                pid = p.get("id")
                if pid is None:
                    continue
                name = p.get("short_name") or p.get("name") or str(pid)
                mapping[int(pid)] = name
        return mapping
    except Exception as e:
        print(f"Warning: could not load priorities: {e}", file=sys.stderr)
        return {}


def get_statuses_map(session, base_url):
    """Return {status_id: status_name} mapping from TestRail.
    Falls back to DEFAULT_STATUS_MAP if API call fails.
    """
    try:
        items = api_get(session, base_url, "get_statuses")
        mapping = {}
        if isinstance(items, list):
            for s in items:
                sid = s.get("id")
                if sid is None:
                    continue
                name = s.get("name") or str(sid)
                mapping[int(sid)] = name
        # Force canonical names for known default statuses
        for k, v in DEFAULT_STATUS_MAP.items():
            mapping[k] = v
        return mapping
    except Exception as e:
        print(f"Warning: could not load statuses: {e}", file=sys.stderr)
        return DEFAULT_STATUS_MAP.copy()


def get_plan_runs(session, base_url, plan_id: int):
    plan = api_get(session, base_url, f"get_plan/{plan_id}")
    runs = []
    for entry in plan.get("entries", []):
        for run in entry.get("runs", []):
            runs.append(run["id"])
    if not runs:
        print(f"Warning: No runs found in plan {plan_id}", file=sys.stderr)
    return runs


def get_results_for_run(session, base_url, run_id: int):
    results = []
    offset, limit = 0, 250
    while True:
        try:
            batch = api_get(session, base_url, f"get_results_for_run/{run_id}&limit={limit}&offset={offset}")
        except Exception as e:
            print(f"Error: get_results_for_run({run_id}) failed: {e}", file=sys.stderr)
            break
        # Support both list and paginated dict shapes
        if not batch:
            break
        if isinstance(batch, list):
            items = batch
        elif isinstance(batch, dict) and "results" in batch:
            items = batch.get("results", [])
        else:
            print(f"Warning: Unexpected payload for results (run {run_id}): {type(batch)} keys={list(batch.keys()) if isinstance(batch, dict) else 'n/a'}",
                  file=sys.stderr)
            break
        results.extend(items)
        if len(items) < limit:
            break
        offset += limit
    return results


def get_tests_for_run(session, base_url, run_id: int):
    tests = []
    offset, limit = 0, 250
    while True:
        try:
            batch = api_get(session, base_url, f"get_tests/{run_id}&limit={limit}&offset={offset}")
        except Exception as e:
            print(f"Error: get_tests({run_id}) failed: {e}", file=sys.stderr)
            break
        # Support both list and paginated dict shapes
        if not batch:
            break
        if isinstance(batch, list):
            items = batch
        elif isinstance(batch, dict) and "tests" in batch:
            items = batch.get("tests", [])
        else:
            print(f"Warning: Unexpected payload for tests (run {run_id}): {type(batch)} keys={list(batch.keys()) if isinstance(batch, dict) else 'n/a'}",
                  file=sys.stderr)
            break
        tests.extend(items)
        if len(items) < limit:
            break
        offset += limit
    return tests


def get_plans_for_project(session, base_url, project_id: int, *, is_completed: int | None = None,
                          created_after: int | None = None, created_before: int | None = None) -> list:
    """Return list of plans for a project.
    Supports optional filters and handles both list and paginated dict shapes.
    """
    plans: list = []
    offset, limit = 0, 250
    while True:
        qs = [f"limit={limit}", f"offset={offset}"]
        if is_completed is not None:
            qs.append(f"is_completed={is_completed}")
        if created_after is not None:
            qs.append(f"created_after={created_after}")
        if created_before is not None:
            qs.append(f"created_before={created_before}")
        endpoint = f"get_plans/{project_id}&" + "&".join(qs)
        try:
            batch = api_get(session, base_url, endpoint)
        except Exception:
            break
        if not batch:
            break
        if isinstance(batch, list):
            items = batch
        elif isinstance(batch, dict):
            # Some instances may return a dict wrapper, try common keys
            items = batch.get("plans") or batch.get("items") or []
        else:
            items = []
        plans.extend(items)
        if len(items) < limit:
            break
        offset += limit
    return plans


def get_attachments_for_test(session, base_url, test_id: int):
    try:
        data = api_get(session, base_url, f"get_attachments_for_test/{test_id}")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # Some instances may wrap in dict
            return data.get("attachments", [])
        return []
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return []
        print(f"Warning: attachments fetch failed for test {test_id}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Warning: attachments fetch failed for test {test_id}: {e}", file=sys.stderr)
        return []


def download_attachment(session, base_url, attachment_id: int):
    """Download an attachment.
    Returns either (temp_path, content_type) when streaming, or (bytes, content_type) for backward-compatible mocks/tests.
    """
    url = f"{base_url}/index.php?/api/v2/get_attachment/{attachment_id}"
    start = time.perf_counter()
    try:
        with session.get(url, stream=True) as r:
            r.raise_for_status()
            content_type = r.headers.get("Content-Type")
            # Write to a temp file to avoid holding full content in memory
            fd, tmp_path = tempfile.mkstemp(prefix=f"att_{attachment_id}_", suffix=".bin")
            tmp = Path(tmp_path)
            with os.fdopen(fd, "wb") as f:
                for chunk in r.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        f.write(chunk)
            record_api_call("GET", f"get_attachment/{attachment_id}", (time.perf_counter() - start) * 1000.0, "ok")
            return tmp, content_type
    except Exception as exc:
        record_api_call("GET", f"get_attachment/{attachment_id}", (time.perf_counter() - start) * 1000.0, "error", str(exc))
        raise


def sanitize_filename(name: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in ("-", "_", ".", " ") else "_" for c in name)
    return cleaned.strip().replace(" ", "_") or "attachment"


def summarize_results(results, status_map=DEFAULT_STATUS_MAP):
    df = pd.DataFrame(results)
    # If no results or unexpected payload (e.g., missing test_id), return empty frame with expected columns
    if df.empty or "test_id" not in df.columns:
        empty_cols = ["test_id", "status_id", "comment", "created_on"]
        return {"total": 0, "by_status": {}, "pass_rate": 0.0, "df": pd.DataFrame(columns=empty_cols)}

    # Deduplicate to the latest result per test_id
    sort_cols = [c for c in ["test_id", "created_on", "id"] if c in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols)
    df = df.drop_duplicates("test_id", keep="last")

    # Map status_id to names; keep original names if API provided
    if "status_name" not in df.columns:
        sid = pd.to_numeric(df.get("status_id"), errors="coerce")
        df["status_name"] = sid.map(lambda x: status_map.get(int(x), str(int(x))) if pd.notna(x) else "Untested")
    else:
        df["status_name"] = df["status_name"].fillna("")

    total = len(df)
    by_status = df["status_name"].value_counts().to_dict()
    passed = by_status.get("Passed", 0)
    pass_rate = round((passed / total) * 100, 2) if total else 0.0
    return {"total": total, "by_status": by_status, "pass_rate": pass_rate, "df": df}


def build_test_table(tests_df: pd.DataFrame, results_df: pd.DataFrame, status_map=DEFAULT_STATUS_MAP, users_map=None, priorities_map=None):
    users_map = users_map or {}
    priorities_map = priorities_map or {}
    # Normalize results_df
    if results_df.empty:
        results_df = pd.DataFrame(columns=["test_id", "status_id", "comment"])
    if "test_id" not in results_df.columns:
        # Ensure merge key exists even if no data
        results_df = results_df.assign(test_id=pd.Series(dtype="int64"))

    # Normalize tests_df
    if "id" in tests_df.columns and "test_id" not in tests_df.columns:
        tests_df = tests_df.rename(columns={"id": "test_id"})
    # Reduce to relevant columns
    test_keep = [c for c in ["test_id", "title", "priority_id", "refs", "assignedto_id", "status_id"] if c in tests_df.columns]
    tests_df = tests_df[test_keep] if test_keep else pd.DataFrame(columns=["test_id", "title", "priority_id", "refs", "assignedto_id", "status_id"])
    if "test_id" not in tests_df.columns:
        tests_df = pd.DataFrame(columns=["test_id", "title", "priority_id", "type_id", "refs"])

    # Deduplicate results on latest created. Exclude status fields; source of truth is tests_df status
    res_keep = [c for c in ["test_id", "comment", "created_on", "assignedto_id"] if c in results_df.columns]
    results_df = results_df[res_keep] if res_keep else results_df
    sort_cols = [c for c in ["test_id", "created_on"] if c in results_df.columns]
    if sort_cols:
        results_df = results_df.sort_values(sort_cols)
    if "test_id" in results_df.columns and not results_df.empty:
        results_df = results_df.drop_duplicates("test_id", keep="last")

    # Map test-level status_id to friendly status (source of truth)
    if "status_id" in tests_df.columns:
        try:
            sid = pd.to_numeric(tests_df["status_id"], errors="coerce").astype("Int64")
            tests_df["status_name"] = sid.map(lambda x: status_map.get(int(x), str(int(x))) if pd.notna(x) else "Untested")
        except Exception:
            tests_df["status_name"] = "Untested"
    else:
        tests_df["status_name"] = "Untested"

    merged = tests_df.merge(results_df, on="test_id", how="left")
    # Sort rows so non-Passed appear first (Failed, Blocked, Retest, Untested, then Passed)
    status_order_map = {"Failed": 0, "Blocked": 1, "Retest": 2, "Untested": 3, "Passed": 4}
    merged["_status_order"] = merged["status_name"].map(lambda s: status_order_map.get(str(s), 2))
    # Secondary sort by test_id for stability
    if "test_id" in merged.columns:
        merged = merged.sort_values(["_status_order", "test_id"])  
    else:
        merged = merged.sort_values(["_status_order"])  
    # Normalize blanks as 'Untested' for clarity
    merged["status_name"] = merged["status_name"].replace({None: ""}).fillna("")
    merged.loc[merged["status_name"] == "", "status_name"] = "Untested"
    # Assignee name: prefer tests' assignedto, fallback to results'
    assignee_series = None
    if "assignedto_id" in merged.columns:
        assignee_series = merged["assignedto_id"]
    elif "assignedto_id_x" in merged.columns:
        assignee_series = merged["assignedto_id_x"]
    if assignee_series is None and "assignedto_id_y" in merged.columns:
        assignee_series = merged["assignedto_id_y"]
    if assignee_series is not None:
        aid = pd.to_numeric(assignee_series, errors="coerce").astype("Int64")
        merged["assignee"] = aid.map(lambda x: users_map.get(int(x), str(int(x)) if pd.notna(x) else "") if pd.notna(x) else "")
    else:
        merged["assignee"] = ""

    # Priority label from priority_id
    if "priority_id" in merged.columns:
        try:
            pid = pd.to_numeric(merged["priority_id"], errors="coerce").astype("Int64")
            merged["priority"] = pid.map(lambda x: priorities_map.get(int(x), str(int(x))) if pd.notna(x) else "")
        except Exception:
            merged["priority"] = merged["priority_id"].astype(str)
    else:
        merged["priority"] = ""

    # Select and order columns for output
    desired = ["test_id", "title", "status_name", "assignee", "priority"]
    cols = [c for c in desired if c in merged]
    cleaned = merged[cols].where(pd.notna(merged[cols]), None)
    return cleaned


def extract_refs(items) -> list[str]:
    """Return sorted unique refs extracted from iterable of dicts or DataFrame rows."""
    refs_set: set[str] = set()
    if isinstance(items, pd.DataFrame):
        iterable = items.to_dict(orient="records")
    else:
        iterable = items
    for item in iterable:
        if not isinstance(item, dict):
            continue
        refs_val = item.get("refs")
        if not refs_val:
            continue
        for ref in str(refs_val).split(","):
            ref_trim = ref.strip()
            if ref_trim:
                refs_set.add(ref_trim)
    return sorted(refs_set)


def compress_image_data(data: bytes, content_type: str | None):
    if not content_type or not str(content_type).lower().startswith("image/"):
        return data, content_type
    max_dim = int(os.getenv("ATTACHMENT_IMAGE_MAX_DIM", "1200"))
    jpeg_quality = int(os.getenv("ATTACHMENT_JPEG_QUALITY", "65"))
    min_quality = int(os.getenv("ATTACHMENT_MIN_JPEG_QUALITY", "40"))
    max_bytes = int(os.getenv("ATTACHMENT_MAX_IMAGE_BYTES", "450000"))
    min_quality = max(15, min(min_quality, jpeg_quality))

    try:
        with Image.open(BytesIO(data)) as img:
            work = img.copy()
            if max(work.size) > max_dim:
                work.thumbnail((max_dim, max_dim), Image.LANCZOS)

            def save_png(image_obj):
                buffer = BytesIO()
                image_obj.save(buffer, format="PNG", optimize=True, compress_level=6)
                return buffer.getvalue(), "image/png"

            def save_jpeg(image_obj, quality):
                buffer = BytesIO()
                image_obj.convert("RGB").save(buffer, format="JPEG", optimize=True, quality=quality)
                return buffer.getvalue(), "image/jpeg"

            img_format = (img.format or "").upper()
            if img_format == "PNG":
                out_bytes, out_type = save_png(work)
            else:
                out_bytes, out_type = save_jpeg(work, jpeg_quality)

            def enforce_size(bytes_payload, image_obj, current_type):
                if max_bytes <= 0 or len(bytes_payload) <= max_bytes:
                    return bytes_payload, current_type
                target_quality = min(jpeg_quality, 80)
                while target_quality > min_quality:
                    target_quality = max(min_quality, target_quality - 10)
                    candidate, candidate_type = save_jpeg(image_obj, target_quality)
                    if len(candidate) <= max_bytes or target_quality == min_quality:
                        return candidate, candidate_type
                if len(bytes_payload) <= max_bytes:
                    return bytes_payload, current_type
                shrink_ratio = math.sqrt(max_bytes / len(bytes_payload))
                if shrink_ratio < 0.98:
                    new_dim = max(320, int(max(image_obj.size) * shrink_ratio))
                    shrunk = image_obj.copy()
                    shrunk.thumbnail((new_dim, new_dim), Image.LANCZOS)
                    return save_jpeg(shrunk, min_quality)
                return bytes_payload, current_type

            out_bytes, out_type = enforce_size(out_bytes, work, out_type)
            return out_bytes, out_type
    except Exception:
        return data, content_type


def compress_image_file(input_path: Path, content_type: str | None, output_path: Path, inline_limit: int):
    """Compress an image from disk to disk, returning (final_content_type, size_bytes, inline_payload or None)."""
    max_dim = int(os.getenv("ATTACHMENT_IMAGE_MAX_DIM", "1200"))
    jpeg_quality = int(os.getenv("ATTACHMENT_JPEG_QUALITY", "65"))
    min_quality = int(os.getenv("ATTACHMENT_MIN_JPEG_QUALITY", "40"))
    max_bytes = int(os.getenv("ATTACHMENT_MAX_IMAGE_BYTES", "450000"))
    min_quality = max(15, min(min_quality, jpeg_quality))

    try:
        with Image.open(input_path) as img:
            work = img.copy()
            if max(work.size) > max_dim:
                work.thumbnail((max_dim, max_dim), Image.LANCZOS)

            def save_png(image_obj, target_path):
                image_obj.save(target_path, format="PNG", optimize=True, compress_level=6)
                return "image/png"

            def save_jpeg(image_obj, target_path, quality):
                image_obj.convert("RGB").save(target_path, format="JPEG", optimize=True, quality=quality)
                return "image/jpeg"

            img_format = (img.format or "").upper()
            if img_format == "PNG":
                out_type = save_png(work, output_path)
            else:
                out_type = save_jpeg(work, output_path, jpeg_quality)

            def enforce_size(image_obj, current_type):
                if max_bytes <= 0:
                    return current_type
                size_now = output_path.stat().st_size if output_path.exists() else 0
                if size_now <= max_bytes:
                    return current_type
                target_quality = min(jpeg_quality, 80)
                while target_quality > min_quality:
                    target_quality = max(min_quality, target_quality - 10)
                    out_type_local = save_jpeg(image_obj, output_path, target_quality)
                    size_now = output_path.stat().st_size
                    if size_now <= max_bytes or target_quality == min_quality:
                        return out_type_local
                size_now = output_path.stat().st_size
                if size_now <= max_bytes:
                    return current_type
                shrink_ratio = math.sqrt(max_bytes / float(size_now))
                if shrink_ratio < 0.98:
                    new_dim = max(320, int(max(image_obj.size) * shrink_ratio))
                    shrunk = image_obj.copy()
                    shrunk.thumbnail((new_dim, new_dim), Image.LANCZOS)
                    out_type_local = save_jpeg(shrunk, output_path, min_quality)
                    return out_type_local
                return current_type

            out_type = enforce_size(work, out_type)
            size_bytes = output_path.stat().st_size if output_path.exists() else 0
            inline_payload = None
            if inline_limit and size_bytes <= inline_limit and size_bytes > 0:
                inline_payload = output_path.read_bytes()
            return out_type, size_bytes, inline_payload
    except Exception:
        # Fallback: copy original bytes
        try:
            output_path.write_bytes(input_path.read_bytes())
            size_bytes = output_path.stat().st_size
            inline_payload = None
            if inline_limit and size_bytes <= inline_limit and size_bytes > 0:
                inline_payload = output_path.read_bytes()
            return content_type, size_bytes, inline_payload
        except Exception:
            return content_type, 0, None


def render_html(context: dict, out_path: Path):
    env = Environment(loader=FileSystemLoader("templates"), autoescape=select_autoescape())
    tpl = env.get_template("daily_report.html.j2")
    html = tpl.render(**context)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return str(out_path)


def generate_report(project: int, plan: int | None = None, run: int | None = None,
                    run_ids: list[int] | None = None, progress=None) -> str:
    """Generate a report for a plan or run and return the output HTML path."""
    def notify(stage: str, **payload):
        log_payload = {k: payload.get(k) for k in sorted(payload)}
        print(f"[report-log] stage={stage} payload={log_payload}", flush=True)
        if progress:
            try:
                progress(stage, payload)
            except Exception:
                pass

    if (plan is None and run is None) or (plan is not None and run is not None):
        raise ValueError("Provide exactly one of plan or run")
    if run_ids is not None:
        if plan is None:
            raise ValueError("run_ids requires a plan")
        if run is not None:
            raise ValueError("Cannot combine run_ids with single run")
        run_ids = [int(rid) for rid in run_ids]
        if not run_ids:
            raise ValueError("run_ids must include at least one run id")

    base_url = env_or_die("TESTRAIL_BASE_URL").rstrip("/")
    user = env_or_die("TESTRAIL_USER")
    api_key = env_or_die("TESTRAIL_API_KEY")
    log_memory("start")

    session = requests.Session()
    session.auth = (user, api_key)

    # Enrichment data
    project_obj = get_project(session, base_url, project)
    project_name = project_obj.get("name") or f"Project {project}"
    plan_name = None
    run_names: dict[int, str] = {}
    plan_run_ids: list[int] = []
    if plan is not None:
        plan_obj = get_plan(session, base_url, plan)
        plan_name = plan_obj.get("name") or f"Plan {plan}"
        for entry in plan_obj.get("entries", []):
            for r in entry.get("runs", []):
                rid = r.get("id")
                if rid is not None:
                    rid_int = int(rid)
                    run_names[rid_int] = r.get("name") or str(rid)
                    plan_run_ids.append(rid_int)
        if run_ids:
            missing = [rid for rid in run_ids if rid not in plan_run_ids]
            if missing:
                raise ValueError(f"Run IDs not found in plan {plan}: {missing}")

    user_lookup_allowed = True
    users_map = {}
    try:
        users_map = get_users_map(session, base_url)
    except UserLookupForbidden as err:
        # Bulk endpoint forbidden; fall back to per-user lookups until they fail too.
        users_map = {}
        print(f"Warning: bulk user lookup forbidden ({err}); falling back to get_user per ID", file=sys.stderr)
    priorities_map = get_priorities_map(session, base_url)
    statuses_map = get_statuses_map(session, base_url)

    if run is not None:
        run_ids_resolved = [int(run)]
    else:
        if run_ids:
            run_ids_resolved = [rid for rid in run_ids if rid in plan_run_ids]
        else:
            run_ids_resolved = plan_run_ids or get_plan_runs(session, base_url, plan)  # type: ignore[arg-type]
    if not run_ids_resolved:
        raise ValueError("No runs available to generate report")

    notify("initializing", plan=plan, run=run, run_count=len(run_ids or []))
    summary = {"total": 0, "Passed": 0, "Failed": 0}
    tables = []
    # Time-based trend removed

    report_refs: set[str] = set()
    # Allow tuning concurrency with env while keeping conservative defaults
    try:
        attachment_workers_env = int(os.getenv("ATTACHMENT_WORKERS", "2"))
    except ValueError:
        attachment_workers_env = 2
    attachment_workers = max(1, min(4, attachment_workers_env))

    try:
        run_workers_env = int(os.getenv("RUN_WORKERS", "2"))
    except ValueError:
        run_workers_env = 2
    # Allow higher ceiling if explicitly requested
    try:
        run_workers_ceiling = int(os.getenv("RUN_WORKERS_MAX", "4"))
    except ValueError:
        run_workers_ceiling = 4
    run_workers_ceiling = max(1, min(8, run_workers_ceiling))
    max_workers = max(1, min(run_workers_ceiling, min(max(1, len(run_ids_resolved)), run_workers_env)))

    inline_embed_limit = int(os.getenv("ATTACHMENT_INLINE_MAX_BYTES", "250000"))
    attachment_inline_limit = inline_embed_limit
    attachment_size_limit = int(os.getenv("ATTACHMENT_MAX_BYTES", "520000000"))

    def _fetch_run_data(rid: int):
        results = get_results_for_run(session, base_url, rid)
        tests = get_tests_for_run(session, base_url, rid)
        return rid, tests, results

    run_data: list[tuple[int, list[dict], list[dict]]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch_run_data, rid): rid for rid in run_ids_resolved}
        for future in as_completed(futures):
            try:
                rid, tests, results = future.result()
                run_data.append((rid, tests, results))
                log_memory(f"fetched_run_data_{rid}")
            except Exception as e:
                rid = futures[future]
                print(f"Warning: failed to fetch run {rid}: {e}", file=sys.stderr)

    run_data.sort(key=lambda item: run_ids_resolved.index(item[0]))
    log_memory("after_fetch_runs")

    total_runs = len(run_data)
    for idx, (rid, tests, results) in enumerate(run_data, start=1):
        notify("processing_run", run_id=rid, index=idx, total=total_runs)
        # Ensure assignee IDs are resolvable to names
        if user_lookup_allowed:
            try:
                test_ids = {int(x) for x in pd.Series(tests).apply(lambda r: r.get("assignedto_id") if isinstance(r, dict) else None).dropna().tolist()}
            except Exception:
                test_ids = set()
            try:
                result_ids = {int(x) for x in pd.DataFrame(results).get("assignedto_id", pd.Series([], dtype="float")).dropna().astype(int).tolist()}
            except Exception:
                result_ids = set()
            for uid in (test_ids | result_ids):
                if uid in users_map:
                    continue
                try:
                    u = get_user(session, base_url, uid)
                except UserLookupForbidden as err:
                    user_lookup_allowed = False
                    print(f"Warning: disabling per-user lookups ({err})", file=sys.stderr)
                    break
                if isinstance(u, dict) and u.get("id") is not None:
                    users_map[int(u["id"])] = u.get("name") or u.get("email") or str(u["id"])

        res_summary = summarize_results(results)
        table_df = build_test_table(pd.DataFrame(tests), res_summary["df"], users_map=users_map, priorities_map=priorities_map, status_map=statuses_map)
        # Compute counts from the merged table (one row per test)
        counts = table_df["status_name"].value_counts().to_dict()
        normalized_counts: dict[str, int] = {}
        for k, v in counts.items():
            key = str(k)
            normalized_counts[key] = normalized_counts.get(key, 0) + int(v)
        counts = normalized_counts
        run_total = len(table_df)
        run_passed = counts.get("Passed", 0)
        run_failed = counts.get("Failed", 0)
        run_pass_rate = round((run_passed / run_total) * 100, 2) if run_total else 0.0
        # Build run-level donut segments/style
        def _build_segments(counts: dict[str, int]):
            status_colors = {
                "Passed": "#16a34a",
                "Failed": "#ef4444",
                "Blocked": "#f59e0b",
                "Retest": "#3b82f6",
                "Untested": "#9ca3af",
            }
            total = sum(counts.values())
            segments = []
            donut_style = "conic-gradient(#e5e7eb 0 100%)"
            if total > 0:
                cumulative = 0.0
                colors_lc = {k.lower(): v for k, v in status_colors.items()}
                for label, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
                    pct = (count / total) * 100.0
                    start = cumulative
                    end = cumulative + pct
                    color = colors_lc.get(str(label).lower(), "#6b7280")
                    segments.append({"label": label, "count": count, "percent": round(pct, 2), "start": start, "end": end, "color": color})
                    cumulative = end
                donut_style = "conic-gradient(" + ", ".join([f"{s['color']} {s['start']}% {s['end']}%" for s in segments]) + ")"
            return segments, donut_style

        segs, run_donut_style = _build_segments(counts)
        run_refs = extract_refs(tests)
        report_refs.update(run_refs)

        latest_results_df = res_summary["df"]
        comments_by_test: dict[int, str] = {}
        latest_result_ids: dict[int, int] = {}
        if not latest_results_df.empty:
            latest_records = latest_results_df.to_dict(orient="records")
            for rec in latest_records:
                tid = rec.get("test_id")
                if tid is None or pd.isna(tid):
                    continue
                tid_int = int(tid)
                comment = rec.get("comment")
                if comment:
                    comments_by_test[tid_int] = comment
                result_id = rec.get("id")
                if result_id is not None and not pd.isna(result_id):
                    latest_result_ids[tid_int] = int(result_id)
        attachments_by_test: dict[int, list[dict]] = {}
        for tid, result_id in latest_result_ids.items():
            attachments_by_test.setdefault(tid, [])

        def _fetch_metadata(test_id: int):
            try:
                data = get_attachments_for_test(session, base_url, test_id)
                if not isinstance(data, list):
                    if isinstance(data, dict):
                        return test_id, data.get("attachments", [])
                    return test_id, []
                return test_id, data
            except Exception as e:
                print(f"Warning: attachments fetch failed for test {test_id}: {e}", file=sys.stderr)
                return test_id, []

        metadata_map: dict[int, list] = {}
        if latest_result_ids:
            notify("fetching_attachment_metadata", run_id=rid, count=len(latest_result_ids))
            with ThreadPoolExecutor(max_workers=attachment_workers) as executor:
                futures = {executor.submit(_fetch_metadata, tid): tid for tid in latest_result_ids}
                for future in as_completed(futures):
                    tid = futures[future]
                    try:
                        _, payload = future.result()
                    except Exception as e:
                        print(f"Warning: attachments metadata future failed for test {tid}: {e}", file=sys.stderr)
                        payload = []
                    metadata_map[tid] = payload or []
            log_memory(f"after_attachment_metadata_{rid}")

        download_jobs = []
        for tid, payload in metadata_map.items():
            if not payload:
                continue
            result_id = latest_result_ids.get(tid)
            if result_id is None:
                continue
            for att in payload:
                rid_match = att.get("result_id")
                if rid_match is not None and int(rid_match) != result_id:
                    continue
                attachment_id = att.get("id") or att.get("attachment_id")
                if attachment_id is None:
                    continue
                try:
                    attachment_id = int(attachment_id)
                except (TypeError, ValueError):
                    continue
                filename = att.get("name") or att.get("filename") or f"attachment_{attachment_id}"
                safe_filename = sanitize_filename(filename)
                inferred_type = att.get("content_type") or att.get("mime_type") or mimetypes.guess_type(filename)[0]
                ext = Path(safe_filename).suffix
                if not ext and inferred_type:
                    guessed_ext = mimetypes.guess_extension(inferred_type)
                    if guessed_ext:
                        safe_filename = f"{safe_filename}{guessed_ext}"
                        ext = guessed_ext
                if not ext:
                    ext = ""
                unique_filename = f"test_{tid}_att_{attachment_id}{ext}"
                rel_path = Path("attachments") / f"run_{rid}" / unique_filename
                abs_path = Path("out") / rel_path
                abs_path.parent.mkdir(parents=True, exist_ok=True)
                download_jobs.append({
                    "test_id": tid,
                    "attachment_id": attachment_id,
                    "filename": filename,
                    "rel_path": rel_path,
                    "abs_path": abs_path,
                    "initial_type": inferred_type,
                    "size": att.get("size"),
                })

        if download_jobs:
            inline_limit = max(0, inline_embed_limit)
            total_downloads = len(download_jobs)
            notify("downloading_attachments", run_id=rid, total=total_downloads)
            inline_limit = max(0, inline_embed_limit)
            for index, job in enumerate(download_jobs, start=1):
                attachment_id = job["attachment_id"]
                notify("downloading_attachment", run_id=rid, current=index, total=total_downloads, attachment_id=attachment_id)
                if index % 5 == 0:
                    log_memory(f"download_progress_{rid}_{index}")
                resp = download_attachment(session, base_url, attachment_id)
                tmp_path = None
                content_type = None
                if isinstance(resp, tuple) and len(resp) == 2 and isinstance(resp[0], (bytes, bytearray)):
                    # Backward-compatible: caller returned bytes (e.g., tests/mocks)
                    content_type = resp[1]
                    fd, tmp = tempfile.mkstemp(prefix=f"att_{attachment_id}_", suffix=".bin")
                    with os.fdopen(fd, "wb") as f:
                        f.write(resp[0])
                    tmp_path = Path(tmp)
                elif isinstance(resp, tuple) and len(resp) == 2:
                    tmp_path, content_type = resp
                else:
                    raise RuntimeError(f"Unexpected download_attachment response for {attachment_id}: {type(resp)}")

                if tmp_path is None or not Path(tmp_path).exists():
                    raise RuntimeError(f"Attachment temp path missing for {attachment_id}")

                data_size = Path(tmp_path).stat().st_size
                if attachment_size_limit and data_size > attachment_size_limit:
                    stripped = {
                        "attachment_id": attachment_id,
                        "size_bytes": data_size,
                        "limit_bytes": attachment_size_limit,
                        "skipped": True,
                    }
                    notify("attachment_skipped", run_id=rid, **stripped)
                    attachments_by_test.setdefault(job["test_id"], []).append({
                        "name": job["filename"],
                        "path": None,
                        "content_type": content_type,
                        "size": job.get("size") or data_size,
                        "is_image": False,
                        "is_video": bool(content_type and content_type.startswith("video/")),
                        "data_url": None,
                        "inline_embedded": False,
                        "skipped": True,
                    })
                    try:
                        Path(tmp_path).unlink(missing_ok=True)
                    except Exception:
                        pass
                    continue

                is_image_type = bool(content_type and str(content_type).lower().startswith("image/"))
                suffix_map = {
                    "image/jpeg": ".jpg",
                    "image/jpg": ".jpg",
                    "image/png": ".png",
                }
                desired_suffix = suffix_map.get((content_type or "").lower())
                if desired_suffix:
                    current_suffix = job["abs_path"].suffix.lower()
                    if current_suffix != desired_suffix:
                        rel_path = job["rel_path"].with_suffix(desired_suffix)
                        job["rel_path"] = rel_path
                        job["abs_path"] = Path("out") / rel_path
                        job["abs_path"].parent.mkdir(parents=True, exist_ok=True)
                        base_name = Path(job["filename"]).stem or Path(job["filename"]).name
                        job["filename"] = f"{base_name}{desired_suffix}"

                inline_payload = None
                if is_image_type:
                    content_type, size_bytes, inline_payload = compress_image_file(
                        Path(tmp_path),
                        content_type,
                        job["abs_path"],
                        inline_limit,
                    )
                else:
                    job["abs_path"].parent.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.copyfile(tmp_path, job["abs_path"])
                    except OSError:
                        # Last resort: read/write the chunks
                        with open(tmp_path, "rb") as src, open(job["abs_path"], "wb") as dst:
                            shutil.copyfileobj(src, dst, length=64 * 1024)
                    size_bytes = job["abs_path"].stat().st_size if job["abs_path"].exists() else data_size

                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except Exception:
                    pass

                content_type = content_type or job["initial_type"] or mimetypes.guess_type(str(job["abs_path"]))[0]
                is_image = bool(content_type and str(content_type).startswith("image/"))
                data_url = None
                if inline_payload is not None and is_image:
                    try:
                        data_b64 = base64.b64encode(inline_payload).decode("ascii")
                        mime = content_type or "application/octet-stream"
                        data_url = f"data:{mime};base64,{data_b64}"
                    except Exception:
                        data_url = None
                # Use a relative path so the saved HTML works offline and under the /reports/ mount
                public_path = str(job["rel_path"]).replace(os.sep, "/")
                suffix_lc = job["rel_path"].suffix.lower()
                common_video_exts = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".mpg", ".mpeg"}
                is_video = bool(
                    (content_type and str(content_type).startswith("video/"))
                    or suffix_lc in common_video_exts
                )
                attachments_by_test.setdefault(job["test_id"], []).append({
                    "name": job["filename"],
                    "path": public_path,
                    "content_type": content_type,
                    "size": job.get("size") or size_bytes,
                    "is_image": is_image,
                    "is_video": is_video,
                    "data_url": data_url,
                    "inline_embedded": bool(data_url),
                })
            log_memory(f"after_attachment_downloads_{rid}")

        for tid in attachments_by_test:
            attachments_by_test[tid].sort(key=lambda entry: entry["path"])

        rows_payload = []
        for record in table_df.to_dict(orient="records"):
            tid = record.get("test_id")
            tid_int = None
            if tid is not None and not (isinstance(tid, float) and pd.isna(tid)):
                try:
                    tid_int = int(tid)
                except (TypeError, ValueError):
                    tid_int = None
            record["comment"] = comments_by_test.get(tid_int, "")
            record["attachments"] = attachments_by_test.get(tid_int, [])
            rows_payload.append(record)

        tables.append({
            "run_id": rid,
            "run_name": run_names.get(int(rid)) if run_names else None,
            "rows": rows_payload,
            "counts": counts,
            "total": run_total,
            "pass_rate": run_pass_rate,
            "donut_style": run_donut_style,
            "donut_legend": segs,
            "refs": run_refs,
        })
        summary["total"] += run_total
        summary["Passed"] += run_passed
        summary["Failed"] += run_failed
        for k, v in counts.items():
            summary.setdefault("by_status", {})
            summary["by_status"][k] = summary["by_status"].get(k, 0) + v
        # No trend point tracking
        log_memory(f"run_complete_{rid}")

    pass_rate = round((summary["Passed"] / summary["total"]) * 100, 2) if summary["total"] else 0
    # Donut segments
    status_colors = {
        "Passed": "#16a34a",
        "Failed": "#ef4444",
        "Blocked": "#f59e0b",
        "Retest": "#3b82f6",
        "Untested": "#9ca3af",
    }
    status_counts = summary.get("by_status", {})
    total_for_chart = sum(status_counts.values())
    segments = []
    if total_for_chart > 0:
        cumulative = 0.0
        colors_lc = {k.lower(): v for k, v in status_colors.items()}
        for label, count in sorted(status_counts.items(), key=lambda kv: (-kv[1], kv[0])):
            pct = (count / total_for_chart) * 100.0
            start = cumulative
            end = cumulative + pct
            color = colors_lc.get(str(label).lower(), "#6b7280")
            segments.append({"label": label, "count": count, "percent": round(pct, 2), "start": start, "end": end, "color": color})
            cumulative = end
        donut_style = ", ".join([f"{s['color']} {s['start']}% {s['end']}%" for s in segments])
        donut_style = f"conic-gradient({donut_style})"
    else:
        donut_style = "conic-gradient(#e5e7eb 0 100%)"

    report_title = f"Testing Progress Report — {plan_name}" if plan_name else "Testing Progress Report"
    notify("rendering_report", total_runs=total_runs)
    context = {
        "report_title": report_title,
        "generated_at": datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M"),
        "summary": {**summary, "pass_rate": pass_rate},
        "tables": tables,
        "notes": ["Generated automatically from TestRail API"],
        "project_name": project_name,
        "plan_name": plan_name,
        "project_id": project,
        "plan_id": plan,
        "base_url": base_url,
        "donut_style": donut_style,
        "donut_legend": segments,
        "jira_base": "https://bvarta-project.atlassian.net/browse/",
        "report_refs": sorted(report_refs),
    }

    def _safe_filename(name: str) -> str:
        cleaned = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name)
        return cleaned.strip("_") or "Project"

    date_str = datetime.now().strftime('%d%m%y')
    base_name = plan_name if plan_name else project_name
    name_slug = _safe_filename(base_name)
    filename = f"Testing_Progress_Report_{name_slug}_{date_str}.html"
    out_file = Path("out") / filename
    context["output_filename"] = filename
    rendered = render_html(context, out_file)
    log_memory("report_rendered")
    return rendered


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=int, required=True)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--run", type=int)
    group.add_argument("--plan", type=int)
    ap.add_argument(
        "--runs",
        type=int,
        nargs="+",
        help="Optional list of run IDs within the plan to include (use with --plan)",
    )
    args = ap.parse_args()

    try:
        if args.runs and not args.plan:
            raise ValueError("--runs can only be used together with --plan")
        path = generate_report(project=args.project, plan=args.plan, run=args.run, run_ids=args.runs)
        print(f"✅ Report saved to: {path}")
    except (ValueError, requests.exceptions.RequestException) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
