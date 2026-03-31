from __future__ import annotations

from app.agents.plugin_base import BaseIndependentAgent


class ExecutorAgent(BaseIndependentAgent):
    def __init__(self, kernel=None):
        super().__init__(
            name="executor_agent",
            description="执行代理，负责把计划转换成明确动作与产出。",
            capabilities=["action_execution", "task_delivery", "follow_through"],
            kernel=kernel,
        )

