import contextlib
import contextvars
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


DEFAULT_HTTP_TIMEOUT = _env_float("TESTRAIL_HTTP_TIMEOUT", 20.0)
try:
    DEFAULT_HTTP_RETRIES = max(1, int(os.getenv("TESTRAIL_HTTP_RETRIES", "3")))
except (TypeError, ValueError):
    DEFAULT_HTTP_RETRIES = 3
DEFAULT_HTTP_BACKOFF = max(0.5, _env_float("TESTRAIL_HTTP_BACKOFF", 1.6))


# --- Telemetry helpers ---
_telemetry_ctx: contextvars.ContextVar[dict | None] = contextvars.ContextVar(
    "testrail_reporter_telemetry", default=None
)


@contextlib.contextmanager
def capture_telemetry():
    """Capture API call telemetry for the current thread."""
    data = {"api_calls": []}
    token = _telemetry_ctx.set(data)
    try:
        yield data
    finally:
        _telemetry_ctx.reset(token)


def record_api_call(
    kind: str, endpoint: str, elapsed_ms: float, status: str, error: str | None = None
):
    telemetry = _telemetry_ctx.get()
    if not telemetry:
        return
    telemetry.setdefault("api_calls", []).append(
        {
            "kind": kind,
            "endpoint": endpoint,
            "elapsed_ms": round(elapsed_ms, 2),
            "status": status,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


class UserLookupForbidden(Exception):
    """Raised when TestRail denies access to user lookup endpoints."""


class AttachmentTooLarge(Exception):
    """Raised when an attachment streaming download exceeds the allowed limit."""

    def __init__(self, size_bytes: int, limit_bytes: int):
        super().__init__(
            f"Attachment exceeded limit ({size_bytes} > {limit_bytes} bytes)"
        )
        self.size_bytes = size_bytes
        self.limit_bytes = limit_bytes


def api_get(
    session: requests.Session,
    base_url: str,
    endpoint: str,
    *,
    timeout: float | None = None,
    max_attempts: int | None = None,
    backoff: float | None = None,
):
    """GET with configurable timeout + retry for transient errors."""
    url = f"{base_url}/index.php?/api/v2/{endpoint}"
    attempts = max(1, max_attempts or DEFAULT_HTTP_RETRIES)
    delay = backoff or DEFAULT_HTTP_BACKOFF
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        start = time.perf_counter()
        try:
            r = session.get(url, timeout=timeout or DEFAULT_HTTP_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            # Surface TestRail API error payloads early
            if isinstance(data, dict) and any(k in data for k in ("error", "message")):
                msg = data.get("error") or data.get("message") or str(data)
                raise RuntimeError(f"API error for '{endpoint}': {msg}")
            record_api_call(
                "GET", endpoint, (time.perf_counter() - start) * 1000.0, "ok"
            )
            return data
        except requests.exceptions.HTTPError as exc:
            last_exc = exc
            status_code = exc.response.status_code if exc.response is not None else None
            record_api_call(
                "GET",
                endpoint,
                (time.perf_counter() - start) * 1000.0,
                "error",
                str(exc),
            )
            retryable = status_code == 429 or (
                status_code is not None and 500 <= status_code < 600
            )
            if not retryable or attempt == attempts:
                raise
            time.sleep(delay)
            delay *= 1.6
        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
        ) as exc:
            last_exc = exc
            record_api_call(
                "GET",
                endpoint,
                (time.perf_counter() - start) * 1000.0,
                "error",
                str(exc),
            )
            if attempt == attempts:
                raise
            time.sleep(delay)
            delay *= 1.6
        except Exception as exc:
            last_exc = exc
            record_api_call(
                "GET",
                endpoint,
                (time.perf_counter() - start) * 1000.0,
                "error",
                str(exc),
            )
            if attempt == attempts:
                raise
            time.sleep(delay)
            delay *= 1.6
    if last_exc:
        raise last_exc


def api_post(
    session: requests.Session,
    base_url: str,
    endpoint: str,
    payload: dict[str, Any],
    *,
    timeout: float | None = None,
    max_attempts: int | None = None,
    backoff: float | None = None,
):
    """POST with retry/backoff for transient errors."""
    url = f"{base_url}/index.php?/api/v2/{endpoint}"
    attempts = max(1, max_attempts or DEFAULT_HTTP_RETRIES)
    delay = backoff or DEFAULT_HTTP_BACKOFF
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        start = time.perf_counter()
        try:
            r = session.post(url, json=payload, timeout=timeout or DEFAULT_HTTP_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict) and any(k in data for k in ("error", "message")):
                msg = data.get("error") or data.get("message") or str(data)
                raise RuntimeError(f"API error for '{endpoint}': {msg}")
            record_api_call(
                "POST", endpoint, (time.perf_counter() - start) * 1000.0, "ok"
            )
            return data
        except requests.exceptions.HTTPError as exc:
            last_exc = exc
            status_code = exc.response.status_code if exc.response is not None else None
            record_api_call(
                "POST",
                endpoint,
                (time.perf_counter() - start) * 1000.0,
                "error",
                str(exc),
            )
            retryable = status_code == 429 or (
                status_code is not None and 500 <= status_code < 600
            )
            if not retryable or attempt == attempts:
                raise
            time.sleep(delay)
            delay *= 1.6
        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
        ) as exc:
            last_exc = exc
            record_api_call(
                "POST",
                endpoint,
                (time.perf_counter() - start) * 1000.0,
                "error",
                str(exc),
            )
            if attempt == attempts:
                raise
            time.sleep(delay)
            delay *= 1.6
        except Exception as exc:
            last_exc = exc
            record_api_call(
                "POST",
                endpoint,
                (time.perf_counter() - start) * 1000.0,
                "error",
                str(exc),
            )
            if attempt == attempts:
                raise
            time.sleep(delay)
            delay *= 1.6
    if last_exc:
        raise last_exc


def get_project(
    session,
    base_url,
    project_id: int,
    *,
    timeout: float | None = None,
    max_attempts: int | None = None,
    backoff: float | None = None,
):
    return api_get(
        session,
        base_url,
        f"get_project/{project_id}",
        timeout=timeout,
        max_attempts=max_attempts,
        backoff=backoff,
    )


def get_plan(
    session,
    base_url,
    plan_id: int,
    *,
    timeout: float | None = None,
    max_attempts: int | None = None,
    backoff: float | None = None,
):
    return api_get(
        session,
        base_url,
        f"get_plan/{plan_id}",
        timeout=timeout,
        max_attempts=max_attempts,
        backoff=backoff,
    )


def get_cases(
    session,
    base_url,
    project_id: int,
    *,
    suite_id: int | None = None,
    section_id: int | None = None,
    timeout: float | None = None,
    max_attempts: int | None = None,
    backoff: float | None = None,
):
    """Return list of cases for a project (optionally filtered by suite/section)."""
    cases: list = []
    offset, limit = 0, 250
    while True:
        qs = [f"limit={limit}", f"offset={offset}"]
        if suite_id is not None:
            qs.append(f"suite_id={suite_id}")
        if section_id is not None:
            qs.append(f"section_id={section_id}")
        endpoint = f"get_cases/{project_id}&" + "&".join(qs)
        data = api_get(
            session,
            base_url,
            endpoint,
            timeout=timeout,
            max_attempts=max_attempts,
            backoff=backoff,
        )
        if not data:
            break
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("cases") or data.get("items") or []
        else:
            items = []
        cases.extend(items)
        if len(items) < limit:
            break
        offset += limit
    return cases


def get_users_map(
    session,
    base_url,
    *,
    timeout: float | None = None,
    max_attempts: int | None = None,
    backoff: float | None = None,
):
    try:
        users = api_get(
            session,
            base_url,
            "get_users",
            timeout=timeout,
            max_attempts=max_attempts,
            backoff=backoff,
        )
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


def get_user(
    session,
    base_url,
    user_id: int,
    *,
    timeout: float | None = None,
    max_attempts: int | None = None,
    backoff: float | None = None,
):
    try:
        return api_get(
            session,
            base_url,
            f"get_user/{user_id}",
            timeout=timeout,
            max_attempts=max_attempts,
            backoff=backoff,
        )
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 403:
            raise UserLookupForbidden("TestRail denied access to get_user") from e
        print(f"Warning: get_user({user_id}) failed: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Warning: get_user({user_id}) failed: {e}", file=sys.stderr)
        return None


def get_priorities_map(
    session,
    base_url,
    *,
    timeout: float | None = None,
    max_attempts: int | None = None,
    backoff: float | None = None,
):
    """Return {priority_id: priority_name} mapping."""
    try:
        items = api_get(
            session,
            base_url,
            "get_priorities",
            timeout=timeout,
            max_attempts=max_attempts,
            backoff=backoff,
        )
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


def get_statuses_map(
    session,
    base_url,
    *,
    timeout: float | None = None,
    max_attempts: int | None = None,
    backoff: float | None = None,
    defaults: dict | None = None,
):
    """Return {status_id: status_name} mapping from TestRail."""
    try:
        items = api_get(
            session,
            base_url,
            "get_statuses",
            timeout=timeout,
            max_attempts=max_attempts,
            backoff=backoff,
        )
        mapping = {}
        if isinstance(items, list):
            for s in items:
                sid = s.get("id")
                if sid is None:
                    continue
                name = s.get("name") or str(sid)
                mapping[int(sid)] = name
        if defaults:
            for k, v in defaults.items():
                mapping[k] = v
        return mapping
    except Exception as e:
        print(f"Warning: could not load statuses: {e}", file=sys.stderr)
        return (defaults or {}).copy()


def get_plan_runs(
    session,
    base_url,
    plan_id: int,
    *,
    timeout: float | None = None,
    max_attempts: int | None = None,
    backoff: float | None = None,
):
    plan = api_get(
        session,
        base_url,
        f"get_plan/{plan_id}",
        timeout=timeout,
        max_attempts=max_attempts,
        backoff=backoff,
    )
    runs = []
    for entry in plan.get("entries", []):
        for run in entry.get("runs", []):
            runs.append(run["id"])
    if not runs:
        print(f"Warning: No runs found in plan {plan_id}", file=sys.stderr)
    return runs


def get_results_for_run(
    session,
    base_url,
    run_id: int,
    *,
    timeout: float | None = None,
    max_attempts: int | None = None,
    backoff: float | None = None,
):
    results = []
    offset, limit = 0, 250
    while True:
        try:
            batch = api_get(
                session,
                base_url,
                f"get_results_for_run/{run_id}&limit={limit}&offset={offset}",
                timeout=timeout,
                max_attempts=max_attempts,
                backoff=backoff,
            )
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
            print(
                f"Warning: Unexpected payload for results (run {run_id}): {type(batch)} "
                f"keys={list(batch.keys()) if isinstance(batch, dict) else 'n/a'}",
                file=sys.stderr,
            )
            break
        results.extend(items)
        if len(items) < limit:
            break
        offset += limit
    return results


def get_tests_for_run(
    session,
    base_url,
    run_id: int,
    *,
    timeout: float | None = None,
    max_attempts: int | None = None,
    backoff: float | None = None,
):
    tests = []
    offset, limit = 0, 250
    while True:
        try:
            batch = api_get(
                session,
                base_url,
                f"get_tests/{run_id}&limit={limit}&offset={offset}",
                timeout=timeout,
                max_attempts=max_attempts,
                backoff=backoff,
            )
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
            print(
                f"Warning: Unexpected payload for tests (run {run_id}): {type(batch)} "
                f"keys={list(batch.keys()) if isinstance(batch, dict) else 'n/a'}",
                file=sys.stderr,
            )
            break
        tests.extend(items)
        if len(items) < limit:
            break
        offset += limit
    return tests


def get_plans_for_project(
    session,
    base_url,
    project_id: int,
    *,
    is_completed: int | None = None,
    created_after: int | None = None,
    created_before: int | None = None,
    timeout: float | None = None,
    max_attempts: int | None = None,
    backoff: float | None = None,
) -> list:
    """Return list of plans for a project."""
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
            batch = api_get(
                session,
                base_url,
                endpoint,
                timeout=timeout,
                max_attempts=max_attempts,
                backoff=backoff,
            )
        except Exception:
            break
        if not batch:
            break
        if isinstance(batch, list):
            items = batch
        elif isinstance(batch, dict):
            items = batch.get("plans") or batch.get("items") or []
        else:
            items = []
        plans.extend(items)
        if len(items) < limit:
            break
        offset += limit
    return plans


def get_attachments_for_test(
    session,
    base_url,
    test_id: int,
    *,
    timeout: float | None = None,
    max_attempts: int | None = None,
    backoff: float | None = None,
):
    try:
        data = api_get(
            session,
            base_url,
            f"get_attachments_for_test/{test_id}",
            timeout=timeout,
            max_attempts=max_attempts,
            backoff=backoff,
        )
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # Some instances may wrap in dict
            return data.get("attachments", [])
        return []
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return []
        print(
            f"Warning: attachments fetch failed for test {test_id}: {e}",
            file=sys.stderr,
        )
        return []
    except Exception as e:
        print(
            f"Warning: attachments fetch failed for test {test_id}: {e}",
            file=sys.stderr,
        )
        return []


def download_attachment(
    session,
    base_url,
    attachment_id: int,
    *,
    max_retries: int = 4,
    size_limit: int | None = None,
    timeout: float | None = None,
    backoff: float | None = None,
):
    """Download an attachment with timeout/backoff."""
    url = f"{base_url}/index.php?/api/v2/get_attachment/{attachment_id}"
    start = time.perf_counter()
    backoff_delay = backoff if backoff is not None else max(1.0, DEFAULT_HTTP_BACKOFF)
    attempt = 0
    while True:
        try:
            with session.get(
                url, stream=True, timeout=timeout or DEFAULT_HTTP_TIMEOUT
            ) as r:
                if r.status_code == 429:
                    retry_after = r.headers.get("Retry-After")
                    wait_for = backoff_delay
                    try:
                        if retry_after:
                            wait_for = max(backoff_delay, float(retry_after))
                    except Exception:
                        wait_for = backoff_delay
                    attempt += 1
                    if attempt > max_retries:
                        r.raise_for_status()
                    time.sleep(wait_for)
                    backoff_delay *= 1.8
                    continue
                r.raise_for_status()
                content_type = r.headers.get("Content-Type")
                # Write to a temp file to avoid holding full content in memory
                fd, tmp_path = tempfile.mkstemp(
                    prefix=f"att_{attachment_id}_", suffix=".bin"
                )
                tmp = Path(tmp_path)
                try:
                    bytes_downloaded = 0
                    with os.fdopen(fd, "wb") as f:
                        for chunk in r.iter_content(chunk_size=64 * 1024):
                            if not chunk:
                                continue
                            bytes_downloaded += len(chunk)
                            if (
                                size_limit
                                and size_limit > 0
                                and bytes_downloaded > size_limit
                            ):
                                raise AttachmentTooLarge(bytes_downloaded, size_limit)
                            f.write(chunk)
                except AttachmentTooLarge:
                    try:
                        tmp.unlink(missing_ok=True)
                    except Exception:
                        pass
                    raise
                record_api_call(
                    "GET",
                    f"get_attachment/{attachment_id}",
                    (time.perf_counter() - start) * 1000.0,
                    "ok",
                )
                return tmp, content_type
        except AttachmentTooLarge as exc:
            record_api_call(
                "GET",
                f"get_attachment/{attachment_id}",
                (time.perf_counter() - start) * 1000.0,
                "error",
                str(exc),
            )
            raise
        except Exception as exc:
            attempt += 1
            if attempt >= max_retries:
                record_api_call(
                    "GET",
                    f"get_attachment/{attachment_id}",
                    (time.perf_counter() - start) * 1000.0,
                    "error",
                    str(exc),
                )
                raise
            time.sleep(backoff_delay)
            backoff_delay *= 1.8


@dataclass(slots=True)
class TestRailClient:
    """Centralized TestRail client with shared timeout/retry config."""

    base_url: str
    auth: tuple[str, str]
    timeout: float = DEFAULT_HTTP_TIMEOUT
    max_attempts: int = DEFAULT_HTTP_RETRIES
    backoff: float = DEFAULT_HTTP_BACKOFF

    def make_session(self) -> requests.Session:
        sess = requests.Session()
        sess.auth = self.auth
        return sess

    def get_project(self, project_id: int):
        with self.make_session() as session:
            return get_project(
                session,
                self.base_url,
                project_id,
                timeout=self.timeout,
                max_attempts=self.max_attempts,
                backoff=self.backoff,
            )

    def get_plan(self, plan_id: int):
        with self.make_session() as session:
            return get_plan(
                session,
                self.base_url,
                plan_id,
                timeout=self.timeout,
                max_attempts=self.max_attempts,
                backoff=self.backoff,
            )

    def get_plan_runs(self, plan_id: int):
        with self.make_session() as session:
            return get_plan_runs(
                session,
                self.base_url,
                plan_id,
                timeout=self.timeout,
                max_attempts=self.max_attempts,
                backoff=self.backoff,
            )

    def get_tests_for_run(self, run_id: int):
        with self.make_session() as session:
            return get_tests_for_run(
                session,
                self.base_url,
                run_id,
                timeout=self.timeout,
                max_attempts=self.max_attempts,
                backoff=self.backoff,
            )

    def get_results_for_run(self, run_id: int):
        with self.make_session() as session:
            return get_results_for_run(
                session,
                self.base_url,
                run_id,
                timeout=self.timeout,
                max_attempts=self.max_attempts,
                backoff=self.backoff,
            )

    def get_plans_for_project(
        self, project_id: int, *, is_completed: int | None = None
    ):
        with self.make_session() as session:
            return get_plans_for_project(
                session,
                self.base_url,
                project_id,
                is_completed=is_completed,
                timeout=self.timeout,
                max_attempts=self.max_attempts,
                backoff=self.backoff,
            )

    def get_users_map(self):
        with self.make_session() as session:
            return get_users_map(
                session,
                self.base_url,
                timeout=self.timeout,
                max_attempts=self.max_attempts,
                backoff=self.backoff,
            )

    def get_user(self, user_id: int):
        with self.make_session() as session:
            return get_user(
                session,
                self.base_url,
                user_id,
                timeout=self.timeout,
                max_attempts=self.max_attempts,
                backoff=self.backoff,
            )

    def get_priorities_map(self):
        with self.make_session() as session:
            return get_priorities_map(
                session,
                self.base_url,
                timeout=self.timeout,
                max_attempts=self.max_attempts,
                backoff=self.backoff,
            )

    def get_statuses_map(self, defaults: dict | None = None):
        with self.make_session() as session:
            return get_statuses_map(
                session,
                self.base_url,
                timeout=self.timeout,
                max_attempts=self.max_attempts,
                backoff=self.backoff,
                defaults=defaults,
            )

    def get_attachments_for_test(self, test_id: int):
        with self.make_session() as session:
            return get_attachments_for_test(
                session,
                self.base_url,
                test_id,
                timeout=self.timeout,
                max_attempts=self.max_attempts,
                backoff=self.backoff,
            )

    def get_cases(
        self,
        project_id: int,
        suite_id: int | None = None,
        section_id: int | None = None,
    ):
        with self.make_session() as session:
            return get_cases(
                session,
                self.base_url,
                project_id,
                suite_id=suite_id,
                section_id=section_id,
                timeout=self.timeout,
                max_attempts=self.max_attempts,
                backoff=self.backoff,
            )

    def download_attachment(
        self, attachment_id: int, *, size_limit: int | None = None, max_retries: int = 4
    ):
        with self.make_session() as session:
            return download_attachment(
                session,
                self.base_url,
                attachment_id,
                max_retries=max_retries,
                size_limit=size_limit,
                timeout=self.timeout,
                backoff=self.backoff,
            )

    # Write operations
    def add_plan(self, project_id: int, payload: dict[str, Any]):
        with self.make_session() as session:
            return api_post(
                session,
                self.base_url,
                f"add_plan/{project_id}",
                payload,
                timeout=self.timeout,
                max_attempts=self.max_attempts,
                backoff=self.backoff,
            )

    def add_run(self, project_id: int, payload: dict[str, Any]):
        with self.make_session() as session:
            return api_post(
                session,
                self.base_url,
                f"add_run/{project_id}",
                payload,
                timeout=self.timeout,
                max_attempts=self.max_attempts,
                backoff=self.backoff,
            )

    def add_plan_entry(self, plan_id: int, payload: dict[str, Any]):
        with self.make_session() as session:
            return api_post(
                session,
                self.base_url,
                f"add_plan_entry/{plan_id}",
                payload,
                timeout=self.timeout,
                max_attempts=self.max_attempts,
                backoff=self.backoff,
            )

    def add_case(self, section_id: int, payload: dict[str, Any]):
        with self.make_session() as session:
            return api_post(
                session,
                self.base_url,
                f"add_case/{section_id}",
                payload,
                timeout=self.timeout,
                max_attempts=self.max_attempts,
                backoff=self.backoff,
            )
