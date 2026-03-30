from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.contracts import BaseBusinessModule, TaskRequest
from app.kernel.registry import ModuleRegistry


_GENERIC_CHAT_TASK_TYPES = {"", "chat", "task.chat"}
_EXPLICIT_TASK_TYPE_MAPPING = {
    "office": "office_module",
    "task.office": "office_module",
    "research": "research_module",
    "task.research": "research_module",
    "task.investigation": "research_module",
    "task.research.swarm": "research_module",
    "coding": "coding_module",
    "task.coding": "coding_module",
    "adaptation": "adaptation_module",
    "task.adaptation": "adaptation_module",
}
_AUTO_ROUTABLE_MODULE_IDS = {"office_module", "research_module", "coding_module", "adaptation_module"}

_RESEARCH_CONTEXT_KEYS = {
    "research_query",
    "swarm_inputs",
    "fetch_top_result",
    "fetch_max_chars",
    "max_results",
}

_RESEARCH_KEYWORDS = {
    "research",
    "investigate",
    "investigation",
    "analyze",
    "analysis",
    "compare",
    "comparison",
    "source",
    "sources",
    "citation",
    "citations",
    "evidence",
    "fact check",
    "latest",
    "news",
    "market",
    "trend",
    "competitor",
    "benchmark",
    "findings",
    "report with sources",
    "调研",
    "研究",
    "查资料",
    "资料",
    "来源",
    "出处",
    "证据",
    "对比",
    "比较",
    "新闻",
    "最新",
    "趋势",
    "竞品",
    "市场",
    "互联网新闻",
    "リサーチ",
    "調査",
    "出典",
    "ソース",
    "比較",
    "ニュース",
    "最新情報",
}

_CODING_KEYWORDS = {
    "code",
    "coding",
    "bug",
    "fix",
    "patch",
    "refactor",
    "repository",
    "repo",
    "implement",
    "test failure",
    "write code",
    "代码",
    "修 bug",
    "修复",
    "补丁",
    "仓库",
    "代码库",
    "実装",
    "バグ",
    "修正",
    "コード",
}

_ADAPTATION_KEYWORDS = {
    "adaptation",
    "validate",
    "activate",
    "candidate rollout",
    "migration candidate",
    "升级验证",
    "激活",
    "候选版本",
    "迁移验证",
    "適応",
    "検証",
    "移行",
}

_OFFICE_BIAS_KEYWORDS = {
    "email",
    "draft",
    "rewrite",
    "translate",
    "translation",
    "meeting",
    "agenda",
    "memo",
    "document",
    "attachment",
    "spreadsheet",
    "ppt",
    "reply",
    "邮件",
    "写邮件",
    "润色",
    "翻译",
    "会议",
    "纪要",
    "附件",
    "文档",
    "表格",
    "总结",
    "メール",
    "翻訳",
    "会議",
    "添付",
    "文書",
}


@dataclass(slots=True)
class ModuleSelectionDecision:
    module: BaseBusinessModule | None
    module_id: str
    selection_mode: str
    reasons: list[str] = field(default_factory=list)
    candidate_scores: dict[str, float] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        summary = f"{self.selection_mode}:{self.module_id}" if self.module_id else self.selection_mode
        if self.reasons:
            summary = f"{summary} ({'; '.join(self.reasons[:3])})"
        return {
            "module_id": self.module_id,
            "selection_mode": self.selection_mode,
            "reasons": list(self.reasons),
            "candidate_scores": dict(self.candidate_scores),
            "selection_summary": summary,
        }


