from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


HealthStatus = Literal["healthy", "degraded", "unhealthy"]


@dataclass(slots=True)
class HealthReport:
    component_id: str
    status: HealthStatus = "healthy"
    summary: str = ""
    details: dict[str, object] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status != "unhealthy"

    def to_dict(self) -> dict[str, object]:
        return {
            "component_id": self.component_id,
            "status": self.status,
            "summary": self.summary,
            "details": dict(self.details),
            "ok": self.ok,
        }
