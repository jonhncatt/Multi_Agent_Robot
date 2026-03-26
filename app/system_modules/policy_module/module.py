from __future__ import annotations

from typing import Any

from app.contracts import HealthReport
from app.system_modules.policy_module.manifest import POLICY_MODULE_MANIFEST


class PolicyModule:
    manifest = POLICY_MODULE_MANIFEST

    def __init__(self) -> None:
        self._kernel_context: Any = None

    def init(self, kernel_context: Any) -> None:
        self._kernel_context = kernel_context

    def health_check(self) -> HealthReport:
        return HealthReport(
            component_id=self.manifest.module_id,
            status="healthy",
            summary="policy module active",
        )

    def shutdown(self) -> None:
        return None

    def check(self, policy_name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        _ = policy_name, payload
        return {"ok": True, "reason": "default_allow"}
