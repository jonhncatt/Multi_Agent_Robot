from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from packages.agent_core.role_registry import RegisteredRole, RoleRegistry
from packages.agent_core.runtime_controller import RoleRuntimeController
from packages.runtime_core.capability_loader import (
    AgentModule,
    CapabilityBundle,
    MemoryModule,
    OutputModule,
    ToolModule,
    load_capability_bundles,
)


@dataclass(slots=True)
class AgentCapabilityRuntime:
    module_paths: tuple[str, ...]
    bundles: tuple[CapabilityBundle, ...]
    role_registry: RoleRegistry
    runtime_controller: RoleRuntimeController
    agent_modules: tuple[AgentModule, ...]
    tool_modules: tuple[ToolModule, ...]
    output_modules: tuple[OutputModule, ...]
    memory_modules: tuple[MemoryModule, ...]
    primary_agent_module: AgentModule | None
    primary_tool_module: ToolModule | None
    primary_output_module: OutputModule | None
    primary_memory_module: MemoryModule | None
    tools: Any
    metadata: dict[str, Any] = field(default_factory=dict)


def _merge_role_registries(bundles: list[CapabilityBundle]) -> tuple[RoleRegistry, dict[str, str]]:
    merged = RoleRegistry()
    role_sources: dict[str, str] = {}
    for bundle in bundles:
        builder = bundle.build_role_registry
        if builder is None:
            continue
        registry = builder()
        for item in registry.roles():
            merged.register(
                RegisteredRole(
                    role=item.role,
                    title=item.title,
                    kind=item.kind,
                    description=item.description,
                    handler=item.handler,
                    executable=item.executable,
                    controller_backed=item.controller_backed,
                    multi_instance_ready=item.multi_instance_ready,
                    supports_parent_child=item.supports_parent_child,
                    runtime_profiles=tuple(item.runtime_profiles),
                    meta=dict(item.meta),
                )
            )
            role_sources[item.role] = bundle.module_id
    return merged, role_sources


def _collect_agent_modules(bundles: list[CapabilityBundle]) -> tuple[list[AgentModule], AgentModule | None]:
    modules: list[AgentModule] = []
    primary: AgentModule | None = None
    for bundle in bundles:
        for item in bundle.agent_modules:
            modules.append(item)
            if primary is None and item.default:
                primary = item
    if primary is None and modules:
        primary = modules[0]
    return modules, primary


def _collect_tool_modules(bundles: list[CapabilityBundle]) -> tuple[list[ToolModule], ToolModule | None]:
    modules: list[ToolModule] = []
    primary: ToolModule | None = None
    for index, bundle in enumerate(bundles):
        raw_items = list(bundle.tool_modules)
        if not raw_items and bundle.tool_executor_factory is not None:
            raw_items = [
                ToolModule(
                    module_id=f"{bundle.module_id}.tools",
                    title=f"{bundle.module_id} Tool Module",
                    description=f"{bundle.module_id} 提供的默认工具模块。",
                    build_executor=bundle.tool_executor_factory,
                    default=index == 0,
                    tool_names=tuple(bundle.metadata.get("tools") or ()),
                    metadata={"bundle_module_id": bundle.module_id, "synthetic": True},
                )
            ]
        for item in raw_items:
            modules.append(item)
            if primary is None and item.default:
                primary = item
    if primary is None and modules:
        primary = modules[0]
    return modules, primary


def _collect_output_modules(bundles: list[CapabilityBundle]) -> tuple[list[OutputModule], OutputModule | None]:
    modules: list[OutputModule] = []
    primary: OutputModule | None = None
    for bundle in bundles:
        for item in bundle.output_modules:
            modules.append(item)
            if primary is None and item.default:
                primary = item
    if primary is None and modules:
        primary = modules[0]
    return modules, primary


def _collect_memory_modules(bundles: list[CapabilityBundle]) -> tuple[list[MemoryModule], MemoryModule | None]:
    modules: list[MemoryModule] = []
    primary: MemoryModule | None = None
    for bundle in bundles:
        for item in bundle.memory_modules:
            modules.append(item)
            if primary is None and item.default:
                primary = item
    if primary is None and modules:
        primary = modules[0]
    return modules, primary


def build_agent_capability_runtime(config: Any, module_paths: list[str] | tuple[str, ...]) -> AgentCapabilityRuntime:
    normalized_paths = tuple(str(item or "").strip() for item in module_paths if str(item or "").strip())
    if not normalized_paths:
        raise RuntimeError("No capability modules configured")

    bundles = list(load_capability_bundles(normalized_paths, config=config))
    if not bundles:
        raise RuntimeError("Capability loader did not load any modules")

    role_registry, role_sources = _merge_role_registries(bundles)
    agent_modules, primary_agent_module = _collect_agent_modules(bundles)
    tool_modules, primary_tool_module = _collect_tool_modules(bundles)
    output_modules, primary_output_module = _collect_output_modules(bundles)
    memory_modules, primary_memory_module = _collect_memory_modules(bundles)
    if not tool_modules or primary_tool_module is None or primary_tool_module.build_executor is None:
        raise RuntimeError("No capability module provides a ToolModule")

    tools = primary_tool_module.build_executor(config)
    runtime_controller = RoleRuntimeController(role_registry)
    metadata = {
        "module_paths": list(normalized_paths),
        "modules": [
            {
                "module_id": bundle.module_id,
                "version": bundle.version,
                "manifest": dict(bundle.manifest),
                "metadata": dict(bundle.metadata),
                "provides_tools": bundle.tool_executor_factory is not None or bool(bundle.tool_modules),
                "provides_roles": bundle.build_role_registry is not None,
                "provides_agent_modules": bool(bundle.agent_modules),
            }
            for bundle in bundles
        ],
        "agent_modules": [
            {
                "module_id": item.module_id,
                "title": item.title,
                "roles": list(item.roles),
                "profiles": list(item.profiles),
            }
            for item in agent_modules
        ],
        "tool_modules": [
            {
                "module_id": item.module_id,
                "title": item.title,
                "tool_names": list(item.tool_names),
            }
            for item in tool_modules
        ],
        "output_modules": [
            {
                "module_id": item.module_id,
                "title": item.title,
                "output_kinds": list(item.output_kinds),
            }
            for item in output_modules
        ],
        "memory_modules": [
            {
                "module_id": item.module_id,
                "title": item.title,
                "signal_kinds": list(item.signal_kinds),
            }
            for item in memory_modules
        ],
        "primary_agent_module": primary_agent_module.module_id if primary_agent_module else "",
        "primary_tool_module": primary_tool_module.module_id,
        "primary_output_module": primary_output_module.module_id if primary_output_module else "",
        "primary_memory_module": primary_memory_module.module_id if primary_memory_module else "",
        "extra_tool_modules": [item.module_id for item in tool_modules[1:]],
        "role_sources": role_sources,
    }
    return AgentCapabilityRuntime(
        module_paths=normalized_paths,
        bundles=tuple(bundles),
        role_registry=role_registry,
        runtime_controller=runtime_controller,
        agent_modules=tuple(agent_modules),
        tool_modules=tuple(tool_modules),
        output_modules=tuple(output_modules),
        memory_modules=tuple(memory_modules),
        primary_agent_module=primary_agent_module,
        primary_tool_module=primary_tool_module,
        primary_output_module=primary_output_module,
        primary_memory_module=primary_memory_module,
        tools=tools,
        metadata=metadata,
    )
