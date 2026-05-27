"""
app/core/rate_limiter.py — Sliding-window rate limiter for login brute-force protection.

In-process implementation using a plain dict.
For multi-instance deployments, swap the backend to Redis (same interface).

Usage:
    from app.core.rate_limiter import login_rate_limiter
    login_rate_limiter.check(key)   # raises 429 if limit exceeded
    login_rate_limiter.record_failure(key)
    login_rate_limiter.reset(key)   # call on successful login
"""
import time
from collections import defaultdict
from threading import Lock
from typing import NamedTuple

from fastapi import HTTPException, status

from app.core.config import get_settings


class _WindowState(NamedTuple):
    timestamps: list  # epoch seconds of failed attempts
    locked_until: float  # epoch second; 0 = not locked


class _SlidingWindowLimiter:
    def __init__(self, *, max_attempts: int, window_seconds: int, lockout_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        self._store: dict[str, _WindowState] = defaultdict(lambda: _WindowState([], 0.0))
        self._lock = Lock()

    def _prune(self, timestamps: list, now: float) -> list:
        cutoff = now - self.window_seconds
        return [t for t in timestamps if t > cutoff]

    def check(self, key: str) -> None:
        """Raise HTTP 429 if the key is rate-limited or locked out."""
        now = time.time()
        with self._lock:
            state = self._store[key]
            if state.locked_until and now < state.locked_until:
                retry_after = int(state.locked_until - now)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Account temporarily locked. Try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)},
                )
            timestamps = self._prune(state.timestamps, now)
            self._store[key] = _WindowState(timestamps, state.locked_until)

    def record_failure(self, key: str) -> None:
        """Record a failed attempt. Triggers lockout when max_attempts is hit."""
        now = time.time()
        with self._lock:
            state = self._store[key]
            timestamps = self._prune(state.timestamps, now) + [now]
            locked_until = state.locked_until
            if len(timestamps) >= self.max_attempts:
                locked_until = now + self.lockout_seconds
                timestamps = []  # reset window so lockout_seconds is the only barrier
            self._store[key] = _WindowState(timestamps, locked_until)

    def reset(self, key: str) -> None:
        """Clear failures after a successful login."""
        with self._lock:
            self._store.pop(key, None)


def _build_limiter() -> _SlidingWindowLimiter:
    s = get_settings()
    return _SlidingWindowLimiter(
        max_attempts=s.login_max_attempts,
        window_seconds=s.login_rate_window_seconds,
        lockout_seconds=s.login_lockout_seconds,
    )


# Module-level singleton — one limiter for login attempts keyed by email or IP
login_rate_limiter: _SlidingWindowLimiter = _build_limiter()
