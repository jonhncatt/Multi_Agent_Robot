from __future__ import annotations

from typing import Any


PIPELINE_HOOK_HANDLERS: dict[str, str] = {
    "before_route_finalize": "_hook_before_route_finalize",
    "before_worker_prompt": "_hook_before_worker_prompt",
    "before_reviewer": "_hook_before_reviewer",
    "after_planner": "_hook_after_planner",
    "before_structurer": "_hook_before_structurer",
}


def pipeline_route_snapshot(route: dict[str, Any] | None) -> dict[str, Any]:
    payload = dict(route or {})
    return {
        "task_type": str(payload.get("task_type") or "standard").strip(),
        "primary_intent": str(payload.get("primary_intent") or "").strip(),
        "execution_policy": str(payload.get("execution_policy") or "").strip(),
        "use_worker_tools": bool(payload.get("use_worker_tools")),
        "use_planner": bool(payload.get("use_planner")),
        "use_reviewer": bool(payload.get("use_reviewer")),
        "use_revision": bool(payload.get("use_revision")),
        "use_structurer": bool(payload.get("use_structurer")),
    }


def build_pipeline_hook_telemetry(
    *,
    phase: str,
    handler_name: str,
    hook_payload: dict[str, Any],
    route_before: dict[str, Any] | None = None,
    route_after: dict[str, Any] | None = None,
) -> dict[str, Any]:
    before = pipeline_route_snapshot(route_before)
    after = pipeline_route_snapshot(route_after)
    changed_fields = [key for key in after.keys() if before.get(key) != after.get(key)]
    return {
        "phase": str(phase or "").strip(),
        "handler": str(handler_name or "").strip(),
        "changed_fields": changed_fields,
        "route_changed": bool(changed_fields),
        "task_type_before": str(before.get("task_type") or ""),
        "task_type_after": str(after.get("task_type") or ""),
        "primary_intent_before": str(before.get("primary_intent") or ""),
        "primary_intent_after": str(after.get("primary_intent") or ""),
        "execution_policy_before": str(before.get("execution_policy") or ""),
        "execution_policy_after": str(after.get("execution_policy") or ""),
        "prompt_injection_count": len(hook_payload.get("prompt_injections") or []),
        "trace_note_count": len(hook_payload.get("trace_notes") or []),
        "debug_entry_count": len(hook_payload.get("debug_entries") or []),
    }


def build_pipeline_hook_panel_payload(items: list[dict[str, Any]]) -> tuple[str, list[str]]:
    if not items:
        return "当前未命中 pipeline hooks。", []
    latest = items[-1]
    summary = f"已命中 {len(items)} 个 pipeline hook；最近阶段={str(latest.get('phase') or '(unknown)')}。"
    bullets: list[str] = []
    for item in items[-6:]:
        changed_fields = item.get("changed_fields") or []
        changed_text = ", ".join(str(field) for field in changed_fields[:4]) if changed_fields else "(none)"
        bullets.append(
            f"{item.get('phase')}: handler={item.get('handler') or '(unknown)'}, "
            f"changed={str(bool(item.get('route_changed'))).lower()}, fields={changed_text}"
        )
    return summary, bullets
