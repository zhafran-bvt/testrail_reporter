
import requests

from testrail_client import (
    AttachmentTooLarge,
    api_get,
    capture_telemetry,
    download_attachment,
)


def test_api_get_retries_on_429(monkeypatch):
    calls = []
    monkeypatch.setattr("time.sleep", lambda _x: None)

    class FakeResponse:
        def __init__(self, status_code, payload=None, headers=None):
            self.status_code = status_code
            self._payload = payload or {}
            self.headers = headers or {}

        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.exceptions.HTTPError(response=self)

        def json(self):
            return self._payload

    class FakeSession:
        def __init__(self, responses):
            self._responses = iter(responses)

        def get(self, url, timeout=None):
            calls.append(timeout)
            return next(self._responses)

    resp_429 = FakeResponse(429, headers={"Retry-After": "0"})
    resp_ok = FakeResponse(200, {"ok": True})
    session = FakeSession([resp_429, resp_ok])

    with capture_telemetry() as telemetry:
        data = api_get(
            session, "http://x", "get_stuff", timeout=1, max_attempts=2, backoff=0
        )

    assert data == {"ok": True}
    assert calls == [1, 1]
    api_calls = telemetry.get("api_calls", [])
    assert len(api_calls) == 2
    assert api_calls[-1]["status"] == "ok"


def test_download_attachment_enforces_size_limit(monkeypatch, tmp_path):
    monkeypatch.setattr("time.sleep", lambda _x: None)

    class FakeStream:
        status_code = 200
        headers = {"Content-Type": "text/plain"}

        def __init__(self):
            self._iter = iter([b"a" * 4, b"b" * 4])

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size=8192):
            return self._iter

    class FakeSession:
        def get(self, url, stream=True, timeout=None):
            return FakeStream()

    session = FakeSession()
    base_url = "http://x"
    attachment_id = 123

    with capture_telemetry() as telemetry:
        try:
            download_attachment(
                session,
                base_url,
                attachment_id,
                size_limit=5,
                max_retries=1,
                timeout=1,
                backoff=0,
            )
        except AttachmentTooLarge as exc:
            assert exc.limit_bytes == 5
        else:
            raise AssertionError("Expected AttachmentTooLarge")

    api_calls = telemetry.get("api_calls", [])
    assert len(api_calls) == 1
    assert api_calls[0]["status"] == "error"
