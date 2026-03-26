from __future__ import annotations

from app.contracts import ModuleManifest


OUTPUT_MODULE_MANIFEST = ModuleManifest(
    module_id="output_module",
    module_kind="system",
    version="1.0.0",
    description="System output formatter module.",
    capabilities=["output.format"],
    required_tools=[],
    required_system_modules=[],
    min_kernel_version="1.0.0",
    hot_swappable=True,
    entrypoint="app.system_modules.output_module.module:OutputModule",
)
