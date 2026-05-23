"""Unit tests for app.core.rate_limiter."""
import time

import pytest
from fastapi import HTTPException

from app.core.rate_limiter import _SlidingWindowLimiter


def make_limiter(max_attempts=3, window_seconds=60, lockout_seconds=300):
    return _SlidingWindowLimiter(
        max_attempts=max_attempts,
        window_seconds=window_seconds,
        lockout_seconds=lockout_seconds,
    )


class TestSlidingWindowLimiter:
    def test_check_clean_key_passes(self):
        limiter = make_limiter()
        limiter.check("user@example.com")  # should not raise

    def test_single_failure_does_not_lock(self):
        limiter = make_limiter(max_attempts=3)
        limiter.record_failure("user@a.com")
        limiter.check("user@a.com")  # still under threshold

    def test_two_failures_do_not_lock(self):
        limiter = make_limiter(max_attempts=3)
        limiter.record_failure("user@a.com")
        limiter.record_failure("user@a.com")
        limiter.check("user@a.com")  # still under threshold

    def test_max_attempts_triggers_lockout(self):
        limiter = make_limiter(max_attempts=3, lockout_seconds=300)
        for _ in range(3):
            limiter.record_failure("user@a.com")
        with pytest.raises(HTTPException) as exc:
            limiter.check("user@a.com")
        assert exc.value.status_code == 429

    def test_lockout_message_includes_retry_after(self):
        limiter = make_limiter(max_attempts=2, lockout_seconds=600)
        limiter.record_failure("user@a.com")
        limiter.record_failure("user@a.com")
        with pytest.raises(HTTPException) as exc:
            limiter.check("user@a.com")
        assert "Retry-After" in exc.value.headers

    def test_reset_clears_failures(self):
        limiter = make_limiter(max_attempts=3, lockout_seconds=300)
        for _ in range(3):
            limiter.record_failure("user@a.com")
        limiter.reset("user@a.com")
        limiter.check("user@a.com")  # should not raise after reset

    def test_reset_nonexistent_key_ok(self):
        limiter = make_limiter()
        limiter.reset("nobody@a.com")  # should not raise

    def test_different_keys_isolated(self):
        limiter = make_limiter(max_attempts=3, lockout_seconds=300)
        for _ in range(3):
            limiter.record_failure("bad@a.com")
        limiter.check("good@a.com")  # different key — unaffected

    def test_window_prunes_old_failures(self):
        limiter = make_limiter(max_attempts=3, window_seconds=1, lockout_seconds=300)
        limiter.record_failure("user@a.com")
        limiter.record_failure("user@a.com")
        time.sleep(1.1)  # wait for window to expire
        limiter.record_failure("user@a.com")  # only 1 in window now
        limiter.check("user@a.com")  # should not be locked

    def test_check_locked_key_raises_429(self):
        limiter = make_limiter(max_attempts=1, lockout_seconds=300)
        limiter.record_failure("locked@a.com")
        with pytest.raises(HTTPException) as exc:
            limiter.check("locked@a.com")
        assert exc.value.status_code == 429

    def test_retry_after_value_is_positive(self):
        limiter = make_limiter(max_attempts=1, lockout_seconds=60)
        limiter.record_failure("user@a.com")
        with pytest.raises(HTTPException) as exc:
            limiter.check("user@a.com")
        retry_after = int(exc.value.headers["Retry-After"])
        assert retry_after > 0
        assert retry_after <= 60
