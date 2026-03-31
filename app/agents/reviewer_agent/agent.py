from __future__ import annotations

from app.agents.plugin_base import BaseIndependentAgent


class ReviewerAgent(BaseIndependentAgent):
    def __init__(self, kernel=None):
        super().__init__(
            name="reviewer_agent",
            description="审查代理，负责结果审阅、一致性检查与可交付验收。",
            capabilities=["review", "consistency_check", "acceptance"],
            kernel=kernel,
        )

