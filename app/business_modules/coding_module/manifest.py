from __future__ import annotations

from app.contracts import ModuleManifest


CODING_MODULE_MANIFEST = ModuleManifest(
    module_id="coding_module",
    module_kind="business",
    version="0.1.0",
    description="Coding business module skeleton for repository analysis and patch tasks.",
    capabilities=["task.coding"],
    required_tools=["workspace.read", "workspace.write", "file.read", "write.patch", "session.lookup"],
    required_system_modules=["memory_module", "output_module", "tool_runtime_module", "policy_module"],
    min_kernel_version="1.0.0",
    hot_swappable=True,
    entrypoint="app.business_modules.coding_module.module:CodingModule",
)
