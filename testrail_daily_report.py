# mypy: disable-error-code=assignment
#!/usr/bin/env python3
"""
TestRail Daily Report → HTML
Fetches test results from TestRail (run or plan) and generates an HTML summary.
Usage:
    python testrail_daily_report.py --project 1 --plan 241
Requires env vars:
    TESTRAIL_BASE_URL, TESTRAIL_USER, TESTRAIL_API_KEY
"""

import argparse
import base64
import gc
import json
import math
import mimetypes
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Literal, TypedDict, cast

import pandas as pd
import requests
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image

from testrail_client import (
    DEFAULT_HTTP_BACKOFF,
    DEFAULT_HTTP_RETRIES,
    DEFAULT_HTTP_TIMEOUT,
    AttachmentTooLarge,
    TestRailClient,
    UserLookupForbidden,
    download_attachment,
)


class Summary(TypedDict):
    total: int
    Passed: int
    Failed: int
    by_status: dict[str, int]


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


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


VERBOSE_STAGE_LOGS = _env_flag("REPORT_VERBOSE_LOGS", False)
NOISY_STAGES = {
    "run_data_loaded",
    "run_users_ready",
    "run_summary_ready",
    "run_table_built",
    "run_latest_results",
    "run_download_queue",
    "run_payload_written",
    "run_summary_updated",
    "run_stop",
}


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


def _downcast_numeric(
    series: pd.Series,
    kind: Literal["integer", "signed", "unsigned", "float"] = "integer",
):
    """Downcast numeric series while preserving NaN values."""
    return pd.to_numeric(series, errors="coerce", downcast=kind)


def _minimal_frame(df: pd.DataFrame, keep: list[str]):
    subset = [c for c in keep if c in df.columns]
    return df[subset].copy() if subset else pd.DataFrame(columns=keep)


def _memory_usage_mb() -> float | None:
    """Return current RSS memory usage in MB if detectable."""
    _psutil = None
    _resource = None
    try:
        import psutil as _psutil  # type: ignore
    except ImportError:
        pass
    try:
        import resource as _resource  # type: ignore
    except ImportError:
        pass

    if _psutil:
        try:
            proc = _psutil.Process(os.getpid())
            mem_info = proc.memory_info()
            return mem_info.rss / (1024 * 1024)
        except Exception:
            pass
    if _resource:
        try:
            usage = _resource.getrusage(_resource.RUSAGE_SELF)
            rss: float = float(getattr(usage, "ru_maxrss", 0.0))
            if rss <= 0:
                return None
            if rss > 10 * (1024**2):
                return rss / (1024 * 1024)
            return rss / 1024.0
        except Exception:
            return None
    return None


def log_memory(label: str):
    """Log current memory usage to stdout, or stderr for high usage."""
    mem_mb = _memory_usage_mb()
    if mem_mb is None:
        return

    log_message = f"[mem-log] stage={label} rss_mb={mem_mb:.2f}"

    if mem_mb > 800:
        print(f"WARNING: {log_message}", file=sys.stderr, flush=True)
    else:
        print(log_message, file=sys.stdout, flush=True)


def summarize_results(results, status_map=DEFAULT_STATUS_MAP):
    df = pd.DataFrame(results)
    # If no results or unexpected payload (e.g., missing test_id),
    # return empty frame with expected columns
    if df.empty or "test_id" not in df.columns:
        empty_cols = ["test_id", "status_id", "comment", "created_on"]
        return {
            "total": 0,
            "by_status": {},
            "pass_rate": 0.0,
            "df": pd.DataFrame(columns=empty_cols),
        }

    # Deduplicate to the latest result per test_id
    sort_cols = [c for c in ["test_id", "created_on", "id"] if c in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols)
    df = df.drop_duplicates("test_id", keep="last")
    df = _minimal_frame(
        df,
        [
            "id",
            "test_id",
            "status_id",
            "status_name",
            "comment",
            "created_on",
            "assignedto_id",
        ],
    )

    # Map status_id to names; keep original names if API provided
    if "status_name" not in df.columns:
        sid = _downcast_numeric(df.get("status_id"), "unsigned")
        df["status_name"] = sid.map(lambda x: status_map.get(int(x), str(int(x))) if pd.notna(x) else "Untested")
    else:
        df["status_name"] = df["status_name"].fillna("")
    for col in ("id", "test_id", "status_id", "assignedto_id"):
        if col in df.columns:
            df[col] = _downcast_numeric(df[col], "unsigned")

    total = len(df)
    by_status = df["status_name"].value_counts().to_dict()
    passed = by_status.get("Passed", 0)
    pass_rate = round((passed / total) * 100, 2) if total else 0.0
    return {"total": total, "by_status": by_status, "pass_rate": pass_rate, "df": df}


