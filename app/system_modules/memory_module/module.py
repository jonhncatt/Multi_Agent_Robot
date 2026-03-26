from __future__ import annotations

from typing import Any

from app.contracts import HealthReport
from app.system_modules.memory_module.manifest import MEMORY_MODULE_MANIFEST


class MemoryModule:
    manifest = MEMORY_MODULE_MANIFEST

    def __init__(self) -> None:
        self._kernel_context: Any = None
        self._store: dict[str, Any] = {}

    def init(self, kernel_context: Any) -> None:
        self._kernel_context = kernel_context

    def health_check(self) -> HealthReport:
        return HealthReport(
            component_id=self.manifest.module_id,
            status="healthy",
            summary="memory module active",
            details={"key_count": len(self._store)},
        )

    def shutdown(self) -> None:
        self._store.clear()

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(str(key or ""), default)

    def set(self, key: str, value: Any) -> None:
        self._store[str(key or "")] = value
