from __future__ import annotations

from app.agents.plugin_base import BaseIndependentAgent


class CoordinatorAgent(BaseIndependentAgent):
    def __init__(self, kernel=None):
        super().__init__(
            name="coordinator_agent",
            description="协同代理，负责多 Agent 任务编排、顺序与依赖协调。",
            capabilities=["coordination", "dependency_management", "orchestration"],
            kernel=kernel,
        )

