"""infrastructure/service_mesh_native.py — Service Mesh for MAGNATRIX-OS.

Pure-stdlib service mesh with discovery, registration, health checks,
load balancing, circuit breaker, retry, timeout, tracing, and metrics.

Rules: no third-party deps, type hints, docstrings, self-test in __main__.
"""
from __future__ import annotations

import json
import random
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol


class ServiceStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ServiceInstance:
    """A single running instance of a service."""
    service_name: str
    instance_id: str
    host: str
    port: int
    meta: Dict[str, Any] = field(default_factory=dict)
    status: ServiceStatus = ServiceStatus.HEALTHY
    last_check: float = 0.0
    fail_count: int = 0
    request_count: int = 0
    error_count: int = 0
    latency_ms: float = 0.0


class Transport(Protocol):
    """Protocol for request transport; mock or real HTTP client can implement."""

    def request(self, host: str, port: int, payload: bytes, timeout: float) -> bytes:
        ...


class ServiceMesh:
    """Lightweight service mesh for intra-cluster communication.

    Features:
        - In-memory service registry
        - Health check with failure threshold
        - Round-robin + random load balancing
        - Circuit breaker (fail threshold + recovery timeout)
        - Exponential backoff retry
        - Request timeout enforcement
        - Correlation-ID tracing
        - Latency/error metrics
    """

    def __init__(
        self,
        health_interval: float = 5.0,
        circuit_fail_threshold: int = 3,
        circuit_recovery: float = 10.0,
        default_timeout: float = 2.0,
        max_retries: int = 3,
    ) -> None:
        self._registry: Dict[str, List[ServiceInstance]] = defaultdict(list)
        self._round_robin_idx: Dict[str, int] = defaultdict(int)
        self._circuit_open_until: Dict[str, float] = {}
        self._health_interval = health_interval
        self._circuit_fail_threshold = circuit_fail_threshold
        self._circuit_recovery = circuit_recovery
        self._default_timeout = default_timeout
        self._max_retries = max_retries
        self._metrics: List[Dict[str, Any]] = []
        self._transport: Optional[Transport] = None

    # ---- Registration -----------------------------------------------

    def register(
        self,
        service_name: str,
        host: str,
        port: int,
        meta: Optional[Dict[str, Any]] = None,
    ) -> ServiceInstance:
        """Register a new service instance."""
        inst = ServiceInstance(
            service_name=service_name,
            instance_id=str(uuid.uuid4())[:8],
            host=host,
            port=port,
            meta=meta or {},
            last_check=time.time(),
        )
        self._registry[service_name].append(inst)
        return inst

    def deregister(self, service_name: str, instance_id: str) -> bool:
        """Remove an instance from the registry."""
        before = len(self._registry[service_name])
        self._registry[service_name] = [
            i for i in self._registry[service_name] if i.instance_id != instance_id
        ]
        return len(self._registry[service_name]) < before

    def list_services(self) -> Dict[str, List[ServiceInstance]]:
        return {k: list(v) for k, v in self._registry.items()}

    # ---- Health check -----------------------------------------------

    def health_check(
        self,
        service_name: str,
        checker: Callable[[ServiceInstance], bool],
    ) -> None:
        """Run a health check on all instances of a service."""
        now = time.time()
        for inst in self._registry.get(service_name, []):
            if now - inst.last_check < self._health_interval:
                continue
            healthy = checker(inst)
            inst.last_check = now
            if healthy:
                inst.fail_count = 0
                inst.status = ServiceStatus.HEALTHY
            else:
                inst.fail_count += 1
                inst.status = ServiceStatus.DEGRADED if inst.fail_count < self._circuit_fail_threshold else ServiceStatus.UNHEALTHY
                key = f"{inst.service_name}:{inst.instance_id}"
                if inst.fail_count >= self._circuit_fail_threshold:
                    self._circuit_open_until[key] = now + self._circuit_recovery

    # ---- Load balancing ---------------------------------------------

    def _pick_instance(self, service_name: str, strategy: str = "round_robin") -> Optional[ServiceInstance]:
        """Select an instance by strategy, skipping unhealthy / open-circuit."""
        candidates = self._registry.get(service_name, [])
        now = time.time()
        healthy = []
        for c in candidates:
            key = f"{c.service_name}:{c.instance_id}"
            if self._circuit_open_until.get(key, 0) > now:
                continue
            if c.status != ServiceStatus.UNHEALTHY:
                healthy.append(c)
        if not healthy:
            return None
        if strategy == "random":
            return random.choice(healthy)
        idx = self._round_robin_idx[service_name] % len(healthy)
        self._round_robin_idx[service_name] += 1
        return healthy[idx]

    # ---- Circuit breaker --------------------------------------------

    def _is_circuit_open(self, inst: ServiceInstance) -> bool:
        key = f"{inst.service_name}:{inst.instance_id}"
        return time.time() < self._circuit_open_until.get(key, 0.0)

    def _record_failure(self, inst: ServiceInstance) -> None:
        inst.error_count += 1
        inst.fail_count += 1
        key = f"{inst.service_name}:{inst.instance_id}"
        if inst.fail_count >= self._circuit_fail_threshold:
            self._circuit_open_until[key] = time.time() + self._circuit_recovery

    def _record_success(self, inst: ServiceInstance) -> None:
        inst.fail_count = 0

    # ---- Request with retry + timeout -------------------------------

    def call(
        self,
        service_name: str,
        payload: bytes = b"",
        timeout: Optional[float] = None,
        retries: Optional[int] = None,
        strategy: str = "round_robin",
        correlation_id: Optional[str] = None,
    ) -> bytes:
        """Send a request to a service instance with full mesh resilience."""
        cid = correlation_id or str(uuid.uuid4())[:12]
        timeout = timeout if timeout is not None else self._default_timeout
        retries = retries if retries is not None else self._max_retries
        last_err: Optional[Exception] = None

        for attempt in range(retries + 1):
            inst = self._pick_instance(service_name, strategy)
            if inst is None:
                raise ServiceMeshError(f"No healthy instance for '{service_name}'")

            start = time.perf_counter()
            try:
                if self._transport is None:
                    # Default mock transport for pure-stdlib mode
                    result = self._mock_transport(inst.host, inst.port, payload, timeout)
                else:
                    result = self._transport.request(inst.host, inst.port, payload, timeout)
                latency = (time.perf_counter() - start) * 1000
                inst.request_count += 1
                inst.latency_ms = latency
                self._record_success(inst)
                self._metrics.append({
                    "cid": cid,
                    "service": service_name,
                    "instance": inst.instance_id,
                    "latency_ms": round(latency, 2),
                    "status": "success",
                    "attempt": attempt,
                })
                return result
            except Exception as exc:
                latency = (time.perf_counter() - start) * 1000
                self._record_failure(inst)
                last_err = exc
                self._metrics.append({
                    "cid": cid,
                    "service": service_name,
                    "instance": inst.instance_id,
                    "latency_ms": round(latency, 2),
                    "status": "error",
                    "attempt": attempt,
                    "error": str(exc),
                })
                backoff = min(2 ** attempt, 8.0)
                time.sleep(backoff)

        raise ServiceMeshError(f"All retries exhausted for '{service_name}': {last_err}")

    def _mock_transport(self, host: str, port: int, payload: bytes, timeout: float) -> bytes:
        """Deterministic mock transport for self-testing."""
        # Simulate occasional failure for resilience testing
        if random.random() < 0.05:
            raise ServiceMeshError("mock transport failure")
        return json.dumps({"echo": payload.decode("utf-8", errors="replace"), "host": host, "port": port}).encode()

    # ---- Metrics & tracing ------------------------------------------

    def get_metrics(self) -> List[Dict[str, Any]]:
        return self._metrics[:]

    def get_correlation_path(self, cid: str) -> List[Dict[str, Any]]:
        return [m for m in self._metrics if m.get("cid") == cid]

    def set_transport(self, transport: Transport) -> None:
        self._transport = transport

    def summary(self) -> Dict[str, Any]:
        """Aggregate metrics by service."""
        agg: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"requests": 0, "errors": 0, "latency_sum": 0.0})
        for m in self._metrics:
            svc = m["service"]
            agg[svc]["requests"] += 1
            if m["status"] == "error":
                agg[svc]["errors"] += 1
            agg[svc]["latency_sum"] += m.get("latency_ms", 0)
        result = {}
        for svc, data in agg.items():
            total = data["requests"]
            result[svc] = {
                "requests": total,
                "errors": data["errors"],
                "error_rate": round(data["errors"] / total, 4) if total else 0,
                "avg_latency_ms": round(data["latency_sum"] / total, 2) if total else 0,
            }
        return result


