from __future__ import annotations

from typing import Any

from app.agents.agent_plugin import AgentPlugin, placeholder_result


PLUGIN = AgentPlugin(
    plugin_id="file_reader_agent",
    title="File Reader Agent",
    description="文件解析 Agent：读取附件并提取结构化内容。",
)


def run(message: str, *, context: dict[str, Any] | None = None) -> dict[str, Any]:
    return placeholder_result(PLUGIN, message, context=context)
