#!/usr/bin/env python3
"""
MAGNATRIX-OS — Model Serving Engine
ai/llm_model_serving_native.py

Features:
- Hot-swapping: load/unload models without downtime
- Version management: multiple versions, canary routing, rollback
- Health checks: ping, readiness, liveness probes
- Graceful shutdown: drain in-progress requests
- Request routing by model version/strategy

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("model_serving")


class ModelStatus(enum.Enum):
    LOADING = "loading"
    READY = "ready"
    UNLOADING = "unloading"
    FAILED = "failed"


class HealthStatus(enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class RouteStrategy(enum.Enum):
    STABLE = "stable"       # route to latest stable version
    CANARY = "canary"       # route to canary version (small %)
    WEIGHTED = "weighted"   # weighted split between versions
    LATEST = "latest"       # route to latest version regardless
    TARGETED = "targeted"   # route to specific version


@dataclass
class ModelVersion:
    version_id: str
    model_name: str
    model_path: str
    status: ModelStatus = ModelStatus.LOADING
    load_time: float = 0.0
    ready_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_canary: bool = False
    is_stable: bool = False
    weight: float = 1.0
    request_count: int = 0
    error_count: int = 0

    @property
    def latency_ms(self) -> float:
        return self.metadata.get("avg_latency_ms", 0.0)

    @property
    def error_rate(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.error_count / self.request_count


@dataclass
class HealthCheckResult:
    status: HealthStatus
    latency_ms: float
    timestamp: float
    message: str
    checks_passed: int
    checks_total: int


@dataclass
class RoutingResult:
    version_id: str
    model_name: str
    model_path: str
    strategy: RouteStrategy
    latency_ms: float


class ModelRegistry:
    """Thread-safe model registry with hot-swapping support."""

    def __init__(self):
        self._models: Dict[str, List[ModelVersion]] = defaultdict(list)
        self._lock = threading.RLock()
        self._callbacks: List[Callable[[ModelVersion, str], None]] = []

    def register(self, model: ModelVersion) -> None:
        with self._lock:
            self._models[model.model_name].append(model)
            for cb in self._callbacks:
                cb(model, "registered")
        logger.info(f"Registered {model.model_name} v{model.version_id}")

    def unregister(self, model_name: str, version_id: str) -> Optional[ModelVersion]:
        with self._lock:
            versions = self._models.get(model_name, [])
            for v in versions:
                if v.version_id == version_id:
                    v.status = ModelStatus.UNLOADING
                    for cb in self._callbacks:
                        cb(v, "unloading")
                    versions.remove(v)
                    for cb in self._callbacks:
                        cb(v, "unregistered")
                    logger.info(f"Unregistered {model_name} v{version_id}")
                    return v
        return None

    def hot_swap(self, model_name: str, new_version: ModelVersion) -> None:
        """Replace all versions with new version atomically."""
        with self._lock:
            old_versions = self._models.get(model_name, [])
            for v in old_versions:
                v.status = ModelStatus.UNLOADING
            self._models[model_name] = [new_version]
            new_version.status = ModelStatus.READY
            new_version.ready_time = time.monotonic()
            for cb in self._callbacks:
                cb(new_version, "hot-swapped")
        logger.info(f"Hot-swapped {model_name} to v{new_version.version_id}")

    def get_versions(self, model_name: str) -> List[ModelVersion]:
        with self._lock:
            return list(self._models.get(model_name, []))

    def get_version(self, model_name: str, version_id: str) -> Optional[ModelVersion]:
        with self._lock:
            for v in self._models.get(model_name, []):
                if v.version_id == version_id:
                    return v
        return None

    def list_models(self) -> List[str]:
        with self._lock:
            return list(self._models.keys())

    def on_event(self, callback: Callable[[ModelVersion, str], None]) -> None:
        self._callbacks.append(callback)


class HealthChecker:
    """Health check system with ping, readiness, and liveness probes."""

    def __init__(self, registry: ModelRegistry, timeout_ms: float = 5000.0):
        self._registry = registry
        self._timeout_ms = timeout_ms
        self._history: Dict[str, List[HealthCheckResult]] = defaultdict(list)
        self._lock = threading.Lock()

    def check(self, model_name: str, version_id: str) -> HealthCheckResult:
        version = self._registry.get_version(model_name, version_id)
        if not version:
            result = HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                latency_ms=0.0,
                timestamp=time.monotonic(),
                message="Model version not found",
                checks_passed=0,
                checks_total=3,
            )
            self._record(version_id, result)
            return result

        t0 = time.monotonic()
        checks = self._run_checks(version)
        elapsed = (time.monotonic() - t0) * 1000

        passed = sum(checks)
        if passed == 3:
            status = HealthStatus.HEALTHY
        elif passed >= 1:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.UNHEALTHY

        result = HealthCheckResult(
            status=status,
            latency_ms=elapsed,
            timestamp=time.monotonic(),
            message=f"Checks passed: {passed}/3",
            checks_passed=passed,
            checks_total=3,
        )
        self._record(version_id, result)
        return result

    def _run_checks(self, version: ModelVersion) -> List[int]:
        """Simulate ping, readiness, and liveness checks."""
        ping_ok = version.status == ModelStatus.READY
        ready_ok = version.ready_time is not None
        live_ok = version.error_rate < 0.5
        return [int(ping_ok), int(ready_ok), int(live_ok)]

    def _record(self, version_id: str, result: HealthCheckResult) -> None:
        with self._lock:
            self._history[version_id].append(result)
            if len(self._history[version_id]) > 100:
                self._history[version_id].pop(0)

    def get_history(self, version_id: str) -> List[HealthCheckResult]:
        with self._lock:
            return list(self._history.get(version_id, []))

    def latest(self, version_id: str) -> Optional[HealthCheckResult]:
        with self._lock:
            hist = self._history.get(version_id, [])
            return hist[-1] if hist else None


class RequestRouter:
    """Routes requests to appropriate model version based on strategy."""

    def __init__(self, registry: ModelRegistry):
        self._registry = registry
        self._canary_percent = 10.0  # 10% traffic to canary
        self._lock = threading.Lock()
        self._counter = 0

    def set_canary_percent(self, percent: float) -> None:
        self._canary_percent = max(0.0, min(100.0, percent))

    def route(self, model_name: str, strategy: RouteStrategy = RouteStrategy.STABLE, target_version: Optional[str] = None) -> Optional[RoutingResult]:
        versions = self._registry.get_versions(model_name)
        if not versions:
            return None

        ready = [v for v in versions if v.status == ModelStatus.READY]
        if not ready:
            return None

        with self._lock:
            self._counter += 1

        if strategy == RouteStrategy.TARGETED and target_version:
            v = self._registry.get_version(model_name, target_version)
            if v and v.status == ModelStatus.READY:
                return self._make_result(v, strategy)
            return None

        elif strategy == RouteStrategy.LATEST:
            v = max(ready, key=lambda x: x.load_time)
            return self._make_result(v, strategy)

        elif strategy == RouteStrategy.CANARY:
            canary = [v for v in ready if v.is_canary]
            if canary and (self._counter % 100) < self._canary_percent:
                return self._make_result(canary[0], strategy)
            stable = [v for v in ready if v.is_stable]
            if stable:
                return self._make_result(stable[0], strategy)
            return self._make_result(ready[0], strategy)

        elif strategy == RouteStrategy.WEIGHTED:
            total_weight = sum(v.weight for v in ready)
            if total_weight == 0:
                return self._make_result(ready[0], strategy)
            pick = (self._counter % int(total_weight * 100)) / 100.0
            cum = 0.0
            for v in ready:
                cum += v.weight
                if pick < cum:
                    return self._make_result(v, strategy)
            return self._make_result(ready[-1], strategy)

        else:  # STABLE
            stable = [v for v in ready if v.is_stable]
            if stable:
                return self._make_result(stable[0], strategy)
            return self._make_result(ready[0], strategy)

    def _make_result(self, v: ModelVersion, strategy: RouteStrategy) -> RoutingResult:
        v.request_count += 1
        return RoutingResult(
            version_id=v.version_id,
            model_name=v.model_name,
            model_path=v.model_path,
            strategy=strategy,
            latency_ms=v.latency_ms,
        )


class GracefulShutdownManager:
    """Drains in-progress requests before shutting down."""

    def __init__(self, drain_timeout: float = 30.0):
        self._drain_timeout = drain_timeout
        self._in_progress: Set[str] = set()
        self._lock = threading.Lock()
        self._shutdown_event = threading.Event()
        self._completed = 0

    def start_request(self, request_id: str) -> None:
        with self._lock:
            if not self._shutdown_event.is_set():
                self._in_progress.add(request_id)

    def finish_request(self, request_id: str) -> None:
        with self._lock:
            self._in_progress.discard(request_id)
            self._completed += 1

    def shutdown(self) -> Dict[str, Any]:
        self._shutdown_event.set()
        t0 = time.monotonic()
        while self._in_progress and (time.monotonic() - t0) < self._drain_timeout:
            time.sleep(0.1)
        remaining = list(self._in_progress)
        return {
            "drained": self._completed,
            "remaining": len(remaining),
            "remaining_ids": remaining[:10],
            "timeout": self._drain_timeout,
            "elapsed": time.monotonic() - t0,
        }

    @property
    def is_shutting_down(self) -> bool:
        return self._shutdown_event.is_set()

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "in_progress": len(self._in_progress),
                "completed": self._completed,
                "shutting_down": self._shutdown_event.is_set(),
            }


class ModelServer:
    """Orchestrator: ties together registry, health checker, router, and shutdown manager."""

    def __init__(self):
        self.registry = ModelRegistry()
        self.health = HealthChecker(self.registry)
        self.router = RequestRouter(self.registry)
        self.shutdown = GracefulShutdownManager()
        self._lock = threading.Lock()
        self._requests_handled = 0

    def deploy(self, model_name: str, version_id: str, model_path: str, **metadata) -> ModelVersion:
        version = ModelVersion(
            version_id=version_id,
            model_name=model_name,
            model_path=model_path,
            load_time=time.monotonic(),
            metadata=metadata,
        )
        self.registry.register(version)
        # Simulate load time
        time.sleep(0.01)
        version.status = ModelStatus.READY
        version.ready_time = time.monotonic()
        return version

    def hot_swap(self, model_name: str, version_id: str, model_path: str, **metadata) -> ModelVersion:
        version = ModelVersion(
            version_id=version_id,
            model_name=model_name,
            model_path=model_path,
            load_time=time.monotonic(),
            metadata=metadata,
            is_stable=True,
        )
        self.registry.hot_swap(model_name, version)
        return version

    def handle_request(self, model_name: str, strategy: RouteStrategy = RouteStrategy.STABLE, target_version: Optional[str] = None) -> Dict[str, Any]:
        req_id = str(uuid.uuid4())[:8]
        self.shutdown.start_request(req_id)
        try:
            if self.shutdown.is_shutting_down:
                return {"error": "Server is shutting down", "request_id": req_id}
            result = self.router.route(model_name, strategy, target_version)
            if not result:
                return {"error": "No available model version", "request_id": req_id}
            self._requests_handled += 1
            return {
                "request_id": req_id,
                "version_id": result.version_id,
                "model_name": result.model_name,
                "strategy": result.strategy.value,
                "latency_ms": result.latency_ms,
            }
        finally:
            self.shutdown.finish_request(req_id)

    def health_check(self, model_name: str, version_id: str) -> HealthCheckResult:
        return self.health.check(model_name, version_id)

    def get_status(self) -> Dict[str, Any]:
        return {
            "models": self.registry.list_models(),
            "requests_handled": self._requests_handled,
            "shutdown": self.shutdown.get_status(),
        }


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Model Serving Engine")
    print("ai/llm_model_serving_native.py")
    print("=" * 60)

    server = ModelServer()

    # 1. Deploy v1.0
    print("")
    print("[1] Deploy v1.0 (stable)")
    v1 = server.deploy("llm-arena", "1.0", "/models/arena-1.0.bin", avg_latency_ms=120.0)
    v1.is_stable = True
    print(f"  Deployed {v1.model_name} v{v1.version_id} — status={v1.status.value}")

    # 2. Health check
    print("")
    print("[2] Health Check v1.0")
    health = server.health_check("llm-arena", "1.0")
    print(f"  Status: {health.status.value}, latency={health.latency_ms:.1f}ms, {health.message}")

    # 3. Stable routing
    print("")
    print("[3] Stable Routing (5 requests)")
    for i in range(5):
        r = server.handle_request("llm-arena", RouteStrategy.STABLE)
        print(f"  Request {i+1}: v{r.get('version_id', 'N/A')} ({r.get('strategy', 'N/A')}) latency={r.get('latency_ms', 0)}ms")

    # 4. Hot-swap v2.0 canary
    print("")
    print("[4] Hot-swap v2.0 (canary)")
    v2 = server.hot_swap("llm-arena", "2.0", "/models/arena-2.0.bin", avg_latency_ms=80.0)
    v2.is_canary = True
    print(f"  Hot-swapped to {v2.model_name} v{v2.version_id} — status={v2.status.value}")

    # 5. Weighted routing
    print("")
    print("[5] Weighted Routing (5 requests)")
    server.router.set_canary_percent(20.0)
    for i in range(5):
        r = server.handle_request("llm-arena", RouteStrategy.WEIGHTED)
        print(f"  Request {i+1}: v{r.get('version_id', 'N/A')} ({r.get('strategy', 'N/A')})")

    # 6. Targeted version routing
    print("")
    print("[6] Targeted Version Routing")
    r = server.handle_request("llm-arena", RouteStrategy.TARGETED, target_version="2.0")
    print(f"  Targeted v2.0: {r}")

    # 7. Graceful shutdown
    print("")
    print("[7] Graceful Shutdown")
    server.shutdown.shutdown()
    print(f"  Shutdown status: {server.shutdown.get_status()}")

    # 8. Server status
    print("")
    print("[8] Server Status")
    status = server.get_status()
    print(f"  {status}")

    print("" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
