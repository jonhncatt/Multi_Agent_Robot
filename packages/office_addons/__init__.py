from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from packages.agent_core.role_registry import RoleRegistry
from packages.runtime_core import CapabilityBundle


def _manifest_path() -> Path:
    return (Path(__file__).resolve().parent / 'manifest.json').resolve()


def read_manifest() -> dict[str, Any]:
    return json.loads(_manifest_path().read_text(encoding='utf-8'))


def build_addon_role_registry() -> RoleRegistry:
    return RoleRegistry()


def build_capability_bundle(*, config: Any | None = None) -> CapabilityBundle:
    manifest = read_manifest()
    return CapabilityBundle(
        module_id=str(manifest.get('module_id') or 'office_addons'),
        version=str(manifest.get('version') or '0.1.0'),
        manifest=manifest,
        build_role_registry=build_addon_role_registry,
        tool_executor_factory=None,
        metadata={
            'profiles': list(manifest.get('profiles') or []),
            'tools': list(manifest.get('tools') or []),
            'roles': list(manifest.get('roles') or []),
            'notes': list(manifest.get('notes') or []),
        },
    )
