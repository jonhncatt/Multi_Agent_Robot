from __future__ import annotations


class PlannerRole:
    role_id = "planner"

    def describe(self) -> str:
        return "Build execution plan for Worker."
