from __future__ import annotations

from typing import Any

from app.contracts import HealthReport, ToolCall, ToolResult
from app.system_modules.tool_runtime_module.manifest import TOOL_RUNTIME_MODULE_MANIFEST


class ToolRuntimeModule:
    manifest = TOOL_RUNTIME_MODULE_MANIFEST

    def __init__(self) -> None:
        self._kernel_context: Any = None

    def init(self, kernel_context: Any) -> None:
        self._kernel_context = kernel_context

    def health_check(self) -> HealthReport:
        provider_count = 0
        try:
            provider_count = len(self._kernel_context.registry.list_providers()) if self._kernel_context else 0
        except Exception:
            provider_count = 0
        return HealthReport(
            component_id=self.manifest.module_id,
            status="healthy",
            summary="tool runtime active",
            details={"provider_count": provider_count},
        )

    def shutdown(self) -> None:
        return None

    def execute(self, call: ToolCall) -> ToolResult:
        if self._kernel_context is None:
            return ToolResult(
                ok=False,
                tool_name=call.name,
                provider_id="",
                error="tool runtime module not initialized",
            )
        return self._kernel_context.tool_bus.execute(call)
