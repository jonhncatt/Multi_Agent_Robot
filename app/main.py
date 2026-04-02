from __future__ import annotations

import asyncio
import json
import os
import queue
from pathlib import Path
import subprocess
import threading
import time
from typing import Any, Callable
import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.bootstrap import AgentOSRuntime, assemble_runtime
from app.config import load_config
from app.core.bootstrap import build_kernel_runtime
from app.core.healthcheck import build_kernel_health_payload
from app.evals import run_regression_evals
from app.evolution import EvolutionStore
from app.kernel.llm_router import LLMRouter
from app.models import (
    ChatRequest,
    ChatResponse,
    ClearStatsResponse,
    DeleteSessionResponse,
    EvalCaseResult,
    EvalRunRequest,
    EvalRunResponse,
    EvolutionRuntimeResponse,
    HealthResponse,
    KernelManifestUpdateRequest,
    KernelShadowPipelineRequest,
    KernelShadowAutoRepairRequest,
    KernelShadowPackageRequest,
    KernelShadowPatchWorkerRequest,
    KernelShadowReplayRequest,
    KernelShadowSelfUpgradeRequest,
    KernelRuntimeResponse,
    KernelShadowSmokeRequest,
    NewSessionResponse,
    RoleLabRuntimeResponse,
    SessionDetailResponse,
    SessionListItem,
    SessionListResponse,
    SessionTurn,
    UpdateSessionTitleRequest,
    UpdateSessionTitleResponse,
    SandboxDrillRequest,
    SandboxDrillResponse,
    SandboxDrillStep,
    TokenStatsResponse,
    TokenTotals,
    TokenUsage,
    UploadResponse,
)
from app.openai_auth import OpenAIAuthManager
from app.operations_overview import build_platform_operations_overview
from app.product_profiles import ensure_product_profile_env
from app.storage import SessionStore, ShadowLogStore, TokenStatsStore, UploadStore
PRODUCT_PROFILE = ensure_product_profile_env()
config = load_config()
session_store = SessionStore(config.sessions_dir)
upload_store = UploadStore(config.uploads_dir)
token_stats_store = TokenStatsStore(config.token_stats_path)
shadow_log_store = ShadowLogStore(config.shadow_logs_dir)
evolution_store = EvolutionStore(config.overlay_profile_path, config.evolution_logs_dir)
kernel_runtime = build_kernel_runtime(config)
agent_os_runtime: AgentOSRuntime = assemble_runtime(
    config,
    kernel_runtime=kernel_runtime,
)
APP_VERSION = "0.3.5"


def _resolve_build_version() -> str:
    override = str(
        os.environ.get("MULTI_AGENT_TEAM_BUILD_VERSION") or ""
    ).strip()
    if override:
        return override

    repo_root = Path(__file__).resolve().parent.parent
    try:
        commit = (
            subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                check=True,
                timeout=2,
            ).stdout.strip()
        )
    except Exception:
        commit = ""
    try:
        branch = (
            subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                check=True,
                timeout=2,
            ).stdout.strip()
        )
    except Exception:
        branch = ""

    parts = [f"v{APP_VERSION}"]
    if branch and commit:
        parts.append(f"{branch}@{commit}")
    elif commit:
        parts.append(commit)
    return " · ".join(parts)


BUILD_VERSION = _resolve_build_version()


_FALLBACK_AGENT_PLUGIN_KEYS: tuple[str, ...] = (
    "router_agent",
    "coordinator_agent",
    "planner_agent",
    "researcher_agent",
    "file_reader_agent",
    "summarizer_agent",
    "fixer_agent",
    "worker_agent",
    "conflict_detector_agent",
    "reviewer_agent",
    "revision_agent",
    "structurer_agent",
)

_AGENT_PLUGIN_META: dict[str, dict[str, object]] = {
    "router_agent": {
        "sprite_role": "router",
        "supports_swarm": True,
        "swarm_mode": "fanout_router",
        "capability_tags": ["intent-routing", "policy-gate", "swarm-dispatch"],
        "summary": "入口分流与多插件调度分发。",
    },
    "coordinator_agent": {
        "sprite_role": "coordinator",
        "supports_swarm": True,
        "swarm_mode": "supervisor",
        "capability_tags": ["task-coordination", "multi-agent-sync", "swarm-supervision"],
        "summary": "负责跨插件协作、合流与冲突仲裁。",
    },
    "planner_agent": {
        "sprite_role": "planner",
        "supports_swarm": True,
        "swarm_mode": "plan-then-swarm",
        "capability_tags": ["plan-decomposition", "constraint-check", "swarm-plan"],
        "summary": "生成执行计划并分配到子插件。",
    },
    "researcher_agent": {
        "sprite_role": "researcher",
        "supports_swarm": True,
        "swarm_mode": "parallel-research",
        "capability_tags": ["evidence-search", "citation-merge", "swarm-retrieval"],
        "summary": "并行检索信息并汇总证据。",
    },
    "file_reader_agent": {
        "sprite_role": "file_reader",
        "supports_swarm": False,
        "swarm_mode": "none",
        "capability_tags": ["document-parse", "attachment-extract"],
        "summary": "读取附件并提取结构化文本。",
    },
    "summarizer_agent": {
        "sprite_role": "summarizer",
        "supports_swarm": False,
        "swarm_mode": "none",
        "capability_tags": ["context-compress", "summary-write"],
        "summary": "上下文压缩与结论摘要。",
    },
    "fixer_agent": {
        "sprite_role": "fixer",
        "supports_swarm": False,
        "swarm_mode": "none",
        "capability_tags": ["error-repair", "patch-hint"],
        "summary": "定位故障并给出修复策略。",
    },
    "worker_agent": {
        "sprite_role": "worker",
        "supports_swarm": True,
        "swarm_mode": "tool-swarm",
        "capability_tags": ["tool-execution", "action-loop", "swarm-worker"],
        "summary": "执行主任务与工具调用循环。",
    },
    "conflict_detector_agent": {
        "sprite_role": "conflict_detector",
        "supports_swarm": True,
        "swarm_mode": "consensus-check",
        "capability_tags": ["conflict-detect", "consistency-check", "swarm-vote"],
        "summary": "检测结论冲突并给出一致性判断。",
    },
    "reviewer_agent": {
        "sprite_role": "reviewer",
        "supports_swarm": True,
        "swarm_mode": "multi-review",
        "capability_tags": ["quality-review", "risk-check", "swarm-review"],
        "summary": "对结果做质量审阅与风险评估。",
    },
    "revision_agent": {
        "sprite_role": "revision",
        "supports_swarm": False,
        "swarm_mode": "none",
        "capability_tags": ["revision", "final-polish"],
        "summary": "根据审阅意见生成最终修订版。",
    },
    "structurer_agent": {
        "sprite_role": "structurer",
        "supports_swarm": False,
        "swarm_mode": "none",
        "capability_tags": ["format-structuring", "output-shaping"],
        "summary": "将结果整理成目标结构与格式。",
    },
}


def _agent_title_from_key(key: str) -> str:
    normalized = str(key or "").strip().replace("-", "_")
    if not normalized:
        return "LLM Agent"
    words = [item for item in normalized.split("_") if item]
    return " ".join(word.capitalize() for word in words)


