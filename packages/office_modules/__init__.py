from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from packages.runtime_core.capability_loader import CapabilityBundle

def _manifest_path() -> Path:
    return (Path(__file__).resolve().parent / "manifest.json").resolve()


def build_office_agent_modules():
    from .agent_module import build_office_agent_modules as _build_office_agent_modules

    return _build_office_agent_modules()


def build_office_memory_modules():
    from .memory_module import build_office_memory_modules as _build_office_memory_modules

    return _build_office_memory_modules()


def build_office_output_modules():
    from .output_module import build_office_output_modules as _build_office_output_modules

    return _build_office_output_modules()


def build_office_role_registry():
    from .roles import build_office_role_registry as _build_office_role_registry

    return _build_office_role_registry()


def build_office_tool_modules():
    from .tools import build_office_tool_modules as _build_office_tool_modules

    return _build_office_tool_modules()


def get_tool_executor(*args: Any, **kwargs: Any):
    from .tools import get_tool_executor as _get_tool_executor

    return _get_tool_executor(*args, **kwargs)


def read_office_manifest() -> dict[str, Any]:
    return json.loads(_manifest_path().read_text(encoding="utf-8"))


def build_capability_bundle(*, config: Any | None = None) -> CapabilityBundle:
    manifest = read_office_manifest()
    metadata = {
        "agent_modules": list(manifest.get("agent_modules") or []),
        "memory_modules": list(manifest.get("memory_modules") or []),
        "profiles": list(manifest.get("profiles") or []),
        "output_modules": list(manifest.get("output_modules") or []),
        "tools": list(manifest.get("tools") or []),
        "tool_modules": list(manifest.get("tool_modules") or []),
        "roles": list(manifest.get("roles") or []),
    }
    return CapabilityBundle(
        module_id=str(manifest.get("module_id") or "office_modules"),
        version=str(manifest.get("version") or "0.1.0"),
        manifest=manifest,
        build_role_registry=build_office_role_registry,
        tool_executor_factory=get_tool_executor,
        agent_modules=build_office_agent_modules(),
        tool_modules=build_office_tool_modules(),
        output_modules=build_office_output_modules(),
        memory_modules=build_office_memory_modules(),
        metadata=metadata,
    )


def load_office_capability_bundle(*, config: Any | None = None) -> CapabilityBundle:
    return build_capability_bundle(config=config)


__all__ = [
    "build_capability_bundle",
    "build_office_agent_modules",
    "build_office_memory_modules",
    "build_office_role_registry",
    "build_office_output_modules",
    "build_office_tool_modules",
    "get_tool_executor",
    "load_office_capability_bundle",
    "read_office_manifest",
]
