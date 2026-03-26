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


class HttpWebProvider(BaseToolProvider):
    provider_id = "http_web_provider"
    supported_tools = ["web.search", "web.fetch"]

    def __init__(self, config: AppConfig, *, executor: LocalToolExecutor | None = None) -> None:
        self._config = config
        self._executor = executor or LocalToolExecutor(config)

    def execute(self, call: ToolCall) -> ToolResult:
        tool_name = str(call.name or "").strip()
        args = dict(call.arguments or {})

        if tool_name == "web.search":
            payload = self._executor.execute(
                "search_web",
                {
                    "query": str(args.get("query") or ""),
                    "max_results": max(1, _coerce_int(args.get("max_results"), 5)),
                    "timeout_sec": max(3, _coerce_int(args.get("timeout_sec"), self._config.web_fetch_timeout_sec)),
                },
            )
            return self._result(tool_name, payload)

        if tool_name == "web.fetch":
            download_mode = bool(args.get("download", False)) or bool(str(args.get("dst_path") or "").strip())
            if download_mode:
                payload = self._executor.execute(
                    "download_web_file",
                    {
                        "url": str(args.get("url") or ""),
                        "dst_path": str(args.get("dst_path") or ""),
                        "overwrite": bool(args.get("overwrite", True)),
                        "create_dirs": bool(args.get("create_dirs", True)),
                        "timeout_sec": max(3, _coerce_int(args.get("timeout_sec"), 20)),
                        "max_bytes": max(1024, _coerce_int(args.get("max_bytes"), 52428800)),
                    },
                )
            else:
                payload = self._executor.execute(
                    "fetch_web",
                    {
                        "url": str(args.get("url") or ""),
                        "max_chars": max(512, _coerce_int(args.get("max_chars"), self._config.web_fetch_max_chars)),
                        "timeout_sec": max(3, _coerce_int(args.get("timeout_sec"), self._config.web_fetch_timeout_sec)),
                    },
                )
            return self._result(tool_name, payload)

        return ToolResult(
            ok=False,
            tool_name=tool_name,
            provider_id=self.provider_id,
            error=f"unsupported tool: {tool_name}",
        )

    def health_check(self) -> HealthReport:
        return HealthReport(
            component_id=self.provider_id,
            status="healthy",
            summary="web provider active",
            details={
                "supported_tools": list(self.supported_tools),
                "allow_all_domains": bool(self._config.web_allow_all_domains),
                "allowed_domains_count": len(self._config.web_allowed_domains),
            },
        )

    def _result(self, tool_name: str, payload: dict[str, Any]) -> ToolResult:
        return ToolResult(
            ok=bool(payload.get("ok")),
            tool_name=tool_name,
            provider_id=self.provider_id,
            data=payload,
            error=str(payload.get("error") or ""),
        )
