import types
from unittest.mock import Mock

from fastapi.testclient import TestClient

import app.main as main
from app.core.dependencies import get_testrail_client, require_write_enabled


def test_manage_plan_requires_write_flag(monkeypatch):
    """Test that manage plan endpoint works when write is enabled."""
    api = TestClient(main.app)
    fake = Mock()

    def add_plan(project_id, payload):
        return {"id": 999, "name": payload["name"]}

    fake.add_plan = add_plan

    # Override dependencies
    main.app.dependency_overrides[get_testrail_client] = lambda: fake
    main.app.dependency_overrides[require_write_enabled] = lambda: True

    try:
        resp = api.post("/api/manage/plan", json={"project": 1, "name": "X"})
        assert resp.status_code in (200, 201)
    finally:
        main.app.dependency_overrides.clear()


def test_manage_plan_creates_with_fake_client(monkeypatch):
    api = TestClient(main.app)
    fake = Mock()
    called = {}

    def add_plan(project_id, payload):
        called["project"] = project_id
        called["payload"] = payload
        return {"id": 123}

    fake.add_plan = add_plan

    # Override dependencies
    main.app.dependency_overrides[get_testrail_client] = lambda: fake
    main.app.dependency_overrides[require_write_enabled] = lambda: True

    try:
        resp = api.post(
            "/api/manage/plan",
            json={"project": 2, "name": "My Plan", "description": "desc"},
        )
        assert resp.status_code == 200
        assert resp.json().get("plan", {}).get("id") == 123
        assert called["project"] == 2
        assert called["payload"]["name"] == "My Plan"
    finally:
        main.app.dependency_overrides.clear()


def test_manage_run_targets_plan_entry(monkeypatch):
    api = TestClient(main.app)
    fake = Mock()
    called = {}

    def add_plan_entry(plan_id, payload):
        called["plan_id"] = plan_id
        called["payload"] = payload
        return {"id": 55}

    fake.add_plan_entry = add_plan_entry

    # Override dependencies
    main.app.dependency_overrides[get_testrail_client] = lambda: fake
    main.app.dependency_overrides[require_write_enabled] = lambda: True

    # Mock config values
    from app.core.config import config

    monkeypatch.setattr(config, "DEFAULT_SUITE_ID", 1)

    try:
        resp = api.post(
            "/api/manage/run",
            json={"project": 1, "plan_id": 99, "name": "Run", "include_all": True},
        )
        assert resp.status_code == 200
        assert resp.json().get("run", {}).get("id") == 55
        assert called["plan_id"] == 99
        assert called["payload"]["suite_id"] == 1
    finally:
        main.app.dependency_overrides.clear()


def test_manage_case_calls_client(monkeypatch):
    api = TestClient(main.app)
    fake = Mock()
    called = {}

    def add_case(section_id, payload):
        called["section_id"] = section_id
        called["payload"] = payload
        return {"id": 777}

    fake.add_case = add_case

    # Override dependencies
    main.app.dependency_overrides[get_testrail_client] = lambda: fake
    main.app.dependency_overrides[require_write_enabled] = lambda: True

    # Mock config values
    from app.core.config import config

    monkeypatch.setattr(config, "DEFAULT_SECTION_ID", 6)
    monkeypatch.setattr(config, "DEFAULT_TEMPLATE_ID", 4)
    monkeypatch.setattr(config, "DEFAULT_TYPE_ID", 7)
    monkeypatch.setattr(config, "DEFAULT_PRIORITY_ID", 2)

    try:
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
    finally:
        main.app.dependency_overrides.clear()
