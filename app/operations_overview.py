from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _gate_status(summary: dict[str, Any]) -> str:
    total = int(summary.get("total") or 0)
    passed = int(summary.get("passed") or 0)
    failed = int(summary.get("failed") or 0)
    if total <= 0:
        return "missing"
    if bool(summary.get("ok")) and failed == 0 and passed == total:
        return "pass"
    return "fail"


def _build_gate_item(
    *,
    gate_id: str,
    label: str,
    artifact_path: Path,
    docs_path: str,
) -> dict[str, Any]:
    summary = _read_json(artifact_path)
    return {
        "id": gate_id,
        "label": label,
        "status": _gate_status(summary),
        "passed": int(summary.get("passed") or 0),
        "failed": int(summary.get("failed") or 0),
        "total": int(summary.get("total") or 0),
        "artifact_path": str(artifact_path.relative_to(artifact_path.parents[2])),
        "docs_path": docs_path,
    }


def _count_replay_samples(root: Path) -> dict[str, Any]:
    families = {}
    total = 0
    for folder in sorted(root.iterdir()) if root.exists() else []:
        if not folder.is_dir():
            continue
        count = len(sorted(folder.glob("*.json")))
        families[folder.name] = count
        total += count
    return {
        "root": str(root.relative_to(root.parents[1])) if root.exists() else "evals/replay_samples",
        "total_samples": total,
        "families": families,
    }


def build_platform_operations_overview(repo_root: Path | None = None) -> dict[str, Any]:
    root = (repo_root or Path(__file__).resolve().parent.parent).resolve()
    artifacts_dir = root / "artifacts"
    evals_dir = root / "evals"

    office_gate = _build_gate_item(
        gate_id="office",
        label="Office Gate",
        artifact_path=artifacts_dir / "evals" / "regression-summary.json",
        docs_path="docs/operations/quality_gates.zh-CN.md",
    )
    research_gate = _build_gate_item(
        gate_id="research",
        label="Research Gate",
        artifact_path=artifacts_dir / "evals" / "research-gate-summary.json",
        docs_path="docs/operations/research_module_operations.zh-CN.md",
    )
    swarm_gate = _build_gate_item(
        gate_id="swarm",
        label="Swarm Gate",
        artifact_path=artifacts_dir / "evals" / "swarm-gate-summary.json",
        docs_path="docs/operations/swarm_mvp_operations.zh-CN.md",
    )
    gates = [office_gate, research_gate, swarm_gate]
    green_count = sum(1 for item in gates if item["status"] == "pass")

    metrics = _read_json(artifacts_dir / "platform_metrics" / "latest.json")
    research_metrics = dict(metrics.get("research_module") or {})
    swarm_metrics = dict(metrics.get("swarm") or {})

    replay = _count_replay_samples(evals_dir / "replay_samples")
    smoke_layers = [
        {
            "id": "baseline",
            "label": "Baseline Smoke",
            "entry": "python scripts/demo_minimal_agent_os.py --check",
            "purpose": "主应用基线、自检入口、最小聊天链路。",
            "ci": True,
        },
        {
            "id": "module",
            "label": "Module Smoke",
            "entry": "python scripts/demo_research_module.py --check",
            "purpose": "research_module 稳态模块烟测。",
            "ci": True,
        },
        {
            "id": "swarm",
            "label": "Swarm Smoke",
            "entry": "python scripts/demo_research_swarm.py --check",
            "purpose": "research Swarm MVP 的业务输出与降级烟测。",
            "ci": True,
        },
        {
            "id": "release",
            "label": "Release Smoke",
            "entry": "/api/kernel/shadow/smoke + contracts + replay",
            "purpose": "迁移或发布前使用，不进入默认 CI。",
            "ci": False,
        },
    ]

    docs_index = [
        {"label": "平台运营总览", "path": "docs/operations/platform_operations_overview.zh-CN.md"},
        {"label": "质量门禁", "path": "docs/operations/quality_gates.zh-CN.md"},
        {"label": "Smoke Matrix", "path": "docs/operations/smoke_matrix.zh-CN.md"},
        {"label": "Research 运营文档", "path": "docs/operations/research_module_operations.zh-CN.md"},
        {"label": "Swarm 运营文档", "path": "docs/operations/swarm_mvp_operations.zh-CN.md"},
        {"label": "Swarm Runbook", "path": "docs/operations/swarm_mvp_runbook.zh-CN.md"},
        {"label": "项目汇报模板", "path": "docs/operations/platform_reporting_template.zh-CN.md"},
        {"label": "Replay Samples", "path": "evals/replay_samples/README.md"},
    ]

    return {
        "generated_at": str(metrics.get("generated_at") or ""),
        "headline": "平台迁移已收口，当前进入可运营、可汇报、可扩展阶段。",
        "subheadline": f"{green_count}/{len(gates)} 个 gate 绿色；research 与 swarm 都已具备独立质量入口。",
        "gates": gates,
        "research_metrics": research_metrics,
        "swarm_metrics": swarm_metrics,
        "replay": replay,
        "smoke_layers": smoke_layers,
        "docs_index": docs_index,
    }
