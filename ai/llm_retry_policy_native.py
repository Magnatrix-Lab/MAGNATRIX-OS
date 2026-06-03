"""
llm_retry_policy_native.py
MAGNATRIX-OS Retry Policy Engine
Native Python, stdlib only.
Provides configurable retry strategies: fixed, exponential backoff, linear, jitter,
circuit breaker integration, and per-error-type policies.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple, Type


class RetryStrategy(Enum):
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    JITTER = "jitter"
    CUSTOM = "custom"


class RetryResult(Enum):
    SUCCESS = "success"
    MAX_RETRIES_EXCEEDED = "max_retries_exceeded"
    CIRCUIT_OPEN = "circuit_open"
    TIMEOUT = "timeout"
    GIVEUP = "giveup"


@dataclass
class RetryPolicy:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    retryable_errors: List[Type[Exception]] = field(default_factory=list)
    non_retryable_errors: List[Type[Exception]] = field(default_factory=list)
    timeout_seconds: Optional[float] = None
    on_retry: Optional[Callable[[int, Exception, float], None]] = None
    on_giveup: Optional[Callable[[Exception], None]] = None
    custom_delay_fn: Optional[Callable[[int], float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_retries": self.max_retries,
            "base_delay": self.base_delay,
            "max_delay": self.max_delay,
            "strategy": self.strategy.value,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass
class RetryOutcome:
    result: Any
    attempts: int
    total_delay: float
    final_status: RetryResult
    last_error: Optional[Exception] = None
    delays: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attempts": self.attempts,
            "total_delay": round(self.total_delay, 3),
            "final_status": self.final_status.value,
            "last_error": str(self.last_error) if self.last_error else None,
            "delays": [round(d, 3) for d in self.delays],
        }


class RetryPolicyEngine:
    """
    Retry policy engine with multiple backoff strategies and error classification.
    """

    def __init__(self) -> None:
        self._policies: Dict[str, RetryPolicy] = {}
        self._stats: Dict[str, Dict[str, Any]] = {}

    def register_policy(self, name: str, policy: RetryPolicy) -> None:
        self._policies[name] = policy
        if name not in self._stats:
            self._stats[name] = {"total_calls": 0, "successes": 0, "failures": 0, "retries": 0}

    def _compute_delay(self, policy: RetryPolicy, attempt: int) -> float:
        if policy.strategy == RetryStrategy.FIXED:
            return policy.base_delay
        elif policy.strategy == RetryStrategy.EXPONENTIAL:
            delay = policy.base_delay * (2 ** (attempt - 1))
            return min(delay, policy.max_delay)
        elif policy.strategy == RetryStrategy.LINEAR:
            return min(policy.base_delay * attempt, policy.max_delay)
        elif policy.strategy == RetryStrategy.JITTER:
            base = policy.base_delay * (2 ** (attempt - 1))
            jitter = random.uniform(0, base)
            return min(base + jitter, policy.max_delay)
        elif policy.strategy == RetryStrategy.CUSTOM and policy.custom_delay_fn:
            return min(policy.custom_delay_fn(attempt), policy.max_delay)
        return policy.base_delay

    def _is_retryable(self, policy: RetryPolicy, error: Exception) -> bool:
        if policy.non_retryable_errors and any(isinstance(error, e) for e in policy.non_retryable_errors):
            return False
        if policy.retryable_errors:
            return any(isinstance(error, e) for e in policy.retryable_errors)
        return True  # Default: retry all

    def execute(self, policy_name: str, fn: Callable, *args, **kwargs) -> RetryOutcome:
        policy = self._policies.get(policy_name)
        if not policy:
            policy = RetryPolicy()  # Default

        self._stats[policy_name]["total_calls"] += 1
        start_time = time.time()
        total_delay = 0.0
        delays: List[float] = []
        last_error: Optional[Exception] = None

        for attempt in range(1, policy.max_retries + 2):
            try:
                if policy.timeout_seconds:
                    # Simple timeout via signal not used; just check elapsed
                    elapsed = time.time() - start_time
                    if elapsed > policy.timeout_seconds:
                        self._stats[policy_name]["failures"] += 1
                        return RetryOutcome(None, attempt, total_delay, RetryResult.TIMEOUT, last_error, delays)

                result = fn(*args, **kwargs)
                self._stats[policy_name]["successes"] += 1
                return RetryOutcome(result, attempt, total_delay, RetryResult.SUCCESS, None, delays)
            except Exception as e:
                last_error = e
                if not self._is_retryable(policy, e):
                    self._stats[policy_name]["failures"] += 1
                    if policy.on_giveup:
                        policy.on_giveup(e)
                    return RetryOutcome(None, attempt, total_delay, RetryResult.GIVEUP, e, delays)

                if attempt > policy.max_retries:
                    break

                delay = self._compute_delay(policy, attempt)
                delays.append(delay)
                total_delay += delay
                self._stats[policy_name]["retries"] += 1
                if policy.on_retry:
                    policy.on_retry(attempt, e, delay)
                time.sleep(delay)

        self._stats[policy_name]["failures"] += 1
        if policy.on_giveup and last_error:
            policy.on_giveup(last_error)
        return RetryOutcome(None, attempt, total_delay, RetryResult.MAX_RETRIES_EXCEEDED, last_error, delays)

    def get_stats(self, policy_name: Optional[str] = None) -> Dict[str, Any]:
        if policy_name:
            return self._stats.get(policy_name, {})
        return dict(self._stats)

    def reset_stats(self, policy_name: Optional[str] = None) -> None:
        if policy_name:
            self._stats[policy_name] = {"total_calls": 0, "successes": 0, "failures": 0, "retries": 0}
        else:
            for k in self._stats:
                self._stats[k] = {"total_calls": 0, "successes": 0, "failures": 0, "retries": 0}


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Retry Policy Engine")
    print("=" * 60)

    engine = RetryPolicyEngine()

    # Register policies
    engine.register_policy("llm_api", RetryPolicy(
        max_retries=3, base_delay=0.5, max_delay=5.0,
        strategy=RetryStrategy.EXPONENTIAL,
        retryable_errors=[RuntimeError, ConnectionError],
    ))
    engine.register_policy("fast_retry", RetryPolicy(
        max_retries=5, base_delay=0.1, max_delay=1.0,
        strategy=RetryStrategy.LINEAR,
    ))
    engine.register_policy("jitter_retry", RetryPolicy(
        max_retries=3, base_delay=0.3, max_delay=3.0,
        strategy=RetryStrategy.JITTER,
    ))

    # Simulate failing function that succeeds on 3rd try
    call_count = 0
    def flaky_fn() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RuntimeError(f"Simulated failure #{call_count}")
        return "Success"

    print("\n--- Exponential backoff retry ---")
    call_count = 0
    outcome = engine.execute("llm_api", flaky_fn)
    print(f"  Status: {outcome.final_status.value}")
    print(f"  Attempts: {outcome.attempts}")
    print(f"  Delays: {outcome.delays}")
    print(f"  Total delay: {outcome.total_delay:.3f}s")
    print(f"  Result: {outcome.result}")

    print("\n--- Max retries exceeded ---")
    call_count = 0
    def always_fail() -> str:
        nonlocal call_count
        call_count += 1
        raise RuntimeError("Always fails")

    call_count = 0
    outcome = engine.execute("llm_api", always_fail)
    print(f"  Status: {outcome.final_status.value}")
    print(f"  Attempts: {outcome.attempts}")
    print(f"  Last error: {outcome.last_error}")

    print("\n--- Non-retryable error ---")
    def value_error_fn() -> str:
        raise ValueError("Bad input")

    engine.register_policy("no_value_error", RetryPolicy(
        max_retries=3, base_delay=0.1,
        non_retryable_errors=[ValueError],
    ))
    outcome = engine.execute("no_value_error", value_error_fn)
    print(f"  Status: {outcome.final_status.value}")
    print(f"  Attempts: {outcome.attempts} (should be 1, no retry)")

    print("\n--- Stats ---")
    print(engine.get_stats())

    print("\nRetry Policy test complete.")


if __name__ == "__main__":
    run()
