from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.bootstrap.config import AgentOSAssembleConfig, build_assemble_config
from app.business_modules import AdaptationModule, CodingModule, OfficeModule, ResearchModule
from app.config import AppConfig
from app.kernel import KernelHost
from app.local_tools import LocalToolExecutor
from app.system_modules import MemoryModule, OutputModule, PolicyModule, ToolRuntimeModule
from app.tool_providers import (
    HttpWebProvider,
    LocalFileProvider,
    LocalWorkspaceProvider,
    PatchWriteProvider,
    SessionStoreProvider,
)


@dataclass(slots=True)
class AgentOSRuntime:
    kernel: KernelHost
    office_module: OfficeModule
    system_modules: dict[str, object]
    business_modules: dict[str, object]
    providers: dict[str, object]
    _legacy_host: Any | None = None
    _legacy_host_factory: Callable[[], Any] | None = None

    def bind_legacy_host(self, host: Any) -> None:
        self._legacy_host = host
        self.office_module.bind_legacy_host(host)

    def get_legacy_host(self) -> Any | None:
        if self._legacy_host is not None:
            return self._legacy_host
        if self._legacy_host_factory is None:
            return None
        self.bind_legacy_host(self._legacy_host_factory())
        return self._legacy_host

    def snapshot(self) -> dict[str, object]:
        return {
            "kernel": self.kernel.health_snapshot(),
            "modules": {
                "system": sorted(self.system_modules.keys()),
                "business": sorted(self.business_modules.keys()),
            },
            "providers": sorted(self.providers.keys()),
            "office_workflow": self.office_module.workflow_plan(),
        }


def assemble_runtime(
    app_config: AppConfig,
    *,
    kernel_runtime: Any | None = None,
    legacy_host: Any | None = None,
    legacy_host_factory: Callable[[], Any] | None = None,
    assemble_config: AgentOSAssembleConfig | None = None,
) -> AgentOSRuntime:
    cfg = assemble_config or build_assemble_config(app_config)
    kernel = KernelHost(kernel_version=cfg.kernel_version)
    shared_executor = LocalToolExecutor(app_config)

    system_modules: dict[str, object] = {
        "memory_module": MemoryModule(),
        "output_module": OutputModule(),
        "tool_runtime_module": ToolRuntimeModule(),
        "policy_module": PolicyModule(),
    }

    office_module = OfficeModule(
        config=app_config,
        legacy_host=legacy_host,
        kernel_runtime=kernel_runtime,
    )
    business_modules: dict[str, object] = {
        "office_module": office_module,
    }
    if cfg.include_research_module:
        business_modules["research_module"] = ResearchModule()
    if cfg.include_coding_module:
        business_modules["coding_module"] = CodingModule()
    if cfg.include_adaptation_module:
        business_modules["adaptation_module"] = AdaptationModule()

    for module in [*system_modules.values(), *business_modules.values()]:
        kernel.register_module(module)  # type: ignore[arg-type]

    providers: dict[str, object] = {
        "local_workspace_provider": LocalWorkspaceProvider(app_config, executor=shared_executor),
        "local_file_provider": LocalFileProvider(app_config, executor=shared_executor),
        "http_web_provider": HttpWebProvider(app_config, executor=shared_executor),
        "patch_write_provider": PatchWriteProvider(app_config, executor=shared_executor),
    }
    if cfg.enable_session_provider:
        providers["session_store_provider"] = SessionStoreProvider(app_config, executor=shared_executor)

    for provider in providers.values():
        kernel.register_provider(provider)  # type: ignore[arg-type]

    kernel.init()

    runtime = AgentOSRuntime(
        kernel=kernel,
        office_module=office_module,
        system_modules=system_modules,
        business_modules=business_modules,
        providers=providers,
        _legacy_host=legacy_host,
        _legacy_host_factory=legacy_host_factory,
    )
    if legacy_host is not None:
        runtime.bind_legacy_host(legacy_host)
    return runtime
