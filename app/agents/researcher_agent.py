from __future__ import annotations

from typing import Any

from app.agents.agent_plugin import AgentPlugin, placeholder_result


PLUGIN = AgentPlugin(
    plugin_id="researcher_agent",
    title="Researcher Agent",
    description="研究 Agent：负责信息检索、证据聚合与来源整理。",
)


def run(message: str, *, context: dict[str, Any] | None = None) -> dict[str, Any]:
    return placeholder_result(PLUGIN, message, context=context)
