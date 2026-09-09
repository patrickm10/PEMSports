import time
from typing import Any, Optional

class SimpleCache:
    """A lightweight, in-memory TTL cache to replace the missing cache implementation."""
    def __init__(self):
        self._store = {}
    
    def get(self, key: str) -> Optional[Any]:
        if key in self._store:
            entry = self._store[key]
            if entry["expires_at"] is None or entry["expires_at"] > time.time():
                return entry["data"]
            else:
                del self._store[key]
        return None
        
    def set(self, key: str, data: Any, ttl: Optional[int] = 300):
        expires_at = time.time() + ttl if ttl else None
        self._store[key] = {
            "data": data,
            "expires_at": expires_at
        }

    def clear(self) -> None:
        self._store.clear()

cache = SimpleCache()
