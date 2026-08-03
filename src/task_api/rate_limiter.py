# src/task_api/rate_limiter.py
# Sliding-window rate limiting service to enforce request rate limits across endpoints.
# Connects to: src/task_api/main.py
# Created: 2026-08-02

import time
import threading
from typing import Dict, List, Tuple


class RateLimiter:
    """Thread-safe sliding-window rate limiter for HTTP endpoints."""

    def __init__(self):
        self._requests: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def check_rate_limit(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int]:
        """
        Check if request under key exceeds max_requests within window_seconds.
        Returns Tuple[is_allowed: bool, retry_after_seconds: int].
        """
        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            if key not in self._requests:
                self._requests[key] = []

            # Filter out timestamps older than the sliding window
            valid_timestamps = [t for t in self._requests[key] if t > window_start]
            self._requests[key] = valid_timestamps

            if len(valid_timestamps) >= max_requests:
                oldest_in_window = valid_timestamps[0]
                retry_after = int(window_seconds - (now - oldest_in_window)) + 1
                return False, max(retry_after, 1)

            self._requests[key].append(now)
            return True, 0

    def reset(self):
        """Clear all stored rate limit state (useful for tests)."""
        with self._lock:
            self._requests.clear()


rate_limiter = RateLimiter()
