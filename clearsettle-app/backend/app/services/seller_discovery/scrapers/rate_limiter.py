"""
Async token-bucket rate limiter.

Designed for per-source request throttling in the discovery engine.
Thread-safe within a single asyncio event loop (uses asyncio.Lock).

Token bucket algorithm:
  - Bucket refills at `rate_rps` tokens per second.
  - Burst allows short bursts above the sustained rate.
  - acquire() blocks until a token is available, then consumes one.
  - Jitter is added on top of the calculated wait — this is the main
    compliance mechanism: it prevents detectable fixed-interval patterns.

Typical configuration (from Settings):
  rate_rps = 0.5   →  one request every 2 seconds (sustained)
  burst    = 1     →  no burst (single token bucket)

Scale note:
  This limiter is per-process. For horizontal scaling with multiple workers,
  replace with a Redis-backed token bucket (e.g. redis-py INCR + EXPIRE).
"""
from __future__ import annotations

import asyncio
import logging
import random
import time

logger = logging.getLogger(__name__)


class AsyncTokenBucket:
    """
    Async token bucket with per-request jitter.

    Args:
        rate_rps   — sustained rate in requests per second (e.g. 0.5 = 1 req/2s)
        burst      — maximum tokens accumulated; set to 1 for strict limiting
        jitter_min — minimum extra sleep after acquiring a token (seconds)
        jitter_max — maximum extra sleep after acquiring a token (seconds)
    """

    def __init__(
        self,
        rate_rps:   float = 0.5,
        burst:      int   = 1,
        jitter_min: float = 0.5,
        jitter_max: float = 2.5,
    ):
        if rate_rps <= 0:
            raise ValueError("rate_rps must be positive")
        if burst < 1:
            raise ValueError("burst must be >= 1")

        self._rate      = rate_rps
        self._burst     = float(burst)
        self._tokens    = float(burst)     # start full
        self._updated   = time.monotonic()
        self._lock      = asyncio.Lock()
        self._jitter_min = jitter_min
        self._jitter_max = jitter_max

    async def acquire(self) -> float:
        """
        Block until a token is available, consume it, apply jitter.

        Returns the total time slept (token wait + jitter) in seconds.
        Callers don't need this value but it's useful for logging.
        """
        total_sleep = 0.0

        async with self._lock:
            now     = time.monotonic()
            elapsed = now - self._updated
            # Refill tokens proportional to elapsed time, capped at burst
            self._tokens  = min(self._burst, self._tokens + elapsed * self._rate)
            self._updated = now

            if self._tokens < 1.0:
                wait = (1.0 - self._tokens) / self._rate
                logger.debug("Rate limiter waiting %.2fs for token", wait)
                await asyncio.sleep(wait)
                total_sleep += wait
                self._tokens = 0.0
            else:
                self._tokens -= 1.0

        # Jitter applied outside the lock so other waiters aren't blocked by it
        jitter = random.uniform(self._jitter_min, self._jitter_max)
        await asyncio.sleep(jitter)
        total_sleep += jitter

        return total_sleep

    @property
    def current_tokens(self) -> float:
        """Approximate token count — for monitoring / logging only."""
        now     = time.monotonic()
        elapsed = now - self._updated
        return min(self._burst, self._tokens + elapsed * self._rate)


# ── Factory ───────────────────────────────────────────────────────────────────

def make_rate_limiter(rate_rps: float, burst: int = 1) -> AsyncTokenBucket:
    """Convenience factory. Pulls defaults from Settings when not provided."""
    return AsyncTokenBucket(rate_rps=rate_rps, burst=burst)
