from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MAIN_APP_PATH = REPO_ROOT / "app" / "main.py"


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(str(alias.name or ""))
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(str(node.module))
    return modules


def test_main_app_no_longer_imports_runtime_assembly_directly() -> None:
    imported = _imported_modules(MAIN_APP_PATH)
    assert "app.bootstrap" not in imported
    assert "packages.runtime_core.legacy_host_support" not in imported


def test_main_app_uses_explicit_chat_runtime_boundary() -> None:
    content = MAIN_APP_PATH.read_text(encoding="utf-8")
    assert "from app.chat_product_runtime import ChatProductRuntime" in content
    assert "from app.legacy_platform_runtime import get_legacy_agent_os_runtime" in content
    assert "chat_product_runtime = ChatProductRuntime(config)" in content
    assert "get_chat_product_runtime().runtime_meta()" in content
    assert "get_chat_product_runtime().tool_executor" in content
