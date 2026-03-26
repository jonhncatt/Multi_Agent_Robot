from __future__ import annotations

from typing import Any

from app.intent_classifier import IntentClassifier
from app.policy_router import PolicyRouter
from app.route_verifier import RouteVerifier
from app.router_signals import RouterSignalExtractor


class _StubSettings:
    def __init__(self, *, enable_tools: bool = True) -> None:
        self.enable_tools = enable_tools


class _StubAuthManager:
    def auth_summary(self) -> dict[str, Any]:
        return {"available": False, "reason": "stub_no_llm"}


class _StubAgent:
    def __init__(self) -> None:
        self._auth_manager = _StubAuthManager()

    def _looks_like_context_dependent_followup(self, text: str) -> bool:
        lowered = str(text or "").strip().lower()
        markers = ("继续", "刚才", "改成", "翻成", "再", "按刚才")
        return any(marker in lowered for marker in markers)

    def _looks_like_spec_lookup_request(self, user_message: str, attachment_metas: list[dict[str, Any]]) -> bool:
        _ = attachment_metas
        return "spec" in str(user_message or "").lower()

    def _requires_evidence_mode(self, user_message: str, attachment_metas: list[dict[str, Any]]) -> bool:
        _ = attachment_metas
        lowered = str(user_message or "").lower()
        return any(marker in lowered for marker in ("证据", "出处", "来源", "依据"))

    def _attachment_needs_tooling(self, meta: dict[str, Any]) -> bool:
        return bool(meta.get("needs_tooling"))

    def _attachment_is_inline_parseable(self, meta: dict[str, Any]) -> bool:
        return bool(meta.get("inline_parseable", not bool(meta.get("needs_tooling"))))

    def _looks_like_inline_document_payload(self, user_message: str) -> bool:
        return "```" in str(user_message or "")

    def _looks_like_understanding_request(self, user_message: str) -> bool:
        lowered = str(user_message or "").lower()
        return any(marker in lowered for marker in ("解释", "说明", "总结", "整体"))

    def _looks_like_holistic_document_explanation_request(self, user_message: str) -> bool:
        lowered = str(user_message or "").lower()
        return any(marker in lowered for marker in ("整体", "全文"))

    def _looks_like_source_trace_request(self, user_message: str) -> bool:
        lowered = str(user_message or "").lower()
        return any(marker in lowered for marker in ("出处", "来源", "依据"))

    def _looks_like_explicit_tool_confirmation(self, user_message: str) -> bool:
        return str(user_message or "").strip() in {"继续", "执行", "可以"}

    def _looks_like_meeting_minutes_request(self, user_message: str) -> bool:
        return "会议纪要" in str(user_message or "")

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
        )
        return any(marker in lowered for marker in markers)

    def _looks_like_local_code_lookup_request(self, user_message: str, attachment_metas: list[dict[str, Any]]) -> bool:
        _ = attachment_metas
        lowered = str(user_message or "").lower()
        return any(marker in lowered for marker in ("函数", "repo", "代码"))

    def _message_has_explicit_local_path(self, user_message: str) -> bool:
        lowered = str(user_message or "").lower()
        return ("/" in lowered) and ("." in lowered)

    def _has_file_like_lookup_token(self, text: str) -> bool:
        lowered = str(text or "").lower()
        return any(token in lowered for token in (".py", ".ts", ".md", ".json", "repo"))

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
        markers = ("改", "修改", "改成", "翻成", "写成", "重写", "修复", "邮件")
        return any(marker in lowered for marker in markers)



def _build_layers(*, enable_tools: bool = True):
    agent = _StubAgent()
    settings = _StubSettings(enable_tools=enable_tools)
    extractor = RouterSignalExtractor(
        agent,
        news_hints=("news", "新闻", "今日", "today"),
        followup_reference_hints=("这个", "刚才", "上一个", "上一版", "按刚才", "继续"),
        followup_transform_hints=("改成", "翻成", "写成", "表格", "邮件", "修复", "判断"),
    )
    classifier = IntentClassifier(agent)
    policy_router = PolicyRouter(agent)
    verifier = RouteVerifier()
    return settings, extractor, classifier, policy_router, verifier



