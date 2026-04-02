"""
In-memory TTL cache with a Redis-compatible interface.

Design goals:
- Keys are deterministic strings (e.g. "rankings:qb", "seasons:rb").
- The get/set/invalidate interface is identical to what a Redis client would expose,
  so swapping to Redis in the future only requires changing this module.
- Thread-safe for single-process deployments (uvicorn default). For multi-worker
  gunicorn, replace with Redis to share cache across processes.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

_DEFAULT_TTL = 300  # 5 minutes


class _CacheEntry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, ttl: int) -> None:
        self.value = value
        self.expires_at = time.monotonic() + ttl


class TTLCache:
    def __init__(self, default_ttl: int = _DEFAULT_TTL) -> None:
        self._store: dict[str, _CacheEntry] = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() > entry.expires_at:
            del self._store[key]
            logger.debug("Cache expired: %s", key)
            return None
        logger.debug("Cache hit: %s", key)
        return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        effective_ttl = ttl if ttl is not None else self._default_ttl
        self._store[key] = _CacheEntry(value, effective_ttl)
        logger.debug("Cache set: %s (ttl=%ds)", key, effective_ttl)

    def invalidate(self, key: str) -> bool:
        """Remove a specific key. Returns True if it existed."""
        existed = key in self._store
        self._store.pop(key, None)
        return existed

    def invalidate_prefix(self, prefix: str) -> int:
        """Remove all keys starting with prefix. Returns count removed."""
        keys = [k for k in self._store if k.startswith(prefix)]
        for k in keys:
            del self._store[k]
        if keys:
            logger.info("Cache invalidated %d keys with prefix: %s", len(keys), prefix)
        return len(keys)

    def clear(self) -> None:
        self._store.clear()
        logger.info("Cache cleared")

    @property
    def size(self) -> int:
        return len(self._store)


# Singleton — imported by service layer.
# Lifetime is tied to the uvicorn worker process.
cache = TTLCache(default_ttl=_DEFAULT_TTL)