def _agent_sprite_role_from_key(key: str) -> str:
    raw = str(key or "").strip().replace("-", "_")
    if raw.endswith("_agent"):
        raw = raw[:-6]
    return raw or "worker"


def _build_agent_plugin_descriptor(*, key: str, path: str, exists: bool) -> dict[str, object]:
    meta = _AGENT_PLUGIN_META.get(key, {})
    sprite_role = str(meta.get("sprite_role") or _agent_sprite_role_from_key(key))
    capability_tags = [str(item).strip() for item in (meta.get("capability_tags") or []) if str(item).strip()]
    supports_swarm = bool(meta.get("supports_swarm"))
    swarm_mode = str(meta.get("swarm_mode") or ("none" if not supports_swarm else "generic-swarm")).strip()
    return {
        "key": key,
        "title": _agent_title_from_key(key),
        "path": path,
        "exists": bool(exists),
        "sprite_role": sprite_role,
        "supports_swarm": supports_swarm,
        "swarm_mode": swarm_mode,
        "capability_tags": capability_tags,
        "summary": str(meta.get("summary") or ""),
    }


def _build_control_panel_topology(repo_root: Path) -> dict[str, object]:
    kernel_path = repo_root / "app" / "kernel" / "host.py"
    router_path = repo_root / "app" / "kernel" / "llm_router.py"
    agents_dir = repo_root / "app" / "agents"

    plugin_paths_by_key = {item.stem: item for item in agents_dir.glob("*_agent.py")}
    ordered_keys = [key for key in _FALLBACK_AGENT_PLUGIN_KEYS if key in plugin_paths_by_key]
    ordered_keys.extend(sorted(key for key in plugin_paths_by_key.keys() if key not in ordered_keys))
    if ordered_keys:
        plugin_defs = [
            _build_agent_plugin_descriptor(
                key=key,
                path=str(plugin_paths_by_key[key].relative_to(repo_root)),
                exists=plugin_paths_by_key[key].is_file(),
            )
            for key in ordered_keys[:12]
        ]
    else:
        plugin_defs = [
            _build_agent_plugin_descriptor(
                key=key,
                path=str((agents_dir / f"{key}.py").relative_to(repo_root)),
                exists=(agents_dir / f"{key}.py").is_file(),
            )
            for key in _FALLBACK_AGENT_PLUGIN_KEYS
        ]

    return {
        "kernel": {
            "key": "kernel_core",
            "title": "稳定 Kernel",
            "path": str(kernel_path.relative_to(repo_root)),
            "exists": kernel_path.is_file(),
        },
        "central_router": {
            "key": "llm_central_router",
            "title": "LLM 中央调度器",
            "path": str(router_path.relative_to(repo_root)),
            "exists": router_path.is_file(),
        },
        "agent_plugins": plugin_defs,
        "slot_count": 12,
    }


class AgentRunQueue:
    """
    Single-workspace lane queue:
    - one active run per session
    - bounded global concurrency across sessions
    """

    def __init__(self, max_concurrent_runs: int) -> None:
        self._global_sem = threading.BoundedSemaphore(max(1, int(max_concurrent_runs)))
        self._locks_guard = threading.Lock()
        self._session_locks: dict[str, threading.Lock] = {}

    def _get_session_lock(self, session_id: str) -> threading.Lock:
        sid = str(session_id or "").strip() or "__anon__"
        with self._locks_guard:
            lock = self._session_locks.get(sid)
            if lock is None:
                lock = threading.Lock()
                self._session_locks[sid] = lock
            return lock

    def run_slot(self, session_id: str):
        sid = str(session_id or "").strip() or "__anon__"
        started = time.monotonic()
        session_lock = self._get_session_lock(sid)
        session_lock.acquire()
        self._global_sem.acquire()
        wait_ms = int((time.monotonic() - started) * 1000)
        return _AgentRunQueueTicket(self._global_sem, session_lock, wait_ms)


class _AgentRunQueueTicket:
    def __init__(
        self,
        global_sem: threading.BoundedSemaphore,
        session_lock: threading.Lock,
        wait_ms: int,
    ) -> None:
        self._global_sem = global_sem
        self._session_lock = session_lock
        self.wait_ms = max(0, int(wait_ms))
        self._released = False

    def release(self) -> None:
        if self._released:
            return
        self._released = True
        try:
            self._global_sem.release()
        finally:
            self._session_lock.release()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
        return False


run_queue = AgentRunQueue(config.max_concurrent_runs)


def get_kernel_runtime():
    return kernel_runtime


def get_evolution_store() -> EvolutionStore:
    return evolution_store


def get_agent_os_runtime() -> AgentOSRuntime:
    return agent_os_runtime


def get_llm_router() -> LLMRouter:
    router = getattr(agent_os_runtime.kernel, "llm_router", None)
    if router is None:
        router = LLMRouter(agent_os_runtime.kernel)
        agent_os_runtime.kernel.attach_llm_router(router)
    return router


