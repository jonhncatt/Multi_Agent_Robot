from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_HTML = REPO_ROOT / 'app' / 'static' / 'index.html'
APP_JS = REPO_ROOT / 'app' / 'static' / 'app.js'


def test_workstation_shell_mounts_exist() -> None:
    html = INDEX_HTML.read_text()
    assert 'app-shell--two-column' in html
    assert 'rightRailResizer' not in html
    required_ids = [
        'appShell',
        'leftRailResizer',
        'opsRail',
        'commandPalette',
        'commandPaletteInput',
        'commandPaletteList',
        'executionDagView',
        'executionLogView',
        'executionLogFilters',
        'executionLogAutoBtn',
    ]
    for item in required_ids:
        assert f'id="{item}"' in html, item


def test_workstation_shell_behaviors_are_wired() -> None:
    script = APP_JS.read_text()
    required_tokens = [
        'setupRailResizer(leftRailResizer, "left")',
        'renderExecutionDag()',
        'renderExecutionLog()',
        'openCommandPalette()',
        'pushExecutionLogEntry(',
    ]
    for token in required_tokens:
        assert token in script, token
    assert 'collapse-right' not in script
