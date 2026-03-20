from __future__ import annotations

from typing import Any

from app.agents.runtime_profiles import RuntimeProfile
from app.role_runtime import RoleContext, RoleResult, RoleSpec


def validate_role_spec(spec: RoleSpec) -> dict[str, Any]:
    errors: list[str] = []
    if not str(spec.role or "").strip():
        errors.append("missing role")
    if str(spec.kind or "").strip() not in {"agent", "processor", "hybrid"}:
        errors.append(f"invalid kind: {spec.kind}")
    return {
        "ok": not errors,
        "role": str(spec.role or ""),
        "kind": str(spec.kind or ""),
        "output_keys": list(spec.output_keys),
        "errors": errors,
    }


def validate_role_context(context: RoleContext) -> dict[str, Any]:
    errors: list[str] = []
    if not str(context.role or "").strip():
        errors.append("missing context.role")
    if not isinstance(context.route, dict):
        errors.append("context.route must be dict")
    if not isinstance(context.attachment_metas, list):
        errors.append("context.attachment_metas must be list")
    if not isinstance(context.tool_events, list):
        errors.append("context.tool_events must be list")
    return {
        "ok": not errors,
        "role": str(context.role or ""),
        "primary_user_request": context.primary_user_request,
        "errors": errors,
    }


def validate_role_result(result: RoleResult) -> dict[str, Any]:
    errors: list[str] = []
    spec_check = validate_role_spec(result.spec)
    context_check = validate_role_context(result.context)
    if not spec_check["ok"]:
        errors.extend([f"spec: {item}" for item in spec_check["errors"]])
    if not context_check["ok"]:
        errors.extend([f"context: {item}" for item in context_check["errors"]])
    if not isinstance(result.payload, dict):
        errors.append("payload must be dict")
    missing_output_keys = [
        key
        for key in result.spec.output_keys
        if str(key or "").strip() and key not in result.payload
    ]
    if missing_output_keys:
        errors.append(f"missing output keys: {', '.join(missing_output_keys)}")
    return {
        "ok": not errors,
        "role": str(result.spec.role or ""),
        "output_keys": list(result.spec.output_keys),
        "missing_output_keys": missing_output_keys,
        "errors": errors,
    }


def validate_runtime_profile(profile: RuntimeProfile) -> dict[str, Any]:
    errors: list[str] = []
    if not str(profile.profile_id or "").strip():
        errors.append("missing profile_id")
    if not str(profile.title or "").strip():
        errors.append("missing title")
    if not isinstance(profile.preferred_specialists, tuple):
        errors.append("preferred_specialists must be tuple")
    return {
        "ok": not errors,
        "profile_id": str(profile.profile_id or ""),
        "errors": errors,
        "preferred_specialists": list(profile.preferred_specialists),
    }
