from __future__ import annotations

from app.contracts.errors import ModuleInitError
from app.contracts.module import BaseModule


class LifecycleManager:
    def __init__(self) -> None:
        self._initialized: list[BaseModule] = []

    def init_module(self, module: BaseModule, *, kernel_context: object) -> None:
        try:
            module.init(kernel_context)
        except Exception as exc:
            raise ModuleInitError(f"module init failed: {module.manifest.identity()} ({exc})") from exc
        self._initialized.append(module)

    def init_modules(self, modules: list[BaseModule], *, kernel_context: object) -> None:
        for module in modules:
            self.init_module(module, kernel_context=kernel_context)

    def shutdown_all(self) -> None:
        for module in reversed(self._initialized):
            try:
                module.shutdown()
            except Exception:
                continue
        self._initialized.clear()
