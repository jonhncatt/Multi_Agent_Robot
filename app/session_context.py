from __future__ import annotations

import re
from typing import Any


_ATTACHMENT_CONTEXT_CLEAR_HINTS = (
    "忽略之前附件",
    "忽略附件",
    "不要参考附件",
    "别参考附件",
    "不要用附件",
    "不基于附件",
    "清空附件",
    "reset attachments",
    "clear attachments",
    "ignore previous attachment",
    "ignore previous attachments",
)
_ATTACHMENT_CONTEXT_FILE_HINTS = (
    "附件",
    "图片",
    "截图",
    "照片",
    "文档",
    "pdf",
    "docx",
    "xlsx",
    "pptx",
    "这个pdf",
    "这个文档",
    "这个文件",
    "上个pdf",
    "上个文档",
    "上个文件",
    "上一个附件",
    "上一个截图",
    "上一个图片",
    "this image",
    "this screenshot",
    "image",
    "screenshot",
)
_ATTACHMENT_CONTEXT_REFERENCE_HINTS = (
    "这个",
    "这份",
    "上个",
    "上一个",
    "刚才",
    "之前",
    "前面",
    "那个",
    "this",
    "that",
    "previous",
    "last",
)
_ATTACHMENT_CONTEXT_ACTION_HINTS = (
    "继续",
    "接着",
    "解析",
    "识别",
    "ocr",
    "转录",
    "抄录",
    "总结",
    "概括",
    "解读",
    "翻译",
    "提取",
    "原文",
    "文中",
    "出现",
    "用法",
    "语法",
    "什么意思",
    "查找",
    "看到",
    "看到了",
    "看一下",
    "继续看",
    "继续读",
    "continue",
    "transcribe",
    "extract text",
    "summarize",
    "analyze",
    "extract",
    "find",
)


def normalize_attachment_ids(raw_ids: list[str] | None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in raw_ids or []:
        item = str(raw or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def message_clears_attachment_context(message: str) -> bool:
    text = str(message or "").strip().lower()
    if not text:
        return False
    return any(hint in text for hint in _ATTACHMENT_CONTEXT_CLEAR_HINTS)


def message_requests_attachment_context(message: str) -> bool:
    raw = str(message or "").strip()
    if not raw:
        return False
    text = raw.lower()
    if any(hint in text for hint in _ATTACHMENT_CONTEXT_FILE_HINTS):
        return True
    has_ref = any(hint in text for hint in _ATTACHMENT_CONTEXT_REFERENCE_HINTS)
    has_action = any(hint in text for hint in _ATTACHMENT_CONTEXT_ACTION_HINTS)
    if has_ref and has_action:
        return True
    if len(raw) <= 40 and (
        any(token in text for token in ("什么意思", "怎么用", "用法", "语法", "在文中", "有没有出现", "是否出现"))
        or bool(re.search(r"[\"'“”‘’「『].{1,24}[\"'“”‘’」』]", raw))
    ):
        return True
    if len(raw) <= 12 and any(token in text for token in ("继续", "接着", "然后呢", "继续吧", "接着说")):
        return True
    if len(raw) <= 24 and re.search(r"\b(continue|go on|next)\b", text):
        return True
    return False


def infer_session_active_attachment_ids(session: dict[str, Any]) -> list[str]:
    if bool(session.get("attachment_context_cleared")):
        return []
    from_state = session.get("active_attachment_ids")
    if isinstance(from_state, list):
        normalized = normalize_attachment_ids([str(item or "") for item in from_state])
        if normalized:
            return normalized

    turns_raw = session.get("turns", [])
    if not isinstance(turns_raw, list):
        return []
    for turn in reversed(turns_raw):
        if not isinstance(turn, dict) or str(turn.get("role") or "") != "user":
            continue
        attachments = turn.get("attachments", [])
        if not isinstance(attachments, list) or not attachments:
            continue
        normalized = normalize_attachment_ids(
            [str(item.get("id") or "") for item in attachments if isinstance(item, dict)]
        )
        if normalized:
            return normalized
    return []


def attachment_context_key(attachment_ids: list[str] | None) -> str:
    normalized = normalize_attachment_ids(attachment_ids)
    if not normalized:
        return ""
    return "|".join(normalized)


def resolve_attachment_context(
    session: dict[str, Any],
    *,
    message: str,
    requested_attachment_ids: list[str] | None,
) -> dict[str, Any]:
    requested = normalize_attachment_ids(requested_attachment_ids)
    remembered = infer_session_active_attachment_ids(session)
    clear_context = message_clears_attachment_context(message)
    attachment_context_mode = "none"
    auto_linked_attachment_ids: list[str] = []

    if clear_context:
        effective_attachment_ids = requested
        attachment_context_mode = "cleared" if not requested else "explicit"
    elif requested:
        effective_attachment_ids = requested
        attachment_context_mode = "explicit"
    elif remembered and message_requests_attachment_context(message):
        effective_attachment_ids = remembered
        attachment_context_mode = "auto_linked"
        auto_linked_attachment_ids = list(remembered)
    else:
        effective_attachment_ids = []

    return {
        "requested_attachment_ids": requested,
        "remembered_attachment_ids": remembered,
        "effective_attachment_ids": effective_attachment_ids,
        "attachment_context_mode": attachment_context_mode,
        "auto_linked_attachment_ids": auto_linked_attachment_ids,
        "clear_attachment_context": clear_context,
        "attachment_context_key": attachment_context_key(effective_attachment_ids),
    }


def apply_attachment_context_result(
    session: dict[str, Any],
    *,
    resolved_attachment_ids: list[str] | None,
    attachment_context_mode: str,
    clear_attachment_context: bool = False,
    requested_attachment_ids: list[str] | None = None,
) -> None:
    resolved = normalize_attachment_ids(resolved_attachment_ids)
    requested = normalize_attachment_ids(requested_attachment_ids)
    if attachment_context_mode in {"explicit", "auto_linked"}:
        session["active_attachment_ids"] = resolved
        session["attachment_context_cleared"] = False
    elif clear_attachment_context and not requested:
        session["active_attachment_ids"] = []
        session["attachment_context_cleared"] = True


def _coerce_route_state_map(raw: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for key, value in raw.items():
        normalized_key = str(key or "").strip()
        if not normalized_key or not isinstance(value, dict):
            continue
        out[normalized_key] = dict(value)
    return out


def resolve_scoped_route_state(
    session: dict[str, Any],
    *,
    attachment_ids: list[str] | None,
) -> tuple[dict[str, Any], str]:
    context_key = attachment_context_key(attachment_ids)
    if context_key:
        scoped = _coerce_route_state_map(session.get("attachment_route_states")).get(context_key)
        if isinstance(scoped, dict) and scoped:
            return dict(scoped), "attachment"
        return {}, "attachment_miss"
    route_state = session.get("route_state")
    if isinstance(route_state, dict) and route_state:
        return dict(route_state), "session"
    return {}, "none"


def store_scoped_route_state(
    session: dict[str, Any],
    *,
    attachment_ids: list[str] | None,
    route_state: dict[str, Any] | None,
) -> None:
    normalized_state = dict(route_state or {})
    session["route_state"] = normalized_state

    context_key = attachment_context_key(attachment_ids)
    if not context_key:
        return

    scoped_states = _coerce_route_state_map(session.get("attachment_route_states"))
    if normalized_state:
        scoped_states[context_key] = normalized_state
    else:
        scoped_states.pop(context_key, None)
    session["attachment_route_states"] = scoped_states
