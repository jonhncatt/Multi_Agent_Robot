from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable


EventHandler = Callable[[dict[str, Any]], None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        key = str(event_name or "").strip()
        if not key:
            return
        self._handlers[key].append(handler)

    def publish(self, event_name: str, payload: dict[str, Any] | None = None) -> None:
        key = str(event_name or "").strip()
        if not key:
            return
        event = {"event": key, **dict(payload or {})}
        for handler in list(self._handlers.get(key, [])):
            try:
                handler(event)
            except Exception:
                continue
