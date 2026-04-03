from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import app.main as main_app
from app.bootstrap import AgentOSAssembleConfig, assemble_runtime
from app.config import load_config
from app.evolution import EvolutionStore
from app.storage import SessionStore, ShadowLogStore, TokenStatsStore, UploadStore


def test_chat_endpoint_prefers_plugin_orchestrator_path(monkeypatch, tmp_path: Path) -> None:
    for name in ("sessions", "uploads", "shadow_logs", "evolution_logs"):
        (tmp_path / name).mkdir(parents=True, exist_ok=True)

    runtime = assemble_runtime(
        load_config(),
        assemble_config=AgentOSAssembleConfig(
            include_research_module=True,
            include_coding_module=True,
            include_adaptation_module=True,
            enable_session_provider=True,
        ),
    )

    monkeypatch.setattr(main_app, "agent_os_runtime", runtime)
    monkeypatch.setattr(main_app, "session_store", SessionStore(tmp_path / "sessions"))
    monkeypatch.setattr(main_app, "upload_store", UploadStore(tmp_path / "uploads"))
    monkeypatch.setattr(main_app, "token_stats_store", TokenStatsStore(tmp_path / "token_stats.json"))
    monkeypatch.setattr(main_app, "shadow_log_store", ShadowLogStore(tmp_path / "shadow_logs"))
    monkeypatch.setattr(
        main_app,
        "evolution_store",
        EvolutionStore(tmp_path / "overlay_profile.json", tmp_path / "evolution_logs"),
    )
    monkeypatch.setattr(
        main_app.OpenAIAuthManager,
        "auth_summary",
        lambda self: {"available": True, "reason": "", "mode": "test"},
    )

    def _fake_orchestration(**kwargs):
        _ = kwargs
        return {
            "text": "插件编排主链路结果",
            "selected_module_id": "researcher_agent",
            "kernel_routing": {
                "mode": "plugin_orchestrator_v1",
                "selection_summary": "router_agent -> researcher_agent",
            },
            "tool_events": [],
            "attachment_note": "",
            "execution_plan": ["router_agent -> researcher_agent", "1. planner_agent", "2. researcher_agent"],
            "execution_trace": ["中央调度路由: router_agent -> researcher_agent"],
            "pipeline_hooks": [],
            "debug_flow": [],
            "agent_panels": [],
            "active_roles": ["planner_agent", "researcher_agent"],
            "current_role": "researcher_agent",
            "role_states": [
                {"role": "planner_agent", "status": "done", "phase": "completed", "detail": ""},
                {"role": "researcher_agent", "status": "done", "phase": "completed", "detail": ""},
            ],
            "answer_bundle": {"summary": "插件编排主链路结果", "claims": [], "citations": [], "warnings": []},
            "token_usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30, "llm_calls": 2},
            "effective_model": "gpt-test",
            "route_state": {},
            "business_result": {"mode": "plugin_orchestrator_v1", "target_agent": "researcher_agent"},
        }

    monkeypatch.setattr(main_app, "_run_main_chat_plugin_orchestration", _fake_orchestration)

    client = TestClient(main_app.app)
    response = client.post(
        "/api/chat",
        json={
            "message": "给我今天的互联网新闻，并附上主要来源。",
            "settings": {
                "model": "gpt-test",
                "max_output_tokens": 1024,
                "max_context_turns": 20,
                "enable_tools": True,
                "response_style": "short",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["selected_business_module"] == "researcher_agent"
    assert payload["kernel_routing"]["mode"] == "plugin_orchestrator_v1"
    assert payload["business_result"]["mode"] == "plugin_orchestrator_v1"
    assert any("router_agent -> researcher_agent" in item for item in payload["execution_trace"])
