from __future__ import annotations

import json
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from app.context_assembly import ContextAssembler
from app.intent_classifier import IntentClassifier
from app.intent_schema import ActiveTask
from app.policy_router import PolicyRouter
from app.route_trace import build_route_trace
from app.route_verifier import RouteVerifier
from app.router_signals import RouterSignalExtractor


class StubSettings:
    def __init__(self, *, enable_tools: bool = True) -> None:
        self.enable_tools = enable_tools
        self.response_style = "normal"


class StubAuthManager:
    def __init__(self, *, available: bool) -> None:
        self._available = available

    def auth_summary(self) -> dict[str, Any]:
        return {
            "available": self._available,
            "reason": "stub_llm_available" if self._available else "stub_no_llm",
        }


@dataclass
class StubMessage:
    content: str


class StubAgent:
    def __init__(self, *, llm_available: bool = False, llm_payload: dict[str, Any] | None = None) -> None:
        self._auth_manager = StubAuthManager(available=llm_available)
        self._llm_payload = dict(llm_payload or {})
        self._SystemMessage = StubMessage
        self._HumanMessage = StubMessage
        self.config = SimpleNamespace(summary_model="gpt-test-summary")

    def _looks_like_context_dependent_followup(self, text: str) -> bool:
        lowered = str(text or "").strip().lower()
        markers = ("继续", "刚才", "改成", "翻成", "再", "按刚才", "continue", "rewrite", "shorter")
        return any(marker in lowered for marker in markers)

    def _looks_like_spec_lookup_request(self, user_message: str, attachment_metas: list[dict[str, Any]]) -> bool:
        _ = attachment_metas
        return "spec" in str(user_message or "").lower()

    def _requires_evidence_mode(self, user_message: str, attachment_metas: list[dict[str, Any]]) -> bool:
        _ = attachment_metas
        lowered = str(user_message or "").lower()
        return any(marker in lowered for marker in ("证据", "出处", "来源", "依据", "source", "evidence"))

    def _attachment_needs_tooling(self, meta: dict[str, Any]) -> bool:
        return bool(meta.get("needs_tooling"))

    def _attachment_is_inline_parseable(self, meta: dict[str, Any]) -> bool:
        return bool(meta.get("inline_parseable", not bool(meta.get("needs_tooling"))))

    def _looks_like_inline_document_payload(self, user_message: str) -> bool:
        return "```" in str(user_message or "")

    def _looks_like_understanding_request(self, user_message: str) -> bool:
        lowered = str(user_message or "").lower()
        return any(marker in lowered for marker in ("解释", "说明", "总结", "整体", "explain", "summarize"))

    def _looks_like_holistic_document_explanation_request(self, user_message: str) -> bool:
        lowered = str(user_message or "").lower()
        return any(marker in lowered for marker in ("整体", "全文", "full doc"))

    def _looks_like_source_trace_request(self, user_message: str) -> bool:
        lowered = str(user_message or "").lower()
        return any(marker in lowered for marker in ("出处", "来源", "依据", "source", "evidence"))

    def _looks_like_explicit_tool_confirmation(self, user_message: str) -> bool:
        return str(user_message or "").strip().lower() in {"继续", "执行", "可以", "continue", "go ahead", "开始"}

    def _looks_like_meeting_minutes_request(self, user_message: str) -> bool:
        lowered = str(user_message or "").lower()
        return "会议纪要" in lowered or "meeting minutes" in lowered

    def _looks_like_internal_ticket_reference(self, user_message: str) -> bool:
        return "jira" in str(user_message or "").lower()

    def _request_likely_requires_tools(self, user_message: str, attachment_metas: list[dict[str, Any]]) -> bool:
        if attachment_metas:
            return True
        lowered = str(user_message or "").lower()
        markers = (
            "查",
            "定位",
            "repo",
            "函数",
            "新闻",
            "today",
            "web",
            "修改",
            "修复",
            "代码",
            "find",
            "lookup",
            "翻译",
            "translate",
        )
        return any(marker in lowered for marker in markers)

    def _looks_like_local_code_lookup_request(self, user_message: str, attachment_metas: list[dict[str, Any]]) -> bool:
        _ = attachment_metas
        lowered = str(user_message or "").lower()
        return any(marker in lowered for marker in ("函数", "repo", "代码", "function", "file"))

    def _message_has_explicit_local_path(self, user_message: str) -> bool:
        lowered = str(user_message or "").lower()
        return ("/" in lowered) and ("." in lowered)

    def _has_file_like_lookup_token(self, text: str) -> bool:
        lowered = str(text or "").lower()
        return any(token in lowered for token in (".py", ".ts", ".md", ".json", "repo", ".pdf"))

    def _should_auto_search_default_roots(self, user_message: str, attachment_metas: list[dict[str, Any]]) -> bool:
        _ = attachment_metas
        return "默认目录" in str(user_message or "")

    def _infer_followup_primary_intent_from_state(
        self,
        *,
        user_message: str,
        route_state: dict[str, Any] | None,
        signals: dict[str, Any],
    ) -> str:
        _ = user_message, signals
        return str((route_state or {}).get("primary_intent") or "")

    def _looks_like_write_or_edit_action(self, text: str) -> bool:
        lowered = str(text or "").lower()
        markers = (
            "改",
            "修改",
            "改成",
            "翻成",
            "翻译",
            "写成",
            "重写",
            "修复",
            "邮件",
            "write",
            "rewrite",
            "translate",
            "patch",
            "edit",
            "fix",
        )
        return any(marker in lowered for marker in markers)

    def _summarize_attachment_metas_for_agents(self, attachment_metas: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [dict(item) for item in attachment_metas]

    def _invoke_chat_with_runner(
        self,
        *,
        messages: list[StubMessage],
        model: str,
        max_output_tokens: int,
        enable_tools: bool,
    ) -> tuple[StubMessage, None, str, list[str]]:
        _ = messages, max_output_tokens, enable_tools
        return StubMessage(content=json.dumps(self._llm_payload, ensure_ascii=False)), None, model, []

    def _content_to_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(str(item) for item in content)
        return str(content or "")

    def _parse_json_object(self, raw_text: str) -> dict[str, Any] | None:
        try:
            parsed = json.loads(str(raw_text or ""))
        except Exception:
            return None
        return parsed if isinstance(parsed, dict) else None

    def _normalize_string_list(self, values: Any, *, limit: int, item_limit: int) -> list[str]:
        if not isinstance(values, list):
            return []
        out: list[str] = []
        for item in values:
            text = str(item or "").strip()
            if not text:
                continue
            text = text[:item_limit]
            if text not in out:
                out.append(text)
            if len(out) >= limit:
                break
        return out

    def _normalize_specialists(self, values: Any) -> list[str]:
        if not isinstance(values, list):
            return []
        out: list[str] = []
        for item in values:
            text = str(item or "").strip()
            if text and text not in out:
                out.append(text)
        return out


def build_layers(*, enable_tools: bool = True, llm_available: bool = False, llm_payload: dict[str, Any] | None = None):
    agent = StubAgent(llm_available=llm_available, llm_payload=llm_payload)
    settings = StubSettings(enable_tools=enable_tools)
    extractor = RouterSignalExtractor(
        agent,
        news_hints=("news", "新闻", "今日", "today"),
        followup_reference_hints=("这个", "刚才", "上一个", "上一版", "按刚才", "继续", "that", "this", "previous"),
        followup_transform_hints=("改成", "翻成", "写成", "表格", "邮件", "修复", "判断", "rewrite", "translate"),
    )
    classifier = IntentClassifier(agent)
    policy_router = PolicyRouter(agent)
    verifier = RouteVerifier()
    assembler = ContextAssembler()
    return settings, extractor, classifier, policy_router, verifier, assembler


def pdf_attachment(*, attachment_id: str = "pdf-1", name: str = "document.pdf", needs_tooling: bool = True) -> dict[str, Any]:
    return {
        "id": attachment_id,
        "name": name,
        "original_name": name,
        "suffix": ".pdf",
        "content_type": "application/pdf",
        "needs_tooling": needs_tooling,
        "inline_parseable": not needs_tooling,
    }


def translation_active_task(*, target_id: str = "pdf-1", mode: str = "full", progress: dict[str, Any] | None = None) -> dict[str, Any]:
    return ActiveTask(
        task_id="task_pdf_translation",
        task_kind="document_translation",
        target_id=target_id,
        target_type="pdf",
        mode=mode,
        progress=dict(progress or {}),
        started=False,
        finished=False,
        last_user_control="",
    ).model_dump()


def run_pipeline(
    *,
    message: str,
    attachments: list[dict[str, Any]] | None = None,
    route_state: dict[str, Any] | None = None,
    recent_turns: list[dict[str, Any]] | None = None,
    inline_followup_context: bool = False,
    enable_tools: bool = True,
    force_rules_only: bool = False,
    llm_available: bool = False,
    llm_payload: dict[str, Any] | None = None,
):
    settings, extractor, classifier, policy_router, verifier, assembler = build_layers(
        enable_tools=enable_tools,
        llm_available=llm_available,
        llm_payload=llm_payload,
    )
    attachment_metas = list(attachments or [])
    effective_route_state = dict(route_state or {})

    signals = extractor.extract(
        user_message=message,
        attachment_metas=attachment_metas,
        settings=settings,
        route_state=effective_route_state,
        inline_followup_context=inline_followup_context,
    )
    assembled_context = assembler.assemble(
        user_message=message,
        recent_conversation_turns=recent_turns or [],
        active_task=effective_route_state.get("active_task"),
        route_state=effective_route_state,
        user_preferences={"response_style": settings.response_style},
        tool_availability={
            "enable_tools": bool(enable_tools),
            "has_attachments": bool(attachment_metas),
            "attachment_count": len(attachment_metas),
        },
        system_rules=[
            "LLM is the primary semantic classifier; rules are hints and fallback only.",
            "If there is an active task, follow-up control should bind to that task before opening a new one.",
            "Document translation controls should execute directly on the active PDF task instead of asking repeated slot-filling confirmations.",
            "Only use safe clarifying route when there is no active task or no actionable file target.",
        ],
    )
    frame, candidates, decision, raw = classifier.classify_with_context(
        requested_model="gpt-test",
        user_message=message,
        summary="",
        attachment_metas=attachment_metas,
        settings=settings,
        route_state=effective_route_state,
        signals=signals,
        assembled_context=assembled_context,
        force_rules_only=force_rules_only,
    )
    fallback = policy_router.build_fallback_from_decision(
        decision=decision,
        frame=frame,
        settings=settings,
        signals=signals,
        assembled_context=assembled_context,
    )
    route = policy_router.route_from_decision(
        decision=decision,
        frame=frame,
        settings=settings,
        signals=signals,
        fallback=fallback,
        assembled_context=assembled_context,
        source_override=str(decision.source or ""),
        force_disable_llm_router=True,
    )
    route, notes = verifier.verify(
        decision=decision,
        route=route,
        signals=signals,
        frame=frame,
        assembled_context=assembled_context,
    )
    trace = build_route_trace(
        request_id="test-request",
        timestamp="2026-03-27T00:00:00+00:00",
        user_message=message,
        signals=signals,
        frame=frame,
        decision=decision,
        route=route,
        assembled_context=assembled_context,
        runtime_override_notes=[],
        runtime_override_actions=[],
    )
    return {
        "signals": signals,
        "frame": frame,
        "candidates": candidates,
        "decision": decision,
        "route": route,
        "raw": raw,
        "notes": notes,
        "trace": trace,
        "assembled_context": assembled_context,
    }
