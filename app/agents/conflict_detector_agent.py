from __future__ import annotations

from typing import Any

from app.agents.agent_plugin import AgentPlugin, placeholder_result


PLUGIN = AgentPlugin(
    plugin_id="conflict_detector_agent",
    title="Conflict Detector Agent",
    description="冲突检测 Agent：检测证据、结论和执行计划冲突。",
)


def run(message: str, *, context: dict[str, Any] | None = None) -> dict[str, Any]:
    return placeholder_result(PLUGIN, message, context=context)
