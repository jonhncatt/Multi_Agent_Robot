from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TaskRequest:
    task_id: str
    task_type: str
    message: str
    context: dict[str, Any] = field(default_factory=dict)
    attachments: list[dict[str, Any]] = field(default_factory=list)
    settings: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TaskResponse:
    ok: bool
    task_id: str
    text: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": bool(self.ok),
            "task_id": self.task_id,
            "text": self.text,
            "payload": dict(self.payload),
            "warnings": list(self.warnings),
            "error": self.error,
        }
