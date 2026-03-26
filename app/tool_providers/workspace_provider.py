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


class LocalWorkspaceProvider(BaseToolProvider):
    provider_id = "local_workspace_provider"
    supported_tools = ["workspace.read", "workspace.write"]

    def __init__(self, config: AppConfig, *, executor: LocalToolExecutor | None = None) -> None:
        self._executor = executor or LocalToolExecutor(config)

    def execute(self, call: ToolCall) -> ToolResult:
        tool_name = str(call.name or "").strip()
        if tool_name == "workspace.read":
            args = dict(call.arguments or {})
            payload = self._executor.execute(
                "list_directory",
                {
                    "path": str(args.get("path") or "."),
                    "max_entries": max(1, _coerce_int(args.get("max_entries"), 200)),
                },
            )
            return self._result(tool_name, payload)

        if tool_name == "workspace.write":
            return self._execute_workspace_write(call)

        return ToolResult(
            ok=False,
            tool_name=tool_name,
            provider_id=self.provider_id,
            error=f"unsupported tool: {tool_name}",
        )

    def health_check(self) -> HealthReport:
        docker_ok, docker_msg = self._executor.docker_status()
        return HealthReport(
            component_id=self.provider_id,
            status="healthy",
            summary="workspace provider active",
            details={
                "supported_tools": list(self.supported_tools),
                "docker_available": bool(docker_ok),
                "docker_message": docker_msg,
            },
        )

    def _execute_workspace_write(self, call: ToolCall) -> ToolResult:
        args = dict(call.arguments or {})
        operation = str(args.get("operation") or "").strip().lower()

        if operation in {"copy", "copy_file"} or ("src_path" in args and "dst_path" in args):
            payload = self._executor.execute(
                "copy_file",
                {
                    "src_path": str(args.get("src_path") or ""),
                    "dst_path": str(args.get("dst_path") or ""),
                    "overwrite": bool(args.get("overwrite", True)),
                    "create_dirs": bool(args.get("create_dirs", True)),
                },
            )
            return self._result(call.name, payload)

        if operation in {"extract_zip"} or "zip_path" in args:
            payload = self._executor.execute(
                "extract_zip",
                {
                    "zip_path": str(args.get("zip_path") or ""),
                    "dst_dir": str(args.get("dst_dir") or ""),
                    "overwrite": bool(args.get("overwrite", True)),
                    "create_dirs": bool(args.get("create_dirs", True)),
                    "max_entries": max(1, _coerce_int(args.get("max_entries"), 20000)),
                    "max_total_bytes": max(1024, _coerce_int(args.get("max_total_bytes"), 524288000)),
                },
            )
            return self._result(call.name, payload)

        if operation in {"extract_msg_attachments"} or "msg_path" in args:
            payload = self._executor.execute(
                "extract_msg_attachments",
                {
                    "msg_path": str(args.get("msg_path") or ""),
                    "dst_dir": str(args.get("dst_dir") or ""),
                    "overwrite": bool(args.get("overwrite", True)),
                    "create_dirs": bool(args.get("create_dirs", True)),
                    "max_attachments": max(1, _coerce_int(args.get("max_attachments"), 500)),
                    "max_total_bytes": max(1024, _coerce_int(args.get("max_total_bytes"), 524288000)),
                },
            )
            return self._result(call.name, payload)

        if operation in {"append", "append_text"}:
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

        if operation in {"write", "write_text", "create", "overwrite", ""}:
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

        return ToolResult(
            ok=False,
            tool_name=call.name,
            provider_id=self.provider_id,
            error=f"unsupported workspace.write operation: {operation}",
        )

    def _result(self, tool_name: str, payload: dict[str, Any]) -> ToolResult:
        return ToolResult(
            ok=bool(payload.get("ok")),
            tool_name=tool_name,
            provider_id=self.provider_id,
            data=payload,
            error=str(payload.get("error") or ""),
        )
