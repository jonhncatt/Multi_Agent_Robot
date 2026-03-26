from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.contracts import BaseBusinessModule, BaseModule, BaseToolProvider, TaskRequest, TaskResponse
from app.kernel.compatibility import CompatibilityChecker
from app.kernel.event_bus import EventBus
from app.kernel.health import HealthMonitor
from app.kernel.lifecycle import LifecycleManager
from app.kernel.registry import ModuleRegistry
from app.kernel.tool_bus import ToolBus


@dataclass(slots=True)
class KernelContextView:
    kernel_version: str
    registry: ModuleRegistry
    tool_bus: ToolBus
    event_bus: EventBus

    def lookup_module(self, module_id: str) -> BaseModule | None:
        return self.registry.get_module(module_id)


class KernelHost:
    def __init__(
        self,
        *,
        kernel_version: str = "1.0.0",
        registry: ModuleRegistry | None = None,
        lifecycle: LifecycleManager | None = None,
        event_bus: EventBus | None = None,
        tool_bus: ToolBus | None = None,
        compatibility: CompatibilityChecker | None = None,
        health_monitor: HealthMonitor | None = None,
    ) -> None:
        self.kernel_version = str(kernel_version or "1.0.0").strip() or "1.0.0"
        self.registry = registry or ModuleRegistry()
        self.event_bus = event_bus or EventBus()
        self.lifecycle = lifecycle or LifecycleManager()
        self.compatibility = compatibility or CompatibilityChecker(kernel_version=self.kernel_version)
        self.tool_bus = tool_bus or ToolBus(self.registry, event_bus=self.event_bus)
        self.health_monitor = health_monitor or HealthMonitor()
        self._initialized = False

    @property
    def context(self) -> KernelContextView:
        return KernelContextView(
            kernel_version=self.kernel_version,
            registry=self.registry,
            tool_bus=self.tool_bus,
            event_bus=self.event_bus,
        )

    def register_module(self, module: BaseModule) -> None:
        self.compatibility.assert_manifest_compatible(module.manifest)
        self.registry.register_module(module)
        if self._initialized:
            self.lifecycle.init_module(module, kernel_context=self.context)
        self.event_bus.publish("module_registered", {"module_id": module.manifest.module_id, "version": module.manifest.version})

    def register_provider(self, provider: BaseToolProvider) -> None:
        self.registry.register_provider(provider)
        self.event_bus.publish("provider_registered", {"provider_id": provider.provider_id})

    def init(self) -> None:
        if self._initialized:
            return
        modules = self.registry.list_modules()
        self.lifecycle.init_modules(list(modules), kernel_context=self.context)
        self._initialized = True
        self.event_bus.publish("kernel_initialized", {"module_count": len(modules)})

    def shutdown(self) -> None:
        self.lifecycle.shutdown_all()
        self._initialized = False
        self.event_bus.publish("kernel_shutdown", {})

    def invoke(self, module_id: str, request: TaskRequest) -> TaskResponse:
        module = self.registry.get_business_module(module_id)
        if module is None:
            return TaskResponse(
                ok=False,
                task_id=request.task_id,
                error=f"business module not found: {module_id}",
            )
        return module.invoke(request)

    def list_business_modules(self) -> list[BaseBusinessModule]:
        return [m for m in self.registry.list_modules(kind="business") if isinstance(m, BaseBusinessModule)]

    def hot_swap_module(self, module: BaseModule) -> dict[str, object]:
        module_id = str(module.manifest.module_id or "").strip()
        if not module_id:
            return {"ok": False, "error": "module_id is required"}

        previous = self.registry.get_module(module_id)
        if previous is not None and not bool(previous.manifest.hot_swappable):
            return {"ok": False, "error": f"module not hot swappable: {module_id}"}

        self.compatibility.assert_manifest_compatible(module.manifest)
        if self._initialized:
            self.lifecycle.init_module(module, kernel_context=self.context)
            report = module.health_check()
            if report.status == "unhealthy":
                return {"ok": False, "error": f"health check failed for {module.manifest.identity()}"}

        self.registry.register_module(module)
        if previous is not None and previous is not module:
            try:
                previous.shutdown()
            except Exception:
                pass

        self.event_bus.publish(
            "module_swapped",
            {
                "module_id": module_id,
                "version": module.manifest.version,
                "previous_version": previous.manifest.version if previous else "",
            },
        )
        return {
            "ok": True,
            "module_id": module_id,
            "active_version": module.manifest.version,
            "previous_version": previous.manifest.version if previous else "",
        }

    def rollback_module(self, module_id: str) -> dict[str, object]:
        key = str(module_id or "").strip()
        if not key:
            return {"ok": False, "error": "module_id is required"}

        current = self.registry.get_module(key)
        previous = self.registry.rollback_module(key)
        if previous is None:
            return {"ok": False, "error": f"no rollback candidate for module: {key}"}

        if self._initialized:
            try:
                self.lifecycle.init_module(previous, kernel_context=self.context)
                report = previous.health_check()
                if report.status == "unhealthy":
                    raise RuntimeError("rollback health check failed")
            except Exception as exc:
                if current is not None:
                    self.registry.register_module(current)
                return {"ok": False, "error": f"rollback init failed: {exc}"}

        if current is not None and current is not previous:
            try:
                current.shutdown()
            except Exception:
                pass

        self.event_bus.publish(
            "module_rolled_back",
            {
                "module_id": key,
                "active_version": previous.manifest.version,
                "from_version": current.manifest.version if current else "",
            },
        )
        return {
            "ok": True,
            "module_id": key,
            "active_version": previous.manifest.version,
            "from_version": current.manifest.version if current else "",
        }

    def hot_swap_provider(self, provider: BaseToolProvider) -> dict[str, object]:
        provider_id = str(provider.provider_id or "").strip()
        if not provider_id:
            return {"ok": False, "error": "provider_id is required"}
        previous = self.registry.get_provider(provider_id)
        self.registry.register_provider(provider)
        try:
            report = provider.health_check()
        except Exception as exc:
            if previous is not None:
                self.registry.rollback_provider(provider_id)
            return {"ok": False, "error": f"provider health check failed: {exc}"}
        if report.status == "unhealthy":
            if previous is not None:
                self.registry.rollback_provider(provider_id)
            return {"ok": False, "error": f"provider unhealthy: {provider_id}"}
        self.event_bus.publish("provider_swapped", {"provider_id": provider_id})
        return {"ok": True, "provider_id": provider_id}

    def rollback_provider(self, provider_id: str) -> dict[str, object]:
        key = str(provider_id or "").strip()
        if not key:
            return {"ok": False, "error": "provider_id is required"}
        previous = self.registry.rollback_provider(key)
        if previous is None:
            return {"ok": False, "error": f"no rollback candidate for provider: {key}"}
        self.event_bus.publish("provider_rolled_back", {"provider_id": key})
        return {"ok": True, "provider_id": key}

    def health_snapshot(self) -> dict[str, object]:
        payload = self.health_monitor.collect(self.registry)
        payload["kernel_version"] = self.kernel_version
        payload["registry"] = self.registry.to_dict()
        payload["initialized"] = self._initialized
        return payload