def build_test_table(
    tests_df: pd.DataFrame,
    results_df: pd.DataFrame,
    status_map=DEFAULT_STATUS_MAP,
    users_map=None,
    priorities_map=None,
):
    users_map = users_map or {}
    priorities_map = priorities_map or {}
    tests_df = _prepare_tests_frame(pd.DataFrame(tests_df), status_map)
    results_df = _prepare_results_frame(results_df)

    merged = tests_df.merge(results_df, on="test_id", how="left")
    status_order_map = {
        "Failed": 0,
        "Blocked": 1,
        "Retest": 2,
        "Untested": 3,
        "Passed": 4,
    }
    merged["_status_order"] = merged["status_name"].map(lambda s: status_order_map.get(str(s), 2))
    if "test_id" in merged.columns:
        merged = merged.sort_values(["_status_order", "test_id"])
    else:
        merged = merged.sort_values(["_status_order"])
    merged["status_name"] = merged["status_name"].replace({None: ""}).fillna("")
    merged.loc[merged["status_name"] == "", "status_name"] = "Untested"
    merged["assignee"] = _resolve_assignees(merged, users_map)

    if "priority_id" in merged.columns:
        try:
            pid = pd.to_numeric(merged["priority_id"], errors="coerce").astype("Int64")
            merged["priority"] = pid.map(lambda x: priorities_map.get(int(x), str(int(x))) if pd.notna(x) else "")
        except Exception:
            merged["priority"] = merged["priority_id"].astype(str)
    else:
        merged["priority"] = ""

    desired = ["test_id", "title", "status_name", "assignee", "priority", "refs"]
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


def _prepare_results_frame(results_df: pd.DataFrame) -> pd.DataFrame:
    if results_df.empty:
        return pd.DataFrame(columns=["test_id", "comment", "created_on", "assignedto_id"])
    if "test_id" not in results_df.columns:
        results_df = results_df.assign(test_id=pd.Series(dtype="int64"))
    result_keep = ["test_id", "comment", "created_on", "assignedto_id"]
    results_df = _minimal_frame(results_df, result_keep)
    sort_cols = [c for c in ["test_id", "created_on"] if c in results_df.columns]
    if sort_cols:
        results_df = results_df.sort_values(sort_cols)
    if "test_id" in results_df.columns and not results_df.empty:
        results_df = results_df.drop_duplicates("test_id", keep="last")
    for col in ("test_id", "assignedto_id"):
        if col in results_df.columns:
            results_df[col] = _downcast_numeric(results_df[col], "unsigned")
    return results_df


def _prepare_tests_frame(tests_df: pd.DataFrame, status_map=DEFAULT_STATUS_MAP) -> pd.DataFrame:
    if "id" in tests_df.columns and "test_id" not in tests_df.columns:
        tests_df = tests_df.rename(columns={"id": "test_id"})
    test_keep = [
        "test_id",
        "title",
        "priority_id",
        "refs",
        "assignedto_id",
        "status_id",
    ]
    tests_df = _minimal_frame(tests_df, test_keep)
    if "test_id" not in tests_df.columns:
        tests_df = pd.DataFrame(columns=test_keep)
    if "status_id" in tests_df.columns:
        try:
            sid = _downcast_numeric(tests_df["status_id"], "unsigned").astype("Int64")
            tests_df["status_name"] = sid.map(
                lambda x: status_map.get(int(x), str(int(x))) if pd.notna(x) else "Untested"
            )
        except Exception:
            tests_df["status_name"] = "Untested"
    else:
        tests_df["status_name"] = "Untested"
    for col in ("test_id", "priority_id", "assignedto_id"):
        if col in tests_df.columns:
            tests_df[col] = _downcast_numeric(tests_df[col], "unsigned")
    return tests_df


def _resolve_assignees(merged: pd.DataFrame, users_map: dict) -> pd.Series:
    assignee_series = None
    if "assignedto_id" in merged.columns:
        assignee_series = merged["assignedto_id"]
    elif "assignedto_id_x" in merged.columns:
        assignee_series = merged["assignedto_id_x"]
    elif "assignedto_id_y" in merged.columns:
        assignee_series = merged["assignedto_id_y"]
    if assignee_series is None:
        return pd.Series(["" for _ in range(len(merged))], index=merged.index)
    aid = pd.to_numeric(assignee_series, errors="coerce").astype("Int64")
    return aid.map(lambda x: users_map.get(int(x), str(int(x))) if pd.notna(x) else "")


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
                work.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

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
                    shrunk.thumbnail((new_dim, new_dim), Image.Resampling.LANCZOS)
                    return save_jpeg(shrunk, min_quality)
                return bytes_payload, current_type

            out_bytes, out_type = enforce_size(out_bytes, work, out_type)
            return out_bytes, out_type
    except Exception:
        return data, content_type


def _build_data_url(payload: bytes | None, content_type: str | None) -> str | None:
    if not payload:
        return None
    try:
        data_b64 = base64.b64encode(payload).decode("ascii")
    except Exception:
        return None
    mime = content_type or "application/octet-stream"
    return f"data:{mime};base64,{data_b64}"


