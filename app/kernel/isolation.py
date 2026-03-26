from __future__ import annotations

from typing import Any, Callable


def run_isolated(fn: Callable[[], Any], *, on_error: Callable[[Exception], Any] | None = None) -> Any:
    try:
        return fn()
    except Exception as exc:
        if on_error is not None:
            return on_error(exc)
        raise
