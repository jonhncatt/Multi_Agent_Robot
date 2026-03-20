from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class KernelModuleRegistry:
    router: Any
    policy: Any
    attachment_context: Any
    finalizer: Any
    tool_registry: Any | None = None
    providers: dict[str, Any] = field(default_factory=dict)
    selected_refs: dict[str, str] = field(default_factory=dict)
    active_manifest: dict[str, Any] = field(default_factory=dict)
    module_health: dict[str, dict[str, Any]] = field(default_factory=dict)

    def provider_for_mode(self, mode: str) -> Any | None:
        normalized = str(mode or "").strip().lower()
        return self.providers.get(normalized)
