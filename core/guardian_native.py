#!/usr/bin/env python3
"""
Guardian for MAGNATRIX-OS (GENesis-AGI inspired)
System protection, resilience, integrity checks, circuit breaker, recovery.
Pure stdlib -- no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import time
from typing import Any, Callable, Dict, List, Optional


class AlertLevel(enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    FATAL = "fatal"


@dataclasses.dataclass
class SystemHealth:
    timestamp: float
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_tasks: int
    pending_signals: int
    error_rate: float
    last_error: Optional[str] = None


class CircuitBreaker:
    """Circuit breaker pattern for fault tolerance."""

    STATE_CLOSED = "closed"      # Normal operation
    STATE_OPEN = "open"          # Failure threshold reached
    STATE_HALF_OPEN = "half_open"  # Testing recovery

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._state = self.STATE_CLOSED
        self._failures = 0
        self._last_failure_time = 0.0
        self._successes = 0

    def can_execute(self) -> bool:
        if self._state == self.STATE_CLOSED:
            return True
        if self._state == self.STATE_OPEN:
            if time.time() - self._last_failure_time >= self._recovery_timeout:
                self._state = self.STATE_HALF_OPEN
                self._failures = 0
                return True
            return False
        if self._state == self.STATE_HALF_OPEN:
            return True
        return False

    def record_success(self) -> None:
        if self._state == self.STATE_HALF_OPEN:
            self._successes += 1
            if self._successes >= 3:
                self._state = self.STATE_CLOSED
                self._failures = 0
        else:
            self._failures = max(0, self._failures - 1)

    def record_failure(self) -> None:
        self._failures += 1
        self._last_failure_time = time.time()

        if self._state == self.STATE_HALF_OPEN:
            self._state = self.STATE_OPEN
        elif self._failures >= self._failure_threshold:
            self._state = self.STATE_OPEN

    def get_state(self) -> str:
        return self._state


class Guardian:
    """System protection and resilience guardian."""

    def __init__(self) -> None:
        self._health_history: List[SystemHealth] = []
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._alerts: List[Dict[str, Any]] = []
        self._recovery_procedures: Dict[str, Callable] = {}
        self._active: bool = True

    def register_breaker(self, name: str, failure_threshold: int = 5, recovery_timeout: float = 30.0) -> CircuitBreaker:
        breaker = CircuitBreaker(failure_threshold, recovery_timeout)
        self._breakers[name] = breaker
        return breaker

    def check_health(self, cpu: float, memory: float, disk: float, tasks: int, pending: int, errors: float) -> SystemHealth:
        health = SystemHealth(
            timestamp=time.time(),
            cpu_usage=cpu,
            memory_usage=memory,
            disk_usage=disk,
            active_tasks=tasks,
            pending_signals=pending,
            error_rate=errors,
        )
        self._health_history.append(health)
        if len(self._health_history) > 100:
            self._health_history = self._health_history[-100:]

        # Assess health and alert
        self._assess_health(health)
        return health

    def _assess_health(self, health: SystemHealth) -> None:
        if health.cpu_usage > 0.9 or health.memory_usage > 0.9:
            self._alerts.append({
                'level': AlertLevel.CRITICAL,
                'message': f"System resource critical: CPU={health.cpu_usage:.0%}, Memory={health.memory_usage:.0%}",
                'timestamp': time.time(),
            })
        elif health.error_rate > 0.1:
            self._alerts.append({
                'level': AlertLevel.WARNING,
                'message': f"Error rate elevated: {health.error_rate:.1%}",
                'timestamp': time.time(),
            })

    def register_recovery(self, failure_type: str, procedure: Callable) -> None:
        self._recovery_procedures[failure_type] = procedure

    def attempt_recovery(self, failure_type: str) -> bool:
        procedure = self._recovery_procedures.get(failure_type)
        if procedure:
            try:
                procedure()
                return True
            except Exception as e:
                self._alerts.append({
                    'level': AlertLevel.CRITICAL,
                    'message': f"Recovery failed: {str(e)}",
                    'timestamp': time.time(),
                })
                return False
        return False

    def get_health_trend(self, window: int = 10) -> Dict[str, float]:
        if len(self._health_history) < window:
            return {}
        recent = self._health_history[-window:]
        return {
            'avg_cpu': sum(h.cpu_usage for h in recent) / window,
            'avg_memory': sum(h.memory_usage for h in recent) / window,
            'avg_error_rate': sum(h.error_rate for h in recent) / window,
            'max_tasks': max(h.active_tasks for h in recent),
        }

    def is_healthy(self) -> bool:
        if not self._health_history:
            return True
        latest = self._health_history[-1]
        return latest.cpu_usage < 0.9 and latest.memory_usage < 0.9 and latest.error_rate < 0.2

    def get_status(self) -> Dict[str, Any]:
        return {
            'active': self._active,
            'healthy': self.is_healthy(),
            'alerts': len(self._alerts),
            'circuit_breakers': {name: cb.get_state() for name, cb in self._breakers.items()},
            'health_history': len(self._health_history),
        }


def _demo() -> None:
    print("=== Guardian Demo ===\n")

    guardian = Guardian()

    # Register circuit breaker
    cb = guardian.register_breaker('api_calls', failure_threshold=3, recovery_timeout=10)

    # Simulate failures
    for i in range(5):
        if not cb.can_execute():
            print(f"  Request {i+1}: CIRCUIT OPEN (state: {cb.get_state()})")
            continue

        if i < 3:  # First 3 succeed
            cb.record_success()
            print(f"  Request {i+1}: SUCCESS (state: {cb.get_state()})")
        else:  # Then fail
            cb.record_failure()
            print(f"  Request {i+1}: FAILURE (state: {cb.get_state()})")

    # Health check
    health = guardian.check_health(cpu=0.45, memory=0.6, disk=0.3, tasks=5, pending=2, errors=0.02)
    print(f"\nHealth: CPU={health.cpu_usage:.0%}, Memory={health.memory_usage:.0%}")
    print(f"Is healthy: {guardian.is_healthy()}")

    # Critical health
    health = guardian.check_health(cpu=0.95, memory=0.92, disk=0.8, tasks=20, pending=50, errors=0.15)
    print(f"Critical health: alerts={len(guardian._alerts)}")

    print(f"\nStatus: {guardian.get_status()}")

    print("\n=== Guardian Demo Complete ===")


if __name__ == '__main__':
    _demo()
