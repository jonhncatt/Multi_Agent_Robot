from __future__ import annotations

from typing import Any

from app.session_context import (
    apply_attachment_context_result,
    resolve_attachment_context,
    resolve_scoped_route_state,
    store_scoped_route_state,
)


class AttachmentContextModule:
    module_id = "attachment_context"
    version = "1.0.0"

    def resolve_attachment_context(
        self,
        *,
        session: dict[str, Any],
        message: str,
        requested_attachment_ids: list[str] | None,
    ) -> dict[str, Any]:
        return resolve_attachment_context(
            session,
            message=message,
            requested_attachment_ids=requested_attachment_ids,
        )

    def apply_attachment_context_result(
        self,
        *,
        session: dict[str, Any],
        resolved_attachment_ids: list[str] | None,
        attachment_context_mode: str,
        clear_attachment_context: bool = False,
        requested_attachment_ids: list[str] | None = None,
    ) -> None:
        apply_attachment_context_result(
            session,
            resolved_attachment_ids=resolved_attachment_ids,
            attachment_context_mode=attachment_context_mode,
            clear_attachment_context=clear_attachment_context,
            requested_attachment_ids=requested_attachment_ids,
        )

    def resolve_scoped_route_state(
        self,
        *,
        session: dict[str, Any],
        attachment_ids: list[str] | None,
    ) -> tuple[dict[str, Any], str]:
        return resolve_scoped_route_state(session, attachment_ids=attachment_ids)

    def store_scoped_route_state(
        self,
        *,
        session: dict[str, Any],
        attachment_ids: list[str] | None,
        route_state: dict[str, Any] | None,
    ) -> None:
        store_scoped_route_state(session, attachment_ids=attachment_ids, route_state=route_state)
