#!/usr/bin/env python3
"""
Auto Recovery for MAGNATRIX-OS
Dead agent detection, automatic restart, failover, and
pending prompt unblocking. Monitors health and recovers
from failures transparently. Native stdlib only.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import time
import threading
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class HealthState(enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DEAD = "dead"
    RECOVERING = "recovering"


@dataclasses.dataclass
class AgentHealth:
    agent_id: str
    state: HealthState
    last_seen: float
    consecutive_failures: int
    total_restarts: int
    total_failures: int
    avg_response_time_ms: float
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "state": self.state.value,
            "last_seen": self.last_seen,
            "consecutive_failures": self.consecutive_failures,
            "total_restarts": self.total_restarts,
            "total_failures": self.total_failures,
            "avg_response_ms": self.avg_response_time_ms,
        }


@dataclasses.dataclass
class RecoveryAction:
    agent_id: str
    action: str
    timestamp: float
    success: bool
    message: str


class AutoRecovery:
    """Monitors agents, detects failures, and auto-recovers."""

    def __init__(
        self,
        check_interval: float = 5.0,
        max_failures: int = 3,
        restart_cooldown: float = 10.0,
        max_restarts: int = 5,
    ) -> None:
        self.check_interval = check_interval
        self.max_failures = max_failures
        self.restart_cooldown = restart_cooldown
        self.max_restarts = max_restarts
        self._health: Dict[str, AgentHealth] = {}
        self._agents: Dict[str, Any] = {}
        self._health_checks: Dict[str, Callable[[], bool]] = {}
        self._restart_fn: Dict[str, Callable[[], bool]] = {}
        self._failover_fn: Dict[str, Callable[[str], bool]] = {}
        self._pending: Dict[str, List[Dict[str, Any]]] = {}  # agent_id -> pending requests
        self._recovery_log: List[RecoveryAction] = []
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        agent_id: str,
        health_check: Callable[[], bool],
        restart_fn: Callable[[], bool],
        failover_fn: Optional[Callable[[str], bool]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._health_checks[agent_id] = health_check
        self._restart_fn[agent_id] = restart_fn
        if failover_fn:
            self._failover_fn[agent_id] = failover_fn
        self._health[agent_id] = AgentHealth(
            agent_id=agent_id,
            state=HealthState.HEALTHY,
            last_seen=time.time(),
            consecutive_failures=0,
            total_restarts=0,
            total_failures=0,
            avg_response_time_ms=0.0,
            metadata=metadata or {},
        )
        self._pending[agent_id] = []

    # ------------------------------------------------------------------
    # Monitoring
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop(self) -> None:
        self._running = False

    def _monitor_loop(self) -> None:
        while self._running:
            for agent_id in list(self._health.keys()):
                self._check_agent(agent_id)
            time.sleep(self.check_interval)

    def _check_agent(self, agent_id: str) -> None:
        health = self._health[agent_id]
        check_fn = self._health_checks.get(agent_id)
        if not check_fn:
            return
        try:
            start = time.time()
            healthy = check_fn()
            elapsed = (time.time() - start) * 1000
            if healthy:
                health.last_seen = time.time()
                health.consecutive_failures = 0
                health.state = HealthState.HEALTHY
                health.avg_response_time_ms = (health.avg_response_time_ms * 0.8) + (elapsed * 0.2)
            else:
                health.consecutive_failures += 1
                health.total_failures += 1
                if health.consecutive_failures >= self.max_failures:
                    health.state = HealthState.DEAD
                    self._recover(agent_id)
                else:
                    health.state = HealthState.DEGRADED
        except Exception as e:
            health.consecutive_failures += 1
            health.total_failures += 1
            if health.consecutive_failures >= self.max_failures:
                health.state = HealthState.DEAD
                self._recover(agent_id)
            else:
                health.state = HealthState.UNHEALTHY

    # ------------------------------------------------------------------
    # Recovery
    # ------------------------------------------------------------------

    def _recover(self, agent_id: str) -> None:
        health = self._health[agent_id]
        if health.total_restarts >= self.max_restarts:
            self._log_action(agent_id, "max_restarts_exceeded", False, f"Max {self.max_restarts} restarts reached")
            health.state = HealthState.DEAD
            # Try failover
            self._failover(agent_id)
            return
        health.state = HealthState.RECOVERING
        restart_fn = self._restart_fn.get(agent_id)
        if not restart_fn:
            self._failover(agent_id)
            return
        try:
            success = restart_fn()
            health.total_restarts += 1
            if success:
                health.consecutive_failures = 0
                health.last_seen = time.time()
                health.state = HealthState.HEALTHY
                self._log_action(agent_id, "restart", True, "Agent restarted successfully")
                # Unblock pending requests
                self._unblock_pending(agent_id)
            else:
                health.state = HealthState.DEAD
                self._log_action(agent_id, "restart", False, "Restart failed")
                self._failover(agent_id)
        except Exception as e:
            health.state = HealthState.DEAD
            self._log_action(agent_id, "restart", False, str(e))
            self._failover(agent_id)

    def _failover(self, agent_id: str) -> None:
        failover_fn = self._failover_fn.get(agent_id)
        if failover_fn:
            try:
                success = failover_fn(agent_id)
                self._log_action(agent_id, "failover", success, "Failover attempted")
                if success:
                    self._unblock_pending(agent_id)
            except Exception as e:
                self._log_action(agent_id, "failover", False, str(e))
        else:
            self._log_action(agent_id, "failover", False, "No failover handler")
            # Clear pending as failed
            for req in self._pending.get(agent_id, []):
                req["status"] = "failed"
                req["error"] = "Agent dead, no failover available"

    def _unblock_pending(self, agent_id: str) -> None:
        for req in self._pending.get(agent_id, []):
            req["status"] = "unblocked"
            req["unblocked_at"] = time.time()
        self._pending[agent_id] = []

    def _log_action(self, agent_id: str, action: str, success: bool, message: str) -> None:
        self._recovery_log.append(RecoveryAction(
            agent_id=agent_id,
            action=action,
            timestamp=time.time(),
            success=success,
            message=message,
        ))

    # ------------------------------------------------------------------
    # Pending request management
    # ------------------------------------------------------------------

    def add_pending(self, agent_id: str, request: Dict[str, Any]) -> None:
        with self._lock:
            self._pending.setdefault(agent_id, []).append(request)

    def get_pending(self, agent_id: str) -> List[Dict[str, Any]]:
        return self._pending.get(agent_id, [])

    def clear_pending(self, agent_id: str) -> None:
        self._pending[agent_id] = []

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_health(self, agent_id: str) -> Optional[AgentHealth]:
        return self._health.get(agent_id)

    def all_health(self) -> Dict[str, Dict[str, Any]]:
        return {k: v.to_dict() for k, v in self._health.items()}

    def get_recovery_log(self, limit: int = 100) -> List[RecoveryAction]:
        return self._recovery_log[-limit:]

    def stats(self) -> Dict[str, Any]:
        by_state = {}
        for h in self._health.values():
            by_state[h.state.value] = by_state.get(h.state.value, 0) + 1
        total_restarts = sum(h.total_restarts for h in self._health.values())
        total_failures = sum(h.total_failures for h in self._health.values())
        return {
            "agents": len(self._health),
            "by_state": by_state,
            "total_restarts": total_restarts,
            "total_failures": total_failures,
            "recovery_actions": len(self._recovery_log),
            "check_interval": self.check_interval,
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    recovery = AutoRecovery(check_interval=2.0, max_failures=2)
    print("=== Auto Recovery Demo ===\n")
    # Simulate an agent that fails then recovers
    fail_count = 0
    def health_check():
        nonlocal fail_count
        fail_count += 1
        return fail_count > 3  # Fail first 3 checks, then recover
    def restart_fn():
        print("  Restarting agent...")
        return True
    def failover_fn(aid):
        print(f"  Failover for {aid}")
        return True

    recovery.register("agent1", health_check, restart_fn, failover_fn, {"name": "Test Agent"})
    recovery.start()
    time.sleep(5.0)
    recovery.stop()
    print(f"\nHealth: {recovery.all_health()}")
    print(f"Recovery log ({len(recovery.get_recovery_log())} actions):")
    for action in recovery.get_recovery_log():
        print(f"  [{action.timestamp:.0f}] {action.agent_id}: {action.action} -> {'OK' if action.success else 'FAIL'} ({action.message})")
    print(f"\nStats: {recovery.stats()}")


if __name__ == "__main__":
    _demo()
