"""
llm_service_mesh_native.py
MAGNATRIX-OS Service Mesh Engine
Native Python, stdlib only.
Provides service discovery, inter-service routing, load balancing, health-based routing,
and circuit-integrated proxy for the MAGNATRIX-OS ecosystem.
"""

from __future__ import annotations

import json
import random
import threading
import time
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple


class ServiceStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"


class LoadBalanceStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_LOADED = "least_loaded"
    WEIGHTED = "weighted"


@dataclass
class ServiceInstance:
    id: str
    name: str
    host: str
    port: int
    weight: float = 1.0
    status: ServiceStatus = ServiceStatus.HEALTHY
    load: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_heartbeat: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "host": self.host, "port": self.port,
            "weight": self.weight, "status": self.status.value, "load": self.load,
            "metadata": self.metadata, "last_heartbeat": self.last_heartbeat,
            "tags": self.tags,
        }

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"


@dataclass
class RouteRule:
    service_name: str
    path_prefix: str
    target_tags: List[str]
    priority: int = 0
    fallback_service: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_name": self.service_name, "path_prefix": self.path_prefix,
            "target_tags": self.target_tags, "priority": self.priority,
            "fallback_service": self.fallback_service,
        }


class ServiceMeshEngine:
    """
    Service mesh with discovery, routing, and health-aware load balancing.
    """

    def __init__(self, heartbeat_timeout: float = 30.0) -> None:
        self.heartbeat_timeout = heartbeat_timeout
        self._services: Dict[str, List[ServiceInstance]] = {}  # name -> instances
        self._routes: List[RouteRule] = []
        self._lock = threading.Lock()
        self._round_robin: Dict[str, int] = {}  # name -> index
        self._handlers: Dict[str, Callable] = {}
        self._callbacks: List[Callable[[ServiceInstance, ServiceStatus], None]] = []

    def register(self, instance: ServiceInstance) -> None:
        with self._lock:
            if instance.name not in self._services:
                self._services[instance.name] = []
                self._round_robin[instance.name] = 0
            # Remove old instance with same id
            self._services[instance.name] = [i for i in self._services[instance.name] if i.id != instance.id]
            self._services[instance.name].append(instance)

    def deregister(self, service_name: str, instance_id: str) -> bool:
        with self._lock:
            if service_name not in self._services:
                return False
            self._services[service_name] = [i for i in self._services[service_name] if i.id != instance_id]
            return True

    def heartbeat(self, service_name: str, instance_id: str) -> bool:
        with self._lock:
            for inst in self._services.get(service_name, []):
                if inst.id == instance_id:
                    inst.last_heartbeat = time.time()
                    if inst.status == ServiceStatus.OFFLINE:
                        inst.status = ServiceStatus.HEALTHY
                    return True
            return False

    def check_health(self, service_name: str, instance_id: str, status: ServiceStatus) -> None:
        with self._lock:
            for inst in self._services.get(service_name, []):
                if inst.id == instance_id:
                    old = inst.status
                    inst.status = status
                    if old != status:
                        for cb in self._callbacks:
                            try:
                                cb(inst, status)
                            except Exception:
                                pass
                    return

    def get_instances(self, service_name: str, healthy_only: bool = True) -> List[ServiceInstance]:
        with self._lock:
            instances = list(self._services.get(service_name, []))
        if healthy_only:
            cutoff = time.time() - self.heartbeat_timeout
            instances = [i for i in instances if i.status in (ServiceStatus.HEALTHY, ServiceStatus.DEGRADED)
                         and i.last_heartbeat >= cutoff]
        return instances

    def select(self, service_name: str, strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
               tag: Optional[str] = None) -> Optional[ServiceInstance]:
        instances = self.get_instances(service_name)
        if tag:
            instances = [i for i in instances if tag in i.tags]
        if not instances:
            return None

        with self._lock:
            if strategy == LoadBalanceStrategy.ROUND_ROBIN:
                idx = self._round_robin.get(service_name, 0) % len(instances)
                self._round_robin[service_name] = idx + 1
                return instances[idx]
            elif strategy == LoadBalanceStrategy.RANDOM:
                return random.choice(instances)
            elif strategy == LoadBalanceStrategy.LEAST_LOADED:
                return min(instances, key=lambda i: i.load)
            elif strategy == LoadBalanceStrategy.WEIGHTED:
                total_weight = sum(i.weight for i in instances)
                pick = random.uniform(0, total_weight)
                cumulative = 0.0
                for i in instances:
                    cumulative += i.weight
                    if pick <= cumulative:
                        return i
                return instances[-1]
        return None

    def add_route(self, rule: RouteRule) -> None:
        self._routes.append(rule)
        self._routes.sort(key=lambda r: r.priority, reverse=True)

    def route(self, path: str) -> Optional[RouteRule]:
        for rule in self._routes:
            if path.startswith(rule.path_prefix):
                return rule
        return None

    def proxy(self, service_name: str, request_fn: Callable[[ServiceInstance], Any],
              strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
              fallback_fn: Optional[Callable] = None) -> Any:
        instance = self.select(service_name, strategy)
        if not instance:
            if fallback_fn:
                return fallback_fn()
            raise ServiceUnavailable(f"No healthy instances for {service_name}")
        try:
            result = request_fn(instance)
            instance.load += 1
            return result
        except Exception as e:
            self.check_health(service_name, instance.id, ServiceStatus.DEGRADED)
            raise

    def get_services(self) -> List[str]:
        return list(self._services.keys())

    def get_all_instances(self) -> List[ServiceInstance]:
        with self._lock:
            all_inst = []
            for instances in self._services.values():
                all_inst.extend(instances)
            return all_inst

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = sum(len(v) for v in self._services.values())
            healthy = sum(1 for v in self._services.values() for i in v if i.status == ServiceStatus.HEALTHY)
            return {
                "services": len(self._services),
                "total_instances": total,
                "healthy": healthy,
                "degraded": sum(1 for v in self._services.values() for i in v if i.status == ServiceStatus.DEGRADED),
                "unhealthy": sum(1 for v in self._services.values() for i in v if i.status == ServiceStatus.UNHEALTHY),
                "routes": len(self._routes),
            }

    def on_status_change(self, callback: Callable[[ServiceInstance, ServiceStatus], None]) -> None:
        self._callbacks.append(callback)


