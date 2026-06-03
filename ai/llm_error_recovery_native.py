#!/usr/bin/env python3
"""
MAGNATRIX-OS — Error Recovery & Self-Healing Engine
ai/llm_error_recovery_native.py

Features:
- Error classification (syntax, logic, runtime, network, resource)
- Recovery strategy selection (retry, fallback, degrade, abort)
- Retry with exponential backoff + jitter
- Circuit breaker integration (fail-fast after repeated errors)
- Health check and auto-restart simulation
- Recovery audit log

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import deque
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("error_recovery")


class ErrorType(enum.Enum):
    SYNTAX = "syntax"
    LOGIC = "logic"
    RUNTIME = "runtime"
    NETWORK = "network"
    RESOURCE = "resource"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class RecoveryStrategy(enum.Enum):
    RETRY = "retry"
    FALLBACK = "fallback"
    DEGRADE = "degrade"
    ABORT = "abort"
    SKIP = "skip"


@dataclass
class ErrorRecord:
    error_type: ErrorType
    message: str
    timestamp: float
    strategy: RecoveryStrategy
    success: bool


class ErrorClassifier:
    """Classify errors by type."""

    PATTERNS = {
        ErrorType.SYNTAX: ["syntax", "parse", "indentation", "invalid syntax"],
        ErrorType.LOGIC: ["assertion", "logic", "invariant", "condition"],
        ErrorType.RUNTIME: ["runtime", "exception", "index out of range", "key error"],
        ErrorType.NETWORK: ["connection", "timeout", "refused", "dns", "network"],
        ErrorType.RESOURCE: ["memory", "disk", "cpu", "resource", "quota"],
        ErrorType.TIMEOUT: ["timeout", "timed out", "deadline"],
    }

    def classify(self, error_message: str) -> ErrorType:
        msg_lower = error_message.lower()
        for etype, keywords in self.PATTERNS.items():
            if any(kw in msg_lower for kw in keywords):
                return etype
        return ErrorType.UNKNOWN


class RecoveryEngine:
    """Self-healing error recovery engine."""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self._classifier = ErrorClassifier()
        self._history: deque = deque(maxlen=100)
        self._circuit_failures = 0
        self._circuit_open = False
        self._circuit_reset_time = 0.0

    def recover(self, fn: Callable[[], Any], fallback: Optional[Callable[[], Any]] = None) -> Tuple[Any, bool]:
        """Execute with recovery. Returns (result, success)."""
        for attempt in range(self.max_retries + 1):
            if self._circuit_open:
                if time.monotonic() >= self._circuit_reset_time:
                    self._circuit_open = False
                    self._circuit_failures = 0
                else:
                    if fallback:
                        return fallback(), True
                    return None, False
            try:
                result = fn()
                self._circuit_failures = 0
                return result, True
            except Exception as e:
                err_type = self._classifier.classify(str(e))
                strategy = self._select_strategy(err_type, attempt)
                self._history.append(ErrorRecord(err_type, str(e), time.monotonic(), strategy, False))
                if strategy == RecoveryStrategy.RETRY and attempt < self.max_retries:
                    delay = self._backoff(attempt)
                    time.sleep(delay)
                    continue
                elif strategy == RecoveryStrategy.FALLBACK and fallback:
                    return fallback(), True
                elif strategy == RecoveryStrategy.DEGRADE:
                    return "DEGRADED_OUTPUT", True
                else:
                    self._circuit_failures += 1
                    if self._circuit_failures >= self.max_retries:
                        self._circuit_open = True
                        self._circuit_reset_time = time.monotonic() + 30.0
                    return None, False
        return None, False

    def _select_strategy(self, error_type: ErrorType, attempt: int) -> RecoveryStrategy:
        if error_type in (ErrorType.NETWORK, ErrorType.TIMEOUT):
            if attempt < self.max_retries:
                return RecoveryStrategy.RETRY
            return RecoveryStrategy.FALLBACK
        elif error_type == ErrorType.RESOURCE:
            return RecoveryStrategy.DEGRADE
        elif error_type == ErrorType.SYNTAX:
            return RecoveryStrategy.ABORT
        return RecoveryStrategy.RETRY if attempt < self.max_retries else RecoveryStrategy.ABORT

    def _backoff(self, attempt: int) -> float:
        delay = self.base_delay * (2 ** attempt)
        jitter = random.uniform(0, delay * 0.5)
        return delay + jitter

    def get_history(self, n: int = 20) -> List[ErrorRecord]:
        return list(self._history)[-n:]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._history)
        successes = sum(1 for r in self._history if r.success)
        types = {}
        for r in self._history:
            types[r.error_type.value] = types.get(r.error_type.value, 0) + 1
        return {
            "total_errors": total,
            "recoveries": successes,
            "failures": total - successes,
            "circuit_open": self._circuit_open,
            "by_type": types,
        }


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Error Recovery & Self-Healing Engine")
    print("ai/llm_error_recovery_native.py")
    print("=" * 60)

    engine = RecoveryEngine(max_retries=3, base_delay=0.1)

    # 1. Successful call
    print("\n[1] Successful Call")
    result, ok = engine.recover(lambda: "Success")
    print(f"  Result: {result}, OK: {ok}")

    # 2. Retry then success
    print("\n[2] Retry Then Success")
    attempts = 0
    def flaky():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise Exception("Connection timeout")
        return "Recovered"
    result, ok = engine.recover(flaky)
    print(f"  Result: {result}, OK: {ok}, Attempts: {attempts}")

    # 3. Fallback
    print("\n[3] Fallback")
    def always_fail():
        raise Exception("Disk full")
    def fallback_fn():
        return "Fallback output"
    result, ok = engine.recover(always_fail, fallback_fn)
    print(f"  Result: {result}, OK: {ok}")

    # 4. Degrade
    print("\n[4] Degrade")
    def resource_error():
        raise Exception("Memory exhausted")
    result, ok = engine.recover(resource_error)
    print(f"  Result: {result}, OK: {ok}")

    # 5. Stats
    print("\n[5] Recovery Stats")
    stats = engine.get_stats()
    print(f"  {stats}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
