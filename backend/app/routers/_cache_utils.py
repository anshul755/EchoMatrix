from __future__ import annotations

from threading import Lock
from time import monotonic
from typing import Any


class ResponseCache:
    def __init__(self, ttl_seconds: float):
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, tuple[float, Any]] = {}
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        now = monotonic()
        with self._lock:
            entry = self._items.get(key)
            if entry is None:
                return None
            stored_at, value = entry
            if (now - stored_at) >= self.ttl_seconds:
                self._items.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._items[key] = (monotonic(), value)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
