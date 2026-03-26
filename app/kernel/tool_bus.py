from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import replace
from typing import Any

from app.contracts import ProviderUnavailableError, ToolCall, ToolExecutionError, ToolResult
from app.contracts.module import BaseToolProvider
from app.kernel.event_bus import EventBus
from app.kernel.registry import ModuleRegistry


class ToolBus:
    def __init__(self, registry: ModuleRegistry, *, event_bus: EventBus | None = None) -> None:
        self.registry = registry
        self.event_bus = event_bus

    def register_provider(self, provider: BaseToolProvider) -> None:
        self.registry.register_provider(provider)

    def execute(self, call: ToolCall) -> ToolResult:
        normalized_call = replace(call, name=str(call.name or "").strip())
        if not normalized_call.name:
            return ToolResult(
                ok=False,
                tool_name="",
                provider_id="",
                error="tool name is required",
                attempts=1,
            )
        provider = self.registry.provider_for_tool(normalized_call.name)
        if provider is None:
            return ToolResult(
                ok=False,
                tool_name=normalized_call.name,
                provider_id="",
                error=f"no provider registered for tool: {normalized_call.name}",
                attempts=1,
            )

        attempts = max(1, int(normalized_call.retries) + 1)
        last_result = ToolResult(
            ok=False,
            tool_name=normalized_call.name,
            provider_id=provider.provider_id,
            error="tool execution did not start",
            attempts=1,
        )
        for attempt in range(1, attempts + 1):
            result = self._execute_once(provider, normalized_call, attempt=attempt)
            last_result = result
            if result.ok:
                return result

        fallback_tools = [str(item or "").strip() for item in normalized_call.fallback_tools if str(item or "").strip()]
        for fallback_name in fallback_tools:
            fallback_provider = self.registry.provider_for_tool(fallback_name)
            if fallback_provider is None:
                continue
            fallback_call = ToolCall(
                name=fallback_name,
                arguments=dict(normalized_call.arguments),
                timeout_sec=normalized_call.timeout_sec,
                retries=max(0, normalized_call.retries),
                fallback_tools=[],
                metadata={**dict(normalized_call.metadata), "fallback_for": normalized_call.name},
            )
            fallback_result = self._execute_once(fallback_provider, fallback_call, attempt=1)
            if fallback_result.ok:
                fallback_result.fallback_used = True
                return fallback_result
            last_result = fallback_result

        return last_result

    def _execute_once(self, provider: BaseToolProvider, call: ToolCall, *, attempt: int) -> ToolResult:
        timeout = float(call.timeout_sec) if call.timeout_sec else 0.0
        timeout = max(0.0, timeout)

        self._publish(
            "tool_dispatch",
            {
                "tool": call.name,
                "provider_id": provider.provider_id,
                "attempt": attempt,
            },
        )

        try:
            if timeout > 0:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(provider.execute, call)
                    raw_result = future.result(timeout=timeout)
            else:
                raw_result = provider.execute(call)
        except TimeoutError:
            return ToolResult(
                ok=False,
                tool_name=call.name,
                provider_id=provider.provider_id,
                error=f"tool timeout after {timeout:.2f}s",
                attempts=attempt,
            )
        except ProviderUnavailableError as exc:
            return ToolResult(
                ok=False,
                tool_name=call.name,
                provider_id=provider.provider_id,
                error=str(exc),
                attempts=attempt,
            )
        except Exception as exc:
            return ToolResult(
                ok=False,
                tool_name=call.name,
                provider_id=provider.provider_id,
                error=f"provider execution failed: {exc}",
                attempts=attempt,
            )

        result = self._coerce_result(raw_result, call=call, provider=provider, attempt=attempt)
        self._publish(
            "tool_result",
            {
                "tool": result.tool_name,
                "provider_id": result.provider_id,
                "ok": result.ok,
                "attempt": result.attempts,
            },
        )
        return result

    def _coerce_result(self, raw_result: Any, *, call: ToolCall, provider: BaseToolProvider, attempt: int) -> ToolResult:
        if isinstance(raw_result, ToolResult):
            raw_result.attempts = attempt
            if not raw_result.tool_name:
                raw_result.tool_name = call.name
            if not raw_result.provider_id:
                raw_result.provider_id = provider.provider_id
            return raw_result
        if isinstance(raw_result, dict):
            return ToolResult(
                ok=bool(raw_result.get("ok")),
                tool_name=call.name,
                provider_id=str(raw_result.get("provider_id") or provider.provider_id),
                data=dict(raw_result),
                error=str(raw_result.get("error") or ""),
                attempts=attempt,
            )
        return ToolResult(
            ok=False,
            tool_name=call.name,
            provider_id=provider.provider_id,
            error="provider returned unsupported result type",
            attempts=attempt,
        )

    def _publish(self, event: str, payload: dict[str, Any]) -> None:
        if self.event_bus is None:
            return
        self.event_bus.publish(event, payload)

    def execute_or_raise(self, call: ToolCall) -> ToolResult:
        result = self.execute(call)
        if result.ok:
            return result
        raise ToolExecutionError(result.error or f"tool execution failed: {call.name}")
