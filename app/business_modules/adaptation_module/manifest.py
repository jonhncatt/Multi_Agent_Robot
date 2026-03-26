from __future__ import annotations

from app.contracts import ModuleManifest


ADAPTATION_MODULE_MANIFEST = ModuleManifest(
    module_id="adaptation_module",
    module_kind="business",
    version="0.1.0",
    description="Adaptation business module skeleton reserved for candidate/validate/activate workflows.",
    capabilities=["task.adaptation"],
    required_tools=["workspace.read", "write.patch"],
    required_system_modules=["memory_module", "output_module", "tool_runtime_module", "policy_module"],
    min_kernel_version="1.0.0",
    hot_swappable=True,
    entrypoint="app.business_modules.adaptation_module.module:AdaptationModule",
)
