from __future__ import annotations

from app.agents.plugin_base import BaseIndependentAgent


class WorkerAgent(BaseIndependentAgent):
    def __init__(self, kernel=None):
        super().__init__(
            name="worker_agent",
            description="通用执行代理，负责把任务快速落实为可交付结果。",
            capabilities=["execution", "task_completion", "delivery"],
            kernel=kernel,
        )

