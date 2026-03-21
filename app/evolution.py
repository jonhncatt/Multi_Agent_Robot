from __future__ import annotations

import json
import re
import threading
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_EN_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "have",
    "into",
    "your",
    "about",
    "what",
    "when",
    "where",
    "which",
    "would",
    "should",
    "could",
    "please",
    "help",
    "need",
    "give",
    "make",
    "show",
    "today",
    "news",
}

_ZH_STOPWORDS = {
    "这个",
    "那个",
    "我们",
    "你们",
    "你是",
    "就是",
    "然后",
    "因为",
    "所以",
    "现在",
    "之前",
    "之后",
    "一下",
    "一个",
    "已经",
    "还是",
    "继续",
    "直接",
    "整体",
    "怎么",
    "什么",
    "为什么",
    "可以",
    "希望",
    "里面",
    "这里",
    "那个",
    "这个",
    "文档",
    "附件",
    "助手",
}

_PUNCT_SPLIT_RE = re.compile(r"[\s,.;:!?/\\|()\[\]{}<>\-_=+~`'\"，。！？；：、（）【】《》]+")
_ASCII_TERM_RE = re.compile(r"[A-Za-z][A-Za-z0-9_+\-]{2,}")
_CJK_RUN_RE = re.compile(r"[\u4e00-\u9fff]{2,12}")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_profile() -> dict[str, Any]:
    return {
        "version": 1,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "turns_observed": 0,
        "intent_counts": {},
        "runtime_profile_counts": {},
        "response_style_counts": {},
        "attachment_mode_counts": {},
        "domain_terms": {},
        "module_affinity": {
            "router": {},
            "explainer": {},
            "finalizer": {},
        },
        "last_signal": {},
    }


def _read_json(path: Path, fallback: Any) -> Any:
    if not path.is_file():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _increment(counter_map: dict[str, Any], key: str, delta: int = 1) -> None:
    name = str(key or "").strip()
    if not name:
        return
    counter_map[name] = int(counter_map.get(name) or 0) + int(delta)


