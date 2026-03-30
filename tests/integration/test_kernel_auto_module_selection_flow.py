from __future__ import annotations

from app.bootstrap import AgentOSAssembleConfig, assemble_runtime
from app.config import load_config
from app.contracts import TaskRequest
from tests.support_agent_os import DummyLegacyHost, bind_fake_research_provider


def test_kernel_auto_selects_research_module_for_research_like_chat() -> None:
    runtime = assemble_runtime(
        load_config(),
        legacy_host=DummyLegacyHost(),
        assemble_config=AgentOSAssembleConfig(
            include_research_module=True,
            include_coding_module=True,
            include_adaptation_module=True,
            enable_session_provider=True,
        ),
    )
    bind_fake_research_provider(runtime)

    response = runtime.dispatch(
        TaskRequest(
            task_id="auto-research-1",
            task_type="chat",
            message="给我今天的互联网新闻，并附上主要来源。",
            context={"session_id": "auto-research"},
        )
    )

    assert response.ok is True
    assert response.payload["module_id"] == "research_module"
    assert response.payload["kernel_routing"]["selection_mode"] == "auto_intent"
    trace = runtime.kernel.health_snapshot()["recent_traces"][-1]
    assert trace["module_id"] == "research_module"
    assert any(event["stage"] == "module_selection" for event in trace["events"])


def test_kernel_auto_selection_keeps_office_module_for_attachment_workflow() -> None:
    runtime = assemble_runtime(
        load_config(),
        legacy_host=DummyLegacyHost(),
        assemble_config=AgentOSAssembleConfig(
            include_research_module=True,
            include_coding_module=True,
            include_adaptation_module=True,
            enable_session_provider=True,
        ),
    )
    bind_fake_research_provider(runtime)

    response = runtime.dispatch(
        TaskRequest(
            task_id="auto-office-1",
            task_type="chat",
            message="帮我整理附件内容并写一封回复邮件。",
            attachments=[{"id": "att-1", "name": "brief.pdf"}],
            context={"session_id": "auto-office"},
        )
    )

    assert response.ok is True
    assert response.payload["module_id"] == "office_module"
    assert response.payload["kernel_routing"]["module_id"] == "office_module"
