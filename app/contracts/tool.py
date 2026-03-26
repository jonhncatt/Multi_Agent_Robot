from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    timeout_sec: float | None = None
    retries: int = 0
    fallback_tools: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolResult:
    ok: bool
    tool_name: str
    provider_id: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    attempts: int = 1
    fallback_used: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": bool(self.ok),
            "tool_name": self.tool_name,
            "provider_id": self.provider_id,
            "data": dict(self.data),
            "error": self.error,
            "attempts": int(self.attempts),
            "fallback_used": bool(self.fallback_used),
            "metadata": dict(self.metadata),
        }
