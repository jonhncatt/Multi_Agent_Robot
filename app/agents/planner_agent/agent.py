from __future__ import annotations

from app.agents.plugin_base import BaseIndependentAgent


class PlannerAgent(BaseIndependentAgent):
    def __init__(self, kernel=None):
        super().__init__(
            name="planner_agent",
            description="规划代理，负责把复杂目标拆解为可执行阶段与里程碑。",
            capabilities=["task_decomposition", "planning", "milestone_design"],
            kernel=kernel,
        )