class IntelligentModuleSelector:
    """Select the best business module without pushing business orchestration into the kernel."""

    def __init__(self, registry: ModuleRegistry) -> None:
        self._registry = registry

    def select(self, request: TaskRequest, module_id: str | None = None) -> ModuleSelectionDecision:
        explicit = str(module_id or request.context.get("module_id") or "").strip()
        if explicit:
            return self._decision(explicit, "explicit_module_id", ["explicit module_id override"])

        task_type = str(request.task_type or "").strip().lower()
        explicit_target = _EXPLICIT_TASK_TYPE_MAPPING.get(task_type)
        if explicit_target is not None:
            return self._decision(explicit_target, "explicit_task_type", [f"task_type={task_type}"])

        if task_type not in _GENERIC_CHAT_TASK_TYPES:
            return self._decision("office_module", "fallback_default", [f"unmapped task_type={task_type or 'unknown'}"])

        return self._auto_select_for_chat(request)

    def _auto_select_for_chat(self, request: TaskRequest) -> ModuleSelectionDecision:
        candidates = self._auto_candidates()
        if "office_module" not in candidates:
            office = self._registry.get_business_module("office_module")
            candidates["office_module"] = office
        scores = {module_id: 0.0 for module_id in candidates if candidates[module_id] is not None}
        reasons: list[str] = []
        message = str(request.message or "").strip()
        lowered = message.lower()
        context = dict(request.context or {})
        attachments = list(request.attachments or [])

        if "office_module" in scores:
            scores["office_module"] = 1.0

        if attachments and "office_module" in scores:
            scores["office_module"] += 2.5
            reasons.append("attachments bias to office workflow")

        research_score = self._research_score(lowered, message, context)
        coding_score = self._keyword_score(lowered, message, _CODING_KEYWORDS)
        adaptation_score = self._keyword_score(lowered, message, _ADAPTATION_KEYWORDS)
        office_bias = self._keyword_score(lowered, message, _OFFICE_BIAS_KEYWORDS)

        if "research_module" in scores and research_score > 0:
            scores["research_module"] += research_score
            reasons.append("research intent detected")
        if "coding_module" in scores and coding_score > 0:
            scores["coding_module"] += coding_score
            reasons.append("coding intent detected")
        if "adaptation_module" in scores and adaptation_score > 0:
            scores["adaptation_module"] += adaptation_score
            reasons.append("adaptation intent detected")
        if "office_module" in scores and office_bias > 0:
            scores["office_module"] += office_bias
            reasons.append("office workflow bias detected")

        selected_module_id = "office_module"
        if scores:
            selected_module_id = max(
                sorted(scores),
                key=lambda item: (scores[item], item == "research_module", item == "office_module"),
            )

        if selected_module_id != "office_module" and scores.get(selected_module_id, 0.0) <= scores.get("office_module", 0.0):
            selected_module_id = "office_module"

        mode = "auto_intent"
        if selected_module_id == "office_module" and research_score == coding_score == adaptation_score == 0:
            mode = "auto_default"
            reasons.append("no stronger non-office signal")

        return self._decision(selected_module_id, mode, reasons, candidate_scores=scores)

    def _auto_candidates(self) -> dict[str, BaseBusinessModule | None]:
        candidates: dict[str, BaseBusinessModule | None] = {}
        for module in self._registry.list_modules(kind="business"):
            module_id = str(module.manifest.module_id or "").strip()
            if module_id not in _AUTO_ROUTABLE_MODULE_IDS:
                continue
            state = self._registry.module_state(module_id)
            if state.lifecycle == "disabled" or state.health_status == "unhealthy":
                continue
            # Only auto-route into modules that are healthy enough to be default choices.
            if module_id != "office_module" and state.health_status and state.health_status != "healthy":
                continue
            candidates[module_id] = module
        return candidates

    def _research_score(self, lowered: str, original: str, context: dict[str, Any]) -> float:
        score = 0.0
        for key in _RESEARCH_CONTEXT_KEYS:
            value = context.get(key)
            if key == "swarm_inputs" and isinstance(value, list) and len(value) >= 2:
                score += 6.0
            elif value:
                score += 3.0
        score += self._keyword_score(lowered, original, _RESEARCH_KEYWORDS)
        if any(token in lowered for token in ("source", "sources", "citation", "evidence", "latest", "news")):
            score += 1.0
        if any(token in original for token in ("来源", "证据", "新闻", "最新", "出处", "调研", "研究")):
            score += 1.0
        return score

    def _keyword_score(self, lowered: str, original: str, keywords: set[str]) -> float:
        score = 0.0
        for keyword in keywords:
            if keyword.isascii():
                if keyword in lowered:
                    score += 1.0
            elif keyword in original:
                score += 1.0
        return score

    def _decision(
        self,
        module_id: str,
        selection_mode: str,
        reasons: list[str],
        *,
        candidate_scores: dict[str, float] | None = None,
    ) -> ModuleSelectionDecision:
        module = self._registry.get_business_module(module_id)
        return ModuleSelectionDecision(
            module=module,
            module_id=module_id,
            selection_mode=selection_mode,
            reasons=list(dict.fromkeys(item for item in reasons if str(item).strip())),
            candidate_scores=dict(candidate_scores or {}),
        )
