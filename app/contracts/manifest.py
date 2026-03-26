from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


ModuleKind = Literal["system", "business"]


@dataclass(slots=True)
class ModuleManifest:
    module_id: str
    module_kind: ModuleKind
    version: str
    description: str
    capabilities: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    required_system_modules: list[str] = field(default_factory=list)
    min_kernel_version: str = "1.0.0"
    hot_swappable: bool = True
    entrypoint: str = ""

    def identity(self) -> str:
        return f"{self.module_id}@{self.version}"

    def to_dict(self) -> dict[str, object]:
        return {
            "module_id": self.module_id,
            "module_kind": self.module_kind,
            "version": self.version,
            "description": self.description,
            "capabilities": list(self.capabilities),
            "required_tools": list(self.required_tools),
            "required_system_modules": list(self.required_system_modules),
            "min_kernel_version": self.min_kernel_version,
            "hot_swappable": bool(self.hot_swappable),
            "entrypoint": self.entrypoint,
        }
