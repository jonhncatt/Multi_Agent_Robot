from __future__ import annotations

from app.agents.plugin_base import BaseIndependentAgent


class ResearcherAgent(BaseIndependentAgent):
    def __init__(self, kernel=None):
        super().__init__(
            name="researcher_agent",
            description="研究代理，负责检索信息、整理事实与来源。",
            capabilities=["research", "fact_collection", "source_synthesis"],
            kernel=kernel,
        )