class ServiceMeshError(Exception):
    pass


def run() -> None:
    """Self-test: register services, health check, call with retry, metrics."""
    mesh = ServiceMesh(circuit_fail_threshold=2, circuit_recovery=0.5)

    # Register 3 instances of 'orders' — reset last_check so health_check runs immediately
    for i in range(3):
        inst = mesh.register("orders", "127.0.0.1", 8000 + i)
        inst.last_check = 0.0  # force immediate health check

    # Health check — fail instance 2
    def checker(inst: ServiceInstance) -> bool:
        return inst.port != 8001

    mesh.health_check("orders", checker)
    statuses = [i.status.value for i in mesh.list_services()["orders"]]
    assert statuses == ["healthy", "degraded", "healthy"], f"Unexpected: {statuses}"

    # Second health check to push port 8001 over threshold
    for inst in mesh.list_services()["orders"]:
        inst.last_check = 0.0
    mesh.health_check("orders", checker)
    statuses2 = [i.status.value for i in mesh.list_services()["orders"]]
    assert statuses2 == ["healthy", "unhealthy", "healthy"], f"Unexpected: {statuses2}"

    # Make several calls — should avoid unhealthy instance
    random.seed(42)
    for _ in range(10):
        mesh.call("orders", payload=b"{\"action\":\"buy\"}")

    summary = mesh.summary()
    assert "orders" in summary
    assert summary["orders"]["requests"] >= 10

    # Test circuit breaker by forcing failure
    inst = mesh.register(" fragile", "127.0.0.1", 9000)
    mesh._record_failure(mesh._registry[" fragile"][0])
    mesh._record_failure(mesh._registry[" fragile"][0])
    mesh._record_failure(mesh._registry[" fragile"][0])
    assert mesh._is_circuit_open(mesh._registry[" fragile"][0])

    # Metrics path by CID
    cid = "test-cid-001"
    mesh.call("orders", payload=b"trace-me", correlation_id=cid)
    path = mesh.get_correlation_path(cid)
    assert len(path) >= 1
    assert path[0]["cid"] == cid

    print("service_mesh_native.py self-test passed.")
    print("  Summary:", json.dumps(summary, indent=2))


if __name__ == "__main__":
    run()
