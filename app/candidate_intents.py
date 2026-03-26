from __future__ import annotations

from app.intent_schema import ConversationFrame, IntentScore, RequestSignals


_BASE_INTENTS = (
    "understanding",
    "evidence",
    "web",
    "code_lookup",
    "generation",
    "meeting_minutes",
    "standard",
)


class CandidateIntentGenerator:
    def generate(
        self,
        *,
        signals: RequestSignals,
        frame: ConversationFrame,
    ) -> list[IntentScore]:
        scores: dict[str, IntentScore] = {
            intent: IntentScore(intent=intent, score=0.0, evidence=[])
            for intent in _BASE_INTENTS
        }

        if signals.source_trace_request or signals.evidence_required or signals.spec_lookup_request:
            self._bump(scores, "evidence", 0.55, "source/spec/evidence markers")
        if signals.web_request:
            self._bump(scores, "web", 0.60, "web request markers")
        if signals.local_code_lookup_request:
            self._bump(scores, "code_lookup", 0.65, "local code lookup markers")
        if signals.local_code_lookup_request and (signals.source_trace_request or signals.evidence_required or signals.spec_lookup_request):
            self._bump(scores, "code_lookup", 0.28, "code lookup plus evidence markers")
        if signals.grounded_code_generation_context:
            self._bump(scores, "generation", 0.48, "grounded generation context")
        if signals.transform_followup_like and signals.local_code_lookup_request:
            self._bump(scores, "generation", 0.28, "code lookup with transform intent")
        if signals.has_attachments and signals.understanding_request:
            self._bump(scores, "understanding", 0.50, "attachment understanding markers")
        if signals.meeting_minutes_request:
            self._bump(scores, "meeting_minutes", 0.62, "meeting minutes markers")

        inherited = str(frame.dominant_intent or signals.inherited_primary_intent or "").strip().lower()
        if inherited in scores and signals.short_followup_like:
            self._bump(scores, inherited, 0.35, "inherited dominant intent with short followup")

        if signals.transform_followup_like and signals.reference_followup_like:
            self._bump(scores, "generation", 0.28, "transform + reference followup")
            self._bump(scores, "understanding", 0.18, "transform + reference followup")

        clear_intent = any(
            (
                signals.source_trace_request,
                signals.evidence_required,
                signals.spec_lookup_request,
                signals.web_request,
                signals.local_code_lookup_request,
                signals.meeting_minutes_request,
                (signals.has_attachments and signals.understanding_request),
            )
        )
        if signals.request_requires_tools and not clear_intent:
            self._bump(scores, "standard", 0.20, "tools requested without clear intent")

        if signals.context_dependent_followup and inherited in scores:
            self._bump(scores, inherited, 0.18, "context dependent followup")

        if not any(item.score > 0 for item in scores.values()):
            self._bump(scores, "standard", 0.35, "default fallback")

        out = sorted(scores.values(), key=lambda item: item.score, reverse=True)
        for item in out:
            item.score = max(0.0, min(1.0, round(float(item.score), 4)))
        return out

    def _bump(self, scores: dict[str, IntentScore], intent: str, delta: float, evidence: str) -> None:
        current = scores[intent]
        current.score = float(current.score) + float(delta)
        note = str(evidence or "").strip()
        if note and note not in current.evidence:
            current.evidence.append(note)
