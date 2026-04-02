from __future__ import annotations

from typing import Any

from app.agents.agent_plugin import AgentPlugin, placeholder_result


PLUGIN = AgentPlugin(
    plugin_id="router_agent",
    title="Router Agent",
    description="入口分流 Agent：根据任务类型和上下文将请求路由到合适执行插件。",
)


def run(message: str, *, context: dict[str, Any] | None = None) -> dict[str, Any]:
    return placeholder_result(PLUGIN, message, context=context)
