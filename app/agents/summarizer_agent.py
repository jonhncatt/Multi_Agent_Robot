from __future__ import annotations

from typing import Any

from app.agents.agent_plugin import AgentPlugin, placeholder_result


PLUGIN = AgentPlugin(
    plugin_id="summarizer_agent",
    title="Summarizer Agent",
    description="摘要 Agent：压缩长上下文并生成可读结论。",
)


def run(message: str, *, context: dict[str, Any] | None = None) -> dict[str, Any]:
    return placeholder_result(PLUGIN, message, context=context)
