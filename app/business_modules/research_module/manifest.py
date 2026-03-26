from __future__ import annotations

from app.contracts import ModuleManifest


RESEARCH_MODULE_MANIFEST = ModuleManifest(
    module_id="research_module",
    module_kind="business",
    version="0.1.0",
    description="Research business module skeleton for future deep investigation tasks.",
    capabilities=["task.research"],
    required_tools=["web.search", "web.fetch", "file.read", "workspace.read"],
    required_system_modules=["memory_module", "output_module", "tool_runtime_module", "policy_module"],
    min_kernel_version="1.0.0",
    hot_swappable=True,
    entrypoint="app.business_modules.research_module.module:ResearchModule",
)
