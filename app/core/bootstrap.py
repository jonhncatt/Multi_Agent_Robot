from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
from uuid import uuid4

from app.config import AppConfig
from app.core.module_loader import ModuleLoader
from app.core.module_manifest import ActiveModuleManifest, write_active_manifest
from app.core.module_registry import KernelModuleRegistry
from app.core.module_types import ModuleHealthSnapshot, ModuleRuntimeContext
from app.core.supervisor import KernelSupervisor


@dataclass(slots=True)
class KernelRuntime:
    context: ModuleRuntimeContext
    loader: ModuleLoader
    supervisor: KernelSupervisor
    registry: KernelModuleRegistry

    def reload_registry(self) -> KernelModuleRegistry:
        self.registry = self.supervisor.load_registry()
        return self.registry

    def health_snapshot(self) -> ModuleHealthSnapshot:
        return self.supervisor.health_snapshot(self.registry)

    def record_module_failure(self, *, kind: str, requested_ref: str, fallback_ref: str = "", error: str, mode: str | None = None) -> None:
        self.supervisor.record_runtime_failure(
            kind=kind,
            requested_ref=requested_ref,
            fallback_ref=fallback_ref,
            error=error,
            mode=mode,
        )
        self.reload_registry()

    def record_module_success(self, *, kind: str, selected_ref: str, mode: str | None = None) -> None:
        self.supervisor.record_runtime_success(kind=kind, selected_ref=selected_ref, mode=mode)

    def load_shadow_manifest(self) -> ActiveModuleManifest:
        return self.supervisor.load_shadow_manifest()

    def write_shadow_manifest(self, manifest: ActiveModuleManifest) -> None:
        self.supervisor.write_shadow_manifest(manifest)

    def validate_shadow_manifest(self) -> dict[str, object]:
        return self.supervisor.validate_shadow_manifest()

    def validate_active_manifest(self) -> dict[str, object]:
        return self.supervisor.validate_active_manifest()

    def promote_shadow_manifest(self) -> dict[str, object]:
        result = self.supervisor.promote_shadow_manifest()
        if result.get("ok"):
            self.reload_registry()
        return result

    def rollback_active_manifest(self) -> dict[str, object]:
        result = self.supervisor.rollback_active_manifest()
        if result.get("ok"):
            self.reload_registry()
        return result

    def stage_shadow_manifest(self, *, overrides: dict[str, object] | None = None) -> dict[str, object]:
        shadow = self.load_shadow_manifest()
        payload = dict(overrides or {})
        for key in ("router", "policy", "attachment_context", "finalizer", "tool_registry"):
            value = str(payload.get(key) or "").strip()
            if value:
                setattr(shadow, key, value)
        providers = dict(shadow.providers)
        raw_providers = payload.get("providers")
        if isinstance(raw_providers, dict):
            for mode, ref in raw_providers.items():
                mode_text = str(mode or "").strip()
                ref_text = str(ref or "").strip()
                if mode_text and ref_text:
                    providers[mode_text] = ref_text
        shadow.providers = providers
        self.write_shadow_manifest(shadow)
        validation = self.validate_shadow_manifest()
        return {
            "ok": bool(validation.get("ok")),
            "shadow_manifest": shadow.to_dict(),
            "validation": validation,
        }

    def _last_shadow_run_path(self) -> Path:
        return self.context.runtime_dir / "last_shadow_run.json"

    def _write_json(self, path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(path)

    def read_last_shadow_run(self) -> dict[str, object]:
        path = self._last_shadow_run_path()
        if not path.is_file():
            return {}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return raw if isinstance(raw, dict) else {}

    def run_shadow_smoke(
        self,
        *,
        user_message: str = "给我今天的新闻",
        validate_provider: bool = True,
    ) -> dict[str, object]:
        from app.agent import OfficeAgent
        from app.models import ChatSettings

        shadow_manifest = self.load_shadow_manifest()
        validation = self.supervisor.validate_manifest(shadow_manifest)
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8]
        run_dir = self.context.runtime_dir / "shadow_runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        payload: dict[str, object] = {
            "ok": False,
            "run_id": run_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "shadow_manifest": shadow_manifest.to_dict(),
            "validation": validation,
            "runtime_dir": str(run_dir),
        }

        if not validation.get("ok"):
            payload["error"] = "shadow_manifest_invalid"
            self._write_json(run_dir / "smoke_result.json", payload)
            self._write_json(self._last_shadow_run_path(), payload)
            return payload

        smoke_config = replace(
            self.supervisor._config,
            runtime_dir=run_dir,
            active_manifest_path=run_dir / "active_manifest.json",
            shadow_manifest_path=run_dir / "shadow_manifest.json",
            rollback_pointer_path=run_dir / "rollback_pointer.json",
            module_health_path=run_dir / "module_health.json",
        )
        write_active_manifest(smoke_config.active_manifest_path, shadow_manifest)
        write_active_manifest(smoke_config.shadow_manifest_path, shadow_manifest)

        try:
            smoke_runtime = build_kernel_runtime(smoke_config)
            active_validation = smoke_runtime.validate_active_manifest()
            smoke_agent = OfficeAgent(smoke_config, kernel_runtime=smoke_runtime)
            settings = ChatSettings()
            route = smoke_agent._route_request_by_rules(
                user_message=user_message,
                attachment_metas=[],
                settings=settings,
            )
            finalizer_preview = smoke_agent._sanitize_final_answer_text(
                '{"rows":[{"姓名":"张三","分数":95},{"姓名":"李四","分数":88}]}',
                user_message="把数据整理成表格",
                attachment_metas=[],
            )
            provider_info: dict[str, object] = {}
            auth_summary = smoke_agent._debug_openai_auth_summary()
            if validate_provider and bool(auth_summary.get("available")):
                try:
                    runner = smoke_agent._build_llm(
                        model=smoke_config.default_model,
                        max_output_tokens=256,
                        use_responses_api=False,
                    )
                    provider_info = {
                        "ok": True,
                        "mode": str(auth_summary.get("mode") or ""),
                        "runner_class": runner.__class__.__name__,
                    }
                except Exception as exc:
                    provider_info = {
                        "ok": False,
                        "mode": str(auth_summary.get("mode") or ""),
                        "error": str(exc),
                    }
            else:
                provider_info = {
                    "ok": False,
                    "skipped": True,
                    "mode": str(auth_summary.get("mode") or ""),
                    "reason": str(auth_summary.get("reason") or ""),
                }

            payload.update(
                {
                    "ok": True,
                    "route_task_type": str(route.get("task_type") or ""),
                    "route_execution_policy": str(route.get("execution_policy") or ""),
                    "finalizer_preview": str(finalizer_preview or "")[:400],
                    "provider": provider_info,
                    "selected_modules": dict(smoke_runtime.registry.selected_refs),
                    "module_health": dict(smoke_runtime.health_snapshot().module_health),
                    "active_validation": active_validation,
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception as exc:
            payload.update(
                {
                    "ok": False,
                    "error": str(exc),
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                }
            )

        self._write_json(run_dir / "smoke_result.json", payload)
        self._write_json(self._last_shadow_run_path(), payload)
        return payload


def build_kernel_runtime(config: AppConfig) -> KernelRuntime:
    context = ModuleRuntimeContext(
        workspace_root=config.workspace_root,
        modules_dir=config.modules_dir,
        runtime_dir=config.runtime_dir,
    )
    loader = ModuleLoader(context)
    supervisor = KernelSupervisor(config, context=context, loader=loader)
    registry = supervisor.load_registry()
    return KernelRuntime(context=context, loader=loader, supervisor=supervisor, registry=registry)
