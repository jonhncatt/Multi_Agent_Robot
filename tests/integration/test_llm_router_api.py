from __future__ import annotations

from fastapi.testclient import TestClient

import app.main as main_app


def test_agents_list_and_reload_api() -> None:
    client = TestClient(main_app.app)
    listed = client.get("/api/agents")
    assert listed.status_code == 200
    payload = listed.json()
    assert int(payload.get("count") or 0) >= 12

    reloaded = client.post("/api/agents/worker_agent/reload")
    assert reloaded.status_code == 200
    assert bool(reloaded.json().get("ok")) is True


def test_chat_api_runs_via_llm_router(monkeypatch) -> None:
    monkeypatch.setattr(
        main_app.OpenAIAuthManager,
        "auth_summary",
        lambda self: {"available": True, "mode": "test", "reason": ""},
    )
    client = TestClient(main_app.app)
    response = client.post(
        "/api/chat",
        json={
            "message": "请做一个简单计划",
            "settings": {"enable_tools": True},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert str(payload.get("selected_business_module")) == "llm_router_core"

