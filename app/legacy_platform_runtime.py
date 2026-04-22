from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from app.config import AppConfig

_legacy_runtime_lock = threading.Lock()
_legacy_runtime_cache: dict[str, Any] = {}


def _cache_key(config: AppConfig, kernel_runtime: Any | None) -> str:
    workspace_root = str(Path(config.workspace_root).resolve())
    projects_registry = str(Path(config.projects_registry_path).resolve())
    sessions_dir = str(Path(config.sessions_dir).resolve())
    return "::".join(
        [
            workspace_root,
            projects_registry,
            sessions_dir,
            str(id(kernel_runtime)),
        ]
    )


def get_legacy_agent_os_runtime(*, config: AppConfig, kernel_runtime: Any | None = None) -> Any:
    """
    Lazily assemble the historical AgentOS compatibility runtime.

    The chat product hot path should not depend on this object. Legacy kernel,
    migration, and platform-only APIs resolve it on demand through this module.
    """

    key = _cache_key(config, kernel_runtime)
    with _legacy_runtime_lock:
        cached = _legacy_runtime_cache.get(key)
        if cached is not None:
            return cached
        from app.bootstrap import assemble_runtime

        runtime = assemble_runtime(
            config,
            kernel_runtime=kernel_runtime,
        )
        _legacy_runtime_cache[key] = runtime
        return runtime


def reset_legacy_agent_os_runtime_cache() -> None:
    with _legacy_runtime_lock:
        _legacy_runtime_cache.clear()
