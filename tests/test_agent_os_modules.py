from __future__ import annotations

from typing import Any

from app.bootstrap import AgentOSAssembleConfig, assemble_runtime
from app.config import load_config
from app.contracts import TaskRequest


class DummyLegacyHost:
    def run_chat(self, *args: Any, **kwargs: Any) -> tuple[Any, ...]:
        _ = args, kwargs
        return (
            "dummy response",
            [],
            "",
            [],
            [],
            [],
            [],
            [],
            ["router", "planner", "worker"],
            "worker",
            [],
            {},
            {},
            "gpt-test",
            {},
        )


def test_modules_init_invoke_and_health() -> None:
    cfg = load_config()
    runtime = assemble_runtime(
        cfg,
        legacy_host=DummyLegacyHost(),
        assemble_config=AgentOSAssembleConfig(
            include_research_module=True,
            include_coding_module=True,
            include_adaptation_module=True,
            enable_session_provider=False,
        ),
    )

    snapshot = runtime.kernel.health_snapshot()
    assert snapshot["ok"] is True

    system_ids = {item.manifest.module_id for item in runtime.kernel.registry.list_modules(kind="system")}
    assert {"memory_module", "output_module", "tool_runtime_module", "policy_module"} <= system_ids

    office_resp = runtime.kernel.invoke(
        "office_module",
        TaskRequest(
            task_id="t-office",
            task_type="chat",
            message="hello",
            context={"history_turns": [], "summary": "", "session_id": "s-1"},
        ),
    )
    assert office_resp.ok is True
    assert office_resp.text == "dummy response"

    for module_id in ("research_module", "coding_module", "adaptation_module"):
        resp = runtime.kernel.invoke(
            module_id,
            TaskRequest(task_id=f"t-{module_id}", task_type="test", message="ping"),
        )
        assert resp.ok is False
        assert "not implemented yet" in resp.error

