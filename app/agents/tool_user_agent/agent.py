from __future__ import annotations

from app.agents.plugin_base import BaseIndependentAgent


class ToolUserAgent(BaseIndependentAgent):
    def __init__(self, kernel=None):
        super().__init__(
            name="tool_user_agent",
            description="工具代理，负责工具选择、调用策略与执行反馈。",
            capabilities=["tool_selection", "tool_execution", "tool_feedback"],
            kernel=kernel,
        )

