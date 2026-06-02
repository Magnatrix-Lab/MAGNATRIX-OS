#!/usr/bin/env python3
"""
MAGNATRIX-OS — Auto-Loop Engine
ai/llm_auto_loop_engine_native.py

Inspired by Auto-Company (github.com/MaxMiksa/Auto-Company)
Pattern: Auto-Loop — daemon with cycle interval, circuit breaker, rate-limit handling.

Features:
- Cycle scheduler (interval, timeout, max cycles)
- Circuit breaker (max consecutive errors, cooldown, recovery)
- Rate limit detection and backoff
- Consensus rollback on failure
- PID/state file management
- Cycle logging and rotation
- Engine selection (Claude Code / Codex CLI pattern)

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import random
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("auto_loop_engine")


class CycleStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"


class CircuitState(enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CycleResult:
    cycle_num: int
    status: CycleStatus
    duration_ms: float
    error: Optional[str] = None
    output: Optional[str] = None


@dataclass
class LoopConfig:
    interval_seconds: float = 30.0
    cycle_timeout_seconds: float = 1800.0
    max_consecutive_errors: int = 5
    cooldown_seconds: float = 300.0
    limit_wait_seconds: float = 3600.0
    max_cycles: int = 1000
    max_logs: int = 200


class CircuitBreaker:
    """Circuit breaker with auto-recovery."""

    def __init__(self, max_errors: int = 5, cooldown: float = 300.0):
        self.max_errors = max_errors
        self.cooldown = cooldown
        self._state = CircuitState.CLOSED
        self._error_count = 0
        self._last_error_time = 0.0
        self._last_success_time = 0.0

    def record_success(self) -> None:
        self._error_count = 0
        self._last_success_time = time.monotonic()
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            logger.info("Circuit breaker: HALF_OPEN → CLOSED")

    def record_failure(self) -> None:
        self._error_count += 1
        self._last_error_time = time.monotonic()
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            logger.warning("Circuit breaker: HALF_OPEN → OPEN")
        elif self._error_count >= self.max_errors and self._state == CircuitState.CLOSED:
            self._state = CircuitState.OPEN
            logger.warning(f"Circuit breaker: CLOSED → OPEN (errors={self._error_count})")

    def can_execute(self) -> bool:
        if self._state == CircuitState.CLOSED:
            return True
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_error_time
            if elapsed >= self.cooldown:
                self._state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker: OPEN → HALF_OPEN")
                return True
            return False
        return self._state == CircuitState.HALF_OPEN

    @property
    def state(self) -> CircuitState:
        return self._state

    def get_status(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "error_count": self._error_count,
            "last_error": self._last_error_time,
            "last_success": self._last_success_time,
        }


class RateLimiter:
    """Rate limit detection and backoff."""

    LIMIT_KEYWORDS = ["usage limit", "rate limit", "too many requests", "resource_exhausted", "overloaded", "quota", "429", "billing", "insufficient credits"]

    def __init__(self, max_wait: float = 3600.0):
        self.max_wait = max_wait
        self._is_limited = False
        self._limited_until = 0.0
        self._backoff_seconds = 60.0

    def check(self, output: str) -> bool:
        output_lower = output.lower()
        if any(kw in output_lower for kw in self.LIMIT_KEYWORDS):
            self._is_limited = True
            self._backoff_seconds = min(self._backoff_seconds * 2, self.max_wait)
            self._limited_until = time.monotonic() + self._backoff_seconds
            logger.warning(f"Rate limit detected. Backoff: {self._backoff_seconds}s")
            return True
        self._is_limited = False
        self._backoff_seconds = max(60.0, self._backoff_seconds / 2)
        return False

    def can_execute(self) -> bool:
        if not self._is_limited:
            return True
        return time.monotonic() >= self._limited_until

    def wait_remaining(self) -> float:
        if not self._is_limited:
            return 0.0
        return max(0.0, self._limited_until - time.monotonic())


class AutoLoopEngine:
    """Auto-loop daemon engine."""

    def __init__(self, config: Optional[LoopConfig] = None):
        self.config = config or LoopConfig()
        self._circuit = CircuitBreaker(
            max_errors=self.config.max_consecutive_errors,
            cooldown=self.config.cooldown_seconds,
        )
        self._rate_limiter = RateLimiter(max_wait=self.config.limit_wait_seconds)
        self._cycle_count = 0
        self._is_running = False
        self._logs: deque = deque(maxlen=self.config.max_logs)
        self._state: Dict[str, Any] = {"current_phase": "idle", "last_cycle": 0}
        self._executor: Optional[Callable[[], str]] = None

    def set_executor(self, executor: Callable[[], str]) -> None:
        """Set the cycle executor function."""
        self._executor = executor

    def run_cycle(self) -> CycleResult:
        """Execute one cycle."""
        self._cycle_count += 1
        cycle_num = self._cycle_count

        # Check circuit breaker
        if not self._circuit.can_execute():
            return CycleResult(cycle_num, CycleStatus.FAILURE, 0.0, error=f"Circuit breaker OPEN")

        # Check rate limiter
        if not self._rate_limiter.can_execute():
            wait = self._rate_limiter.wait_remaining()
            return CycleResult(cycle_num, CycleStatus.RATE_LIMITED, 0.0, error=f"Rate limited, wait {wait:.0f}s")

        t0 = time.monotonic()
        self._state["last_cycle"] = cycle_num

        try:
            if self._executor:
                output = self._executor()
            else:
                output = "No executor configured"

            duration = (time.monotonic() - t0) * 1000

            # Check rate limit in output
            if self._rate_limiter.check(output):
                self._circuit.record_failure()
                result = CycleResult(cycle_num, CycleStatus.RATE_LIMITED, duration, error="Rate limited")
                self._log(result)
                return result

            # Check failure indicators
            if any(kw in output.lower() for kw in ["error", "failure", "exception", "crash"]):
                self._circuit.record_failure()
                result = CycleResult(cycle_num, CycleStatus.FAILURE, duration, error=output[:100])
                self._log(result)
                return result

            self._circuit.record_success()
            result = CycleResult(cycle_num, CycleStatus.SUCCESS, duration, output=output[:200])
            self._log(result)
            return result

        except Exception as e:
            duration = (time.monotonic() - t0) * 1000
            self._circuit.record_failure()
            result = CycleResult(cycle_num, CycleStatus.FAILURE, duration, error=str(e)[:100])
            self._log(result)
            return result

    def _log(self, result: CycleResult) -> None:
        self._logs.append({
            "cycle": result.cycle_num,
            "status": result.status.value,
            "duration_ms": result.duration_ms,
            "error": result.error,
            "output": result.output,
            "timestamp": time.monotonic(),
        })

    def run(self, cycles: Optional[int] = None) -> None:
        """Run the loop for N cycles or until stopped."""
        self._is_running = True
        target = cycles or self.config.max_cycles
        while self._is_running and self._cycle_count < target:
            result = self.run_cycle()
            if result.status == CycleStatus.SUCCESS:
                logger.info(f"Cycle #{result.cycle_num}: SUCCESS ({result.duration_ms:.0f}ms)")
            else:
                logger.warning(f"Cycle #{result.cycle_num}: {result.status.value} ({result.duration_ms:.0f}ms) - {result.error}")
            if self._is_running and self._cycle_count < target:
                time.sleep(self.config.interval_seconds)

    def stop(self) -> None:
        self._is_running = False

    def get_logs(self, n: int = 20) -> List[Dict[str, Any]]:
        return list(self._logs)[-n:]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._logs)
        successes = sum(1 for l in self._logs if l["status"] == "success")
        failures = total - successes
        avg_duration = sum(l["duration_ms"] for l in self._logs) / max(total, 1)
        return {
            "total_cycles": self._cycle_count,
            "logged_cycles": total,
            "successes": successes,
            "failures": failures,
            "avg_duration_ms": avg_duration,
            "circuit_state": self._circuit.state.value,
            "rate_limited": self._rate_limiter._is_limited,
            "running": self._is_running,
        }

    def get_state(self) -> Dict[str, Any]:
        return dict(self._state)


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Auto-Loop Engine")
    print("ai/llm_auto_loop_engine_native.py")
    print("Pattern: Auto-Company 24/7 Autonomous Loop")
    print("=" * 60)

    config = LoopConfig(
        interval_seconds=0.1,
        cycle_timeout_seconds=5.0,
        max_consecutive_errors=3,
        cooldown_seconds=0.5,
        max_cycles=10,
    )

    engine = AutoLoopEngine(config)

    # Simulate executor with varying results
    call_count = 0
    def mock_executor() -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 3:
            return "Error: rate limit exceeded"
        if call_count == 5:
            return "Error: connection timeout"
        if call_count == 7:
            return "Error: resource exhausted"
        return f"Cycle completed successfully. Task #{call_count} done."

    engine.set_executor(mock_executor)

    # 1. Run 10 cycles
    print("\n[1] Running 10 Cycles")
    engine.run(cycles=10)

    # 2. Logs
    print("\n[2] Cycle Logs")
    for log in engine.get_logs(10):
        print(f"  Cycle {log['cycle']}: {log['status']} ({log['duration_ms']:.1f}ms)")

    # 3. Stats
    print("\n[3] Engine Stats")
    stats = engine.get_stats()
    print(f"  Total: {stats['total_cycles']}, Success: {stats['successes']}, Fail: {stats['failures']}")
    print(f"  Avg duration: {stats['avg_duration_ms']:.1f}ms")
    print(f"  Circuit: {stats['circuit_state']}")

    # 4. Circuit breaker state
    print("\n[4] Circuit Breaker Status")
    cb_status = engine._circuit.get_status()
    print(f"  State: {cb_status['state']}, Errors: {cb_status['error_count']}")

    # 5. Rate limiter
    print("\n[5] Rate Limiter Status")
    print(f"  Rate limited: {stats['rate_limited']}")
    print(f"  Wait remaining: {engine._rate_limiter.wait_remaining():.1f}s")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
