import types

from fastapi.testclient import TestClient

import app.main as main


def test_manage_plan_requires_write_flag(monkeypatch):
    """Test that manage plan endpoint works when write is enabled."""
    api = TestClient(main.app)
    fake = types.SimpleNamespace()

    def add_plan(project_id, payload):
        return {"id": 999, "name": payload["name"]}

    fake.add_plan = add_plan
    monkeypatch.setattr(main, "_make_client", lambda: fake)
    monkeypatch.setattr(main, "_write_enabled", lambda: True)

    resp = api.post("/api/manage/plan", json={"project": 1, "name": "X"})
    assert resp.status_code in (200, 201)


def test_manage_plan_creates_with_fake_client(monkeypatch):
    api = TestClient(main.app)
    fake = types.SimpleNamespace()
    called = {}

    def add_plan(project_id, payload):
        called["project"] = project_id
        called["payload"] = payload
        return {"id": 123}

    fake.add_plan = add_plan
    monkeypatch.setattr(main, "_make_client", lambda: fake)
    monkeypatch.setattr(main, "_write_enabled", lambda: True)

    resp = api.post(
        "/api/manage/plan",
        json={"project": 2, "name": "My Plan", "description": "desc"},
    )
    assert resp.status_code == 200
    assert resp.json().get("plan", {}).get("id") == 123
    assert called["project"] == 2
    assert called["payload"]["name"] == "My Plan"


def test_manage_run_targets_plan_entry(monkeypatch):
    api = TestClient(main.app)
    fake = types.SimpleNamespace()
    called = {}

    def add_plan_entry(plan_id, payload):
        called["plan_id"] = plan_id
        called["payload"] = payload
        return {"id": 55}

    fake.add_plan_entry = add_plan_entry
    monkeypatch.setattr(main, "_make_client", lambda: fake)
    monkeypatch.setattr(main, "_write_enabled", lambda: True)
    monkeypatch.setattr(main, "_default_suite_id", lambda: 1)

    resp = api.post(
        "/api/manage/run",
        json={"project": 1, "plan_id": 99, "name": "Run", "include_all": True},
    )
    assert resp.status_code == 200
    assert resp.json().get("run", {}).get("id") == 55
    assert called["plan_id"] == 99
    assert called["payload"]["suite_id"] == 1


def test_manage_case_calls_client(monkeypatch):
    api = TestClient(main.app)
    fake = types.SimpleNamespace()
    called = {}

    def add_case(section_id, payload):
        called["section_id"] = section_id
        called["payload"] = payload
        return {"id": 777}

    fake.add_case = add_case
    monkeypatch.setattr(main, "_make_client", lambda: fake)
    monkeypatch.setattr(main, "_write_enabled", lambda: True)
    monkeypatch.setattr(main, "_default_section_id", lambda: 6)
    monkeypatch.setattr(main, "_default_template_id", lambda: 4)
    monkeypatch.setattr(main, "_default_type_id", lambda: 7)
    monkeypatch.setattr(main, "_default_priority_id", lambda: 2)

    resp = api.post(
        "/api/manage/case",
        json={
            "project": 1,
            "title": "Case title",
            "bdd_scenarios": "Given\nWhen\nThen",
        },
    )
    assert resp.status_code == 200
    assert resp.json().get("case", {}).get("id") == 777
    assert called["section_id"] == 6
    assert called["payload"]["title"] == "Case title"
    assert called["payload"]["template_id"] == 4
    assert called["payload"]["type_id"] == 7
    assert called["payload"]["priority_id"] == 2
    assert called["payload"]["custom_testrail_bdd_scenario"] == [{"content": "Given\nWhen\nThen"}]