app = FastAPI(title=PRODUCT_PROFILE.app_title, version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = (Path(__file__).resolve().parent / "static").resolve()
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.middleware("http")
async def disable_static_cache(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(str(static_dir / "index.html"))


@app.on_event("startup")
async def startup_discover_agents() -> None:
    try:
        await get_llm_router().discover_agents(force=False)
    except Exception as exc:
        print(f"[startup] discover_agents skipped: {exc}")


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    runtime = get_agent_os_runtime()
    docker_ok, docker_msg = runtime.legacy_tools().docker_status()
    auth_summary = OpenAIAuthManager(config).auth_summary()
    kernel_health = build_kernel_health_payload(get_kernel_runtime())
    host_runtime = runtime.debug_kernel_host_snapshot()
    host_runtime["agent_os_runtime"] = get_agent_os_runtime().snapshot()
    control_panel_topology = _build_control_panel_topology(Path(__file__).resolve().parent.parent)
    role_lab_runtime = runtime.debug_role_lab_runtime_snapshot()
    evolution_payload = get_evolution_store().runtime_payload(limit=10)
    tool_registry = runtime.debug_tool_registry_snapshot()
    return HealthResponse(
        ok=True,
        product_profile=PRODUCT_PROFILE.key,
        product_title=PRODUCT_PROFILE.sidebar_title,
        product_tagline=PRODUCT_PROFILE.sidebar_hint,
        product_kernel_title=PRODUCT_PROFILE.kernel_title,
        product_kernel_subtitle=PRODUCT_PROFILE.kernel_subtitle,
        product_role_title=PRODUCT_PROFILE.role_title,
        product_role_legend=PRODUCT_PROFILE.role_legend,
        show_kernel_console=PRODUCT_PROFILE.show_kernel_console,
        show_role_board=PRODUCT_PROFILE.show_role_board,
        app_version=APP_VERSION,
        build_version=BUILD_VERSION,
        model_default=config.default_model,
        llm_provider=str(auth_summary.get("provider") or config.llm_provider or ""),
        llm_api_key_env=str(auth_summary.get("api_key_env") or config.llm_primary_api_key_env or ""),
        auth_mode=str(auth_summary.get("mode") or ""),
        execution_mode_default=config.execution_mode,
        docker_available=docker_ok,
        docker_message=docker_msg,
        platform_name=config.platform_name,
        workspace_root=str(config.workspace_root),
        allow_any_path=config.allow_any_path,
        allowed_roots=[str(path) for path in config.allowed_roots],
        workspace_sibling_root=str(config.workspace_sibling_root or ""),
        allow_workspace_sibling_access=config.allow_workspace_sibling_access,
        default_extra_allowed_roots=[str(path) for path in config.default_extra_allowed_roots],
        extra_allowed_roots_source=config.extra_allowed_roots_source,
        web_allow_all_domains=config.web_allow_all_domains,
        web_allowed_domains=config.web_allowed_domains,
        kernel_active_manifest=dict(kernel_health.get("active_manifest") or {}),
        kernel_shadow_manifest=dict(kernel_health.get("shadow_manifest") or {}),
        kernel_shadow_validation=dict(kernel_health.get("shadow_validation") or {}),
        kernel_shadow_promote_check=dict(kernel_health.get("shadow_promote_check") or {}),
        kernel_rollback_pointer=dict(kernel_health.get("rollback_pointer") or {}),
        kernel_last_shadow_run=dict(kernel_health.get("last_shadow_run") or {}),
        kernel_last_upgrade_run=dict(kernel_health.get("last_upgrade_run") or {}),
        kernel_last_repair_run=dict(kernel_health.get("last_repair_run") or {}),
        kernel_last_patch_worker_run=dict(kernel_health.get("last_patch_worker_run") or {}),
        kernel_last_package_run=dict(kernel_health.get("last_package_run") or {}),
        kernel_selected_modules=dict(kernel_health.get("selected_modules") or {}),
        kernel_module_health=dict(kernel_health.get("module_health") or {}),
        kernel_runtime_files=dict(kernel_health.get("runtime_files") or {}),
        kernel_tool_registry=dict(tool_registry or {}),
        kernel_host_runtime=dict(host_runtime or {}),
        control_panel_topology=dict(control_panel_topology or {}),
        role_lab_runtime=dict(role_lab_runtime or {}),
        assistant_overlay_profile=dict(evolution_payload.get("overlay_profile") or {}),
        assistant_evolution_recent=list(evolution_payload.get("recent_events") or []),
    )


@app.get("/api/role-lab/runtime", response_model=RoleLabRuntimeResponse)
def role_lab_runtime() -> RoleLabRuntimeResponse:
    snapshot = get_agent_os_runtime().debug_role_lab_runtime_snapshot()
    return RoleLabRuntimeResponse(ok=True, detail="role-agent runtime snapshot", role_lab_runtime=dict(snapshot or {}))


def _kernel_runtime_response(
    *,
    ok: bool,
    detail: str = "",
    validation: dict[str, object] | None = None,
    contracts: dict[str, object] | None = None,
    smoke: dict[str, object] | None = None,
    replay: dict[str, object] | None = None,
    pipeline: dict[str, object] | None = None,
    repair: dict[str, object] | None = None,
    patch_worker: dict[str, object] | None = None,
) -> KernelRuntimeResponse:
    kernel_health = build_kernel_health_payload(get_kernel_runtime())
    evolution_payload = get_evolution_store().runtime_payload(limit=10)
    tool_registry = get_agent_os_runtime().debug_tool_registry_snapshot()
    return KernelRuntimeResponse(
        ok=ok,
        detail=detail,
        validation=dict(validation or {}),
        contracts=dict(contracts or {}),
        smoke=dict(smoke or {}),
        replay=dict(replay or {}),
        pipeline=dict(pipeline or {}),
        repair=dict(repair or {}),
        patch_worker=dict(patch_worker or {}),
        kernel_active_manifest=dict(kernel_health.get("active_manifest") or {}),
        kernel_shadow_manifest=dict(kernel_health.get("shadow_manifest") or {}),
        kernel_shadow_validation=dict(kernel_health.get("shadow_validation") or {}),
        kernel_shadow_promote_check=dict(kernel_health.get("shadow_promote_check") or {}),
        kernel_rollback_pointer=dict(kernel_health.get("rollback_pointer") or {}),
        kernel_last_shadow_run=dict(kernel_health.get("last_shadow_run") or {}),
        kernel_last_upgrade_run=dict(kernel_health.get("last_upgrade_run") or {}),
        kernel_last_repair_run=dict(kernel_health.get("last_repair_run") or {}),
        kernel_last_patch_worker_run=dict(kernel_health.get("last_patch_worker_run") or {}),
        kernel_last_package_run=dict(kernel_health.get("last_package_run") or {}),
        kernel_selected_modules=dict(kernel_health.get("selected_modules") or {}),
        kernel_module_health=dict(kernel_health.get("module_health") or {}),
        kernel_runtime_files=dict(kernel_health.get("runtime_files") or {}),
        kernel_tool_registry=dict(tool_registry or {}),
        assistant_overlay_profile=dict(evolution_payload.get("overlay_profile") or {}),
        assistant_evolution_recent=list(evolution_payload.get("recent_events") or []),
    )


@app.get("/api/evolution/runtime", response_model=EvolutionRuntimeResponse)
def evolution_runtime_state(limit: int = 10) -> EvolutionRuntimeResponse:
    payload = get_evolution_store().runtime_payload(limit=limit)
    return EvolutionRuntimeResponse(
        ok=True,
        detail="当前个体覆层与最近进化日志。",
        assistant_overlay_profile=dict(payload.get("overlay_profile") or {}),
        assistant_evolution_recent=list(payload.get("recent_events") or []),
    )


@app.get("/api/operations/overview")
def platform_operations_overview() -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parent.parent
    return build_platform_operations_overview(repo_root)


def _find_shadow_replay_record(run_id: str | None = None) -> dict[str, Any] | None:
    run_id_text = str(run_id or "").strip()
    if run_id_text:
        return shadow_log_store.find_run(run_id_text)
    recent = shadow_log_store.list_recent(limit=1)
    return recent[0] if recent else None


def _find_upgrade_run(run_id: str | None = None) -> dict[str, Any] | None:
    runtime = get_kernel_runtime()
    payload = runtime.find_upgrade_run(run_id)
    return payload if isinstance(payload, dict) and payload else None


def _find_repair_run(run_id: str | None = None) -> dict[str, Any] | None:
    runtime = get_kernel_runtime()
    payload = runtime.find_repair_run(run_id)
    return payload if isinstance(payload, dict) and payload else None


@app.get("/api/kernel/runtime", response_model=KernelRuntimeResponse)
def kernel_runtime_state() -> KernelRuntimeResponse:
    runtime = get_kernel_runtime()
    return _kernel_runtime_response(
        ok=True,
        detail="内核运行时状态。",
        validation=runtime.validate_shadow_manifest(),
    )


@app.get("/api/kernel/repairs", response_model=KernelRuntimeResponse)
def kernel_repair_history(limit: int = 10) -> KernelRuntimeResponse:
    runtime = get_kernel_runtime()
    runs = runtime.list_repair_runs(limit=limit)
    summary = [
        {
            "run_id": str(item.get("run_id") or ""),
            "ok": bool(item.get("ok")),
            "base_upgrade_run_id": str(item.get("base_upgrade_run_id") or ""),
            "strategy": str(item.get("strategy") or ""),
            "attempt_count": len(item.get("attempts") or []) if isinstance(item.get("attempts"), list) else 0,
            "finished_at": str(item.get("finished_at") or ""),
        }
        for item in runs
    ]
    return _kernel_runtime_response(
        ok=True,
        detail="最近 repair attempts。",
        repair={"repair_runs": summary},
    )


@app.get("/api/kernel/patch-workers", response_model=KernelRuntimeResponse)
def kernel_patch_worker_history(limit: int = 10) -> KernelRuntimeResponse:
    runtime = get_kernel_runtime()
    runs = runtime.list_patch_worker_runs(limit=limit)
    summary = [
        {
            "run_id": str(item.get("run_id") or ""),
            "ok": bool(item.get("ok")),
            "base_repair_run_id": str(item.get("base_repair_run_id") or ""),
            "task_count": len(item.get("executed_tasks") or []) if isinstance(item.get("executed_tasks"), list) else 0,
            "round_count": int(item.get("round_count") or 0),
            "stop_reason": str(item.get("stop_reason") or ""),
            "finished_at": str(item.get("finished_at") or ""),
        }
        for item in runs
    ]
    return _kernel_runtime_response(
        ok=True,
        detail="最近 patch worker runs。",
        patch_worker={"patch_worker_runs": summary},
    )


@app.get("/api/kernel/packages", response_model=KernelRuntimeResponse)
def kernel_package_history(limit: int = 10) -> KernelRuntimeResponse:
    runtime = get_kernel_runtime()
    runs = runtime.list_package_runs(limit=limit)
    summary = [
        {
            "run_id": str(item.get("run_id") or ""),
            "ok": bool(item.get("ok")),
            "packaged_count": len(item.get("packaged_modules") or []) if isinstance(item.get("packaged_modules"), list) else 0,
            "packaged_labels": list(item.get("packaged_labels") or []) if isinstance(item.get("packaged_labels"), list) else [],
            "finished_at": str(item.get("finished_at") or ""),
        }
        for item in runs
    ]
    return _kernel_runtime_response(
        ok=True,
        detail="最近 package runs。",
        pipeline={"package_runs": summary},
    )


@app.get("/api/kernel/upgrades", response_model=KernelRuntimeResponse)
def kernel_upgrade_history(limit: int = 10) -> KernelRuntimeResponse:
    runtime = get_kernel_runtime()
    runs = runtime.list_upgrade_runs(limit=limit)
    summary = [
        {
            "run_id": str(item.get("run_id") or ""),
            "ok": bool(item.get("ok")),
            "started_at": str(item.get("started_at") or ""),
            "finished_at": str(item.get("finished_at") or ""),
            "failed_stage": str(((item.get("failure_classification") or {}) if isinstance(item.get("failure_classification"), dict) else {}).get("failed_stage") or ""),
            "category": str(((item.get("failure_classification") or {}) if isinstance(item.get("failure_classification"), dict) else {}).get("category") or ""),
        }
        for item in runs
    ]
    return _kernel_runtime_response(
        ok=True,
        detail="最近 upgrade attempts。",
        pipeline={"upgrade_runs": summary},
    )


@app.post("/api/kernel/shadow/stage", response_model=KernelRuntimeResponse)
def kernel_shadow_stage(req: KernelManifestUpdateRequest) -> KernelRuntimeResponse:
    runtime = get_kernel_runtime()
    result = runtime.stage_shadow_manifest(overrides=req.model_dump(exclude_none=True))
    return _kernel_runtime_response(
        ok=bool(result.get("ok")),
        detail="shadow manifest 已更新。",
        validation=result.get("validation") if isinstance(result.get("validation"), dict) else {},
    )


@app.post("/api/kernel/shadow/validate", response_model=KernelRuntimeResponse)
def kernel_shadow_validate() -> KernelRuntimeResponse:
    runtime = get_kernel_runtime()
    validation = runtime.validate_shadow_manifest()
    return _kernel_runtime_response(
        ok=bool(validation.get("ok")),
        detail="shadow manifest 校验完成。",
        validation=validation,
    )


@app.get("/api/kernel/shadow/promote-check", response_model=KernelRuntimeResponse)
def kernel_shadow_promote_check() -> KernelRuntimeResponse:
    runtime = get_kernel_runtime()
    promote_check = runtime.shadow_promote_check()
    return _kernel_runtime_response(
        ok=bool(promote_check.get("ok")),
        detail="shadow promote 检查完成。",
        validation=runtime.validate_shadow_manifest(),
        pipeline={"promote_check": promote_check},
    )


@app.post("/api/kernel/shadow/contracts", response_model=KernelRuntimeResponse)
def kernel_shadow_contracts() -> KernelRuntimeResponse:
    runtime = get_kernel_runtime()
    contracts = runtime.run_shadow_contracts()
    validation = runtime.validate_shadow_manifest()
    return _kernel_runtime_response(
        ok=bool(contracts.get("ok")),
        detail="shadow contracts 已执行。",
        validation=validation,
        contracts=contracts,
    )


@app.post("/api/kernel/active/contracts", response_model=KernelRuntimeResponse)
def kernel_active_contracts() -> KernelRuntimeResponse:
    runtime = get_kernel_runtime()
    contracts = runtime.run_active_contracts()
    validation = runtime.validate_active_manifest()
    return _kernel_runtime_response(
        ok=bool(contracts.get("ok")),
        detail="active contracts 已执行。",
        validation=validation,
        contracts=contracts,
    )


@app.post("/api/kernel/shadow/smoke", response_model=KernelRuntimeResponse)
def kernel_shadow_smoke(req: KernelShadowSmokeRequest) -> KernelRuntimeResponse:
    runtime = get_kernel_runtime()
    smoke = runtime.run_shadow_smoke(
        user_message=req.message,
        validate_provider=bool(req.validate_provider),
    )
    return _kernel_runtime_response(
        ok=bool(smoke.get("ok")),
        detail="shadow smoke 已执行。",
        validation=runtime.validate_shadow_manifest(),
        smoke=smoke,
    )


@app.get("/api/kernel/shadow/logs", response_model=KernelRuntimeResponse)
def kernel_shadow_logs(limit: int = 10) -> KernelRuntimeResponse:
    records = shadow_log_store.list_recent(limit=limit)
    summary = [
        {
            "run_id": str(item.get("run_id") or ""),
            "logged_at": str(item.get("logged_at") or ""),
            "session_id": str(item.get("session_id") or ""),
            "message_preview": str(item.get("message_preview") or ""),
            "effective_model": str(item.get("effective_model") or ""),
        }
        for item in records
    ]
    return _kernel_runtime_response(
        ok=True,
        detail="最近 shadow log 列表。",
        pipeline={"recent_runs": summary},
    )


@app.post("/api/kernel/shadow/replay", response_model=KernelRuntimeResponse)
def kernel_shadow_replay(req: KernelShadowReplayRequest) -> KernelRuntimeResponse:
    runtime = get_kernel_runtime()
    record = _find_shadow_replay_record(req.run_id)
    if not isinstance(record, dict):
        return _kernel_runtime_response(
            ok=False,
            detail="未找到可回放的 shadow log 记录。",
        )
    replay = runtime.run_shadow_replay(replay_record=record)
    return _kernel_runtime_response(
        ok=bool(replay.get("ok")),
        detail="shadow replay 已执行。",
        validation=runtime.validate_shadow_manifest(),
        replay=replay,
    )


@app.post("/api/kernel/shadow/promote", response_model=KernelRuntimeResponse)
def kernel_shadow_promote() -> KernelRuntimeResponse:
    runtime = get_kernel_runtime()
    result = runtime.promote_shadow_manifest()
    return _kernel_runtime_response(
        ok=bool(result.get("ok")),
        detail="shadow manifest promote 完成。" if result.get("ok") else "shadow manifest promote 失败。",
        validation=result.get("validation") if isinstance(result.get("validation"), dict) else {},
    )


@app.post("/api/kernel/rollback", response_model=KernelRuntimeResponse)
def kernel_runtime_rollback() -> KernelRuntimeResponse:
    runtime = get_kernel_runtime()
    result = runtime.rollback_active_manifest()
    return _kernel_runtime_response(
        ok=bool(result.get("ok")),
        detail="active manifest 回滚完成。" if result.get("ok") else "active manifest 回滚失败。",
        validation=result.get("validation") if isinstance(result.get("validation"), dict) else {},
    )


@app.post("/api/kernel/shadow/pipeline", response_model=KernelRuntimeResponse)
def kernel_shadow_pipeline(req: KernelShadowPipelineRequest) -> KernelRuntimeResponse:
    runtime = get_kernel_runtime()
    overrides = req.model_dump(
        exclude_none=True,
        include={"router", "policy", "attachment_context", "finalizer", "tool_registry", "providers"},
    )
    replay_record = _find_shadow_replay_record(req.replay_run_id) if (req.replay_run_id or shadow_log_store.list_recent(limit=1)) else None
    pipeline = runtime.run_shadow_pipeline(
        overrides=overrides,
        smoke_message=req.smoke_message,
        validate_provider=bool(req.validate_provider),
        replay_record=replay_record if isinstance(replay_record, dict) else None,
        promote_if_healthy=bool(req.promote_if_healthy),
    )
    validation = pipeline.get("validation") if isinstance(pipeline.get("validation"), dict) else {}
    contracts = pipeline.get("contracts") if isinstance(pipeline.get("contracts"), dict) else {}
    smoke = pipeline.get("smoke") if isinstance(pipeline.get("smoke"), dict) else {}
    replay = pipeline.get("replay") if isinstance(pipeline.get("replay"), dict) else {}

    return _kernel_runtime_response(
        ok=bool(pipeline.get("ok")),
        detail="shadow pipeline 已执行。",
        validation=validation,
        contracts=contracts,
        smoke=smoke,
        replay=replay,
        pipeline=pipeline,
    )


@app.post("/api/kernel/shadow/auto-repair", response_model=KernelRuntimeResponse)
def kernel_shadow_auto_repair(req: KernelShadowAutoRepairRequest) -> KernelRuntimeResponse:
    runtime = get_kernel_runtime()
    base_upgrade_run = _find_upgrade_run(req.upgrade_run_id)
    if not isinstance(base_upgrade_run, dict):
        return _kernel_runtime_response(
            ok=False,
            detail="未找到可修复的 upgrade attempt。",
        )
    replay_source_run_id = req.replay_run_id or str(base_upgrade_run.get("replay_source_run_id") or "").strip() or None
    replay_record = _find_shadow_replay_record(replay_source_run_id)
    repair = runtime.run_shadow_auto_repair(
        base_upgrade_run=base_upgrade_run,
        replay_record=replay_record if isinstance(replay_record, dict) else None,
        smoke_message=req.smoke_message,
        validate_provider=req.validate_provider,
        promote_if_healthy=req.promote_if_healthy,
        max_attempts=req.max_attempts,
    )
    repaired_pipeline = repair.get("repaired_pipeline") if isinstance(repair.get("repaired_pipeline"), dict) else {}
    validation = repaired_pipeline.get("validation") if isinstance(repaired_pipeline.get("validation"), dict) else runtime.validate_shadow_manifest()
    contracts = repaired_pipeline.get("contracts") if isinstance(repaired_pipeline.get("contracts"), dict) else {}
    smoke = repaired_pipeline.get("smoke") if isinstance(repaired_pipeline.get("smoke"), dict) else {}
    replay = repaired_pipeline.get("replay") if isinstance(repaired_pipeline.get("replay"), dict) else {}
    return _kernel_runtime_response(
        ok=bool(repair.get("ok")),
        detail="shadow auto-repair 已执行。",
        validation=validation,
        contracts=contracts,
        smoke=smoke,
        replay=replay,
        repair=repair,
    )


@app.post("/api/kernel/shadow/patch-worker", response_model=KernelRuntimeResponse)
def kernel_shadow_patch_worker(req: KernelShadowPatchWorkerRequest) -> KernelRuntimeResponse:
    runtime = get_kernel_runtime()
    repair_run = _find_repair_run(req.repair_run_id)
    if not isinstance(repair_run, dict):
        return _kernel_runtime_response(
            ok=False,
            detail="未找到可执行 patch worker 的 repair run。",
        )
    replay_source_run_id = req.replay_run_id or str((repair_run.get("repaired_pipeline") or {}).get("replay_source_run_id") or "").strip() or None
    replay_record = _find_shadow_replay_record(replay_source_run_id)
    patch_worker = runtime.run_shadow_patch_worker(
        repair_run=repair_run,
        replay_record=replay_record if isinstance(replay_record, dict) else None,
        max_tasks=req.max_tasks,
        max_rounds=req.max_rounds,
        auto_package_on_success=bool(req.auto_package_on_success),
        promote_if_healthy=req.promote_if_healthy,
    )
    pipeline = patch_worker.get("pipeline") if isinstance(patch_worker.get("pipeline"), dict) else {}
    validation = pipeline.get("validation") if isinstance(pipeline.get("validation"), dict) else runtime.validate_shadow_manifest()
    contracts = pipeline.get("contracts") if isinstance(pipeline.get("contracts"), dict) else {}
    smoke = pipeline.get("smoke") if isinstance(pipeline.get("smoke"), dict) else {}
    replay = pipeline.get("replay") if isinstance(pipeline.get("replay"), dict) else {}
    return _kernel_runtime_response(
        ok=bool(patch_worker.get("ok")),
        detail="shadow patch worker 已执行。",
        validation=validation,
        contracts=contracts,
        smoke=smoke,
        replay=replay,
        pipeline=pipeline,
        patch_worker=patch_worker,
    )


@app.post("/api/kernel/shadow/package", response_model=KernelRuntimeResponse)
def kernel_shadow_package(req: KernelShadowPackageRequest) -> KernelRuntimeResponse:
    runtime = get_kernel_runtime()
    package_run = runtime.package_shadow_modules(
        labels=req.labels,
        package_note=req.package_note,
        source_run_id=str(req.source_run_id or ""),
        repair_run_id=str(req.repair_run_id or ""),
        patch_worker_run_id=str(req.patch_worker_run_id or ""),
        runtime_profile=req.runtime_profile,
    )
    validation = package_run.get("validation") if isinstance(package_run.get("validation"), dict) else runtime.validate_shadow_manifest()
    return _kernel_runtime_response(
        ok=bool(package_run.get("ok")),
        detail="shadow modules 已打包为正式版本。" if package_run.get("ok") else "shadow modules 打包失败。",
        validation=validation,
        pipeline={"package_run": package_run},
    )


@app.post("/api/kernel/shadow/self-upgrade", response_model=KernelRuntimeResponse)
def kernel_shadow_self_upgrade(req: KernelShadowSelfUpgradeRequest) -> KernelRuntimeResponse:
    runtime = get_kernel_runtime()
    base_upgrade_run = _find_upgrade_run(req.upgrade_run_id)
    bootstrap_pipeline: dict[str, Any] = {}
    bootstrap_triggered = False
    if not isinstance(base_upgrade_run, dict) or not base_upgrade_run:
        bootstrap_triggered = True
        bootstrap_pipeline = runtime.run_shadow_pipeline(
            overrides={},
            smoke_message=str(req.smoke_message or "给我今天的新闻"),
            validate_provider=bool(req.validate_provider if req.validate_provider is not None else True),
            replay_record=None,
            promote_if_healthy=False,
        )
        base_upgrade_run = bootstrap_pipeline
    replay_source_run_id = req.replay_run_id or str(base_upgrade_run.get("replay_source_run_id") or "").strip() or None
    replay_record = _find_shadow_replay_record(replay_source_run_id)
    self_upgrade = runtime.run_shadow_self_upgrade(
        base_upgrade_run=base_upgrade_run,
        replay_record=replay_record if isinstance(replay_record, dict) else None,
        smoke_message=req.smoke_message,
        validate_provider=req.validate_provider,
        max_attempts=req.max_attempts,
        max_tasks=req.max_tasks,
        max_rounds=req.max_rounds,
        promote_if_healthy=bool(req.promote_if_healthy),
    )
    final_pipeline = self_upgrade.get("final_pipeline") if isinstance(self_upgrade.get("final_pipeline"), dict) else {}
    validation = final_pipeline.get("validation") if isinstance(final_pipeline.get("validation"), dict) else runtime.validate_shadow_manifest()
    contracts = final_pipeline.get("contracts") if isinstance(final_pipeline.get("contracts"), dict) else {}
    smoke = final_pipeline.get("smoke") if isinstance(final_pipeline.get("smoke"), dict) else {}
    replay = final_pipeline.get("replay") if isinstance(final_pipeline.get("replay"), dict) else {}
    return _kernel_runtime_response(
        ok=bool(self_upgrade.get("ok")),
        detail="shadow self-upgrade 已执行（已自动创建 baseline upgrade run）。" if bootstrap_triggered else "shadow self-upgrade 已执行。",
        validation=validation,
        contracts=contracts,
        smoke=smoke,
        replay=replay,
        pipeline={"self_upgrade": self_upgrade, "bootstrap_pipeline": bootstrap_pipeline, "bootstrap_triggered": bootstrap_triggered},
        repair=self_upgrade.get("repair") if isinstance(self_upgrade.get("repair"), dict) else {},
        patch_worker=self_upgrade.get("patch_worker") if isinstance(self_upgrade.get("patch_worker"), dict) else {},
    )


@app.post("/api/session/new", response_model=NewSessionResponse)
def create_session() -> NewSessionResponse:
    session = session_store.create()
    return NewSessionResponse(session_id=session["id"])


@app.delete("/api/session/{session_id}", response_model=DeleteSessionResponse)
def delete_session(session_id: str) -> DeleteSessionResponse:
    deleted = session_store.delete(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return DeleteSessionResponse(ok=True, session_id=session_id)


@app.patch("/api/session/{session_id}/title", response_model=UpdateSessionTitleResponse)
def update_session_title(session_id: str, req: UpdateSessionTitleRequest) -> UpdateSessionTitleResponse:
    loaded = session_store.load(session_id)
    if not loaded:
        raise HTTPException(status_code=404, detail="Session not found")

    title = str(req.title or "").strip()[:120]
    loaded["title"] = title
    session_store.save(loaded)
    return UpdateSessionTitleResponse(ok=True, session_id=session_id, title=title)


@app.get("/api/session/{session_id}", response_model=SessionDetailResponse)
def get_session(session_id: str, max_turns: int = 200) -> SessionDetailResponse:
    loaded = session_store.load(session_id)
    if not loaded:
        raise HTTPException(status_code=404, detail="Session not found")

    turns_raw = loaded.get("turns", [])
    if not isinstance(turns_raw, list):
        turns_raw = []
    limited_turns = turns_raw[-max(1, min(2000, max_turns)) :]
    turns: list[SessionTurn] = []
    for item in limited_turns:
        if not isinstance(item, dict):
            continue
        turns.append(
            SessionTurn(
                role=str(item.get("role") or "user"),
                text=str(item.get("text") or ""),
                answer_bundle=item.get("answer_bundle") or {},
                created_at=str(item.get("created_at")) if item.get("created_at") else None,
            )
        )

    return SessionDetailResponse(
        session_id=session_id,
        title=str(loaded.get("title") or ""),
        summary=str(loaded.get("summary") or ""),
        turn_count=len(turns_raw),
        turns=turns,
    )


@app.get("/api/sessions", response_model=SessionListResponse)
def list_sessions(limit: int = 50) -> SessionListResponse:
    rows = session_store.list_sessions(limit=limit)
    return SessionListResponse(sessions=[SessionListItem(**row) for row in rows])


@app.get("/api/agents")
def list_independent_agents() -> dict[str, Any]:
    router = get_llm_router()
    _run_coro_sync(router.discover_agents(force=False))
    return {"ok": True, "count": len(router.list_agents()), "agents": router.list_agents()}


@app.post("/api/agents/{name}/reload")
def reload_independent_agent(name: str) -> dict[str, Any]:
    router = get_llm_router()
    result = _run_coro_sync(router.reload_single_agent(name))
    if not bool(result.get("ok")):
        raise HTTPException(status_code=404, detail=str(result.get("error") or "reload failed"))
    return result


@app.post("/api/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)) -> UploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    meta = await upload_store.save_upload(file)
    max_bytes = config.max_upload_mb * 1024 * 1024
    if meta["size"] > max_bytes:
        upload_store.delete(meta["id"])
        raise HTTPException(status_code=413, detail=f"File too large (>{config.max_upload_mb}MB)")

    return UploadResponse(
        id=meta["id"],
        name=meta["original_name"],
        mime=meta["mime"],
        size=meta["size"],
        kind=meta["kind"],
    )


@app.get("/api/stats", response_model=TokenStatsResponse)
def get_stats() -> TokenStatsResponse:
    raw = token_stats_store.get_stats(max_records=500)
    sessions: dict[str, TokenTotals] = {}
    for session_id, totals in raw.get("sessions", {}).items():
        sessions[session_id] = TokenTotals(**totals)
    return TokenStatsResponse(
        totals=TokenTotals(**raw.get("totals", {})),
        sessions=sessions,
        records=raw.get("records", []),
    )


@app.post("/api/stats/clear", response_model=ClearStatsResponse)
def clear_stats() -> ClearStatsResponse:
    token_stats_store.clear()
    return ClearStatsResponse(ok=True)


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    return _process_chat_request_minimal(req)


def _resolve_execution_mode(requested_mode: str | None) -> str:
    mode = str(requested_mode or "").strip().lower()
    if mode in {"host", "docker"}:
        return mode
    return config.execution_mode


def _append_drill_step(
    steps: list[SandboxDrillStep],
    *,
    name: str,
    ok: bool,
    detail: str,
    started_at: float,
) -> None:
    steps.append(
        SandboxDrillStep(
            name=name,
            ok=bool(ok),
            detail=str(detail),
            duration_ms=max(0, int((time.perf_counter() - started_at) * 1000)),
        )
    )


@app.post("/api/sandbox/drill", response_model=SandboxDrillResponse)
def sandbox_drill(req: SandboxDrillRequest) -> SandboxDrillResponse:
    run_id = str(uuid.uuid4())
    execution_mode = _resolve_execution_mode(req.execution_mode)
    tools = get_agent_os_runtime().legacy_tools()
    docker_ok, docker_msg = tools.docker_status()
    steps: list[SandboxDrillStep] = []
    failed = 0
    drill_session_id = f"__drill__{run_id}"
    pwd_result: dict[str, Any] | None = None

    started = time.perf_counter()
    _append_drill_step(
        steps,
        name="runtime_context",
        ok=True,
        detail=f"run_id={run_id}, execution_mode={execution_mode}, session_id={drill_session_id}",
        started_at=started,
    )

    if execution_mode == "docker":
        started = time.perf_counter()
        docker_step_ok = bool(docker_ok)
        _append_drill_step(
            steps,
            name="docker_ready",
            ok=docker_step_ok,
            detail=docker_msg or ("Docker server ready." if docker_step_ok else "Docker unavailable."),
            started_at=started,
        )
        if not docker_step_ok:
            failed += 1

    tools.set_runtime_context(execution_mode=execution_mode, session_id=drill_session_id)
    try:
        started = time.perf_counter()
        list_result = tools.list_directory(path=".", max_entries=20)
        list_ok = bool(list_result.get("ok"))
        list_detail = (
            f"path={list_result.get('path', '')}, entries={len(list_result.get('entries') or [])}"
            if list_ok
            else str(list_result.get("error") or "list_directory failed")
        )
        _append_drill_step(
            steps,
            name="list_directory",
            ok=list_ok,
            detail=list_detail,
            started_at=started,
        )
        if not list_ok:
            failed += 1

        started = time.perf_counter()
        pwd_result = tools.run_shell(command="pwd", cwd=".", timeout_sec=12)
        pwd_ok = bool(pwd_result.get("ok"))
        pwd_detail = (
            f"mode={pwd_result.get('execution_mode')}, host_cwd={pwd_result.get('host_cwd')}, "
            f"sandbox_cwd={pwd_result.get('sandbox_cwd') or '-'}"
            if pwd_ok
            else str(pwd_result.get("error") or "run_shell pwd failed")
        )
        _append_drill_step(
            steps,
            name="run_shell_pwd",
            ok=pwd_ok,
            detail=pwd_detail,
            started_at=started,
        )
        if not pwd_ok:
            failed += 1

        started = time.perf_counter()
        if "python3" in config.allowed_commands:
            py_result = tools.run_shell(command="python3 --version", cwd=".", timeout_sec=12)
            py_ok = bool(py_result.get("ok"))
            py_out = str(py_result.get("stdout") or py_result.get("stderr") or "").strip().splitlines()
            py_detail = py_out[0] if py_out else (
                str(py_result.get("error") or "python3 --version failed") if not py_ok else "python3 ok"
            )
            _append_drill_step(
                steps,
                name="run_shell_python3_version",
                ok=py_ok,
                detail=py_detail,
                started_at=started,
            )
            if not py_ok:
                failed += 1
        else:
            _append_drill_step(
                steps,
                name="run_shell_python3_version",
                ok=True,
                detail="skipped: python3 is not in MULTI_AGENT_TEAM_ALLOWED_COMMANDS",
                started_at=started,
            )

        if execution_mode == "docker":
            started = time.perf_counter()
            mapping_ok = False
            mapping_detail = "missing docker pwd result"
            if isinstance(pwd_result, dict) and pwd_result.get("ok"):
                mode = str(pwd_result.get("execution_mode") or "").strip().lower()
                host_cwd = str(pwd_result.get("host_cwd") or "").strip()
                sandbox_cwd = str(pwd_result.get("sandbox_cwd") or "").strip()
                mounts = pwd_result.get("mount_mappings") if isinstance(pwd_result.get("mount_mappings"), list) else []
                mapping_ok = mode == "docker" and bool(host_cwd) and bool(sandbox_cwd) and bool(mounts)
                mapping_detail = (
                    f"mode={mode}, host_cwd={host_cwd}, sandbox_cwd={sandbox_cwd}, mount_count={len(mounts)}"
                )
            _append_drill_step(
                steps,
                name="docker_path_mapping",
                ok=mapping_ok,
                detail=mapping_detail,
                started_at=started,
            )
            if not mapping_ok:
                failed += 1
    finally:
        tools.clear_runtime_context()

    if failed == 0:
        summary = f"沙盒演练通过（{len(steps)} 步）。"
    else:
        summary = f"沙盒演练发现 {failed} 个失败步骤（共 {len(steps)} 步）。"

    return SandboxDrillResponse(
        ok=failed == 0,
        run_id=run_id,
        execution_mode=execution_mode,
        docker_available=docker_ok,
        docker_message=docker_msg,
        summary=summary,
        steps=steps,
    )


@app.post("/api/evals/run", response_model=EvalRunResponse)
def run_evals(req: EvalRunRequest) -> EvalRunResponse:
    run_id = str(uuid.uuid4())
    summary = run_regression_evals(
        include_optional=bool(req.include_optional),
        name_filter=str(req.name_filter or "").strip(),
    )
    passed = int(summary.get("passed") or 0)
    failed = int(summary.get("failed") or 0)
    skipped = int(summary.get("skipped") or 0)
    total = int(summary.get("total") or 0)
    duration_ms = int(summary.get("duration_ms") or 0)
    summary_text = (
        f"回归测试通过：passed={passed}, failed={failed}, skipped={skipped}, total={total}"
        if failed == 0
        else f"回归测试失败：passed={passed}, failed={failed}, skipped={skipped}, total={total}"
    )
    return EvalRunResponse(
        ok=bool(summary.get("ok")),
        run_id=run_id,
        include_optional=bool(summary.get("include_optional")),
        name_filter=str(summary.get("name_filter") or ""),
        cases_path=str(summary.get("cases_path") or ""),
        passed=passed,
        failed=failed,
        skipped=skipped,
        total=total,
        duration_ms=duration_ms,
        summary=summary_text,
        results=[EvalCaseResult(**item) for item in summary.get("results") or [] if isinstance(item, dict)],
    )


def _emit_progress(progress_cb: Callable[[dict[str, Any]], None] | None, event: str, **payload: Any) -> None:
    if not progress_cb:
        return
    try:
        progress_cb({"event": event, **payload})
    except Exception:
        pass


def _run_coro_sync(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    raise RuntimeError("Cannot run sync coroutine bridge inside an active event loop")


def _process_chat_request_minimal(
    req: ChatRequest, progress_cb: Callable[[dict[str, Any]], None] | None = None
) -> ChatResponse:
    auth_summary = OpenAIAuthManager(config).auth_summary()
    if not bool(auth_summary.get("available")):
        raise HTTPException(status_code=500, detail=str(auth_summary.get("reason") or "LLM credentials are required"))
    run_id = str(uuid.uuid4())
    _emit_progress(
        progress_cb,
        "stage",
        code="backend_start",
        detail=f"后端已接收请求，开始处理。run_id={run_id}, auth_mode={auth_summary.get('mode')}",
        run_id=run_id,
    )

    run_id = str(uuid.uuid4())
    _emit_progress(progress_cb, "stage", code="backend_start", detail=f"llm_router 已接收请求。run_id={run_id}", run_id=run_id)
    if not bool(auth_summary.get("available")):
        _emit_progress(
            progress_cb,
            "trace",
            message="当前未检测到可用云端凭据，已切换本地稳态回复模式。",
            run_id=run_id,
        )
    seed_session = session_store.load_or_create(req.session_id)
    session_id = str(seed_session.get("id") or "")
    if not session_id:
        raise HTTPException(status_code=500, detail="Session create failed")

    queue_wait_ms = 0
    with run_queue.run_slot(session_id) as ticket:
        queue_wait_ms = int(ticket.wait_ms)
        session = session_store.load_or_create(session_id)
        history_turns = list(session.get("turns", []))
        router = get_llm_router()
        _emit_progress(progress_cb, "stage", code="routing", detail="中央调度器正在规划执行步骤。", run_id=run_id)
        plan = _run_coro_sync(router.route(req.message, history_turns))
        _emit_progress(progress_cb, "stage", code="executing", detail="独立 Agent 正在执行任务。", run_id=run_id)
        execution = _run_coro_sync(router.execute(plan))
        text = _run_coro_sync(router.summarize(user_query=req.message, plan=plan, execution=execution, history=history_turns))
        text = str(text or "").strip() or "任务执行完成。"

        execution_plan = [
            f"{index}. {str(step.get('agent') or '')}: {str(step.get('task') or '')}"
            for index, step in enumerate(list(plan.get("steps") or []), start=1)
            if isinstance(step, dict)
        ]
        execution_trace = [f"调度方案: {str(plan.get('plan') or 'llm_router_plan')}"]
        for item in list(execution.get("results") or []):
            if not isinstance(item, dict):
                continue
            agent_name = str(item.get("agent") or "unknown")
            status = str(item.get("status") or "unknown")
            if status == "success":
                execution_trace.append(f"[{agent_name}] success")
            else:
                execution_trace.append(f"[{agent_name}] failed: {str(item.get('error') or '')}")

        agent_panels = []
        for item in list(execution.get("results") or []):
            if not isinstance(item, dict):
                continue
            agent_panels.append(
                {
                    "role": str(item.get("agent") or "agent"),
                    "title": str(item.get("agent") or "Agent"),
                    "kind": "agent",
                    "summary": str(item.get("status") or ""),
                    "bullets": [str(item.get("result") or item.get("error") or "")[:240]],
                }
            )

        session_store.append_turn(session, role="user", text=req.message.strip())
        session_store.append_turn(session, role="assistant", text=text)
        session_store.save(session)

        selected_model = req.settings.model or str(get_llm_router().model)
        token_usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "llm_calls": 0,
            "estimated_cost_usd": 0.0,
            "pricing_known": False,
            "pricing_model": selected_model,
            "input_price_per_1m": None,
            "output_price_per_1m": None,
        }
        stats_snapshot = token_stats_store.add_usage(
            session_id=session["id"],
            usage=token_usage,
            model=selected_model,
        )
        session_totals_raw = stats_snapshot.get("sessions", {}).get(session["id"], {})
        global_totals_raw = stats_snapshot.get("totals", {})
        response = ChatResponse(
            session_id=session["id"],
            run_id=run_id,
            effective_model=selected_model,
            queue_wait_ms=queue_wait_ms,
            text=text,
            tool_events=[],
            execution_plan=execution_plan,
            execution_trace=execution_trace,
            debug_flow=[],
            agent_panels=agent_panels,
            active_roles=[str(step.get("agent") or "") for step in list(plan.get("steps") or []) if isinstance(step, dict)],
            current_role=str(list(plan.get("steps") or [{}])[0].get("agent") or "") if list(plan.get("steps") or []) else None,
            role_states=[],
            answer_bundle={},
            attachment_context_mode="none",
            effective_attachment_ids=[],
            auto_linked_attachment_ids=[],
            auto_linked_attachment_names=[],
            missing_attachment_ids=[],
            route_state_scope="none",
            attachment_context_key="",
            token_usage=TokenUsage(**token_usage),
            session_token_totals=TokenTotals(**session_totals_raw),
            global_token_totals=TokenTotals(**global_totals_raw),
            selected_business_module="llm_router_core",
            kernel_routing={"mode": "llm_router", "plan": plan},
            business_result={"plan": plan, "execution": execution},
            turn_count=len(session.get("turns", [])),
            summarized=False,
        )
        _emit_progress(progress_cb, "stage", code="ready", detail="llm_router 返回完成。", run_id=run_id)
        return response


def _sse_pack(event: str, payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {raw}\n\n"


@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest) -> StreamingResponse:
    def event_stream():
        events: queue.Queue[dict[str, Any]] = queue.Queue()
        done_event = threading.Event()

        def emit(payload: dict[str, Any]) -> None:
            event_name = str(payload.get("event") or "message")
            data = {k: v for k, v in payload.items() if k != "event"}
            events.put({"event": event_name, "payload": data})

        def worker() -> None:
            try:
                response = _process_chat_request_minimal(req, progress_cb=emit)
                events.put({"event": "final", "payload": {"response": response.model_dump()}})
            except HTTPException as exc:
                events.put(
                    {
                        "event": "error",
                        "payload": {"status_code": exc.status_code, "detail": str(exc.detail or "HTTP error")},
                    }
                )
            except Exception as exc:
                events.put({"event": "error", "payload": {"status_code": 500, "detail": str(exc)}})
            finally:
                done_event.set()
                events.put({"event": "done", "payload": {"ok": True}})

        threading.Thread(target=worker, daemon=True).start()

        while True:
            try:
                item = events.get(timeout=10.0)
            except queue.Empty:
                yield _sse_pack("heartbeat", {"ts": int(time.time())})
                if done_event.is_set():
                    break
                continue
            event_name = str(item.get("event") or "message")
            payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
            yield _sse_pack(event_name, payload)
            if event_name == "done":
                break

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)
