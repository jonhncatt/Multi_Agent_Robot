from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import tomllib
from typing import Any


DEFAULT_ACTIVE_MANIFEST: dict[str, Any] = {
    "router": "router_rules@1.0.0",
    "policy": "policy_resolver@1.0.0",
    "attachment_context": "attachment_context@1.0.0",
    "finalizer": "finalizer@1.0.0",
    "tool_registry": "tool_registry@1.0.0",
    "providers": {
        "api_key": "provider_openai_api@1.0.0",
        "codex_auth": "provider_codex_auth@1.0.0",
    },
}


@dataclass(frozen=True, slots=True)
class ModuleManifest:
    id: str
    version: str
    api_version: str
    kind: str
    entrypoint: str
    capabilities: tuple[str, ...] = ()
    path: Path | None = None


@dataclass(slots=True)
class ActiveModuleManifest:
    router: str = DEFAULT_ACTIVE_MANIFEST["router"]
    policy: str = DEFAULT_ACTIVE_MANIFEST["policy"]
    attachment_context: str = DEFAULT_ACTIVE_MANIFEST["attachment_context"]
    finalizer: str = DEFAULT_ACTIVE_MANIFEST["finalizer"]
    tool_registry: str = DEFAULT_ACTIVE_MANIFEST["tool_registry"]
    providers: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_ACTIVE_MANIFEST["providers"]))

    def to_dict(self) -> dict[str, Any]:
        return {
            "router": self.router,
            "policy": self.policy,
            "attachment_context": self.attachment_context,
            "finalizer": self.finalizer,
            "tool_registry": self.tool_registry,
            "providers": dict(self.providers),
        }


def version_dir_name(version: str) -> str:
    raw = str(version or "").strip()
    if not raw:
        return "v1"
    major = raw.split(".", 1)[0].strip() or "1"
    if not major.startswith("v"):
        major = f"v{major}"
    return major


def parse_module_ref(ref: str) -> tuple[str, str]:
    raw = str(ref or "").strip()
    if "@" not in raw:
        raise ValueError(f"Invalid module ref: {raw}")
    module_id, version = raw.split("@", 1)
    module_id = module_id.strip()
    version = version.strip()
    if not module_id or not version:
        raise ValueError(f"Invalid module ref: {raw}")
    return module_id, version


def active_manifest_from_dict(raw: dict[str, Any] | None) -> ActiveModuleManifest:
    payload = dict(DEFAULT_ACTIVE_MANIFEST)
    payload["providers"] = dict(DEFAULT_ACTIVE_MANIFEST["providers"])
    if isinstance(raw, dict):
        for key in ("router", "policy", "attachment_context", "finalizer", "tool_registry"):
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                payload[key] = value.strip()
        providers = raw.get("providers")
        if isinstance(providers, dict):
            for mode, ref in providers.items():
                mode_text = str(mode or "").strip()
                ref_text = str(ref or "").strip()
                if mode_text and ref_text:
                    payload["providers"][mode_text] = ref_text
    return ActiveModuleManifest(
        router=str(payload["router"]),
        policy=str(payload["policy"]),
        attachment_context=str(payload["attachment_context"]),
        finalizer=str(payload["finalizer"]),
        tool_registry=str(payload["tool_registry"]),
        providers=dict(payload["providers"]),
    )


def read_active_manifest(path: Path) -> ActiveModuleManifest:
    if not path.is_file():
        return active_manifest_from_dict(None)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return active_manifest_from_dict(None)
    return active_manifest_from_dict(raw if isinstance(raw, dict) else None)


def write_active_manifest(path: Path, manifest: ActiveModuleManifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def read_module_manifest(path: Path) -> ModuleManifest:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    capabilities = tuple(str(item).strip() for item in raw.get("capabilities") or [] if str(item).strip())
    return ModuleManifest(
        id=str(raw.get("id") or "").strip(),
        version=str(raw.get("version") or "").strip(),
        api_version=str(raw.get("api_version") or "").strip(),
        kind=str(raw.get("kind") or "").strip(),
        entrypoint=str(raw.get("entrypoint") or "").strip(),
        capabilities=capabilities,
        path=path,
    )
