from __future__ import annotations

from typing import Any

from app.config import AppConfig
from app.contracts import BaseToolProvider, HealthReport, ToolCall, ToolResult
from app.local_tools import LocalToolExecutor


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


class SessionStoreProvider(BaseToolProvider):
    provider_id = "session_store_provider"
    supported_tools = ["session.lookup"]

    def __init__(self, config: AppConfig, *, executor: LocalToolExecutor | None = None) -> None:
        self._executor = executor or LocalToolExecutor(config)

    def execute(self, call: ToolCall) -> ToolResult:
        if str(call.name or "").strip() != "session.lookup":
            return ToolResult(
                ok=False,
                tool_name=call.name,
                provider_id=self.provider_id,
                error=f"unsupported tool: {call.name}",
            )

        args = dict(call.arguments or {})
        session_id = str(args.get("session_id") or "").strip()
        if session_id:
            payload = self._executor.execute(
                "read_session_history",
                {
                    "session_id": session_id,
                    "max_turns": max(1, _coerce_int(args.get("max_turns"), 80)),
                },
            )
        else:
            payload = self._executor.execute(
                "list_sessions",
                {"max_sessions": max(1, _coerce_int(args.get("max_sessions"), 20))},
            )

        return ToolResult(
            ok=bool(payload.get("ok")),
            tool_name=call.name,
            provider_id=self.provider_id,
            data=payload,
            error=str(payload.get("error") or ""),
        )

    def health_check(self) -> HealthReport:
        return HealthReport(
            component_id=self.provider_id,
            status="healthy",
            summary="session provider active",
            details={"supported_tools": list(self.supported_tools)},
        )
