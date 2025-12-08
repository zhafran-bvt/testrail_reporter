import requests

from testrail_client import (
    AttachmentTooLarge,
    TestRailClient,
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


# --- CRUD Method Tests ---


def test_update_plan_with_valid_data(monkeypatch):
    """Test update_plan with valid data returns updated plan."""
    calls = []

    def fake_api_post(session, base_url, endpoint, payload, **kwargs):
        calls.append(("POST", endpoint, payload))
        return {"id": 123, "name": "Updated Plan", "description": "New desc"}

    monkeypatch.setattr("testrail_client.api_post", fake_api_post)

    client = TestRailClient(
        base_url="http://test.testrail.io",
        auth=("user", "pass"),
        timeout=10,
        max_attempts=1,
        backoff=0,
    )

    payload = {"name": "Updated Plan", "description": "New desc"}
    result = client.update_plan(123, payload)

    assert result["id"] == 123
    assert result["name"] == "Updated Plan"
    assert len(calls) == 1
    assert calls[0][0] == "POST"
    assert "update_plan/123" in calls[0][1]
    assert calls[0][2] == payload


def test_update_plan_with_api_error(monkeypatch):
    """Test update_plan handles API errors appropriately."""

    def fake_api_post(session, base_url, endpoint, payload, **kwargs):
        raise requests.exceptions.HTTPError("Invalid plan ID")

    monkeypatch.setattr("testrail_client.api_post", fake_api_post)

    client = TestRailClient(
        base_url="http://test.testrail.io",
        auth=("user", "pass"),
        timeout=10,
        max_attempts=1,
        backoff=0,
    )

    payload = {"name": "Updated Plan"}
    try:
        client.update_plan(999, payload)
        assert False, "Expected HTTPError"
    except requests.exceptions.HTTPError:
        pass


def test_update_run_with_valid_data(monkeypatch):
    """Test update_run with valid data returns updated run."""
    calls = []

    def fake_api_post(session, base_url, endpoint, payload, **kwargs):
        calls.append(("POST", endpoint, payload))
        return {"id": 456, "name": "Updated Run", "description": "New run desc"}

    monkeypatch.setattr("testrail_client.api_post", fake_api_post)

    client = TestRailClient(
        base_url="http://test.testrail.io",
        auth=("user", "pass"),
        timeout=10,
        max_attempts=1,
        backoff=0,
    )

    payload = {"name": "Updated Run", "description": "New run desc"}
    result = client.update_run(456, payload)

    assert result["id"] == 456
    assert result["name"] == "Updated Run"
    assert len(calls) == 1
    assert "update_run/456" in calls[0][1]


def test_update_run_with_api_error(monkeypatch):
    """Test update_run handles API errors appropriately."""

    def fake_api_post(session, base_url, endpoint, payload, **kwargs):
        raise requests.exceptions.HTTPError("Run not found")

    monkeypatch.setattr("testrail_client.api_post", fake_api_post)

    client = TestRailClient(
        base_url="http://test.testrail.io",
        auth=("user", "pass"),
        timeout=10,
        max_attempts=1,
        backoff=0,
    )

    payload = {"name": "Updated Run"}
    try:
        client.update_run(999, payload)
        assert False, "Expected HTTPError"
    except requests.exceptions.HTTPError:
        pass


def test_update_case_with_valid_data(monkeypatch):
    """Test update_case with valid data returns updated case."""
    calls = []

    def fake_api_post(session, base_url, endpoint, payload, **kwargs):
        calls.append(("POST", endpoint, payload))
        return {"id": 789, "title": "Updated Case", "refs": "REF-123"}

    monkeypatch.setattr("testrail_client.api_post", fake_api_post)

    client = TestRailClient(
        base_url="http://test.testrail.io",
        auth=("user", "pass"),
        timeout=10,
        max_attempts=1,
        backoff=0,
    )

    payload = {"title": "Updated Case", "refs": "REF-123"}
    result = client.update_case(789, payload)

    assert result["id"] == 789
    assert result["title"] == "Updated Case"
    assert len(calls) == 1
    assert "update_case/789" in calls[0][1]


def test_update_case_with_api_error(monkeypatch):
    """Test update_case handles API errors appropriately."""

    def fake_api_post(session, base_url, endpoint, payload, **kwargs):
        raise requests.exceptions.HTTPError("Permission denied")

    monkeypatch.setattr("testrail_client.api_post", fake_api_post)

    client = TestRailClient(
        base_url="http://test.testrail.io",
        auth=("user", "pass"),
        timeout=10,
        max_attempts=1,
        backoff=0,
    )

    payload = {"title": "Updated Case"}
    try:
        client.update_case(999, payload)
        assert False, "Expected HTTPError"
    except requests.exceptions.HTTPError:
        pass


def test_delete_plan_with_valid_id(monkeypatch):
    """Test delete_plan with valid ID returns success."""
    calls = []

    def fake_api_post(session, base_url, endpoint, payload, **kwargs):
        calls.append(("POST", endpoint, payload))
        return {"success": True}

    monkeypatch.setattr("testrail_client.api_post", fake_api_post)

    client = TestRailClient(
        base_url="http://test.testrail.io",
        auth=("user", "pass"),
        timeout=10,
        max_attempts=1,
        backoff=0,
    )

    result = client.delete_plan(123)

    assert result["success"] is True
    assert len(calls) == 1
    assert "delete_plan/123" in calls[0][1]
    assert calls[0][2] == {}


def test_delete_plan_with_api_error(monkeypatch):
    """Test delete_plan handles API errors appropriately."""

    def fake_api_post(session, base_url, endpoint, payload, **kwargs):
        raise requests.exceptions.HTTPError("Plan not found")

    monkeypatch.setattr("testrail_client.api_post", fake_api_post)

    client = TestRailClient(
        base_url="http://test.testrail.io",
        auth=("user", "pass"),
        timeout=10,
        max_attempts=1,
        backoff=0,
    )

    try:
        client.delete_plan(999)
        assert False, "Expected HTTPError"
    except requests.exceptions.HTTPError:
        pass


def test_delete_run_with_valid_id(monkeypatch):
    """Test delete_run with valid ID returns success."""
    calls = []

    def fake_api_post(session, base_url, endpoint, payload, **kwargs):
        calls.append(("POST", endpoint, payload))
        return {"success": True}

    monkeypatch.setattr("testrail_client.api_post", fake_api_post)

    client = TestRailClient(
        base_url="http://test.testrail.io",
        auth=("user", "pass"),
        timeout=10,
        max_attempts=1,
        backoff=0,
    )

    result = client.delete_run(456)

    assert result["success"] is True
    assert len(calls) == 1
    assert "delete_run/456" in calls[0][1]
    assert calls[0][2] == {}


def test_delete_run_with_api_error(monkeypatch):
    """Test delete_run handles API errors appropriately."""

    def fake_api_post(session, base_url, endpoint, payload, **kwargs):
        raise requests.exceptions.HTTPError("Internal server error")

    monkeypatch.setattr("testrail_client.api_post", fake_api_post)

    client = TestRailClient(
        base_url="http://test.testrail.io",
        auth=("user", "pass"),
        timeout=10,
        max_attempts=1,
        backoff=0,
    )

    try:
        client.delete_run(999)
        assert False, "Expected HTTPError"
    except requests.exceptions.HTTPError:
        pass


def test_delete_case_with_valid_id(monkeypatch):
    """Test delete_case with valid ID returns success."""
    calls = []

    def fake_api_post(session, base_url, endpoint, payload, **kwargs):
        calls.append(("POST", endpoint, payload))
        return {"success": True}

    monkeypatch.setattr("testrail_client.api_post", fake_api_post)

    client = TestRailClient(
        base_url="http://test.testrail.io",
        auth=("user", "pass"),
        timeout=10,
        max_attempts=1,
        backoff=0,
    )

    result = client.delete_case(789)

    assert result["success"] is True
    assert len(calls) == 1
    assert "delete_case/789" in calls[0][1]
    assert calls[0][2] == {}


def test_delete_case_with_api_error(monkeypatch):
    """Test delete_case handles API errors appropriately."""

    def fake_api_post(session, base_url, endpoint, payload, **kwargs):
        raise requests.exceptions.HTTPError("Permission denied")

    monkeypatch.setattr("testrail_client.api_post", fake_api_post)

    client = TestRailClient(
        base_url="http://test.testrail.io",
        auth=("user", "pass"),
        timeout=10,
        max_attempts=1,
        backoff=0,
    )

    try:
        client.delete_case(999)
        assert False, "Expected HTTPError"
    except requests.exceptions.HTTPError:
        pass
