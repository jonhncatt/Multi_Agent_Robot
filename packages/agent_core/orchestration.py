from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from packages.agent_core.role_registry import RegisteredRole, RoleRegistry
from packages.agent_core.runtime_controller import RoleRuntimeController
from packages.runtime_core import CapabilityBundle, load_capability_bundles


@dataclass(slots=True)
class AgentCapabilityRuntime:
    module_paths: tuple[str, ...]
    bundles: tuple[CapabilityBundle, ...]
    role_registry: RoleRegistry
    runtime_controller: RoleRuntimeController
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


def build_agent_capability_runtime(config: Any, module_paths: list[str] | tuple[str, ...]) -> AgentCapabilityRuntime:
    normalized_paths = tuple(str(item or "").strip() for item in module_paths if str(item or "").strip())
    if not normalized_paths:
        raise RuntimeError("No capability modules configured")

    bundles = list(load_capability_bundles(normalized_paths, config=config))
    if not bundles:
        raise RuntimeError("Capability loader did not load any modules")

    role_registry, role_sources = _merge_role_registries(bundles)
    tool_factories = [
        (bundle.module_id, bundle.tool_executor_factory)
        for bundle in bundles
        if bundle.tool_executor_factory is not None
    ]
    if not tool_factories:
        raise RuntimeError("No capability module provides a tool executor")

    primary_tool_module, tool_factory = tool_factories[0]
    tools = tool_factory(config)
    runtime_controller = RoleRuntimeController(role_registry)
    metadata = {
        "module_paths": list(normalized_paths),
        "modules": [
            {
                "module_id": bundle.module_id,
                "version": bundle.version,
                "manifest": dict(bundle.manifest),
                "metadata": dict(bundle.metadata),
                "provides_tools": bundle.tool_executor_factory is not None,
                "provides_roles": bundle.build_role_registry is not None,
            }
            for bundle in bundles
        ],
        "primary_tool_module": primary_tool_module,
        "extra_tool_modules": [module_id for module_id, _ in tool_factories[1:]],
        "role_sources": role_sources,
    }
    return AgentCapabilityRuntime(
        module_paths=normalized_paths,
        bundles=tuple(bundles),
        role_registry=role_registry,
        runtime_controller=runtime_controller,
        tools=tools,
        metadata=metadata,
    )
