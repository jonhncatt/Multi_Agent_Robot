from __future__ import annotations

from typing import Any

from app.business_modules.coding_module.manifest import CODING_MODULE_MANIFEST
from app.contracts import HealthReport, TaskRequest, TaskResponse


class CodingModule:
    manifest = CODING_MODULE_MANIFEST

    def __init__(self) -> None:
        self._kernel_context: Any = None

    def init(self, kernel_context: Any) -> None:
        self._kernel_context = kernel_context

    def health_check(self) -> HealthReport:
        return HealthReport(
            component_id=self.manifest.module_id,
            status="degraded",
            summary="coding module skeleton is loaded",
        )

    def shutdown(self) -> None:
        return None

    def invoke(self, request: TaskRequest) -> TaskResponse:
        return TaskResponse(
            ok=False,
            task_id=request.task_id,
            error="coding_module is not implemented yet",
            warnings=["skeleton module"],
        )
