"""Caching service with TTL support."""

import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any


class TTLCache:
    """Thread-safe TTL cache implementation."""

    def __init__(self, ttl_seconds: int = 120, maxsize: int = 128):
        self.ttl = ttl_seconds
        self.maxsize = max(1, maxsize)
        self._store: dict[tuple, tuple[float, Any]] = {}
        self._order: deque[tuple] = deque()
        self._lock = threading.Lock()

    def _discard(self, key: tuple):
        """Remove a key from cache."""
        self._store.pop(key, None)
        try:
            self._order.remove(key)
        except ValueError:
            pass

    def _record(self, key: tuple):
        """Record key access for LRU eviction."""
        try:
            self._order.remove(key)
        except ValueError:
            pass
        self._order.append(key)
        while len(self._order) > self.maxsize:
            oldest = self._order.popleft()
            self._store.pop(oldest, None)

    def get(self, key: tuple):
        """Get value from cache if not expired."""
        now = time.time()
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            expires_at, value = entry
            if expires_at <= now:
                self._discard(key)
                return None
        return value.copy() if isinstance(value, dict) else value, expires_at

    def set(self, key: tuple, value: Any, ttl_seconds: int | None = None):
        """Set value in cache with TTL."""
        ttl = ttl_seconds if ttl_seconds is not None else self.ttl
        expires_at = time.time() + max(1, ttl)
        with self._lock:
            self._store[key] = (
                expires_at,
                value.copy() if isinstance(value, dict) else value,
            )
            self._record(key)
        return expires_at

    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._store.clear()
            self._order.clear()

    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._store)

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                "size": len(self._store),
                "maxsize": self.maxsize,
                "ttl_seconds": self.ttl,
            }


def cache_meta(hit: bool, expires_at: float) -> dict[str, Any]:
    """Generate cache metadata for API responses."""
    return {
        "cache": {
            "hit": hit,
            "expires_at": datetime.fromtimestamp(expires_at, timezone.utc).isoformat(),
            "seconds_remaining": max(0, int(expires_at - time.time())),
        }
    }
