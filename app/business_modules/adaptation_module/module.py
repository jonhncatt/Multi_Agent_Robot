from __future__ import annotations

from typing import Any

from app.business_modules.adaptation_module.manifest import ADAPTATION_MODULE_MANIFEST
from app.contracts import HealthReport, TaskRequest, TaskResponse


class AdaptationModule:
    manifest = ADAPTATION_MODULE_MANIFEST

    def __init__(self) -> None:
        self._kernel_context: Any = None

    def init(self, kernel_context: Any) -> None:
        self._kernel_context = kernel_context

    def health_check(self) -> HealthReport:
        return HealthReport(
            component_id=self.manifest.module_id,
            status="degraded",
            summary="adaptation module skeleton is loaded",
        )

    def shutdown(self) -> None:
        return None

    def invoke(self, request: TaskRequest) -> TaskResponse:
        return TaskResponse(
            ok=False,
            task_id=request.task_id,
            error="adaptation_module is not implemented yet",
            warnings=["skeleton module"],
        )