def _run_pipeline(
    *,
    message: str,
    attachments: list[dict[str, Any]] | None = None,
    route_state: dict[str, Any] | None = None,
    inline_followup_context: bool = False,
    enable_tools: bool = True,
):
    settings, extractor, classifier, policy_router, verifier = _build_layers(enable_tools=enable_tools)
    attachment_metas = list(attachments or [])

    signals = extractor.extract(
        user_message=message,
        attachment_metas=attachment_metas,
        settings=settings,
        route_state=route_state,
        inline_followup_context=inline_followup_context,
    )
    frame = classifier.resolve_frame(
        user_message=message,
        route_state=route_state,
        signals=signals,
    )
    decision, raw = classifier.classify_decision(
        requested_model="gpt-test",
        user_message=message,
        summary="",
        attachment_metas=attachment_metas,
        settings=settings,
        route_state=route_state,
        signals=signals,
    )
    fallback = policy_router.build_fallback_from_decision(
        decision=decision,
        frame=frame,
        settings=settings,
        signals=signals,
    )
    route = policy_router.route_from_decision(
        decision=decision,
        frame=frame,
        settings=settings,
        signals=signals,
        fallback=fallback,
        source_override=str(decision.source or ""),
        force_disable_llm_router=True,
    )
    route, notes = verifier.verify(
        decision=decision,
        route=route,
        signals=signals,
        frame=frame,
    )
    return signals, frame, decision, route, raw, notes



def test_followup_transform_inherits_frame_and_avoids_standard() -> None:
    _, frame, decision, route, _, _ = _run_pipeline(
        message="继续，按刚才那个改成日文邮件",
        route_state={
            "primary_intent": "understanding",
            "active_entities": ["设计摘要"],
            "execution_policy": "understanding_direct",
        },
        inline_followup_context=True,
    )
    assert frame.dominant_intent == "understanding"
    assert decision.inherited_from_state == "understanding"
    assert route["execution_policy"] == "followup_transform_pipeline"
    assert route["task_type"] == "followup_transform"
    assert route["use_planner"] is True



def test_mixed_intent_attachment_to_table_and_email_uses_mixed_pipeline() -> None:
    _, _, decision, route, _, _ = _run_pipeline(
        message="解释这个附件，再整理成表格后写成邮件",
        attachments=[{"inline_parseable": True, "needs_tooling": False}],
    )
    assert decision.mixed_intent is True
    assert route["execution_policy"] == "mixed_intent_planner_pipeline"
    assert route["use_planner"] is True



def test_evidence_plus_repo_fix_has_competing_candidates_and_escalation() -> None:
    _, _, decision, route, _, _ = _run_pipeline(
        message="帮我查这个结论出处，并按 repo 代码给个修复建议",
    )
    scores = {item.intent: float(item.score) for item in decision.candidates}
    assert scores.get("evidence", 0.0) > 0.0
    assert scores.get("generation", 0.0) > 0.0
    assert decision.margin < 0.12
    assert decision.escalation_reason in {"llm_unavailable", "margin_or_ambiguity_or_followup_transform", "small_margin"}
    assert route["use_planner"] is True



def test_low_confidence_short_input_goes_to_clarifying_safe_route() -> None:
    _, _, decision, route, _, _ = _run_pipeline(message="嗯")
    assert decision.confidence < 0.60
    assert route["execution_policy"] == "standard_safe_pipeline"
    assert route["use_planner"] is True
    assert route["use_reviewer"] is True



def test_repo_function_and_modify_prefers_grounded_generation_pipeline() -> None:
    _, _, decision, route, _, _ = _run_pipeline(
        message="帮我看这个 repo 里的函数，并改一下实现",
    )
    candidates = [item.intent for item in decision.candidates[:3]]
    assert "code_lookup" in candidates or decision.second_intent == "code_lookup"
    assert "generation" in candidates or decision.top_intent == "generation"
    assert route["execution_policy"] == "grounded_generation_pipeline"
    assert route["use_reviewer"] is True
    assert route["use_revision"] is True



def test_web_news_with_three_judgements_keeps_web_pipeline_with_review() -> None:
    _, _, decision, route, _, _ = _run_pipeline(
        message="今天 AI 新闻有什么，顺便给个三点判断",
    )
    assert decision.top_intent == "web"
    assert route["execution_policy"] == "web_research_full_pipeline"
    assert route["use_planner"] is True
    assert route["use_reviewer"] is True
