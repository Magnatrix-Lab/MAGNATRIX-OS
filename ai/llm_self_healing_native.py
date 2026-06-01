"""Self-Healing Engine — Failure detection, auto-restart, circuit breaker, health monitoring.

Modul ini menyediakan:
- HealthMonitor: continuous health checks with configurable probes
- CircuitBreaker: prevent cascade failures, auto-recovery
- AutoRestart: restart failed components with backoff
- FailureTracker: log and analyze failure patterns
- SelfHealingOrchestrator: coordinate all healing mechanisms
"""

from __future__ import annotations

import json
import time
import uuid
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from enum import Enum, auto


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CircuitState(Enum):
    CLOSED = auto()      # Normal operation
    OPEN = auto()        # Failing, reject requests
    HALF_OPEN = auto()   # Testing recovery


@dataclass
class HealthProbe:
    """Single health check probe."""
    probe_id: str
    name: str
    component: str
    check_fn: Optional[Callable[[], bool]] = None
    interval: float = 30.0
    timeout: float = 5.0
    last_run: float = 0.0
    consecutive_failures: int = 0
    consecutive_successes: int = 0


@dataclass
class HealthRecord:
    """Health check result."""
    probe_id: str
    timestamp: float
    healthy: bool
    latency: float
    message: str = ""


@dataclass
class FailureEvent:
    """Recorded failure event."""
    event_id: str
    component: str
    error_type: str
    error_message: str
    timestamp: float
    auto_resolved: bool = False
    resolution_time: Optional[float] = None


class HealthMonitor:
    """Continuous health monitoring with configurable probes."""

    def __init__(self):
        self._probes: Dict[str, HealthProbe] = {}
        self._records: List[HealthRecord] = []
        self._status: Dict[str, HealthStatus] = {}
        self._threshold: int = 3  # failures before degraded
        self._critical: int = 5   # failures before unhealthy

    def register(self, probe: HealthProbe) -> None:
        self._probes[probe.probe_id] = probe
        self._status[probe.component] = HealthStatus.UNKNOWN

    def check(self, probe_id: str) -> HealthRecord:
        probe = self._probes.get(probe_id)
        if not probe:
            return HealthRecord(probe_id, time.time(), False, 0.0, "Unknown probe")
        start = time.time()
        e = None
        try:
            if probe.check_fn:
                healthy = probe.check_fn()
            else:
                healthy = True
        except Exception as exc:
            e = exc
            healthy = False
        latency = time.time() - start
        record = HealthRecord(probe_id, time.time(), healthy, latency, "" if healthy else str(e))
        self._records.append(record)
        probe.last_run = time.time()
        if healthy:
            probe.consecutive_successes += 1
            probe.consecutive_failures = 0
        else:
            probe.consecutive_failures += 1
            probe.consecutive_successes = 0
        self._update_status(probe, healthy)
        return record

    def check_all(self) -> Dict[str, HealthRecord]:
        return {pid: self.check(pid) for pid in self._probes}

    def _update_status(self, probe: HealthProbe, healthy: bool) -> None:
        if healthy and probe.consecutive_successes >= 2:
            self._status[probe.component] = HealthStatus.HEALTHY
        elif not healthy and probe.consecutive_failures >= self._critical:
            self._status[probe.component] = HealthStatus.UNHEALTHY
        elif not healthy and probe.consecutive_failures >= self._threshold:
            self._status[probe.component] = HealthStatus.DEGRADED

    def get_status(self, component: Optional[str] = None) -> Dict[str, HealthStatus]:
        if component:
            return {component: self._status.get(component, HealthStatus.UNKNOWN)}
        return dict(self._status)

    def get_overall(self) -> HealthStatus:
        statuses = list(self._status.values())
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        if any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        if all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        return HealthStatus.UNKNOWN


