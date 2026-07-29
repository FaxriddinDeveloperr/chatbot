"""Oddiy sliding-window rate limiter: bitta odamdan daqiqasiga 5 xabar."""

from __future__ import annotations

import time
from collections import defaultdict, deque


class RateLimiter:
    """Har bir user uchun oxirgi `window` soniyadagi xabarlarni sanaydi."""

    def __init__(self, limit: int = 5, window: float = 60.0) -> None:
        self.limit = limit
        self.window = window
        self._hits: dict[int, deque[float]] = defaultdict(deque)

    def allow(self, user_id: int) -> bool:
        now = time.monotonic()
        hits = self._hits[user_id]
        while hits and now - hits[0] > self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True


rate_limiter = RateLimiter()
