from __future__ import annotations

from typing import Any

from app.contracts import HealthReport, TaskResponse
from app.system_modules.output_module.manifest import OUTPUT_MODULE_MANIFEST


class OutputModule:
    manifest = OUTPUT_MODULE_MANIFEST

    def __init__(self) -> None:
        self._kernel_context: Any = None

    def init(self, kernel_context: Any) -> None:
        self._kernel_context = kernel_context

    def health_check(self) -> HealthReport:
        return HealthReport(
            component_id=self.manifest.module_id,
            status="healthy",
            summary="output module active",
        )

    def shutdown(self) -> None:
        return None

    def format_response(self, response: TaskResponse) -> dict[str, Any]:
        return response.to_dict()
