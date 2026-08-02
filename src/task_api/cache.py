# src/task_api/cache.py
# High-performance in-memory and pluggable caching service with write-invalidation support.
# Connects to: src/task_api/main.py
# Created: 2026-08-02

import time
import json
import threading
from typing import Optional, Any, Dict


class CacheService:
    """Thread-safe response cache manager with TTL expiration and pattern invalidation."""

    def __init__(self, default_ttl_seconds: int = 60):
        self.default_ttl = default_ttl_seconds
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Retrieve cached item if not expired."""
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None

            if time.time() > entry["expires_at"]:
                del self._store[key]
                return None

            return entry["data"]

    def set(self, key: str, data: Any, ttl_seconds: Optional[int] = None) -> None:
        """Store item in cache with TTL."""
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expires_at = time.time() + ttl
        with self._lock:
            self._store[key] = {
                "data": data,
                "expires_at": expires_at
            }

    def invalidate_user_cache(self, owner_id: int) -> None:
        """Invalidate all cached keys associated with a specific user ID."""
        prefix = f"tasks:user:{owner_id}:"
        with self._lock:
            keys_to_del = [k for k in self._store if k.startswith(prefix)]
            for k in keys_to_del:
                del self._store[k]

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._store.clear()


cache_service = CacheService(default_ttl_seconds=60)
