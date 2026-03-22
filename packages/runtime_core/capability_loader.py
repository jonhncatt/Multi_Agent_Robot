from __future__ import annotations

from dataclasses import dataclass, field
import importlib
from typing import Any, Callable


AgentRuntimeFactory = Callable[..., Any]
ToolExecutorFactory = Callable[[Any], Any]
RoleRegistryBuilder = Callable[[], Any]


@dataclass(frozen=True, slots=True)
class AgentModule:
    module_id: str
    title: str
    description: str = ""
    build_runtime: AgentRuntimeFactory | None = None
    default: bool = False
    roles: tuple[str, ...] = ()
    profiles: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ToolModule:
    module_id: str
    title: str
    description: str = ""
    build_executor: ToolExecutorFactory | None = None
    default: bool = False
    tool_names: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OutputModule:
    module_id: str
    title: str
    description: str = ""
    default: bool = False
    output_kinds: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MemoryModule:
    module_id: str
    title: str
    description: str = ""
    default: bool = False
    signal_kinds: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CapabilityBundle:
    module_id: str
    version: str
    manifest: dict[str, Any] = field(default_factory=dict)
    build_role_registry: RoleRegistryBuilder | None = None
    tool_executor_factory: ToolExecutorFactory | None = None
    agent_modules: tuple[AgentModule, ...] = ()
    tool_modules: tuple[ToolModule, ...] = ()
    output_modules: tuple[OutputModule, ...] = ()
    memory_modules: tuple[MemoryModule, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


class CapabilityModuleLoader:
    def __init__(self) -> None:
        self._cache: dict[str, CapabilityBundle] = {}

    def load(self, module_path: str, *, config: Any | None = None, force_reload: bool = False) -> CapabilityBundle:
        key = str(module_path or "").strip()
        if not key:
            raise ValueError("module_path must not be empty")
        if not force_reload and key in self._cache:
            return self._cache[key]

        module = importlib.import_module(key)
        builder = getattr(module, "build_capability_bundle", None)
        if builder is None or not callable(builder):
            raise RuntimeError(f"capability module {key} does not expose build_capability_bundle(config=...)")
        bundle = builder(config=config)
        if not isinstance(bundle, CapabilityBundle):
            raise RuntimeError(f"capability module {key} returned invalid bundle: {type(bundle)!r}")
        self._cache[key] = bundle
        return bundle


_DEFAULT_LOADER = CapabilityModuleLoader()


def load_capability_bundle(module_path: str, *, config: Any | None = None, force_reload: bool = False) -> CapabilityBundle:
    return _DEFAULT_LOADER.load(module_path, config=config, force_reload=force_reload)


def load_capability_bundles(
    module_paths: list[str] | tuple[str, ...],
    *,
    config: Any | None = None,
    force_reload: bool = False,
) -> list[CapabilityBundle]:
    bundles: list[CapabilityBundle] = []
    for raw in module_paths:
        module_path = str(raw or "").strip()
        if not module_path:
            continue
        bundles.append(load_capability_bundle(module_path, config=config, force_reload=force_reload))
    return bundles
