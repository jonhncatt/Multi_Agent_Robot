from __future__ import annotations

ROLE_CHAIN: tuple[str, ...] = (
    "router",
    "planner",
    "worker",
    "reviewer",
    "revision",
)


def build_office_workflow_plan() -> list[str]:
    return [
        "Router routes task intent and minimum execution path.",
        "Planner creates execution plan for Worker.",
        "Worker executes tools and drafts answer.",
        "Reviewer performs quality/evidence review when required.",
        "Revision applies final wording adjustments when review warns/blocks.",
    ]
