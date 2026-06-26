#!/usr/bin/env python3
"""
Self-Healing Engine — MAGNATRIX-OS Auto-Recovery & Health Monitor
===================================================================
Monitor modules, detect failures (health check), auto-restart, retry
with backoff, fallback to degraded mode. No external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations

import threading
import time
import traceback
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    RECOVERING = "recovering"


@dataclass
class HealthReport:
    """Health status report for a module."""
    module_name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    response_time_ms: float = 0.0
    last_check: float = 0.0
    consecutive_failures: int = 0
    total_checks: int = 0
    total_failures: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryAction:
    """A recovery action taken by the self-healing engine."""
    module_name: str
    action: str
    timestamp: float = field(default_factory=time.time)
    success: bool = False
    error: Optional[str] = None


class HealthChecker:
    """
    Periodic health checker for modules.
    
    Supports ping-based, custom probe, and passive monitoring.
    """

    def __init__(self, check_interval_ms: float = 5000.0):
        self.check_interval_ms = check_interval_ms
        self._probes: Dict[str, Callable[[], bool]] = {}
        self._reports: Dict[str, HealthReport] = {}
        self._lock = threading.RLock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def register_probe(self, module_name: str, probe: Callable[[], bool]) -> None:
        """Register a health probe function for a module."""
        with self._lock:
            self._probes[module_name] = probe
            if module_name not in self._reports:
                self._reports[module_name] = HealthReport(module_name=module_name)

    def unregister_probe(self, module_name: str) -> None:
        """Remove a health probe."""
        with self._lock:
            self._probes.pop(module_name, None)
            self._reports.pop(module_name, None)

    def check_module(self, module_name: str) -> HealthReport:
        """Run a single health check on a module."""
        with self._lock:
            probe = self._probes.get(module_name)
            report = self._reports.get(module_name)
            if not report:
                report = HealthReport(module_name=module_name)
                self._reports[module_name] = report

        if not probe:
            report.status = HealthStatus.UNKNOWN
            report.last_check = time.time()
            return report

        start = time.time()
        try:
            success = probe()
            elapsed = (time.time() - start) * 1000
            report.response_time_ms = elapsed
            report.last_check = time.time()
            report.total_checks += 1

            if success:
                report.consecutive_failures = 0
                report.error_message = None
                if report.status in (HealthStatus.UNHEALTHY, HealthStatus.UNKNOWN):
                    report.status = HealthStatus.RECOVERING
                elif report.status == HealthStatus.RECOVERING:
                    report.status = HealthStatus.HEALTHY
                else:
                    report.status = HealthStatus.HEALTHY
            else:
                report.consecutive_failures += 1
                report.total_failures += 1
                if report.consecutive_failures >= 3:
                    report.status = HealthStatus.UNHEALTHY
                elif report.consecutive_failures >= 1:
                    report.status = HealthStatus.DEGRADED

        except Exception as e:
            report.response_time_ms = (time.time() - start) * 1000
            report.last_check = time.time()
            report.total_checks += 1
            report.total_failures += 1
            report.consecutive_failures += 1
            report.error_message = str(e)
            if report.consecutive_failures >= 3:
                report.status = HealthStatus.UNHEALTHY
            else:
                report.status = HealthStatus.DEGRADED

        return report

    def check_all(self) -> Dict[str, HealthReport]:
        """Run health checks on all registered modules."""
        with self._lock:
            names = list(self._probes.keys())
        return {name: self.check_module(name) for name in names}

    def start(self) -> None:
        """Start periodic health checking."""
        self._running = True
        self._thread = threading.Thread(target=self._check_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop periodic health checking."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _check_loop(self) -> None:
        while self._running:
            self.check_all()
            time.sleep(self.check_interval_ms / 1000.0)

    def get_report(self, module_name: str) -> Optional[HealthReport]:
        with self._lock:
            return self._reports.get(module_name)

    def get_all_reports(self) -> Dict[str, HealthReport]:
        with self._lock:
            return {k: v for k, v in self._reports.items()}


class RecoveryEngine:
    """
    Execute recovery actions for failed modules.
    
    Supports: restart, retry, fallback, circuit breaker.
    """

    def __init__(self, max_retries: int = 3, backoff_base_ms: float = 1000.0):
        self.max_retries = max_retries
        self.backoff_base_ms = backoff_base_ms
        self._actions: Dict[str, List[RecoveryAction]] = {}
        self._lock = threading.Lock()
        self._circuit_breakers: Dict[str, Dict[str, Any]] = {}  # module -> {failures, last_failure, open}
        self._circuit_threshold = 5
        self._circuit_timeout_ms = 30000.0

    def restart_module(self, module_name: str, restart_fn: Callable[[], bool]) -> RecoveryAction:
        """Attempt to restart a module."""
        action = RecoveryAction(module_name=module_name, action="restart")
        try:
            action.success = restart_fn()
        except Exception as e:
            action.error = str(e)
            action.success = False
        self._record_action(action)
        return action

    def retry_with_backoff(self, module_name: str, operation: Callable[[], Any]) -> Tuple[Any, RecoveryAction]:
        """Retry an operation with exponential backoff."""
        action = RecoveryAction(module_name=module_name, action="retry")
        result = None
        for attempt in range(self.max_retries + 1):
            try:
                result = operation()
                action.success = True
                break
            except Exception as e:
                if attempt < self.max_retries:
                    delay = self.backoff_base_ms * (2 ** attempt) / 1000.0
                    time.sleep(delay)
                else:
                    action.error = str(e)
                    action.success = False
        self._record_action(action)
        return result, action

    def fallback(self, module_name: str, fallback_fn: Callable[[], Any]) -> Tuple[Any, RecoveryAction]:
        """Execute a fallback operation."""
        action = RecoveryAction(module_name=module_name, action="fallback")
        try:
            result = fallback_fn()
            action.success = True
            self._record_action(action)
            return result, action
        except Exception as e:
            action.error = str(e)
            action.success = False
            self._record_action(action)
            return None, action

    def check_circuit_breaker(self, module_name: str) -> bool:
        """Check if circuit breaker is open for a module."""
        with self._lock:
            cb = self._circuit_breakers.get(module_name)
            if not cb:
                return True  # Circuit closed (healthy)
            if cb["open"]:
                elapsed = (time.time() - cb["last_failure"]) * 1000
                if elapsed > self._circuit_timeout_ms:
                    cb["open"] = False
                    cb["failures"] = 0
                    return True
                return False
            return True

    def record_failure(self, module_name: str) -> None:
        """Record a failure for circuit breaker tracking."""
        with self._lock:
            if module_name not in self._circuit_breakers:
                self._circuit_breakers[module_name] = {"failures": 0, "last_failure": 0, "open": False}
            cb = self._circuit_breakers[module_name]
            cb["failures"] += 1
            cb["last_failure"] = time.time()
            if cb["failures"] >= self._circuit_threshold:
                cb["open"] = True

    def record_success(self, module_name: str) -> None:
        """Record a success, resetting circuit breaker."""
        with self._lock:
            if module_name in self._circuit_breakers:
                self._circuit_breakers[module_name] = {"failures": 0, "last_failure": 0, "open": False}

    def _record_action(self, action: RecoveryAction) -> None:
        with self._lock:
            if action.module_name not in self._actions:
                self._actions[action.module_name] = []
            self._actions[action.module_name].append(action)

    def get_actions(self, module_name: Optional[str] = None) -> List[RecoveryAction]:
        with self._lock:
            if module_name:
                return list(self._actions.get(module_name, []))
            return [a for actions in self._actions.values() for a in actions]

    def reset_circuit_breaker(self, module_name: str) -> None:
        with self._lock:
            self._circuit_breakers[module_name] = {"failures": 0, "last_failure": 0, "open": False}


class SelfHealingEngine:
    """
    Top-level self-healing engine for MAGNATRIX-OS.
    
    Monitors all modules, detects failures, and auto-recovers.
    """

    CAPABILITIES = ["self_healing", "monitoring", "recovery", "health_check"]

    def __init__(self, repo_root: str = "."):
        self.repo_root = repo_root
        self._health_checker = HealthChecker(check_interval_ms=5000.0)
        self._recovery = RecoveryEngine(max_retries=3, backoff_base_ms=1000.0)
        self._monitored_modules: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._running = False
        self._healing_thread: Optional[threading.Thread] = None
        self._stats = {"checks": 0, "recoveries": 0, "failures": 0, "circuit_breaks": 0}

    def monitor_module(self, name: str, instance: Any,
                       check_fn: Optional[Callable[[], bool]] = None) -> None:
        """Register a module for monitoring."""
        with self._lock:
            self._monitored_modules[name] = instance

        def default_probe() -> bool:
            try:
                # Check if module has a health method
                if hasattr(instance, "health") and callable(instance.health):
                    return instance.health()
                # Check if module is not None and has expected attributes
                return instance is not None
            except Exception:
                return False

        probe = check_fn or default_probe
        self._health_checker.register_probe(name, probe)

    def unmonitor_module(self, name: str) -> None:
        """Stop monitoring a module."""
        with self._lock:
            self._monitored_modules.pop(name, None)
        self._health_checker.unregister_probe(name)

    def start(self) -> None:
        """Start self-healing monitoring."""
        self._running = True
        self._health_checker.start()
        self._healing_thread = threading.Thread(target=self._healing_loop, daemon=True)
        self._healing_thread.start()

    def stop(self) -> None:
        """Stop self-healing monitoring."""
        self._running = False
        self._health_checker.stop()
        if self._healing_thread and self._healing_thread.is_alive():
            self._healing_thread.join(timeout=2.0)

    def _healing_loop(self) -> None:
        """Main healing loop: check health and recover."""
        while self._running:
            time.sleep(5.0)
            if not self._running:
                break

            reports = self._health_checker.get_all_reports()
            for name, report in reports.items():
                if report.status == HealthStatus.UNHEALTHY:
                    self._attempt_recovery(name, report)
                elif report.status == HealthStatus.DEGRADED:
                    # Check if circuit breaker is open
                    if not self._recovery.check_circuit_breaker(name):
                        with self._lock:
                            self._stats["circuit_breaks"] += 1

    def _attempt_recovery(self, name: str, report: HealthReport) -> None:
        """Attempt to recover an unhealthy module."""
        with self._lock:
            instance = self._monitored_modules.get(name)
            self._stats["checks"] += 1

        if not instance:
            return

        # Check circuit breaker
        if not self._recovery.check_circuit_breaker(name):
            return

        # Try restart if module has stop/start
        restart_success = False
        if hasattr(instance, "stop") and hasattr(instance, "start"):
            def restart():
                try:
                    instance.stop()
                    time.sleep(0.5)
                    instance.start()
                    return True
                except Exception:
                    return False
            action = self._recovery.restart_module(name, restart)
            restart_success = action.success

        if restart_success:
            self._recovery.record_success(name)
            with self._lock:
                self._stats["recoveries"] += 1
        else:
            self._recovery.record_failure(name)
            with self._lock:
                self._stats["failures"] += 1

    def get_health_report(self, module_name: Optional[str] = None) -> Union[HealthReport, Dict[str, HealthReport]]:
        if module_name:
            return self._health_checker.get_report(module_name) or HealthReport(module_name=module_name)
        return self._health_checker.get_all_reports()

    def get_recovery_actions(self, module_name: Optional[str] = None) -> List[RecoveryAction]:
        return self._recovery.get_actions(module_name)

    def reset_circuit_breaker(self, module_name: str) -> None:
        self._recovery.reset_circuit_breaker(module_name)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._stats)

    def handle_message(self, message: Dict[str, Any]) -> Any:
        action = message.get("action", "")
        if action == "health":
            return {k: {"status": v.status.value, "failures": v.consecutive_failures}
                    for k, v in self.get_health_report().items()}
        elif action == "recoveries":
            return [{"module": a.module_name, "action": a.action, "success": a.success}
                    for a in self.get_recovery_actions()]
        elif action == "stats":
            return self.get_stats()
        elif action == "reset_circuit":
            self.reset_circuit_breaker(message.get("module", ""))
            return {"ok": True}
        return None

    def on_event(self, event) -> None:
        pass
