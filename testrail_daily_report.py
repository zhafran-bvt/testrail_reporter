#!/usr/bin/env python3
"""
TestRail Daily Report → HTML
Fetches test results from TestRail (run or plan) and generates an HTML summary.
Usage:
    python testrail_daily_report.py --project 1 --plan 241
Requires env vars:
    TESTRAIL_BASE_URL, TESTRAIL_USER, TESTRAIL_API_KEY
"""

import os, sys, argparse, requests, pandas as pd, mimetypes
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
from dotenv import load_dotenv

# Ensure .env overrides any existing env so local config is honored
load_dotenv(override=True)


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


def api_get(session: requests.Session, base_url: str, endpoint: str):
    url = f"{base_url}/index.php?/api/v2/{endpoint}"
    r = session.get(url)
    r.raise_for_status()
    data = r.json()
    # Surface TestRail API error payloads early
    if isinstance(data, dict) and any(k in data for k in ("error", "message")):
        msg = data.get("error") or data.get("message") or str(data)
        raise RuntimeError(f"API error for '{endpoint}': {msg}")
    return data


def get_project(session, base_url, project_id: int):
    return api_get(session, base_url, f"get_project/{project_id}")


def get_plan(session, base_url, plan_id: int):
    return api_get(session, base_url, f"get_plan/{plan_id}")


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
    except Exception as e:
        print(f"Warning: could not load users: {e}", file=sys.stderr)
        return {}


## Removed get_run helper as time-based trend was dropped


def get_user(session, base_url, user_id: int):
    try:
        return api_get(session, base_url, f"get_user/{user_id}")
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
    url = f"{base_url}/index.php?/api/v2/get_attachment/{attachment_id}"
    r = session.get(url)
    r.raise_for_status()
    return r.content, r.headers.get("Content-Type")


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


def render_html(context: dict, out_path: Path):
    env = Environment(loader=FileSystemLoader("templates"), autoescape=select_autoescape())
    tpl = env.get_template("daily_report.html.j2")
    html = tpl.render(**context)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return str(out_path)


def generate_report(project: int, plan: int | None = None, run: int | None = None) -> str:
    """Generate a report for a plan or run and return the output HTML path."""
    if (plan is None and run is None) or (plan is not None and run is not None):
        raise ValueError("Provide exactly one of plan or run")

    base_url = env_or_die("TESTRAIL_BASE_URL").rstrip("/")
    user = env_or_die("TESTRAIL_USER")
    api_key = env_or_die("TESTRAIL_API_KEY")

    session = requests.Session()
    session.auth = (user, api_key)

    # Enrichment data
    project_obj = get_project(session, base_url, project)
    project_name = project_obj.get("name") or f"Project {project}"
    plan_name = None
    run_names: dict[int, str] = {}
    if plan is not None:
        plan_obj = get_plan(session, base_url, plan)
        plan_name = plan_obj.get("name") or f"Plan {plan}"
        for entry in plan_obj.get("entries", []):
            for r in entry.get("runs", []):
                rid = r.get("id")
                if rid is not None:
                    run_names[int(rid)] = r.get("name") or str(rid)

    users_map = get_users_map(session, base_url)
    priorities_map = get_priorities_map(session, base_url)
    statuses_map = get_statuses_map(session, base_url)

    run_ids = [run] if run is not None else get_plan_runs(session, base_url, plan)  # type: ignore[arg-type]
    summary = {"total": 0, "Passed": 0, "Failed": 0}
    tables = []
    # Time-based trend removed

    report_refs: set[str] = set()
    attachment_workers = max(1, int(os.getenv("ATTACHMENT_WORKERS", "4")))

    for rid in run_ids:
        results = get_results_for_run(session, base_url, rid)
        tests = get_tests_for_run(session, base_url, rid)
        # Ensure assignee IDs are resolvable to names
        try:
            test_ids = {int(x) for x in pd.Series(tests).apply(lambda r: r.get("assignedto_id") if isinstance(r, dict) else None).dropna().tolist()}
        except Exception:
            test_ids = set()
        try:
            result_ids = {int(x) for x in pd.DataFrame(results).get("assignedto_id", pd.Series([], dtype="float")).dropna().astype(int).tolist()}
        except Exception:
            result_ids = set()
        for uid in (test_ids | result_ids):
            if uid not in users_map:
                u = get_user(session, base_url, uid)
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
            def _download(job):
                attachment_id = job["attachment_id"]
                data, content_type = download_attachment(session, base_url, attachment_id)
                job["abs_path"].write_bytes(data)
                return content_type

            with ThreadPoolExecutor(max_workers=attachment_workers) as executor:
                future_map = {executor.submit(_download, job): job for job in download_jobs}
                for future in as_completed(future_map):
                    job = future_map[future]
                    tid = job["test_id"]
                    try:
                        content_type = future.result()
                    except Exception as e:
                        print(f"Warning: download failed for attachment {job['attachment_id']}: {e}", file=sys.stderr)
                        continue
                    content_type = content_type or job["initial_type"] or mimetypes.guess_type(str(job["abs_path"]))[0]
                    is_image = bool(content_type and content_type.startswith("image/"))
                    attachments_by_test.setdefault(tid, []).append({
                        "name": job["filename"],
                        "path": str(job["rel_path"]).replace(os.sep, "/"),
                        "content_type": content_type,
                        "size": job["size"],
                        "is_image": is_image,
                    })

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
    return render_html(context, out_file)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=int, required=True)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--run", type=int)
    group.add_argument("--plan", type=int)
    args = ap.parse_args()

    try:
        path = generate_report(project=args.project, plan=args.plan, run=args.run)
        print(f"✅ Report saved to: {path}")
    except (ValueError, requests.exceptions.RequestException) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