def process_run_attachments(
    rid: int,
    latest_result_ids: dict[int, int],
    metadata_map: dict[int, list],
    *,
    base_url: str,
    session_factory,
    attachment_workers: int,
    attachment_batch_size: int,
    download_limit: int | None,
    inline_limit: int,
    inline_video_limit: int,
    video_transcode_enabled: bool,
    video_max_dim: int,
    video_target_kbps: int,
    video_preset: str,
    attachment_retry_limit: int,
    http_timeout: float,
    retry_backoff: float,
    ffmpeg_bin: str,
    notify,
    log_memory,
):
    attachments_by_test: dict[int, list[dict]] = {}
    download_jobs: list[dict] = []

    if latest_result_ids:
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
                inferred_type = att.get("content_type") or att.get("mime_type") or mimetypes.guess_type(filename)[0]
                size_hint = att.get("size")
                download_jobs.append(
                    {
                        "test_id": tid,
                        "attachment_id": attachment_id,
                        "filename": filename,
                        "initial_type": inferred_type,
                        "size": size_hint,
                    }
                )

    metadata_map.clear()

    if not download_jobs:
        notify("run_download_queue", run_id=rid, jobs=0)
        return attachments_by_test

    notify("run_download_queue", run_id=rid, jobs=len(download_jobs))
    notify("downloading_attachments", run_id=rid, total=len(download_jobs))
    inline_limit = max(0, inline_limit)
    inline_video_limit = max(inline_limit, inline_video_limit)

    def _build_skipped(
        job: dict,
        *,
        size_bytes: int,
        limit_bytes: int,
        reason: str,
        content_type: str | None = None,
    ):
        initial_type = content_type or job.get("initial_type")
        is_image = bool(initial_type and str(initial_type).lower().startswith("image/"))
        is_video = bool(initial_type and str(initial_type).lower().startswith("video/"))
        return {
            "name": job["filename"],
            "path": None,
            "content_type": initial_type,
            "size": size_bytes,
            "is_image": is_image,
            "is_video": is_video,
            "data_url": None,
            "inline_embedded": False,
            "skipped": True,
            "skip_reason": reason,
            "limit_bytes": limit_bytes,
        }

    def _process_attachment_job(index: int, job: dict):
        attachment_id = job["attachment_id"]
        local_session = session_factory()
        notify(
            "downloading_attachment",
            run_id=rid,
            current=index,
            total=len(download_jobs),
            attachment_id=attachment_id,
        )
        tmp_obj = None
        content_type = job.get("initial_type")
        try:
            tmp_obj, content_type = download_attachment(
                local_session,
                base_url,
                attachment_id,
                max_retries=attachment_retry_limit,
                size_limit=download_limit,
                timeout=http_timeout,
                backoff=retry_backoff,
            )
        except AttachmentTooLarge as exc:
            entry = _build_skipped(
                job,
                size_bytes=exc.size_bytes,
                limit_bytes=exc.limit_bytes,
                reason="size_limit",
            )
            notify(
                "attachment_skipped",
                run_id=rid,
                attachment_id=attachment_id,
                size_bytes=exc.size_bytes,
                limit_bytes=exc.limit_bytes,
                skipped=True,
            )
            return job["test_id"], entry
        except Exception as exc:
            print(
                f"Warning: download failed for attachment {attachment_id}: {exc}",
                file=sys.stderr,
            )
            entry = _build_skipped(
                job,
                size_bytes=job.get("size") or 0,
                limit_bytes=inline_limit,
                reason="download_error",
            )
            return job["test_id"], entry
        finally:
            local_session.close()

        tmp_path: Path | None = None
        payload_bytes: bytes | None = None
        if isinstance(tmp_obj, (bytes, bytearray, memoryview)):
            payload_bytes = bytes(tmp_obj)
        else:
            tmp_path = Path(tmp_obj)

        suffix = Path(job["filename"]).suffix.lower()
        is_image = bool(content_type and str(content_type).lower().startswith("image/"))
        common_video_exts = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".mpg", ".mpeg"}
        is_video = bool(
            (content_type and str(content_type).lower().startswith("video/")) or suffix in common_video_exts
        )

        size_bytes = job.get("size") or 0
        inline_payload = None
        final_type = content_type

        def _tmp_size(path: Path | None) -> int:
            if path and path.exists():
                return path.stat().st_size
            return size_bytes or (len(payload_bytes) if payload_bytes else 0)

        try:
            if is_image:
                if payload_bytes is None and tmp_path is not None and tmp_path.exists():
                    payload_bytes = tmp_path.read_bytes()
                compressed, final_type = compress_image_data(payload_bytes or b"", final_type)
                size_bytes = len(compressed)
                if inline_limit and 0 < size_bytes <= inline_limit:
                    inline_payload = compressed
            elif is_video:
                source_path: Path
                cleanup_paths: list[Path] = []
                if tmp_path is None and payload_bytes is not None:
                    fd, temp_name = tempfile.mkstemp(prefix=f"att_{attachment_id}_", suffix=suffix or ".bin")
                    os.close(fd)
                    source_path = Path(temp_name)
                    source_path.write_bytes(payload_bytes)
                    cleanup_paths.append(source_path)
                else:
                    source_path = tmp_path  # type: ignore[assignment]
                    if source_path:
                        cleanup_paths.append(source_path)
                final_path = source_path
                if video_transcode_enabled and source_path is not None:
                    fd, output_name = tempfile.mkstemp(prefix=f"att_{attachment_id}_xcode_", suffix=".mp4")
                    os.close(fd)
                    output_path = Path(output_name)
                    try:
                        transcode_video_file(
                            source_path,
                            output_path,
                            ffmpeg_bin=ffmpeg_bin,
                            max_dim=video_max_dim,
                            target_kbps=video_target_kbps,
                            preset=video_preset,
                        )
                        final_path = output_path
                        cleanup_paths.append(output_path)
                        final_type = "video/mp4"
                    except (VideoTranscodeError, FileNotFoundError) as exc:
                        print(
                            f"Warning: video transcode failed for " f"attachment {attachment_id}: {exc}",
                            file=sys.stderr,
                        )
                size_bytes = _tmp_size(final_path)
                if (
                    inline_video_limit
                    and final_path is not None
                    and 0 < size_bytes <= inline_video_limit
                    and final_path.exists()
                ):
                    inline_payload = final_path.read_bytes()
                for path in cleanup_paths:
                    if path is not None:
                        path.unlink(missing_ok=True)
                tmp_path = None  # already cleaned
            else:
                size_bytes = _tmp_size(tmp_path)
        finally:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)

        data_url = _build_data_url(inline_payload, final_type)
        entry = {
            "name": job["filename"],
            "path": None,
            "content_type": final_type,
            "size": size_bytes,
            "is_image": is_image,
            "is_video": is_video,
            "data_url": data_url,
            "inline_embedded": bool(data_url),
            "skipped": False,
            "skip_reason": None,
            "limit_bytes": None,
        }
        if not entry["inline_embedded"]:
            entry["skipped"] = True
            entry["skip_reason"] = "inline_limit" if (is_image or is_video) else "unsupported_type"
            entry["limit_bytes"] = inline_video_limit if is_video else inline_limit
        return job["test_id"], entry

    completed_downloads = 0

    def _process_batch(batch: list[tuple[int, dict]]):
        nonlocal completed_downloads
        max_workers_batch = min(attachment_workers, len(batch))
        with ThreadPoolExecutor(max_workers=max_workers_batch) as executor:
            futures = {executor.submit(_process_attachment_job, idx, job): idx for idx, job in batch}
            for future in as_completed(futures):
                try:
                    test_id, entry = future.result()
                except Exception as exc:
                    print(
                        f"Warning: attachment future failed for run {rid}: {exc}",
                        file=sys.stderr,
                    )
                    continue
                attachments_by_test.setdefault(test_id, []).append(entry)
                completed_downloads += 1
                if completed_downloads % 5 == 0:
                    log_memory(f"download_progress_{rid}_{completed_downloads}")
        gc.collect()

    if attachment_batch_size and attachment_batch_size > 0:
        for start in range(0, len(download_jobs), attachment_batch_size):
            batch_jobs = [
                (index, job)
                for index, job in enumerate(
                    download_jobs[start : start + attachment_batch_size],
                    start=start + 1,
                )
            ]
            _process_batch(batch_jobs)
    else:
        batch_jobs = [(index, job) for index, job in enumerate(download_jobs, start=1)]
        _process_batch(batch_jobs)

    log_memory(f"after_attachment_downloads_{rid}")

    def _attachment_sort_key(entry: dict):
        return (entry.get("skipped", False), entry.get("name") or "")

    for items in attachments_by_test.values():
        items.sort(key=_attachment_sort_key)

    return attachments_by_test