class ServiceUnavailable(Exception):
    pass


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Service Mesh Engine")
    print("=" * 60)

    mesh = ServiceMeshEngine(heartbeat_timeout=60.0)

    # Register services
    for i in range(3):
        mesh.register(ServiceInstance(
            id=f"llm-{i}", name="llm_inference", host="10.0.0.1", port=8000 + i,
            weight=1.0, tags=["gpu"], metadata={"model": "gpt-4o"}
        ))
    for i in range(2):
        mesh.register(ServiceInstance(
            id=f"embed-{i}", name="embedding", host="10.0.0.2", port=9000 + i,
            weight=1.5, tags=["cpu"], metadata={"dims": 1536}
        ))

    print("\n--- Stats ---")
    print(mesh.stats())

    print("\n--- Round Robin Selection ---")
    for i in range(5):
        inst = mesh.select("llm_inference", LoadBalanceStrategy.ROUND_ROBIN)
        print(f"  Pick {i+1}: {inst.id} @ {inst.address}")

    print("\n--- Weighted Selection ---")
    counts: Dict[str, int] = {}
    for _ in range(100):
        inst = mesh.select("embedding", LoadBalanceStrategy.WEIGHTED)
        counts[inst.id] = counts.get(inst.id, 0) + 1
    print(f"  Distribution: {counts}")

    print("\n--- Routing ---")
    mesh.add_route(RouteRule("llm_inference", "/generate", ["gpu"], priority=10))
    mesh.add_route(RouteRule("embedding", "/embed", ["cpu"], priority=5))
    for path in ["/generate", "/embed", "/unknown"]:
        rule = mesh.route(path)
        print(f"  {path} -> {rule.service_name if rule else 'no route'}")

    print("\n--- Health Check ---")
    mesh.check_health("llm_inference", "llm-1", ServiceStatus.DEGRADED)
    healthy = mesh.get_instances("llm_inference", healthy_only=True)
    print(f"  Healthy instances after degrade: {len(healthy)}")

    print("\nService Mesh test complete.")


if __name__ == "__main__":
    run()
