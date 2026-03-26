from __future__ import annotations

import importlib
from typing import Any

from app.contracts.errors import ModuleLoadError


class ModuleLoader:
    def load(self, entrypoint: str, **kwargs: Any) -> Any:
        target = str(entrypoint or "").strip()
        if ":" not in target:
            raise ModuleLoadError(f"invalid entrypoint: {target!r}")
        module_path, symbol = target.split(":", 1)
        module_path = module_path.strip()
        symbol = symbol.strip()
        if not module_path or not symbol:
            raise ModuleLoadError(f"invalid entrypoint: {target!r}")
        try:
            module = importlib.import_module(module_path)
        except Exception as exc:
            raise ModuleLoadError(f"import failed for {module_path}: {exc}") from exc
        try:
            factory = getattr(module, symbol)
        except Exception as exc:
            raise ModuleLoadError(f"symbol not found: {target}") from exc
        if callable(factory):
            try:
                return factory(**kwargs)
            except TypeError:
                return factory()
        return factory
