from __future__ import annotations

from app.contracts import ModuleManifest


OFFICE_MODULE_MANIFEST = ModuleManifest(
    module_id="office_module",
    module_kind="business",
    version="1.0.0",
    description="Office business module with internal Router/Planner/Worker/Reviewer/Revision workflow.",
    capabilities=["task.chat", "task.office", "task.workflow"],
    required_tools=[
        "workspace.read",
        "file.read",
        "web.search",
        "web.fetch",
        "workspace.write",
        "write.patch",
        "session.lookup",
    ],
    required_system_modules=["memory_module", "output_module", "tool_runtime_module", "policy_module"],
    min_kernel_version="1.0.0",
    hot_swappable=True,
    entrypoint="app.business_modules.office_module.module:OfficeModule",
)
