from __future__ import annotations

from packages.runtime_core.capability_loader import OutputModule


def build_office_output_modules() -> tuple[OutputModule, ...]:
    return (
        OutputModule(
            module_id="output_finalizer",
            title="Output Module",
            description="负责最终答案整理、表格/邮件改写与输出收口。",
            default=True,
            output_kinds=("markdown", "table", "mail", "answer_bundle"),
            metadata={"family": "office", "source": "finalizer"},
        ),
    )
