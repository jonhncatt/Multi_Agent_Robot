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


class PatchWriteProvider(BaseToolProvider):
    provider_id = "patch_write_provider"
    supported_tools = ["write.patch"]

    def __init__(self, config: AppConfig, *, executor: LocalToolExecutor | None = None) -> None:
        self._executor = executor or LocalToolExecutor(config)

    def execute(self, call: ToolCall) -> ToolResult:
        if str(call.name or "").strip() != "write.patch":
            return ToolResult(
                ok=False,
                tool_name=call.name,
                provider_id=self.provider_id,
                error=f"unsupported tool: {call.name}",
            )

        args = dict(call.arguments or {})
        operation = str(args.get("operation") or "").strip().lower()

        if operation in {"replace", "patch", ""}:
            payload = self._executor.execute(
                "replace_in_file",
                {
                    "path": str(args.get("path") or ""),
                    "old_text": str(args.get("old_text") or args.get("target") or ""),
                    "new_text": str(args.get("new_text") or args.get("replacement") or ""),
                    "replace_all": bool(args.get("replace_all", False)),
                    "max_replacements": max(1, _coerce_int(args.get("max_replacements"), 1)),
                },
            )
            return self._result(call.name, payload)

        if operation in {"write"}:
            payload = self._executor.execute(
                "write_text_file",
                {
                    "path": str(args.get("path") or ""),
                    "content": str(args.get("content") or ""),
                    "overwrite": bool(args.get("overwrite", True)),
                    "create_dirs": bool(args.get("create_dirs", True)),
                },
            )
            return self._result(call.name, payload)

        if operation in {"append"}:
            payload = self._executor.execute(
                "append_text_file",
                {
                    "path": str(args.get("path") or ""),
                    "content": str(args.get("content") or ""),
                    "create_if_missing": bool(args.get("create_if_missing", True)),
                    "create_dirs": bool(args.get("create_dirs", True)),
                },
            )
            return self._result(call.name, payload)

        return ToolResult(
            ok=False,
            tool_name=call.name,
            provider_id=self.provider_id,
            error=f"unsupported write.patch operation: {operation}",
        )

    def health_check(self) -> HealthReport:
        return HealthReport(
            component_id=self.provider_id,
            status="healthy",
            summary="patch write provider active",
            details={"supported_tools": list(self.supported_tools)},
        )

    def _result(self, tool_name: str, payload: dict[str, Any]) -> ToolResult:
        return ToolResult(
            ok=bool(payload.get("ok")),
            tool_name=tool_name,
            provider_id=self.provider_id,
            data=payload,
            error=str(payload.get("error") or ""),
        )