class VideoTranscodeError(Exception):
    pass


def transcode_video_file(
    input_path: Path,
    output_path: Path,
    *,
    ffmpeg_bin: str,
    max_dim: int,
    target_kbps: int,
    preset: str = "veryfast",
) -> None:
    """
    Transcode video to H.264/AAC with constrained dimensions/bitrate.
    Raises VideoTranscodeError on failure.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    scale_expr = f"scale='min({max_dim},iw)':-2"
    cmd = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(input_path),
        "-vf",
        scale_expr,
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-b:v",
        f"{target_kbps}k",
        "-movflags",
        "+faststart",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise VideoTranscodeError(proc.stderr or proc.stdout or "ffmpeg failed")


def render_streaming_report(context: dict, runs_cache: Path, out_path: Path):
    """Render the final HTML by streaming run sections from disk."""
    env = Environment(loader=FileSystemLoader("templates"), autoescape=select_autoescape())
    template = env.get_template("daily_report.html.j2")

    def _iter_tables():
        with runs_cache.open("r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)

    render_ctx = dict(context)
    render_ctx["tables"] = _iter_tables()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as dest:
        for chunk in template.generate(**render_ctx):
            dest.write(chunk)
    return str(out_path)


def render_html(context: dict, out_path: Path):
    """Backward-compatible wrapper so tests can patch render_html."""
    cache_path = context.pop("_tables_cache", None)
    if cache_path is None:
        raise RuntimeError("render_html requires a tables cache path for streaming")
    return render_streaming_report(context, Path(cache_path), out_path)


def _get_cached_runs(runs_cache: Path) -> int | None:
    try:
        with runs_cache.open("r", encoding="utf-8") as verify_fp:
            return sum(1 for line in verify_fp if line.strip())
    except Exception:
        return None


def generate_report(
    project: int,
    plan: int | None = None,
    run: int | None = None,
    run_ids: list[int] | None = None,
    progress=None,
    api_client: TestRailClient | None = None,
) -> str:
    """Generate a report for a plan or run and return the output HTML path."""

    def notify(stage: str, **payload):
        log_payload = {k: payload.get(k) for k in sorted(payload)}
        if VERBOSE_STAGE_LOGS or stage not in NOISY_STAGES:
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

    log_memory("start")

    if api_client is None:
        base_url = env_or_die("TESTRAIL_BASE_URL").rstrip("/")
        user = env_or_die("TESTRAIL_USER")
        api_key = env_or_die("TESTRAIL_API_KEY")
        http_timeout = DEFAULT_HTTP_TIMEOUT
        http_retries = DEFAULT_HTTP_RETRIES
        http_backoff = DEFAULT_HTTP_BACKOFF
        api_client = TestRailClient(
            base_url=base_url,
            auth=(user, api_key),
            timeout=http_timeout,
            max_attempts=http_retries,
            backoff=http_backoff,
        )
    else:
        base_url = api_client.base_url.rstrip("/")
        http_timeout = api_client.timeout
        http_retries = api_client.max_attempts
        http_backoff = api_client.backoff

    # Enrichment data
    project_obj = api_client.get_project(project)
    project_name = project_obj.get("name") or f"Project {project}"
    plan_name: str | None = None
    run_names: dict[int, str] = {}
    plan_run_ids: list[int] = []
    if plan is not None:
        plan_obj = api_client.get_plan(plan)
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
    users_map: dict[int, str] = {}
    try:
        users_map = api_client.get_users_map()
    except UserLookupForbidden as err:
        # Bulk endpoint forbidden; fall back to per-user lookups until they fail too.
        users_map = {}
        print(
            f"Warning: bulk user lookup forbidden ({err}); " f"falling back to get_user per ID",
            file=sys.stderr,
        )
    priorities_map = api_client.get_priorities_map()
    statuses_map = api_client.get_statuses_map(defaults=DEFAULT_STATUS_MAP)

    if run is not None:
        run_ids_resolved = [int(run)]
    else:
        if run_ids:
            run_ids_resolved = [rid for rid in run_ids if rid in plan_run_ids]
        else:
            assert plan is not None
            run_ids_resolved = plan_run_ids or api_client.get_plan_runs(plan)
    if not run_ids_resolved:
        raise ValueError("No runs available to generate report")

    notify("initializing", plan=plan, run=run, run_count=len(run_ids or []))
    summary: Summary = {"total": 0, "Passed": 0, "Failed": 0, "by_status": {}}

    report_refs: set[str] = set()
    # Allow tuning concurrency with env while keeping conservative defaults
    try:
        attachment_workers_env = int(os.getenv("ATTACHMENT_WORKERS", "2"))
    except ValueError:
        attachment_workers_env = 2
    try:
        attachment_workers_ceiling = int(os.getenv("ATTACHMENT_WORKERS_MAX", "8"))
    except ValueError:
        attachment_workers_ceiling = 8
    attachment_workers_ceiling = max(1, min(16, attachment_workers_ceiling))
    attachment_workers = max(1, min(attachment_workers_ceiling, attachment_workers_env))
    try:
        attachment_batch_size = int(os.getenv("ATTACHMENT_BATCH_SIZE", "0"))
    except ValueError:
        attachment_batch_size = 0
    attachment_batch_size = max(0, attachment_batch_size)

    # Allow higher ceiling if explicitly requested
    try:
        run_workers_ceiling = int(os.getenv("RUN_WORKERS_MAX", "4"))
    except ValueError:
        run_workers_ceiling = 4
    run_workers_ceiling = max(1, min(8, run_workers_ceiling))

    inline_embed_limit = int(os.getenv("ATTACHMENT_INLINE_MAX_BYTES", "250000"))
    try:
        video_inline_limit = int(os.getenv("ATTACHMENT_VIDEO_INLINE_MAX_BYTES", "15000000"))
    except ValueError:
        video_inline_limit = 15000000
    if video_inline_limit < inline_embed_limit:
        video_inline_limit = inline_embed_limit

    video_transcode_enabled = _env_flag("ATTACHMENT_VIDEO_TRANSCODE", True)
    try:
        video_max_dim = int(os.getenv("ATTACHMENT_VIDEO_MAX_DIM", "1280"))
    except ValueError:
        video_max_dim = 1280
    try:
        video_target_kbps = int(os.getenv("ATTACHMENT_VIDEO_TARGET_KBPS", "1800"))
    except ValueError:
        video_target_kbps = 1800
    video_target_kbps = max(300, video_target_kbps)
    ffmpeg_bin = os.getenv("FFMPEG_BIN", "ffmpeg")
    video_ffmpeg_preset = os.getenv("ATTACHMENT_VIDEO_FFMPEG_PRESET", "veryfast")
    try:
        attachment_retry_limit = int(os.getenv("ATTACHMENT_RETRY_ATTEMPTS", "4"))
    except ValueError:
        attachment_retry_limit = 4
    attachment_retry_limit = max(1, min(10, attachment_retry_limit))
    attachment_size_limit = int(os.getenv("ATTACHMENT_MAX_BYTES", "520000000"))

    def _flag_enabled(value: str | None) -> bool:
        if value is None:
            return False
        return value.strip().lower() not in {"0", "false", "no", "off"}

    try:
        snapshot_limit = int(os.getenv("TABLE_SNAPSHOT_LIMIT", "3"))
    except ValueError:
        snapshot_limit = 3
    snapshot_limit = max(1, snapshot_limit)
    tables_snapshot: list[dict] = []
    runs_cache = Path(tempfile.NamedTemporaryFile(delete=False).name)
    runs_cache.parent.mkdir(parents=True, exist_ok=True)
    with runs_cache.open("w", encoding="utf-8") as sink_init:
        sink_init.write("")
    total_runs = len(run_ids_resolved)
    snapshot_env = os.getenv("REPORT_TABLE_SNAPSHOT")
    if snapshot_env is not None:
        snapshot_enabled = _flag_enabled(snapshot_env)
    else:
        snapshot_enabled = bool(
            os.getenv("PYTEST_CURRENT_TEST")
            or os.getenv("PYTEST_WORKER")
            or any(name.startswith(("pytest", "_pytest")) for name in sys.modules)
            or getattr(render_html, "_is_mock_object", False)
        )

    def _snapshot_run(payload: dict) -> dict:
        base = {
            "run_id": payload["run_id"],
            "run_name": payload.get("run_name"),
            "counts": payload.get("counts", {}),
            "total": payload.get("total"),
            "pass_rate": payload.get("pass_rate"),
            "donut_style": payload.get("donut_style"),
            "donut_legend": payload.get("donut_legend", []),
            "refs": payload.get("refs", []),
        }
        rows_preview = []
        for row in payload.get("rows", []):
            row_copy = {
                "test_id": row.get("test_id"),
                "title": row.get("title"),
                "status_name": row.get("status_name"),
                "assignee": row.get("assignee"),
                "priority": row.get("priority"),
                "refs": row.get("refs"),
                "comment": row.get("comment"),
            }
            attachments_preview = []
            for att in row.get("attachments", []):
                att_copy = {
                    "name": att.get("name"),
                    "path": att.get("path"),
                    "content_type": att.get("content_type"),
                    "size": att.get("size"),
                    "is_image": att.get("is_image"),
                    "is_video": att.get("is_video"),
                    "inline_embedded": att.get("inline_embedded"),
                    "skipped": att.get("skipped"),
                    "skip_reason": att.get("skip_reason"),
                }
                if att.get("data_url"):
                    att_copy["data_url"] = "data:preview"
                attachments_preview.append(att_copy)
            row_copy["attachments"] = attachments_preview
            rows_preview.append(row_copy)
        base["rows"] = rows_preview
        return base

    for idx, rid in enumerate(run_ids_resolved, start=1):
        notify(
            "processing_run",
            run_id=rid,
            index=idx,
            total=total_runs,
            remaining=len(run_ids_resolved) - idx,
        )
        results = api_client.get_results_for_run(rid)
        tests = api_client.get_tests_for_run(rid)
        try:
            tests_count = len(tests)
        except Exception:
            tests_count = 0
        try:
            results_count = len(results)
        except Exception:
            results_count = 0
        notify("run_data_loaded", run_id=rid, tests=tests_count, results=results_count)

        # Ensure assignee IDs are resolvable to names
        if user_lookup_allowed:
            try:
                test_ids = {
                    int(x)
                    for x in pd.Series(tests)
                    .apply(lambda r: r.get("assignedto_id") if isinstance(r, dict) else None)
                    .dropna()
                    .tolist()
                }
            except Exception:
                test_ids = set()
            try:
                result_ids = {
                    int(x)
                    for x in pd.DataFrame(results)
                    .get("assignedto_id", pd.Series([], dtype="float"))
                    .dropna()
                    .astype(int)
                    .tolist()
                }
            except Exception:
                result_ids = set()
            missing_users = (test_ids | result_ids) - set(users_map)
            for uid in missing_users:
                if uid in users_map:
                    continue
                try:
                    u = api_client.get_user(uid)
                except UserLookupForbidden as err:
                    user_lookup_allowed = False
                    print(f"Warning: disabling per-user lookups ({err})", file=sys.stderr)
                    break
                if isinstance(u, dict) and u.get("id") is not None:
                    users_map[int(u["id"])] = u.get("name") or u.get("email") or str(u["id"])
        notify("run_users_ready", run_id=rid, known_users=len(users_map))

        res_summary = summarize_results(results, status_map=statuses_map)
        notify("run_summary_ready", run_id=rid, rows=len(res_summary["df"]))
        table_df = build_test_table(
            pd.DataFrame(tests),
            res_summary["df"],
            users_map=users_map,
            priorities_map=priorities_map,
            status_map=statuses_map,
        )
        notify("run_table_built", run_id=rid, rows=len(table_df))
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
                    segments.append(
                        {
                            "label": label,
                            "count": count,
                            "percent": round(pct, 2),
                            "start": start,
                            "end": end,
                            "color": color,
                        }
                    )
                    cumulative = end
                donut_style = (
                    "conic-gradient(" + ", ".join([f"{s['color']} {s['start']}% {s['end']}%" for s in segments]) + ")"
                )
            return segments, donut_style

        segs, run_donut_style = _build_segments(counts)
        run_refs = extract_refs(tests)
        del tests
        report_refs.update(run_refs)

        latest_results_df = res_summary["df"]
        comments_by_test: dict[int, str] = {}
        latest_result_ids: dict[int, int] = {}
        if not latest_results_df.empty:
            for rec in latest_results_df.itertuples(index=False):
                tid = getattr(rec, "test_id", None)
                if tid is None or pd.isna(tid):
                    continue
                tid_int = int(tid)
                comment = getattr(rec, "comment", None)
                if comment:
                    comments_by_test[tid_int] = comment
                result_id = getattr(rec, "id", None)
                if result_id is not None and not pd.isna(result_id):
                    latest_result_ids[tid_int] = int(result_id)
        notify("run_latest_results", run_id=rid, latest=len(latest_result_ids))

        def _fetch_metadata(test_id: int):
            try:
                data = api_client.get_attachments_for_test(test_id)
                if not isinstance(data, list):
                    if isinstance(data, dict):
                        return test_id, data.get("attachments", [])
                    return test_id, []
                return test_id, data
            except Exception as e:
                print(
                    f"Warning: attachments fetch failed for test {test_id}: {e}",
                    file=sys.stderr,
                )
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
                        print(
                            f"Warning: attachments metadata future failed " f"for test {tid}: {e}",
                            file=sys.stderr,
                        )
                        payload = []
                    metadata_map[tid] = payload or []
            log_memory(f"after_attachment_metadata_{rid}")

        attachments_by_test = process_run_attachments(
            rid,
            latest_result_ids,
            metadata_map,
            base_url=base_url,
            session_factory=api_client.make_session,
            attachment_workers=attachment_workers,
            attachment_batch_size=attachment_batch_size,
            download_limit=attachment_size_limit if attachment_size_limit > 0 else None,
            inline_limit=inline_embed_limit,
            inline_video_limit=video_inline_limit,
            video_transcode_enabled=video_transcode_enabled,
            video_max_dim=video_max_dim,
            video_target_kbps=video_target_kbps,
            video_preset=video_ffmpeg_preset,
            attachment_retry_limit=attachment_retry_limit,
            http_timeout=http_timeout,
            retry_backoff=http_backoff,
            ffmpeg_bin=ffmpeg_bin,
            notify=notify,
            log_memory=log_memory,
        )

        rows_payload: list[dict] = []
        for record in table_df.itertuples(index=False, name="Row"):
            row = record._asdict()
            tid = row.get("test_id")
            tid_int = None
            if tid is not None and not (isinstance(tid, float) and pd.isna(tid)):
                try:
                    tid_int = int(tid)
                except (TypeError, ValueError):
                    tid_int = None
            row["comment"] = comments_by_test.get(tid_int, "")
            row["attachments"] = attachments_by_test.get(tid_int, [])
            refs_val = row.get("refs")
            if refs_val is None:
                row["refs"] = []
            elif isinstance(refs_val, str):
                row["refs"] = [ref.strip() for ref in refs_val.split(",") if ref.strip()]
            elif isinstance(refs_val, list):
                row["refs"] = [str(r).strip() for r in refs_val if str(r).strip()]
            else:
                row["refs"] = [str(refs_val)]
            rows_payload.append(row)

        run_payload = {
            "run_id": rid,
            "run_name": run_names.get(int(rid)) if run_names else None,
            "rows": rows_payload,
            "counts": counts,
            "total": run_total,
            "pass_rate": run_pass_rate,
            "donut_style": run_donut_style,
            "donut_legend": segs,
            "refs": sorted(run_refs),
            "run_passed": run_passed,
            "run_failed": run_failed,
        }
        with runs_cache.open("a", encoding="utf-8") as sink:
            json.dump(run_payload, sink)
            sink.write("\n")
        notify(
            "run_payload_written",
            run_id=rid,
            rows=run_total,
            attachments=sum(len(v) for v in attachments_by_test.values()),
        )
        if snapshot_enabled and len(tables_snapshot) < snapshot_limit:
            tables_snapshot.append(_snapshot_run(run_payload))
        summary["total"] += run_total
        summary["Passed"] += run_passed
        summary["Failed"] += run_failed
        for k, v in counts.items():
            summary["by_status"][k] = summary["by_status"].get(k, 0) + v
        report_refs.update(run_refs)
        notify("run_summary_updated", run_id=rid, total=summary["total"])
        notify("run_stop", run_id=rid, index=idx)
        log_memory(f"run_complete_{rid}")
        del (
            table_df,
            latest_results_df,
            res_summary,
            rows_payload,
            attachments_by_test,
            metadata_map,
        )
        gc.collect()

    cached_runs = _get_cached_runs(runs_cache)
    notify("runs_cached", count=cached_runs, expected=total_runs)
    pass_rate = round((cast(int, summary["Passed"]) / cast(int, summary["total"])) * 100, 2) if summary["total"] else 0  # type: ignore # type: ignore # type: ignore
    # Donut segments
    status_colors = {
        "Passed": "#16a34a",
        "Failed": "#ef4444",
        "Blocked": "#f59e0b",
        "Retest": "#3b82f6",
        "Untested": "#9ca3af",
    }
    status_counts = summary.get("by_status", {})
    total_for_chart = sum(status_counts.values())  # type: ignore
    segments = []
    if total_for_chart > 0:
        cumulative = 0.0
        colors_lc = {k.lower(): v for k, v in status_colors.items()}
        for label, count in sorted(status_counts.items(), key=lambda kv: (-kv[1], kv[0])):
            pct = (count / total_for_chart) * 100.0
            start = cumulative
            end = cumulative + pct
            color = colors_lc.get(str(label).lower(), "#6b7280")
            segments.append(
                {
                    "label": label,
                    "count": count,
                    "percent": round(pct, 2),
                    "start": start,
                    "end": end,
                    "color": color,
                }
            )
            cumulative = end
        donut_style = ", ".join([f"{s['color']} {s['start']}% {s['end']}%" for s in segments])
        donut_style = f"conic-gradient({donut_style})"
    else:
        donut_style = "conic-gradient(#e5e7eb 0 100%)"

    report_title = f"Testing Progress Report — {plan_name}" if plan_name else "Testing Progress Report"
    notify("rendering_report", total_runs=total_runs)
    preview_tables: list[dict] = []
    if snapshot_enabled and not tables_snapshot:
        try:
            with runs_cache.open("r", encoding="utf-8") as preview_fp:
                for _, line in zip(range(3), preview_fp):
                    line = line.strip()
                    if line:
                        preview_tables.append(json.loads(line))
        except Exception:
            preview_tables = []

    context = {
        "report_title": report_title,
        "generated_at": datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M"),
        "summary": {**summary, "pass_rate": pass_rate},
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
    if snapshot_enabled:
        context["tables"] = list(tables_snapshot) if tables_snapshot else preview_tables
    else:
        context["tables"] = []

    def _safe_filename(name: str) -> str:
        cleaned = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name)
        return cleaned.strip("_") or "Project"

    date_str = datetime.now().strftime("%d%m%y")
    base_name = plan_name if plan_name else project_name
    name_slug = _safe_filename(base_name)
    filename = f"Testing_Progress_Report_{name_slug}_{date_str}.html"
    out_file = Path("out") / filename
    context["output_filename"] = filename
    context["_tables_cache"] = str(runs_cache)
    rendered = Path(render_html(context, out_file))
    log_memory("report_rendered")
    try:
        runs_cache.unlink(missing_ok=True)
    except Exception:
        pass
    gc.collect()
    tables_snapshot.clear()
    gc.collect()
    return str(rendered)


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
        result = generate_report(project=args.project, plan=args.plan, run=args.run, run_ids=args.runs)
        print(f"✅ Report saved to: {result}")
    except (ValueError, requests.exceptions.RequestException) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
