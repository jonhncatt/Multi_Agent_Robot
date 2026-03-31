from __future__ import annotations

from app.agents.plugin_base import BaseIndependentAgent


class CoderAgent(BaseIndependentAgent):
    def __init__(self, kernel=None):
        super().__init__(
            name="coder_agent",
            description="编码代理，负责代码实现、修复与重构建议。",
            capabilities=["coding", "debugging", "refactoring"],
            kernel=kernel,
        )

