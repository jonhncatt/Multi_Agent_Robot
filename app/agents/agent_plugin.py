from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AgentPlugin:
    plugin_id: str
    title: str
    description: str
    kind: str = "llm"


def placeholder_result(plugin: AgentPlugin, message: str, *, context: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {
        "plugin_id": plugin.plugin_id,
        "title": plugin.title,
        "handled": False,
        "reason": "plugin scaffold only; runtime wiring pending",
        "message_preview": str(message or "").strip()[:200],
        "context_keys": sorted((context or {}).keys()),
    }
    return payload
