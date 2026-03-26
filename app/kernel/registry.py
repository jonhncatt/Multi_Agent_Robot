from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.contracts import BaseBusinessModule, BaseModule, BaseToolProvider


@dataclass(slots=True)
class RegistrySnapshot:
    system_modules: list[str]
    business_modules: list[str]
    providers: list[str]
    tool_map: dict[str, str]
    active_module_versions: dict[str, str]


class ModuleRegistry:
    def __init__(self) -> None:
        self._system_modules: dict[str, BaseModule] = {}
        self._business_modules: dict[str, BaseBusinessModule] = {}
        self._module_history: dict[str, list[BaseModule]] = {}
        self._module_versions: dict[str, str] = {}
        self._providers: dict[str, BaseToolProvider] = {}
        self._provider_history: dict[str, list[BaseToolProvider]] = {}
        self._tool_to_provider: dict[str, str] = {}

    def register_module(self, module: BaseModule) -> None:
        module_id = str(module.manifest.module_id or "").strip()
        if not module_id:
            raise ValueError("module_id is required")
        existing = self.get_module(module_id)
        if existing is not None:
            self._module_history.setdefault(module_id, []).append(existing)
        if module.manifest.module_kind == "business":
            self._business_modules[module_id] = module  # type: ignore[assignment]
            self._system_modules.pop(module_id, None)
        else:
            self._system_modules[module_id] = module
            self._business_modules.pop(module_id, None)
        self._module_versions[module_id] = str(module.manifest.version or "")

    def rollback_module(self, module_id: str) -> BaseModule | None:
        key = str(module_id or "").strip()
        history = self._module_history.get(key) or []
        if not history:
            return None
        previous = history.pop()
        if previous.manifest.module_kind == "business":
            self._business_modules[key] = previous  # type: ignore[assignment]
            self._system_modules.pop(key, None)
        else:
            self._system_modules[key] = previous
            self._business_modules.pop(key, None)
        self._module_versions[key] = str(previous.manifest.version or "")
        return previous

    def active_module_version(self, module_id: str) -> str:
        return str(self._module_versions.get(str(module_id or "").strip()) or "")

    def register_provider(self, provider: BaseToolProvider) -> None:
        provider_id = str(provider.provider_id or "").strip()
        if not provider_id:
            raise ValueError("provider_id is required")
        existing = self._providers.get(provider_id)
        if existing is not None:
            self._provider_history.setdefault(provider_id, []).append(existing)
        self._providers[provider_id] = provider
        self._rebuild_tool_map()

    def rollback_provider(self, provider_id: str) -> BaseToolProvider | None:
        key = str(provider_id or "").strip()
        history = self._provider_history.get(key) or []
        if not history:
            return None
        previous = history.pop()
        self._providers[key] = previous
        self._rebuild_tool_map()
        return previous

    def provider_for_tool(self, tool_name: str) -> BaseToolProvider | None:
        provider_id = self._tool_to_provider.get(str(tool_name or "").strip())
        if not provider_id:
            return None
        return self._providers.get(provider_id)

    def get_provider(self, provider_id: str) -> BaseToolProvider | None:
        return self._providers.get(str(provider_id or "").strip())

    def get_module(self, module_id: str) -> BaseModule | None:
        key = str(module_id or "").strip()
        if key in self._business_modules:
            return self._business_modules[key]
        return self._system_modules.get(key)

    def get_business_module(self, module_id: str) -> BaseBusinessModule | None:
        return self._business_modules.get(str(module_id or "").strip())

    def list_modules(self, *, kind: str | None = None) -> list[BaseModule]:
        if kind == "business":
            return list(self._business_modules.values())
        if kind == "system":
            return list(self._system_modules.values())
        return [*self._system_modules.values(), *self._business_modules.values()]

    def list_providers(self) -> list[BaseToolProvider]:
        return list(self._providers.values())

    def snapshot(self) -> RegistrySnapshot:
        return RegistrySnapshot(
            system_modules=sorted(self._system_modules.keys()),
            business_modules=sorted(self._business_modules.keys()),
            providers=sorted(self._providers.keys()),
            tool_map=dict(sorted(self._tool_to_provider.items())),
            active_module_versions=dict(sorted(self._module_versions.items())),
        )

    def to_dict(self) -> dict[str, Any]:
        snap = self.snapshot()
        return {
            "system_modules": snap.system_modules,
            "business_modules": snap.business_modules,
            "providers": snap.providers,
            "tool_map": dict(snap.tool_map),
            "active_module_versions": dict(snap.active_module_versions),
            "module_history_depth": {
                key: len(items)
                for key, items in sorted(self._module_history.items())
                if items
            },
            "provider_history_depth": {
                key: len(items)
                for key, items in sorted(self._provider_history.items())
                if items
            },
        }

    def _rebuild_tool_map(self) -> None:
        mapping: dict[str, str] = {}
        for provider_id, provider in self._providers.items():
            for tool_name in provider.supported_tools:
                name = str(tool_name or "").strip()
                if not name:
                    continue
                mapping[name] = provider_id
        self._tool_to_provider = mapping
