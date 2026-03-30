from __future__ import annotations

from app.contracts import ModuleManifest, TaskRequest
from app.kernel.host import KernelHost
from tests.support_agent_os import EchoBusinessModule


def _register_business_modules(kernel: KernelHost, *, coding_healthy: bool = True) -> None:
    kernel.register_module(
        EchoBusinessModule(
            manifest=ModuleManifest(
                module_id="office_module",
                module_kind="business",
                version="1.0.0",
                description="office",
                capabilities=["task.chat", "task.office"],
            ),
            text="office",
        )
    )
    kernel.register_module(
        EchoBusinessModule(
            manifest=ModuleManifest(
                module_id="research_module",
                module_kind="business",
                version="1.0.0",
                description="research",
                capabilities=["task.research", "task.investigation"],
            ),
            text="research",
        )
    )
    kernel.register_module(
        EchoBusinessModule(
            manifest=ModuleManifest(
                module_id="coding_module",
                module_kind="business",
                version="0.1.0",
                description="coding",
                capabilities=["task.coding"],
            ),
            text="coding",
            healthy=coding_healthy,
        )
    )
    kernel.register_module(
        EchoBusinessModule(
            manifest=ModuleManifest(
                module_id="adaptation_module",
                module_kind="business",
                version="0.1.0",
                description="adaptation",
                capabilities=["task.adaptation"],
            ),
            text="adaptation",
            healthy=False,
        )
    )
    kernel.init()


def test_explicit_module_id_wins_over_auto_selection() -> None:
    kernel = KernelHost()
    _register_business_modules(kernel)

    decision = kernel.select_module(
        TaskRequest(task_id="req-1", task_type="chat", message="请调研今天的互联网新闻并附上来源"),
        module_id="office_module",
    )

    assert decision.module_id == "office_module"
    assert decision.selection_mode == "explicit_module_id"


def test_chat_request_with_research_signals_selects_research_module() -> None:
    kernel = KernelHost()
    _register_business_modules(kernel)

    decision = kernel.select_module(
        TaskRequest(
            task_id="req-2",
            task_type="chat",
            message="请调研今天的互联网新闻，并附上主要来源和证据。",
        )
    )

    assert decision.module_id == "research_module"
    assert decision.selection_mode == "auto_intent"
    assert decision.candidate_scores["research_module"] > decision.candidate_scores["office_module"]


def test_chat_request_with_attachments_keeps_office_module() -> None:
    kernel = KernelHost()
    _register_business_modules(kernel)

    decision = kernel.select_module(
        TaskRequest(
            task_id="req-3",
            task_type="chat",
            message="帮我整理这个附件并写一封回复邮件。",
            attachments=[{"id": "att-1", "name": "brief.pdf"}],
        )
    )

    assert decision.module_id == "office_module"
    assert decision.candidate_scores["office_module"] >= decision.candidate_scores.get("research_module", 0.0)


def test_auto_selection_does_not_route_into_unhealthy_skeleton_module() -> None:
    kernel = KernelHost()
    _register_business_modules(kernel, coding_healthy=False)

    decision = kernel.select_module(
        TaskRequest(
            task_id="req-4",
            task_type="chat",
            message="帮我修一下这个 Python bug，并给出 patch。",
        )
    )

    assert decision.module_id == "office_module"
    assert "coding_module" not in decision.candidate_scores


def test_explicit_task_type_still_routes_to_coding_module() -> None:
    kernel = KernelHost()
    _register_business_modules(kernel, coding_healthy=False)

    decision = kernel.select_module(
        TaskRequest(
            task_id="req-5",
            task_type="task.coding",
            message="fix this bug",
        )
    )

    assert decision.module_id == "coding_module"
    assert decision.selection_mode == "explicit_task_type"
