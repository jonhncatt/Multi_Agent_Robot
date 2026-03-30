from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import app.main as main_app
from app.bootstrap import AgentOSAssembleConfig, assemble_runtime
from app.config import load_config
from app.evolution import EvolutionStore
from app.storage import SessionStore, ShadowLogStore, TokenStatsStore, UploadStore
from tests.support_agent_os import bind_fake_research_provider


def test_chat_endpoint_auto_selects_research_module(monkeypatch, tmp_path: Path) -> None:
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
    bind_fake_research_provider(runtime)

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

    client = TestClient(main_app.app)
    response = client.post(
        "/api/chat",
        json={
            "message": "给我今天的互联网新闻，并附上主要来源。",
            "settings": {
                "model": None,
                "max_output_tokens": 1024,
                "max_context_turns": 20,
                "enable_tools": True,
                "response_style": "short",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "Research module gathered" in payload["text"]
    assert any("research_module" in item for item in payload["execution_trace"])
