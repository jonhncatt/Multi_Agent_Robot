from __future__ import annotations

from app.agents.plugin_base import BaseIndependentAgent


class SummarizerAgent(BaseIndependentAgent):
    def __init__(self, kernel=None):
        super().__init__(
            name="summarizer_agent",
            description="总结代理，负责压缩信息并输出高密度结论。",
            capabilities=["summarization", "compression", "insight_highlight"],
            kernel=kernel,
        )

