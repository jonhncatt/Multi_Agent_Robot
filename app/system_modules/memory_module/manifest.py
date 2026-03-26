from __future__ import annotations

from app.contracts import ModuleManifest


MEMORY_MODULE_MANIFEST = ModuleManifest(
    module_id="memory_module",
    module_kind="system",
    version="1.0.0",
    description="System memory module for shared state snapshots.",
    capabilities=["memory.read", "memory.write"],
    required_tools=[],
    required_system_modules=[],
    min_kernel_version="1.0.0",
    hot_swappable=True,
    entrypoint="app.system_modules.memory_module.module:MemoryModule",
)
