from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.contracts import HealthReport, ModuleManifest, TaskRequest, TaskResponse, ToolCall, ToolResult
from app.kernel.host import KernelHost


@dataclass
class EchoBusinessModule:
    manifest: ModuleManifest
    text: str
    healthy: bool = True

    def init(self, kernel_context: Any) -> None:
        self._kernel_context = kernel_context

    def health_check(self) -> HealthReport:
        return HealthReport(
            component_id=self.manifest.module_id,
            status="healthy" if self.healthy else "unhealthy",
            summary="ok" if self.healthy else "bad",
        )

    def shutdown(self) -> None:
        return None

    def invoke(self, request: TaskRequest) -> TaskResponse:
        return TaskResponse(ok=True, task_id=request.task_id, text=self.text)


class BrokenProvider:
    provider_id = "broken_provider"
    supported_tools = ["tool.primary"]

    def execute(self, call: ToolCall) -> ToolResult:
        raise RuntimeError(f"boom:{call.name}")

    def health_check(self) -> HealthReport:
        return HealthReport(component_id=self.provider_id, status="degraded", summary="simulated failure")


class FallbackProvider:
    provider_id = "fallback_provider"
    supported_tools = ["tool.fallback"]

    def execute(self, call: ToolCall) -> ToolResult:
        return ToolResult(ok=True, tool_name=call.name, provider_id=self.provider_id, data={"ok": True, "value": 1})

    def health_check(self) -> HealthReport:
        return HealthReport(component_id=self.provider_id, status="healthy", summary="ok")


def test_provider_failure_isolation_with_fallback() -> None:
    kernel = KernelHost()
    kernel.register_provider(BrokenProvider())
    kernel.register_provider(FallbackProvider())
    result = kernel.tool_bus.execute(ToolCall(name="tool.primary", fallback_tools=["tool.fallback"]))
    assert result.ok is True
    assert result.fallback_used is True
    assert result.provider_id == "fallback_provider"

    snapshot = kernel.health_snapshot()
    assert snapshot["ok"] is True
    assert snapshot["initialized"] is False


def test_hot_swap_and_rollback_module() -> None:
    kernel = KernelHost()
    module_v1 = EchoBusinessModule(
        manifest=ModuleManifest(
            module_id="demo_module",
            module_kind="business",
            version="1.0.0",
            description="demo",
        ),
        text="v1",
    )
    module_v2 = EchoBusinessModule(
        manifest=ModuleManifest(
            module_id="demo_module",
            module_kind="business",
            version="1.1.0",
            description="demo",
        ),
        text="v2",
    )

    kernel.register_module(module_v1)
    kernel.init()
    resp_v1 = kernel.invoke("demo_module", TaskRequest(task_id="1", task_type="test", message="ping"))
    assert resp_v1.text == "v1"

    swap = kernel.hot_swap_module(module_v2)
    assert swap["ok"] is True
    assert swap["active_version"] == "1.1.0"
    resp_v2 = kernel.invoke("demo_module", TaskRequest(task_id="2", task_type="test", message="ping"))
    assert resp_v2.text == "v2"

    rollback = kernel.rollback_module("demo_module")
    assert rollback["ok"] is True
    assert rollback["active_version"] == "1.0.0"
    resp_back = kernel.invoke("demo_module", TaskRequest(task_id="3", task_type="test", message="ping"))
    assert resp_back.text == "v1"