def _top_items(counter_map: dict[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    items = [
        {"name": str(name), "count": int(count or 0)}
        for name, count in (counter_map or {}).items()
        if str(name).strip()
    ]
    items.sort(key=lambda item: (-int(item.get("count") or 0), str(item.get("name") or "")))
    return items[: max(1, int(limit))]


def _extract_ascii_terms(text: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for match in _ASCII_TERM_RE.findall(str(text or "")):
        token = str(match).strip()
        lowered = token.lower()
        if lowered in _EN_STOPWORDS:
            continue
        if lowered in seen:
            continue
        seen.add(lowered)
        out.append(token if token.isupper() else lowered)
    return out


def _extract_cjk_terms(text: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    raw = str(text or "")
    for run in _CJK_RUN_RE.findall(raw):
        normalized = str(run).strip()
        if not normalized:
            continue
        if len(normalized) <= 6:
            candidates = [normalized]
        else:
            candidates = [normalized[i : i + 3] for i in range(0, min(len(normalized) - 2, 6))]
        for item in candidates:
            item = str(item).strip()
            if len(item) < 2 or item in _ZH_STOPWORDS or item in seen:
                continue
            seen.add(item)
            out.append(item)
    return out


def extract_domain_terms(*texts: str, limit: int = 8) -> list[str]:
    counter: Counter[str] = Counter()
    for raw in texts:
        text = str(raw or "").strip()
        if not text:
            continue
        for token in _extract_ascii_terms(text):
            counter[token] += 1
        for token in _extract_cjk_terms(text):
            counter[token] += 1
    terms = [name for name, _ in counter.most_common(max(1, int(limit)))]
    return terms


def _detect_finalizer_signals(user_message: str, assistant_text: str, answer_bundle: dict[str, Any]) -> list[str]:
    source = f"{user_message}\n{assistant_text}".lower()
    signals: list[str] = []
    if any(token in source for token in ["表格", "table", "整理成表", "markdown 表", "md表"]):
        signals.append("table_output")
    if any(token in source for token in ["邮件", "email", "mail"]):
        signals.append("mail_output")
    if any(token in source for token in ["翻译", "translation", "translate"]):
        signals.append("translation_output")
    if any(token in source for token in ["出处", "页码", "证据", "citation"]):
        signals.append("citation_grounding")
    citations = answer_bundle.get("citations") if isinstance(answer_bundle, dict) else []
    if isinstance(citations, list) and citations:
        signals.append("evidence_bundle")
    return list(dict.fromkeys(signals))


def build_turn_signal(
    *,
    session_id: str,
    user_message: str,
    assistant_text: str,
    route_state: dict[str, Any] | None,
    answer_bundle: dict[str, Any] | None,
    attachment_context_mode: str,
    attachment_count: int,
    settings: dict[str, Any] | None,
    effective_model: str,
    turn_count: int,
) -> dict[str, Any]:
    route_state = dict(route_state or {})
    answer_bundle = dict(answer_bundle or {})
    settings = dict(settings or {})
    primary_intent = str(route_state.get("primary_intent") or "standard").strip() or "standard"
    execution_policy = str(route_state.get("execution_policy") or "").strip()
    runtime_profile = str(route_state.get("runtime_profile") or "").strip()
    task_type = str(route_state.get("task_type") or "standard").strip() or "standard"
    response_style = str(settings.get("response_style") or "normal").strip() or "normal"
    terms = extract_domain_terms(user_message, str(answer_bundle.get("summary") or ""), assistant_text, limit=8)

    router_signals = [primary_intent, task_type]
    if attachment_count > 0:
        router_signals.append(f"{primary_intent}+attachments")
    if execution_policy:
        router_signals.append(f"policy:{execution_policy}")

    explainer_signals: list[str] = []
    if runtime_profile:
        explainer_signals.append(runtime_profile)
    if primary_intent in {"understanding", "evidence", "web"}:
        explainer_signals.extend(terms[:4])

    finalizer_signals = _detect_finalizer_signals(user_message, assistant_text, answer_bundle)

    modules = {
        "router": [{"signal": item, "delta": 1} for item in dict.fromkeys(router_signals) if item],
        "explainer": [{"signal": item, "delta": 1} for item in dict.fromkeys(explainer_signals) if item],
        "finalizer": [{"signal": item, "delta": 1} for item in dict.fromkeys(finalizer_signals) if item],
    }

    focus_parts = [primary_intent]
    if attachment_count > 0:
        focus_parts.append(f"attachments={attachment_count}")
    if terms:
        focus_parts.append("terms=" + ", ".join(terms[:3]))

    return {
        "id": str(uuid.uuid4()),
        "created_at": _now_iso(),
        "session_id": str(session_id or "").strip(),
        "turn_count": int(turn_count or 0),
        "primary_intent": primary_intent,
        "task_type": task_type,
        "execution_policy": execution_policy,
        "runtime_profile": runtime_profile,
        "response_style": response_style,
        "attachment_context_mode": str(attachment_context_mode or "none").strip() or "none",
        "attachment_count": int(max(0, attachment_count)),
        "effective_model": str(effective_model or "").strip(),
        "domain_terms": terms,
        "modules": modules,
        "summary": " · ".join([part for part in focus_parts if part]),
    }


class EvolutionStore:
    def __init__(self, overlay_profile_path: Path, evolution_logs_dir: Path) -> None:
        self.overlay_profile_path = overlay_profile_path
        self.evolution_logs_dir = evolution_logs_dir
        self._lock = threading.Lock()
        self.overlay_profile_path.parent.mkdir(parents=True, exist_ok=True)
        self.evolution_logs_dir.mkdir(parents=True, exist_ok=True)
        if not self.overlay_profile_path.is_file():
            _write_json(self.overlay_profile_path, _default_profile())

    def load_profile(self) -> dict[str, Any]:
        with self._lock:
            profile = _read_json(self.overlay_profile_path, _default_profile())
            if not isinstance(profile, dict):
                profile = _default_profile()
            return profile

    def save_profile(self, profile: dict[str, Any]) -> None:
        with self._lock:
            _write_json(self.overlay_profile_path, profile)

    def record_turn(
        self,
        *,
        session_id: str,
        user_message: str,
        assistant_text: str,
        route_state: dict[str, Any] | None,
        answer_bundle: dict[str, Any] | None,
        attachment_context_mode: str,
        attachment_count: int,
        settings: dict[str, Any] | None,
        effective_model: str,
        turn_count: int,
    ) -> dict[str, Any]:
        event = build_turn_signal(
            session_id=session_id,
            user_message=user_message,
            assistant_text=assistant_text,
            route_state=route_state,
            answer_bundle=answer_bundle,
            attachment_context_mode=attachment_context_mode,
            attachment_count=attachment_count,
            settings=settings,
            effective_model=effective_model,
            turn_count=turn_count,
        )
        with self._lock:
            profile = _read_json(self.overlay_profile_path, _default_profile())
            if not isinstance(profile, dict):
                profile = _default_profile()
            profile.setdefault("intent_counts", {})
            profile.setdefault("runtime_profile_counts", {})
            profile.setdefault("response_style_counts", {})
            profile.setdefault("attachment_mode_counts", {})
            profile.setdefault("domain_terms", {})
            profile.setdefault("module_affinity", {"router": {}, "explainer": {}, "finalizer": {}})
            profile["turns_observed"] = int(profile.get("turns_observed") or 0) + 1
            profile["updated_at"] = _now_iso()
            _increment(profile["intent_counts"], str(event.get("primary_intent") or "standard"))
            _increment(profile["runtime_profile_counts"], str(event.get("runtime_profile") or "default"))
            _increment(profile["response_style_counts"], str(event.get("response_style") or "normal"))
            _increment(profile["attachment_mode_counts"], str(event.get("attachment_context_mode") or "none"))
            for term in event.get("domain_terms") or []:
                _increment(profile["domain_terms"], str(term))
            for module_name, deltas in (event.get("modules") or {}).items():
                bucket = profile["module_affinity"].setdefault(str(module_name), {})
                for item in deltas if isinstance(deltas, list) else []:
                    _increment(bucket, str(item.get("signal") or ""), int(item.get("delta") or 1))
            profile["last_signal"] = {
                "session_id": str(event.get("session_id") or ""),
                "summary": str(event.get("summary") or ""),
                "primary_intent": str(event.get("primary_intent") or "standard"),
                "runtime_profile": str(event.get("runtime_profile") or ""),
                "domain_terms": list(event.get("domain_terms") or []),
                "updated_at": profile["updated_at"],
            }
            _write_json(self.overlay_profile_path, profile)
            event_path = self.evolution_logs_dir / f"{str(event.get('created_at') or '').replace(':', '').replace('-', '')}-{event['id'][:8]}.json"
            _write_json(event_path, event)
        return event

    def list_events(self, limit: int = 8) -> list[dict[str, Any]]:
        max_items = max(1, min(100, int(limit)))
        items: list[dict[str, Any]] = []
        with self._lock:
            files = sorted(self.evolution_logs_dir.glob("*.json"), reverse=True)
            for path in files[:max_items]:
                payload = _read_json(path, {})
                if isinstance(payload, dict) and payload:
                    items.append(payload)
        items.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return items[:max_items]

    def overlay_snapshot(self, *, limit_terms: int = 8, limit_signals: int = 6) -> dict[str, Any]:
        profile = self.load_profile()
        module_affinity = profile.get("module_affinity") if isinstance(profile.get("module_affinity"), dict) else {}
        module_snapshot = {}
        for module_name in ["router", "explainer", "finalizer"]:
            module_snapshot[module_name] = _top_items(module_affinity.get(module_name) or {}, limit=limit_signals)
        return {
            "version": int(profile.get("version") or 1),
            "turns_observed": int(profile.get("turns_observed") or 0),
            "created_at": str(profile.get("created_at") or ""),
            "updated_at": str(profile.get("updated_at") or ""),
            "intent_counts": _top_items(profile.get("intent_counts") or {}, limit=limit_signals),
            "runtime_profile_counts": _top_items(profile.get("runtime_profile_counts") or {}, limit=limit_signals),
            "response_style_counts": _top_items(profile.get("response_style_counts") or {}, limit=limit_signals),
            "attachment_mode_counts": _top_items(profile.get("attachment_mode_counts") or {}, limit=limit_signals),
            "domain_terms": _top_items(profile.get("domain_terms") or {}, limit=limit_terms),
            "module_affinity": module_snapshot,
            "last_signal": dict(profile.get("last_signal") or {}),
        }

    def runtime_payload(self, limit: int = 8) -> dict[str, Any]:
        return {
            "overlay_profile": self.overlay_snapshot(),
            "recent_events": self.list_events(limit=limit),
        }
