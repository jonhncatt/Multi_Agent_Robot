from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.intent_schema import ActiveTask, TaskControl


_TRANSLATION_MARKERS = (
    "翻译",
    "译成",
    "译为",
    "translate",
    "translation",
)
_START_MARKERS = (
    "开始",
    "开始翻译",
    "start",
    "start translation",
)
_RESUME_MARKERS = (
    "继续",
    "继续翻译",
    "接着",
    "接着翻译",
    "continue",
    "resume",
)
_SENTENCE_MODE_MARKERS = (
    "逐句翻译",
    "逐句",
    "一句一句",
    "sentence by sentence",
)
_RESET_MARKERS = (
    "从第1句开始翻译",
    "从第一句开始翻译",
    "从头开始翻译",
    "从第1句开始",
    "从第一句开始",
    "from sentence 1",
    "from the beginning",
)


class AssembledContext(BaseModel):
    current_user_message: str = ""
    conversation_summary: str = ""
    active_task_summary: str = ""
    active_artifacts: list[str] = Field(default_factory=list)
    user_preferences: dict[str, Any] = Field(default_factory=dict)
    system_rules: list[str] = Field(default_factory=list)
    tool_capabilities: dict[str, Any] = Field(default_factory=dict)
    active_task: ActiveTask | None = None


def coerce_active_task(value: Any) -> ActiveTask | None:
    if isinstance(value, ActiveTask):
        return value
    if not isinstance(value, dict) or not value:
        return None
    try:
        return ActiveTask.model_validate(value)
    except Exception:
        return None


def looks_like_translation_request(message: str) -> bool:
    text = str(message or "").strip().lower()
    if not text:
        return False
    return any(marker in text for marker in _TRANSLATION_MARKERS)


def infer_task_control(user_message: str, active_task: ActiveTask | None) -> TaskControl:
    if active_task is None:
        return TaskControl()

    text = str(user_message or "").strip().lower()
    if not text:
        return TaskControl()

    control = TaskControl(
        start=any(marker in text for marker in _START_MARKERS),
        resume=any(marker in text for marker in _RESUME_MARKERS),
        mode_switch="sentence_by_sentence" if any(marker in text for marker in _SENTENCE_MODE_MARKERS) else None,
        position_reset="sentence:1" if any(marker in text for marker in _RESET_MARKERS) else None,
    )
    if active_task.task_kind == "document_translation" and not control.is_active() and looks_like_translation_request(text):
        control.resume = True
    return control


def detect_pdf_target(attachment_metas: list[dict[str, Any]]) -> tuple[str, str]:
    for meta in attachment_metas or []:
        suffix = str(meta.get("suffix") or "").strip().lower()
        content_type = str(meta.get("content_type") or "").strip().lower()
        original_name = str(meta.get("original_name") or meta.get("name") or "").strip()
        if suffix == ".pdf" or content_type == "application/pdf" or original_name.lower().endswith(".pdf"):
            target_id = str(meta.get("id") or original_name or "pdf")
            return target_id, "pdf"
    return "", ""


class ContextAssembler:
    def assemble(
        self,
        *,
        user_message: str,
        recent_conversation_turns: list[dict[str, Any]] | None,
        active_task: ActiveTask | None,
        route_state: dict[str, Any] | None,
        user_preferences: dict[str, Any] | None,
        tool_availability: dict[str, Any] | None,
        system_rules: list[str] | None,
    ) -> AssembledContext:
        task = coerce_active_task(active_task) or coerce_active_task((route_state or {}).get("active_task"))
        return AssembledContext(
            current_user_message=str(user_message or "").strip(),
            conversation_summary=self._summarize_turns(recent_conversation_turns or []),
            active_task_summary=self._summarize_active_task(task),
            active_artifacts=self._collect_active_artifacts(route_state=route_state, active_task=task),
            user_preferences=dict(user_preferences or {}),
            system_rules=list(system_rules or []),
            tool_capabilities=dict(tool_availability or {}),
            active_task=task,
        )

    def _summarize_turns(self, turns: list[dict[str, Any]]) -> str:
        snippets: list[str] = []
        for turn in turns[-4:]:
            if not isinstance(turn, dict):
                continue
            role = str(turn.get("role") or "unknown").strip()
            text = str(turn.get("text") or turn.get("content") or "").strip().replace("\n", " ")
            if not text:
                continue
            if len(text) > 120:
                text = text[:117].rstrip() + "..."
            snippets.append(f"{role}: {text}")
        return " | ".join(snippets)

    def _summarize_active_task(self, task: ActiveTask | None) -> str:
        if task is None:
            return ""
        progress = task.progress or {}
        progress_text = ", ".join(f"{key}={value}" for key, value in sorted(progress.items())) or "none"
        return (
            f"task_kind={task.task_kind}; "
            f"target={task.target_type}:{task.target_id}; "
            f"mode={task.mode or 'none'}; "
            f"progress={progress_text}; "
            f"started={task.started}; finished={task.finished}"
        )

    def _collect_active_artifacts(
        self,
        *,
        route_state: dict[str, Any] | None,
        active_task: ActiveTask | None,
    ) -> list[str]:
        artifacts: list[str] = []
        for item in list((route_state or {}).get("active_artifacts") or []):
            text = str(item or "").strip()
            if text and text not in artifacts:
                artifacts.append(text)
        if active_task is not None:
            target = f"{active_task.target_type}:{active_task.target_id}"
            if target not in artifacts:
                artifacts.append(target)
        return artifacts[:12]
