from __future__ import annotations

from app.agents.plugin_base import BaseIndependentAgent


class CriticAgent(BaseIndependentAgent):
    def __init__(self, kernel=None):
        super().__init__(
            name="critic_agent",
            description="批判评估代理，负责识别风险、漏洞与逻辑问题。",
            capabilities=["risk_review", "logic_check", "quality_gate"],
            kernel=kernel,
        )

