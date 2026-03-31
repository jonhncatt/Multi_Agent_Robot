from __future__ import annotations

from app.agents.plugin_base import BaseIndependentAgent


class NavigatorAgent(BaseIndependentAgent):
    def __init__(self, kernel=None):
        super().__init__(
            name="navigator_agent",
            description="航行代理，负责全局方向判断、稳态推进与路径修正。",
            capabilities=["direction_setting", "stability_control", "path_adjustment"],
            kernel=kernel,
        )

