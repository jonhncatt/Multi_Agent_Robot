from __future__ import annotations

from app.contracts import ModuleManifest


POLICY_MODULE_MANIFEST = ModuleManifest(
    module_id="policy_module",
    module_kind="system",
    version="1.0.0",
    description="System policy module for global execution constraints.",
    capabilities=["policy.check"],
    required_tools=[],
    required_system_modules=[],
    min_kernel_version="1.0.0",
    hot_swappable=True,
    entrypoint="app.system_modules.policy_module.module:PolicyModule",
)