class CircuitBreaker:
    """Prevent cascade failures by rejecting requests when component is failing."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0,
                 half_open_max: int = 3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max = half_open_max
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._successes = 0
        self._last_failure_time = 0.0
        self._total_requests = 0
        self._rejected_requests = 0

    def call(self, fn: Callable[[], Any]) -> Tuple[Any, bool]:
        """Execute fn if allowed. Returns (result, was_allowed)."""
        self._total_requests += 1
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._successes = 0
            else:
                self._rejected_requests += 1
                return None, False
        if self._state == CircuitState.HALF_OPEN and self._successes >= self.half_open_max:
            self._state = CircuitState.CLOSED
            self._failures = 0

        try:
            result = fn()
            self._on_success()
            return result, True
        except Exception:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._successes += 1
        else:
            self._failures = max(0, self._failures - 1)

    def _on_failure(self) -> None:
        self._failures += 1
        self._last_failure_time = time.time()
        if self._failures >= self.failure_threshold:
            self._state = CircuitState.OPEN

    def get_state(self) -> CircuitState:
        return self._state

    def get_stats(self) -> Dict[str, Any]:
        return {
            "state": self._state.name,
            "failures": self._failures,
            "total_requests": self._total_requests,
            "rejected_requests": self._rejected_requests,
            "rejection_rate": round(self._rejected_requests / max(self._total_requests, 1), 4)
        }


class AutoRestart:
    """Restart failed components with exponential backoff."""

    def __init__(self, max_retries: int = 5, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self._restart_count: Dict[str, int] = {}
        self._last_restart: Dict[str, float] = {}

    def restart(self, component_id: str, restart_fn: Callable[[], bool]) -> Tuple[bool, float]:
        """Attempt restart with backoff. Returns (success, delay)."""
        count = self._restart_count.get(component_id, 0)
        if count >= self.max_retries:
            return False, 0.0
        delay = min(self.base_delay * (2 ** count), self.max_delay)
        time.sleep(delay)
        try:
            success = restart_fn()
        except Exception:
            success = False
        if success:
            self._restart_count[component_id] = 0
        else:
            self._restart_count[component_id] = count + 1
        self._last_restart[component_id] = time.time()
        return success, delay

    def can_restart(self, component_id: str) -> bool:
        return self._restart_count.get(component_id, 0) < self.max_retries

    def get_stats(self, component_id: str) -> Dict[str, Any]:
        return {
            "restart_count": self._restart_count.get(component_id, 0),
            "last_restart": self._last_restart.get(component_id, 0),
            "can_restart": self.can_restart(component_id)
        }


class FailureTracker:
    """Log and analyze failure patterns."""

    def __init__(self, max_events: int = 10000):
        self.max_events = max_events
        self._events: List[FailureEvent] = []

    def record(self, component: str, error_type: str, error_message: str,
               auto_resolved: bool = False) -> FailureEvent:
        event = FailureEvent(
            event_id=str(uuid.uuid4())[:12],
            component=component,
            error_type=error_type,
            error_message=error_message,
            timestamp=time.time(),
            auto_resolved=auto_resolved
        )
        self._events.append(event)
        if len(self._events) > self.max_events:
            self._events = self._events[-self.max_events:]
        return event

    def resolve(self, event_id: str) -> bool:
        for e in self._events:
            if e.event_id == event_id:
                e.auto_resolved = True
                e.resolution_time = time.time()
                return True
        return False

    def get_failures(self, component: Optional[str] = None, limit: int = 100) -> List[FailureEvent]:
        events = self._events
        if component:
            events = [e for e in events if e.component == component]
        return events[-limit:]

    def get_top_errors(self, n: int = 5) -> List[Tuple[str, int]]:
        counts: Dict[str, int] = {}
        for e in self._events:
            counts[e.error_type] = counts.get(e.error_type, 0) + 1
        return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:n]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._events)
        auto_resolved = sum(1 for e in self._events if e.auto_resolved)
        return {
            "total_events": total,
            "auto_resolved": auto_resolved,
            "unresolved": total - auto_resolved,
            "top_errors": self.get_top_errors(5)
        }


class SelfHealingOrchestrator:
    """Coordinate health monitoring, circuit breaking, and auto-restart."""

    def __init__(self):
        self.health = HealthMonitor()
        self.breakers: Dict[str, CircuitBreaker] = {}
        self.restart = AutoRestart()
        self.tracker = FailureTracker()
        self._components: Dict[str, Dict[str, Any]] = {}
        self._running = False

    def register_component(self, component_id: str, check_fn: Optional[Callable[[], bool]] = None,
                           restart_fn: Optional[Callable[[], bool]] = None,
                           probe_interval: float = 30.0) -> None:
        self._components[component_id] = {
            "check_fn": check_fn,
            "restart_fn": restart_fn,
            "probe_interval": probe_interval
        }
        probe = HealthProbe(
            probe_id=f"probe-{component_id}",
            name=f"{component_id} health",
            component=component_id,
            check_fn=check_fn,
            interval=probe_interval
        )
        self.health.register(probe)
        self.breakers[component_id] = CircuitBreaker()

    def tick(self) -> Dict[str, Any]:
        """Run one healing cycle."""
        actions = []
        for cid, cfg in self._components.items():
            probe_id = f"probe-{cid}"
            record = self.check(probe_id)
            if not record.healthy:
                actions.extend(self._handle_failure(cid, cfg))
            else:
                breaker = self.breakers.get(cid)
                if breaker and breaker.get_state() == CircuitState.HALF_OPEN:
                    actions.append({"action": "circuit_recovered", "component": cid})
        return {"timestamp": time.time(), "actions": actions}

    def check(self, probe_id: str) -> HealthRecord:
        record = self.health.check(probe_id)
        if not record.healthy:
            self.tracker.record(
                record.probe_id.replace("probe-", ""),
                "health_check_failed",
                record.message
            )
        return record

    def _handle_failure(self, component_id: str, cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
        actions = []
        # 1. Circuit breaker open?
        breaker = self.breakers.get(component_id)
        if breaker and breaker.get_state() == CircuitState.OPEN:
            actions.append({"action": "circuit_open", "component": component_id})
            return actions

        # 2. Try restart
        restart_fn = cfg.get("restart_fn")
        if restart_fn and self.restart.can_restart(component_id):
            success, delay = self.restart.restart(component_id, restart_fn)
            if success:
                actions.append({"action": "auto_restarted", "component": component_id, "delay": delay})
                self.tracker.record(component_id, "auto_restart_success", "", auto_resolved=True)
            else:
                actions.append({"action": "restart_failed", "component": component_id, "delay": delay})
                self.tracker.record(component_id, "auto_restart_failed", "")
                # 3. Open circuit breaker
                if breaker:
                    try:
                        breaker.call(lambda: (_ for _ in ()).throw(Exception("forced")))
                    except Exception:
                        pass
        return actions

    def get_health(self) -> Dict[str, Any]:
        return {
            "overall": self.health.get_overall().value,
            "components": {k: v.value for k, v in self.health.get_status().items()},
            "circuits": {k: v.get_state().name for k, v in self.breakers.items()},
            "restarts": {k: self.restart.get_stats(k) for k in self._components},
            "failures": self.tracker.get_stats()
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.get_health(), f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("SELF-HEALING ENGINE DEMO")
    print("=" * 70)

    # 1. Health Monitor
    print("\n[1] Health Monitor")
    hm = HealthMonitor()
    hm.register(HealthProbe("probe-api", "API Health", "api", check_fn=lambda: True, interval=10))
    hm.register(HealthProbe("probe-db", "DB Health", "db", check_fn=lambda: False, interval=10))
    results = hm.check_all()
    for pid, rec in results.items():
        print(f"  {pid}: {'HEALTHY' if rec.healthy else 'UNHEALTHY'} ({rec.latency:.4f}s)")
    print(f"  Overall: {hm.get_overall().value}")
    print(f"  Status map: {hm.get_status()}")

    # 2. Circuit Breaker
    print("\n[2] Circuit Breaker")
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=2.0)
    for i in range(5):
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        except RuntimeError:
            pass
    print(f"  State after 5 failures: {cb.get_state().name}")
    print(f"  Stats: {cb.get_stats()}")
    # Wait for recovery
    time.sleep(2.5)
    try:
        cb.call(lambda: "success")
        print(f"  After timeout: {cb.get_state().name}")
    except Exception:
        pass

    # 3. Auto Restart
    print("\n[3] Auto Restart with Backoff")
    ar = AutoRestart(max_retries=3, base_delay=0.1)
    for attempt in range(4):
        success, delay = ar.restart("svc-1", lambda: attempt == 2)  # succeed on 3rd attempt
        print(f"  Attempt {attempt+1}: success={success}, delay={delay:.2f}s")
    print(f"  Stats: {ar.get_stats('svc-1')}")

    # 4. Failure Tracker
    print("\n[4] Failure Tracker")
    ft = FailureTracker()
    for i in range(10):
        ft.record("api", "TimeoutError", f"Request {i} timed out")
    ft.record("db", "ConnectionError", "DB connection refused")
    ft.record("api", "TimeoutError", "Auto-resolved", auto_resolved=True)
    print(f"  Stats: {ft.get_stats()}")
    print(f"  Top errors: {ft.get_top_errors(3)}")

    # 5. Full Orchestrator
    print("\n[5] Full Orchestrator")
    orchestrator = SelfHealingOrchestrator()
    fail_count = [0]
    def flaky_check():
        fail_count[0] += 1
        return fail_count[0] > 2
    def restart_fn():
        fail_count[0] = 0
        return True
    orchestrator.register_component("flaky-service", check_fn=flaky_check, restart_fn=restart_fn, probe_interval=1.0)
    for i in range(6):
        result = orchestrator.tick()
        if result["actions"]:
            print(f"  Cycle {i}: {result['actions']}")
        time.sleep(0.1)
    print(f"  Health: {orchestrator.get_health()}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
