"""
services/rate_limit.py - a tiny in-memory SLIDING WINDOW rate limiter.

    limiter = SlidingWindowLimiter(max_calls=20, window_seconds=60)
    ok, retry_after = limiter.check(user_id)

Each user has a list of the times of their recent calls. A call is allowed when fewer than max_calls happened
in the last window_seconds. Works per server process (good enough for this project).
"""
import threading
import time
from collections import defaultdict, deque


class SlidingWindowLimiter:
    def __init__(self, max_calls: int, window_seconds: float, clock=time.monotonic):
        self.max_calls = max_calls
        self.window = window_seconds
        self.clock = clock
        self._calls: dict = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key) -> tuple[bool, int]:
        """Record a call for `key`. Returns (allowed, seconds_until_next_allowed)."""
        now = self.clock()
        with self._lock:
            q = self._calls[key]
            while q and now - q[0] >= self.window:
                q.popleft()                                    # forget calls older than the window
            if len(q) >= self.max_calls:
                return False, max(1, int(self.window - (now - q[0])) + 1)
            q.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._calls.clear()
