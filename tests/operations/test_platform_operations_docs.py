from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_platform_operations_overview_contains_required_sections() -> None:
    text = (REPO_ROOT / 'docs' / 'operations' / 'platform_operations_overview.md').read_text()
    required = [
        'Current Stage',
        'Main Lines Status',
        'Gate And Smoke Overview',
        'Metrics Overview',
        'Replay Sample Library Overview',
        'Entry Index',
        'platform_reporting_template.md',
        'regression-summary.json',
        'research-gate-summary.json',
        'swarm-gate-summary.json',
    ]
    for item in required:
        assert item in text


def test_platform_reporting_template_contains_reporting_sections() -> None:
    text = (REPO_ROOT / 'docs' / 'operations' / 'platform_reporting_template.md').read_text()
    required = [
        'Current Stage',
        'This Round Status',
        'Risks',
        'Blockers',
        'Next Step',
        'Fill Rules',
    ]
    for item in required:
        assert item in text


def test_chinese_operations_docs_exist() -> None:
    required = [
        'docs/operations/platform_operations_overview.zh-CN.md',
        'docs/operations/platform_reporting_template.zh-CN.md',
        'docs/operations/quality_gates.zh-CN.md',
        'docs/operations/smoke_matrix.zh-CN.md',
        'docs/operations/research_module_operations.zh-CN.md',
        'docs/operations/swarm_mvp_operations.zh-CN.md',
        'docs/operations/swarm_mvp_runbook.zh-CN.md',
        'docs/modules/research_module.zh-CN.md',
    ]
    for rel in required:
        assert (REPO_ROOT / rel).exists()
