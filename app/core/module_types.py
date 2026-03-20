from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class ModuleRuntimeContext:
    workspace_root: Path
    modules_dir: Path
    runtime_dir: Path


@dataclass(frozen=True, slots=True)
class ModuleReference:
    kind: str
    module_id: str
    version: str
    ref: str
    path: Path
    entrypoint: str
    capabilities: tuple[str, ...] = ()


@dataclass(slots=True)
class ModuleSelection:
    kind: str
    requested_ref: str
    resolved_ref: str
    fallback_ref: str = ""
    used_fallback: bool = False


@dataclass(slots=True)
class ModuleHealthRecord:
    status: str = "active"
    failure_count: int = 0
    last_error: str = ""
    last_failure_at: str = ""
    requested_ref: str = ""
    selected_ref: str = ""
    fallback_ref: str = ""


@dataclass(slots=True)
class ModuleHealthSnapshot:
    active_manifest: dict[str, Any] = field(default_factory=dict)
    selected_modules: dict[str, str] = field(default_factory=dict)
    module_health: dict[str, dict[str, Any]] = field(default_factory=dict)
    runtime_files: dict[str, str] = field(default_factory=dict)


@runtime_checkable
class RouterModule(Protocol):
    module_id: str
    version: str

    def route(
        self,
        *,
        agent: Any,
        user_message: str,
        attachment_metas: list[dict[str, Any]],
        settings: Any,
        route_state: dict[str, Any] | None = None,
        inline_followup_context: bool = False,
    ) -> dict[str, Any]: ...


@runtime_checkable
class PolicyModule(Protocol):
    module_id: str
    version: str

    def normalize_route(
        self,
        *,
        agent: Any,
        route: dict[str, Any],
        fallback: dict[str, Any],
        settings: Any,
    ) -> dict[str, Any]: ...


@runtime_checkable
class AttachmentContextModule(Protocol):
    module_id: str
    version: str

    def resolve_attachment_context(
        self,
        *,
        session: dict[str, Any],
        message: str,
        requested_attachment_ids: list[str] | None,
    ) -> dict[str, Any]: ...

    def apply_attachment_context_result(
        self,
        *,
        session: dict[str, Any],
        resolved_attachment_ids: list[str] | None,
        attachment_context_mode: str,
        clear_attachment_context: bool = False,
        requested_attachment_ids: list[str] | None = None,
    ) -> None: ...

    def resolve_scoped_route_state(
        self,
        *,
        session: dict[str, Any],
        attachment_ids: list[str] | None,
    ) -> tuple[dict[str, Any], str]: ...

    def store_scoped_route_state(
        self,
        *,
        session: dict[str, Any],
        attachment_ids: list[str] | None,
        route_state: dict[str, Any] | None,
    ) -> None: ...


@runtime_checkable
class FinalizerModule(Protocol):
    module_id: str
    version: str

    def sanitize(
        self,
        *,
        agent: Any,
        text: str,
        user_message: str,
        attachment_metas: list[dict[str, Any]],
        tool_events: list[Any] | None = None,
        inline_followup_context: bool = False,
    ) -> str: ...


@runtime_checkable
class ProviderModule(Protocol):
    module_id: str
    version: str
    auth_mode: str

    def build_runner(
        self,
        *,
        agent: Any,
        auth: Any,
        model: str,
        max_output_tokens: int,
        use_responses_api: bool | None = None,
    ) -> Any: ...


@runtime_checkable
class ToolRegistryModule(Protocol):
    module_id: str
    version: str

    def build_langchain_tools(self, *, agent: Any) -> list[Any]: ...
