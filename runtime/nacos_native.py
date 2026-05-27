#!/usr/bin/env python3
"""
nacos_native_part1.py — Part 1: Service Registry & Discovery
Nacos native reimplementation (alibaba/nacos). Pure Python, no external deps.
Section: Service Registry, Naming Service, Heartbeat, Health Checks.
"""

from __future__ import annotations

import json
import math
import random
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1A — Core Data Structures
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ServiceInstance:
    """A single instance of a registered service."""
    ip: str
    port: int
    weight: float = 1.0
    healthy: bool = True
    enabled: bool = True
    ephemeral: bool = True
    metadata: Dict[str, str] = field(default_factory=dict)
    service_name: str = ""
    group: str = "DEFAULT_GROUP"
    namespace_id: str = "public"
    instance_id: str = ""
    last_heartbeat: float = 0.0
    cluster_name: str = "DEFAULT"

    def __post_init__(self) -> None:
        if not self.instance_id:
            self.instance_id = f"{self.ip}:{self.port}#{self.cluster_name}"
        if self.last_heartbeat == 0.0:
            self.last_heartbeat = time.time()

    def __repr__(self) -> str:
        status = "healthy" if self.healthy else "unhealthy"
        return f"<ServiceInstance {self.instance_id} {status} weight={self.weight}>"

    def is_expired(self, timeout_ms: int = 5000) -> bool:
        """Check if instance heartbeat has expired."""
        return (time.time() - self.last_heartbeat) * 1000 > timeout_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ip": self.ip, "port": self.port, "weight": self.weight,
            "healthy": self.healthy, "enabled": self.enabled,
            "ephemeral": self.ephemeral, "metadata": self.metadata,
            "serviceName": self.service_name, "group": self.group,
            "namespaceId": self.namespace_id, "instanceId": self.instance_id,
            "lastHeartbeat": self.last_heartbeat, "clusterName": self.cluster_name,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ServiceInstance":
        return cls(
            ip=d["ip"], port=d["port"], weight=d.get("weight", 1.0),
            healthy=d.get("healthy", True), enabled=d.get("enabled", True),
            ephemeral=d.get("ephemeral", True), metadata=d.get("metadata", {}),
            service_name=d.get("serviceName", ""), group=d.get("group", "DEFAULT_GROUP"),
            namespace_id=d.get("namespaceId", "public"),
            instance_id=d.get("instanceId", ""),
            last_heartbeat=d.get("lastHeartbeat", 0.0),
            cluster_name=d.get("clusterName", "DEFAULT"),
        )


@dataclass
class HealthCheckConfig:
    """Configuration for service health checks."""
    check_type: str = "tcp"  # tcp, http, mysql, redis
    interval_ms: int = 5000
    timeout_ms: int = 3000
    unhealthy_threshold: int = 2
    healthy_threshold: int = 1
    http_path: str = "/health"
    http_method: str = "GET"
    expected_status: int = 200

    def __repr__(self) -> str:
        return f"<HealthCheckConfig {self.check_type} interval={self.interval_ms}ms>"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkType": self.check_type, "intervalMs": self.interval_ms,
            "timeoutMs": self.timeout_ms, "unhealthyThreshold": self.unhealthy_threshold,
            "healthyThreshold": self.healthy_threshold, "httpPath": self.http_path,
            "httpMethod": self.http_method, "expectedStatus": self.expected_status,
        }


@dataclass
class ServiceDefinition:
    """Definition of a service with its instances."""
    service_name: str
    group: str = "DEFAULT_GROUP"
    namespace_id: str = "public"
    protect_threshold: float = 0.0  # protect ratio of healthy/total
    metadata: Dict[str, str] = field(default_factory=dict)
    health_check: Optional[HealthCheckConfig] = None
    instances: List[ServiceInstance] = field(default_factory=list)
    clusters: Dict[str, List[ServiceInstance]] = field(default_factory=dict)

    def __repr__(self) -> str:
        healthy = sum(1 for i in self.instances if i.healthy and i.enabled)
        return f"<ServiceDefinition {self.service_name} instances={len(self.instances)} healthy={healthy}>"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "serviceName": self.service_name, "group": self.group,
            "namespaceId": self.namespace_id, "protectThreshold": self.protect_threshold,
            "metadata": self.metadata,
            "healthCheck": self.health_check.to_dict() if self.health_check else None,
            "instances": [i.to_dict() for i in self.instances],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ServiceDefinition":
        insts = [ServiceInstance.from_dict(i) for i in d.get("instances", [])]
        hc = d.get("healthCheck")
        return cls(
            service_name=d["serviceName"], group=d.get("group", "DEFAULT_GROUP"),
            namespace_id=d.get("namespaceId", "public"),
            protect_threshold=d.get("protectThreshold", 0.0),
            metadata=d.get("metadata", {}),
            health_check=HealthCheckConfig(**hc) if hc else None,
            instances=insts,
        )

    def get_healthy_instances(self) -> List[ServiceInstance]:
        return [i for i in self.instances if i.healthy and i.enabled]

    def get_enabled_instances(self) -> List[ServiceInstance]:
        return [i for i in self.instances if i.enabled]

    def get_instances_by_cluster(self, cluster: str) -> List[ServiceInstance]:
        return [i for i in self.instances if i.cluster_name == cluster]


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1B — Health Checker
# ═══════════════════════════════════════════════════════════════════════════════


class HealthChecker(ABC):
    """Abstract health checker for service instances."""

    @abstractmethod
    def check(self, instance: ServiceInstance) -> bool:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


class DefaultHealthChecker(HealthChecker):
    """Default health checker based on heartbeat timeout."""

    def __init__(self, timeout_ms: int = 5000) -> None:
        self.timeout_ms = timeout_ms

    def check(self, instance: ServiceInstance) -> bool:
        return not instance.is_expired(self.timeout_ms)


class TCPHealthChecker(HealthChecker):
    """Simulated TCP health check."""

    def __init__(self, timeout_ms: int = 3000) -> None:
        self.timeout_ms = timeout_ms

    def check(self, instance: ServiceInstance) -> bool:
        return instance.port > 0 and instance.port < 65536


class HTTPHealthChecker(HealthChecker):
    """Simulated HTTP health check."""

    def __init__(self, path: str = "/health", expected_status: int = 200) -> None:
        self.path = path
        self.expected_status = expected_status

    def check(self, instance: ServiceInstance) -> bool:
        return True  # stub


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1C — Service Registry
# ═══════════════════════════════════════════════════════════════════════════════


class ServiceRegistry:
    """In-memory service registry with JSON persistence."""

    def __init__(self, data_dir: str = "./nacos_registry") -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._services: Dict[str, ServiceDefinition] = {}
        self._lock = threading.RLock()
        self._load_snapshot()

    def __repr__(self) -> str:
        return f"<ServiceRegistry services={len(self._services)} dir={self.data_dir}>"

    def _key(self, service_name: str, group: str = "DEFAULT_GROUP",
             namespace: str = "public") -> str:
        return f"{namespace}@@{group}@@{service_name}"

    def _load_snapshot(self) -> None:
        snapshot = self.data_dir / "services.json"
        if snapshot.exists():
            with open(snapshot, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.items():
                    self._services[k] = ServiceDefinition.from_dict(v)

    def _save_snapshot(self) -> None:
        snapshot = self.data_dir / "services.json"
        data = {k: v.to_dict() for k, v in self._services.items()}
        with open(snapshot, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def register(self, instance: ServiceInstance) -> bool:
        """Register a service instance."""
        with self._lock:
            key = self._key(instance.service_name, instance.group, instance.namespace_id)
            if key not in self._services:
                self._services[key] = ServiceDefinition(
                    service_name=instance.service_name,
                    group=instance.group,
                    namespace_id=instance.namespace_id,
                )
            svc = self._services[key]
            existing = {i.instance_id for i in svc.instances}
            if instance.instance_id in existing:
                self.update_instance(instance)
                return True
            svc.instances.append(instance)
            self._save_snapshot()
            return True

    def deregister(self, instance: ServiceInstance) -> bool:
        """Deregister a service instance."""
        with self._lock:
            key = self._key(instance.service_name, instance.group, instance.namespace_id)
            if key not in self._services:
                return False
            svc = self._services[key]
            svc.instances = [i for i in svc.instances if i.instance_id != instance.instance_id]
            if not svc.instances:
                del self._services[key]
            self._save_snapshot()
            return True

    def update_instance(self, instance: ServiceInstance) -> bool:
        """Update an existing instance (e.g., heartbeat refresh)."""
        with self._lock:
            key = self._key(instance.service_name, instance.group, instance.namespace_id)
            if key not in self._services:
                return False
            svc = self._services[key]
            for idx, inst in enumerate(svc.instances):
                if inst.instance_id == instance.instance_id:
                    svc.instances[idx] = instance
                    self._save_snapshot()
                    return True
            return False

    def get_service(self, service_name: str, group: str = "DEFAULT_GROUP",
                    namespace: str = "public") -> Optional[ServiceDefinition]:
        key = self._key(service_name, group, namespace)
        return self._services.get(key)

    def list_services(self, namespace: str = "public") -> List[str]:
        return [
            k.split("@@")[-1]
            for k in self._services
            if k.startswith(f"{namespace}@@")
        ]

    def list_all(self) -> List[ServiceDefinition]:
        return list(self._services.values())

    def set_health_check(self, service_name: str, config: HealthCheckConfig,
                         group: str = "DEFAULT_GROUP", namespace: str = "public") -> bool:
        with self._lock:
            key = self._key(service_name, group, namespace)
            if key not in self._services:
                self._services[key] = ServiceDefinition(service_name, group, namespace)
            self._services[key].health_check = config
            self._save_snapshot()
            return True

    def mark_unhealthy(self, instance: ServiceInstance) -> None:
        instance.healthy = False
        self.update_instance(instance)

    def mark_healthy(self, instance: ServiceInstance) -> None:
        instance.healthy = True
        instance.last_heartbeat = time.time()
        self.update_instance(instance)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1D — Naming Service
# ═══════════════════════════════════════════════════════════════════════════════


class NamingService:
    """Service discovery: lookup, subscribe, DNS-style resolution."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._listeners: Dict[str, List[Callable[[ServiceDefinition], None]]] = {}
        self._subscriptions: Dict[str, Set[str]] = {}
        self._lock = threading.RLock()

    def __repr__(self) -> str:
        return f"<NamingService listeners={sum(len(v) for v in self._listeners.values())}>"

    def discover(self, service_name: str, group: str = "DEFAULT_GROUP",
                 namespace: str = "public", healthy_only: bool = True,
                 cluster: Optional[str] = None) -> List[ServiceInstance]:
        """Discover instances of a service."""
        svc = self.registry.get_service(service_name, group, namespace)
        if not svc:
            return []
        instances = svc.get_healthy_instances() if healthy_only else svc.get_enabled_instances()
        if cluster:
            instances = [i for i in instances if i.cluster_name == cluster]
        return instances

    def select_one(self, service_name: str, group: str = "DEFAULT_GROUP",
                   namespace: str = "public", healthy_only: bool = True) -> Optional[ServiceInstance]:
        """Select a single instance (random for now, load balancer in Part 3)."""
        instances = self.discover(service_name, group, namespace, healthy_only)
        if not instances:
            return None
        return random.choice(instances)

    def subscribe(self, service_name: str, callback: Callable[[ServiceDefinition], None],
                  group: str = "DEFAULT_GROUP", namespace: str = "public") -> None:
        """Subscribe to service changes."""
        key = f"{namespace}@@{group}@@{service_name}"
        with self._lock:
            if key not in self._listeners:
                self._listeners[key] = []
                self._subscriptions.setdefault(service_name, set()).add(key)
            self._listeners[key].append(callback)

    def unsubscribe(self, service_name: str, callback: Callable[[ServiceDefinition], None],
                    group: str = "DEFAULT_GROUP", namespace: str = "public") -> None:
        key = f"{namespace}@@{group}@@{service_name}"
        with self._lock:
            if key in self._listeners:
                self._listeners[key] = [c for c in self._listeners[key] if c != callback]

    def notify(self, service_name: str, group: str = "DEFAULT_GROUP",
               namespace: str = "public") -> None:
        """Notify all subscribers of a service change."""
        key = f"{namespace}@@{group}@@{service_name}"
        svc = self.registry.get_service(service_name, group, namespace)
        with self._lock:
            if key in self._listeners and svc:
                for callback in self._listeners[key]:
                    try:
                        callback(svc)
                    except Exception:
                        pass

    def dns_resolve(self, service_name: str, group: str = "DEFAULT_GROUP",
                    namespace: str = "public") -> List[Tuple[str, int]]:
        """DNS-style resolution: return list of (ip, port) tuples."""
        instances = self.discover(service_name, group, namespace)
        return [(i.ip, i.port) for i in instances]

    def get_service_names(self, namespace: str = "public") -> List[str]:
        return self.registry.list_services(namespace)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1E — Heartbeat Manager
# ═══════════════════════════════════════════════════════════════════════════════


class HeartbeatManager:
    """Periodic heartbeat sender and timeout detector."""

    def __init__(self, registry: ServiceRegistry, check_interval_ms: int = 5000,
                 timeout_ms: int = 15000) -> None:
        self.registry = registry
        self.check_interval_ms = check_interval_ms
        self.timeout_ms = timeout_ms
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._checker = DefaultHealthChecker(timeout_ms)

    def __repr__(self) -> str:
        status = "running" if self._running else "stopped"
        return f"<HeartbeatManager {status} interval={self.check_interval_ms}ms>"

    def send_beat(self, instance: ServiceInstance) -> None:
        """Client sends a heartbeat to refresh instance."""
        instance.last_heartbeat = time.time()
        instance.healthy = True
        self.registry.update_instance(instance)

    def _check_loop(self) -> None:
        while self._running:
            self._check_all()
            time.sleep(self.check_interval_ms / 1000.0)

    def _check_all(self) -> None:
        for svc in self.registry.list_all():
            for inst in svc.instances:
                if inst.ephemeral and not self._checker.check(inst):
                    inst.healthy = False
                    self.registry.update_instance(inst)

    def start(self) -> None:
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._check_loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def check_instance(self, instance: ServiceInstance) -> bool:
        return self._checker.check(instance)


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO — Part 1
# ═══════════════════════════════════════════════════════════════════════════════


def demo_part1() -> None:
    print("=" * 60)
    print("NACOS PART 1 — Service Registry & Discovery Demo")
    print("=" * 60)

    registry = ServiceRegistry(data_dir="./nacos_demo_registry")
    naming = NamingService(registry)
    heartbeat = HeartbeatManager(registry, check_interval_ms=2000, timeout_ms=5000)

    print("\n[1] Register services:")
    inst1 = ServiceInstance(ip="192.168.1.10", port=8080, weight=1.0,
                          service_name="order-service", group="DEFAULT_GROUP",
                          metadata={"version": "v1.0", "region": "us-east"})
    inst2 = ServiceInstance(ip="192.168.1.11", port=8080, weight=2.0,
                            service_name="order-service", group="DEFAULT_GROUP",
                            metadata={"version": "v1.0", "region": "us-west"})
    inst3 = ServiceInstance(ip="192.168.1.20", port=9090, weight=1.0,
                            service_name="payment-service", group="DEFAULT_GROUP",
                            metadata={"version": "v2.0"})

    registry.register(inst1)
    registry.register(inst2)
    registry.register(inst3)
    print(f"  Registered: {inst1}")
    print(f"  Registered: {inst2}")
    print(f"  Registered: {inst3}")

    print("\n[2] Discover order-service:")
    instances = naming.discover("order-service")
    for i in instances:
        print(f"  {i}")

    print("\n[3] DNS resolve order-service:")
    endpoints = naming.dns_resolve("order-service")
    for ep in endpoints:
        print(f"  {ep[0]}:{ep[1]}")

    print("\n[4] Subscribe to order-service:")
    def on_change(svc: ServiceDefinition) -> None:
        print(f"  [NOTIFY] Service {svc.service_name} changed: {len(svc.instances)} instances")

    naming.subscribe("order-service", on_change)
    naming.notify("order-service")

    print("\n[5] Heartbeat simulation:")
    heartbeat.start()
    print(f"  {heartbeat}")
    heartbeat.send_beat(inst1)
    print(f"  Heartbeat sent for {inst1.instance_id}")
    time.sleep(1)
    heartbeat.stop()
    print("  Heartbeat manager stopped")

    print("\n[6] Health check timeout simulation:")
    inst1.last_heartbeat = time.time() - 20  # 20 seconds ago
    registry.update_instance(inst1)
    checker = DefaultHealthChecker(timeout_ms=5000)
    is_healthy = checker.check(inst1)
    print(f"  Instance {inst1.instance_id} healthy: {is_healthy}")

    print("\n[7] Registry snapshot:")
    all_services = registry.list_all()
    for svc in all_services:
        print(f"  {svc}")
        for inst in svc.instances:
            print(f"    - {inst}")

    print("\n[8] Deregister instance:")
    registry.deregister(inst2)
    naming.notify("order-service")
    print(f"  Deregistered {inst2.instance_id}")

    print("\n[9] Final state:")
    for svc in registry.list_all():
        print(f"  {svc}")

    print("\n" + "=" * 60)
    print("Part 1 Demo Complete")
    print("=" * 60)


if __name__ == "__main__":
    demo_part1()

#!/usr/bin/env python3
"""
nacos_native_part2.py — Part 2: Config Center
Nacos native reimplementation (alibaba/nacos). Pure Python, no external deps.
Section: Config Store, Config Listener, Gray Release, Config History, Namespace isolation.
"""

import json
import hashlib
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2A — Config Data Structures
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ConfigData:
    """A single configuration item."""
    data_id: str
    group: str = "DEFAULT_GROUP"
    content: str = ""
    md5: str = ""
    version: int = 0
    encrypted: bool = False
    namespace_id: str = "public"
    metadata: Dict[str, str] = field(default_factory=dict)
    create_time: float = 0.0
    modified_time: float = 0.0
    content_type: str = "text"

    def __post_init__(self) -> None:
        if not self.md5:
            self.md5 = self._compute_md5()
        if self.create_time == 0.0:
            self.create_time = time.time()
        if self.modified_time == 0.0:
            self.modified_time = self.create_time

    def __repr__(self) -> str:
        return f"<ConfigData {self.data_id} v={self.version} md5={self.md5[:8]}>"

    def _compute_md5(self) -> str:
        return hashlib.md5(self.content.encode("utf-8")).hexdigest()

    def update_content(self, new_content: str) -> None:
        self.content = new_content
        self.md5 = self._compute_md5()
        self.version += 1
        self.modified_time = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataId": self.data_id, "group": self.group,
            "content": self.content, "md5": self.md5,
            "version": self.version, "encrypted": self.encrypted,
            "namespaceId": self.namespace_id, "metadata": self.metadata,
            "createTime": self.create_time, "modifiedTime": self.modified_time,
            "contentType": self.content_type,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ConfigData":
        return cls(
            data_id=d["dataId"], group=d.get("group", "DEFAULT_GROUP"),
            content=d.get("content", ""), md5=d.get("md5", ""),
            version=d.get("version", 0), encrypted=d.get("encrypted", False),
            namespace_id=d.get("namespaceId", "public"),
            metadata=d.get("metadata", {}),
            create_time=d.get("createTime", 0.0),
            modified_time=d.get("modifiedTime", 0.0),
            content_type=d.get("contentType", "text"),
        )


@dataclass
class GrayRule:
    """Rule for gray release of a configuration."""
    rule_id: str
    rule_type: str = "ip"  # ip, label, weight
    condition: str = ""  # e.g., "192.168.1.*" or "region=canary"
    percentage: float = 0.0  # 0-100 for weight-based
    enabled: bool = True

    def __repr__(self) -> str:
        return f"<GrayRule {self.rule_type}={self.condition} pct={self.percentage}%>"

    def matches(self, client_info: Dict[str, str]) -> bool:
        """Check if client matches this gray rule."""
        if not self.enabled:
            return False
        if self.rule_type == "ip":
            client_ip = client_info.get("ip", "")
            pattern = self.condition.replace("*", "")
            return client_ip.startswith(pattern)
        elif self.rule_type == "label":
            key, val = self.condition.split("=") if "=" in self.condition else ("", "")
            return client_info.get(key) == val
        elif self.rule_type == "weight":
            client_hash = hash(client_info.get("client_id", "")) % 100
            return client_hash < self.percentage
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ruleId": self.rule_id, "ruleType": self.rule_type,
            "condition": self.condition, "percentage": self.percentage,
            "enabled": self.enabled,
        }


@dataclass
class ConfigSnapshot:
    """Historical snapshot of a config at a specific version."""
    config: ConfigData
    version: int
    timestamp: float
    operator: str = ""
    operation: str = "modify"  # create, modify, delete

    def __repr__(self) -> str:
        return f"<ConfigSnapshot {self.config.data_id} v={self.version} {self.operation}>"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": self.config.to_dict(), "version": self.version,
            "timestamp": self.timestamp, "operator": self.operator,
            "operation": self.operation,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2B — Config Store
# ═══════════════════════════════════════════════════════════════════════════════


class ConfigStore:
    """In-memory config store with JSON persistence."""

    def __init__(self, data_dir: str = "./nacos_config") -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._configs: Dict[str, ConfigData] = {}
        self._lock = threading.RLock()
        self._load_snapshot()

    def __repr__(self) -> str:
        return f"<ConfigStore configs={len(self._configs)} dir={self.data_dir}>"

    def _key(self, data_id: str, group: str = "DEFAULT_GROUP",
             namespace: str = "public") -> str:
        return f"{namespace}@@{group}@@{data_id}"

    def _load_snapshot(self) -> None:
        snapshot = self.data_dir / "configs.json"
        if snapshot.exists():
            with open(snapshot, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.items():
                    self._configs[k] = ConfigData.from_dict(v)

    def _save_snapshot(self) -> None:
        snapshot = self.data_dir / "configs.json"
        data = {k: v.to_dict() for k, v in self._configs.items()}
        with open(snapshot, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def publish(self, config: ConfigData) -> bool:
        """Publish or update a configuration."""
        with self._lock:
            key = self._key(config.data_id, config.group, config.namespace_id)
            if key in self._configs:
                existing = self._configs[key]
                if existing.md5 != config.md5:
                    existing.content = config.content
                    existing.md5 = config.md5
                    existing.version += 1
                    existing.modified_time = time.time()
                    existing.metadata.update(config.metadata)
            else:
                self._configs[key] = config
            self._save_snapshot()
            return True

    def get(self, data_id: str, group: str = "DEFAULT_GROUP",
            namespace: str = "public") -> Optional[ConfigData]:
        key = self._key(data_id, group, namespace)
        return self._configs.get(key)

    def delete(self, data_id: str, group: str = "DEFAULT_GROUP",
               namespace: str = "public") -> bool:
        with self._lock:
            key = self._key(data_id, group, namespace)
            if key in self._configs:
                del self._configs[key]
                self._save_snapshot()
                return True
            return False

    def list_by_namespace(self, namespace: str = "public") -> List[ConfigData]:
        return [c for k, c in self._configs.items() if k.startswith(f"{namespace}@@")]

    def list_all(self) -> List[ConfigData]:
        return list(self._configs.values())

    def search(self, data_id_pattern: str) -> List[ConfigData]:
        return [c for c in self._configs.values() if data_id_pattern in c.data_id]


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2C — Config Listener / Push
# ═══════════════════════════════════════════════════════════════════════════════


class ConfigListener:
    """Listener for configuration changes — push model simulation."""

    def __init__(self, data_id: str, group: str = "DEFAULT_GROUP",
                 namespace: str = "public",
                 callback: Optional[Callable[[ConfigData], None]] = None) -> None:
        self.data_id = data_id
        self.group = group
        self.namespace = namespace
        self.callback = callback
        self.last_md5: Optional[str] = None
        self.listening: bool = False

    def __repr__(self) -> str:
        status = "listening" if self.listening else "stopped"
        return f"<ConfigListener {self.data_id} {status}>"

    def start(self) -> None:
        self.listening = True

    def stop(self) -> None:
        self.listening = False

    def on_change(self, config: ConfigData) -> None:
        if self.callback and self.listening and config.md5 != self.last_md5:
            self.last_md5 = config.md5
            try:
                self.callback(config)
            except Exception:
                pass


class ConfigPushService:
    """Push config changes to registered listeners."""

    def __init__(self, store: ConfigStore) -> None:
        self.store = store
        self._listeners: Dict[str, List[ConfigListener]] = {}
        self._lock = threading.RLock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def __repr__(self) -> str:
        total = sum(len(v) for v in self._listeners.values())
        return f"<ConfigPushService listeners={total}>"

    def add_listener(self, listener: ConfigListener) -> None:
        key = f"{listener.namespace}@@{listener.group}@@{listener.data_id}"
        with self._lock:
            self._listeners.setdefault(key, []).append(listener)
            listener.start()

    def remove_listener(self, listener: ConfigListener) -> None:
        key = f"{listener.namespace}@@{listener.group}@@{listener.data_id}"
        with self._lock:
            if key in self._listeners:
                self._listeners[key] = [l for l in self._listeners[key] if l != listener]

    def _poll_loop(self, interval_ms: int = 1000) -> None:
        while self._running:
            self._check_changes()
            time.sleep(interval_ms / 1000.0)

    def _check_changes(self) -> None:
        for key, listeners in list(self._listeners.items()):
            parts = key.split("@@")
            if len(parts) != 3:
                continue
            namespace, group, data_id = parts
            config = self.store.get(data_id, group, namespace)
            if config:
                for listener in listeners:
                    listener.on_change(config)

    def start(self, interval_ms: int = 1000) -> None:
        if not self._running:
            self._running = True
            self._thread = threading.Thread(
                target=self._poll_loop, args=(interval_ms,), daemon=True
            )
            self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def notify(self, data_id: str, group: str = "DEFAULT_GROUP",
               namespace: str = "public") -> None:
        """Immediate notify for a specific config."""
        key = f"{namespace}@@{group}@@{data_id}"
        config = self.store.get(data_id, group, namespace)
        if not config:
            return
        with self._lock:
            for listener in self._listeners.get(key, []):
                listener.on_change(config)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2D — Gray Release Manager
# ═══════════════════════════════════════════════════════════════════════════════


class GrayReleaseManager:
    """Manages gray releases for configurations."""

    def __init__(self, store: ConfigStore) -> None:
        self.store = store
        self._rules: Dict[str, List[GrayRule]] = {}
        self._gray_configs: Dict[str, ConfigData] = {}
        self._lock = threading.RLock()

    def __repr__(self) -> str:
        return f"<GrayReleaseManager rules={sum(len(v) for v in self._rules.values())}>"

    def _key(self, data_id: str, group: str, namespace: str) -> str:
        return f"{namespace}@@{group}@@{data_id}"

    def add_rule(self, data_id: str, rule: GrayRule, group: str = "DEFAULT_GROUP",
                 namespace: str = "public") -> None:
        key = self._key(data_id, group, namespace)
        with self._lock:
            self._rules.setdefault(key, []).append(rule)

    def remove_rule(self, data_id: str, rule_id: str,
                    group: str = "DEFAULT_GROUP", namespace: str = "public") -> bool:
        key = self._key(data_id, group, namespace)
        with self._lock:
            if key in self._rules:
                before = len(self._rules[key])
                self._rules[key] = [r for r in self._rules[key] if r.rule_id != rule_id]
                return len(self._rules[key]) < before
            return False

    def set_gray_config(self, data_id: str, gray_config: ConfigData,
                        group: str = "DEFAULT_GROUP", namespace: str = "public") -> None:
        key = self._key(data_id, group, namespace)
        with self._lock:
            self._gray_configs[key] = gray_config

    def get_config(self, data_id: str, group: str = "DEFAULT_GROUP",
                   namespace: str = "public",
                   client_info: Optional[Dict[str, str]] = None) -> Optional[ConfigData]:
        """Get config, considering gray rules for this client."""
        key = self._key(data_id, group, namespace)
        base_config = self.store.get(data_id, group, namespace)
        gray_config = self._gray_configs.get(key)
        if not gray_config or not client_info:
            return base_config
        # Check gray rules
        rules = self._rules.get(key, [])
        for rule in rules:
            if rule.matches(client_info):
                return gray_config
        return base_config

    def promote_gray(self, data_id: str, group: str = "DEFAULT_GROUP",
                     namespace: str = "public") -> bool:
        """Promote gray config to production."""
        key = self._key(data_id, group, namespace)
        with self._lock:
            gray = self._gray_configs.get(key)
            if gray:
                self.store.publish(gray)
                del self._gray_configs[key]
                self._rules.pop(key, None)
                return True
            return False

    def rollback_gray(self, data_id: str, group: str = "DEFAULT_GROUP",
                      namespace: str = "public") -> bool:
        """Rollback gray release (remove gray config)."""
        key = self._key(data_id, group, namespace)
        with self._lock:
            if key in self._gray_configs:
                del self._gray_configs[key]
                self._rules.pop(key, None)
                return True
            return False


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2E — Config History & Rollback
# ═══════════════════════════════════════════════════════════════════════════════


class ConfigHistory:
    """Version history and rollback for configurations."""

    def __init__(self, store: ConfigStore,
                 history_dir: str = "./nacos_history") -> None:
        self.store = store
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self._history: Dict[str, List[ConfigSnapshot]] = {}
        self._lock = threading.RLock()
        self._load_history()

    def __repr__(self) -> str:
        total = sum(len(v) for v in self._history.values())
        return f"<ConfigHistory entries={total}>"

    def _key(self, data_id: str, group: str, namespace: str) -> str:
        return f"{namespace}@@{group}@@{data_id}"

    def _load_history(self) -> None:
        snapshot = self.history_dir / "history.json"
        if snapshot.exists():
            with open(snapshot, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.items():
                    self._history[k] = [ConfigSnapshot(
                        config=ConfigData.from_dict(e["config"]),
                        version=e["version"],
                        timestamp=e["timestamp"],
                        operator=e.get("operator", ""),
                        operation=e.get("operation", "modify"),
                    ) for e in v]

    def _save_history(self) -> None:
        snapshot = self.history_dir / "history.json"
        data: Dict[str, List[Dict[str, Any]]] = {}
        for k, v in self._history.items():
            data[k] = [e.to_dict() for e in v]
        with open(snapshot, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def record(self, config: ConfigData, operator: str = "system",
               operation: str = "modify") -> None:
        key = self._key(config.data_id, config.group, config.namespace_id)
        snapshot = ConfigSnapshot(
            config=config, version=config.version,
            timestamp=time.time(), operator=operator, operation=operation
        )
        with self._lock:
            self._history.setdefault(key, []).append(snapshot)
            self._save_history()

    def get_history(self, data_id: str, group: str = "DEFAULT_GROUP",
                    namespace: str = "public") -> List[ConfigSnapshot]:
        key = self._key(data_id, group, namespace)
        return list(self._history.get(key, []))

    def rollback(self, data_id: str, target_version: int,
                 group: str = "DEFAULT_GROUP", namespace: str = "public",
                 operator: str = "system") -> bool:
        """Rollback config to a specific version."""
        key = self._key(data_id, group, namespace)
        with self._lock:
            history = self._history.get(key, [])
            for snapshot in reversed(history):
                if snapshot.version == target_version:
                    old_config = snapshot.config
                    # Create new version from old content
                    new_config = ConfigData(
                        data_id=old_config.data_id,
                        group=old_config.group,
                        content=old_config.content,
                        namespace_id=old_config.namespace_id,
                        metadata=dict(old_config.metadata),
                    )
                    self.store.publish(new_config)
                    self.record(new_config, operator, "rollback")
                    return True
            return False

    def diff(self, data_id: str, v1: int, v2: int,
             group: str = "DEFAULT_GROUP", namespace: str = "public") -> Optional[str]:
        """Get diff between two versions."""
        key = self._key(data_id, group, namespace)
        history = self._history.get(key, [])
        c1: Optional[str] = None
        c2: Optional[str] = None
        for snap in history:
            if snap.version == v1:
                c1 = snap.config.content
            if snap.version == v2:
                c2 = snap.config.content
        if c1 is None or c2 is None:
            return None
        # Simple line diff
        lines1 = c1.splitlines()
        lines2 = c2.splitlines()
        diff_lines: List[str] = []
        for i, (a, b) in enumerate(zip(lines1, lines2)):
            if a != b:
                diff_lines.append(f"Line {i+1}: -{a}")
                diff_lines.append(f"Line {i+1}: +{b}")
        return "\n".join(diff_lines)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2F — Config Namespace
# ═══════════════════════════════════════════════════════════════════════════════


class ConfigNamespace:
    """Namespace isolation for configurations (dev / test / prod)."""

    def __init__(self, namespace_id: str, namespace_name: str,
                 description: str = "") -> None:
        self.namespace_id = namespace_id
        self.namespace_name = namespace_name
        self.description = description
        self.create_time = time.time()
        self.config_count = 0

    def __repr__(self) -> str:
        return f"<ConfigNamespace {self.namespace_id} '{self.namespace_name}' configs={self.config_count}>"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "namespaceId": self.namespace_id,
            "namespaceName": self.namespace_name,
            "description": self.description,
            "createTime": self.create_time,
        }


class NamespaceManager:
    """Manage config namespaces."""

    def __init__(self, data_dir: str = "./nacos_namespaces") -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._namespaces: Dict[str, ConfigNamespace] = {}
        self._load()

    def __repr__(self) -> str:
        return f"<NamespaceManager namespaces={len(self._namespaces)}>"

    def _load(self) -> None:
        snapshot = self.data_dir / "namespaces.json"
        if snapshot.exists():
            with open(snapshot, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.items():
                    ns = ConfigNamespace(
                        namespace_id=v["namespaceId"],
                        namespace_name=v["namespaceName"],
                        description=v.get("description", ""),
                    )
                    ns.create_time = v.get("createTime", time.time())
                    self._namespaces[k] = ns

    def _save(self) -> None:
        snapshot = self.data_dir / "namespaces.json"
        data = {k: v.to_dict() for k, v in self._namespaces.items()}
        with open(snapshot, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def create(self, namespace_id: str, name: str, description: str = "") -> ConfigNamespace:
        ns = ConfigNamespace(namespace_id, name, description)
        self._namespaces[namespace_id] = ns
        self._save()
        return ns

    def get(self, namespace_id: str) -> Optional[ConfigNamespace]:
        return self._namespaces.get(namespace_id)

    def delete(self, namespace_id: str) -> bool:
        if namespace_id in self._namespaces:
            del self._namespaces[namespace_id]
            self._save()
            return True
        return False

    def list_all(self) -> List[ConfigNamespace]:
        return list(self._namespaces.values())


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO — Part 2
# ═══════════════════════════════════════════════════════════════════════════════


def demo_part2() -> None:
    print("=" * 60)
    print("NACOS PART 2 — Config Center Demo")
    print("=" * 60)

    store = ConfigStore(data_dir="./nacos_demo_config")
    push_service = ConfigPushService(store)
    gray_mgr = GrayReleaseManager(store)
    history = ConfigHistory(store, history_dir="./nacos_demo_history")
    ns_mgr = NamespaceManager(data_dir="./nacos_demo_namespaces")

    print("\n[1] Namespace management:")
    ns_mgr.create("dev", "Development", "Dev environment")
    ns_mgr.create("prod", "Production", "Prod environment")
    for ns in ns_mgr.list_all():
        print(f"  {ns}")

    print("\n[2] Publish configurations:")
    cfg1 = ConfigData(
        data_id="app.properties", group="DEFAULT_GROUP",
        content="timeout=5000\nretry=3\n", namespace_id="dev"
    )
    cfg2 = ConfigData(
        data_id="db.yaml", group="DATABASE",
        content="host: localhost\nport: 3306\n", namespace_id="dev"
    )
    store.publish(cfg1)
    store.publish(cfg2)
    print(f"  Published: {cfg1}")
    print(f"  Published: {cfg2}")

    print("\n[3] Record history:")
    history.record(cfg1, "admin", "create")
    cfg1.update_content("timeout=3000\nretry=5\n")
    store.publish(cfg1)
    history.record(cfg1, "admin", "modify")
    print(f"  History entries for app.properties: {len(history.get_history('app.properties', namespace='dev'))}")

    print("\n[4] Config listener:")
    received: List[str] = []
    def on_config_change(config: ConfigData) -> None:
        received.append(f"{config.data_id} v{config.version}")
        print(f"  [PUSH] Config updated: {config.data_id} v{config.version}")

    listener = ConfigListener("app.properties", callback=on_config_change, namespace="dev")
    push_service.add_listener(listener)
    push_service.start(interval_ms=500)

    # Simulate config change
    cfg1.update_content("timeout=1000\nretry=10\n")
    store.publish(cfg1)
    push_service.notify("app.properties", namespace="dev")
    time.sleep(0.5)
    push_service.stop()
    print(f"  Total push notifications: {len(received)}")

    print("\n[5] Gray release:")
    gray_cfg = ConfigData(
        data_id="app.properties", group="DEFAULT_GROUP",
        content="timeout=100\nretry=1\nfeature_flag=new_ui\n",
        namespace_id="dev"
    )
    gray_mgr.set_gray_config("app.properties", gray_cfg, namespace="dev")
    rule = GrayRule(rule_id="r1", rule_type="ip", condition="192.168.1.")
    gray_mgr.add_rule("app.properties", rule, namespace="dev")

    # Client from canary IP
    client_info = {"ip": "192.168.1.55", "client_id": "client-001"}
    result = gray_mgr.get_config("app.properties", namespace="dev", client_info=client_info)
    print(f"  Canary client (192.168.1.55) gets gray config: {'new_ui' in (result.content if result else '')}")

    # Normal client
    normal_info = {"ip": "10.0.0.1", "client_id": "client-002"}
    result2 = gray_mgr.get_config("app.properties", namespace="dev", client_info=normal_info)
    print(f"  Normal client (10.0.0.1) gets base config: {'new_ui' not in (result2.content if result2 else '')}")

    print("\n[6] Rollback:")
    rollback_ok = history.rollback("app.properties", target_version=1, namespace="dev")
    print(f"  Rollback to v1: {rollback_ok}")
    rolled = store.get("app.properties", namespace="dev")
    print(f"  Current content: {rolled.content.strip() if rolled else 'None'}")

    print("\n[7] Diff:")
    diff = history.diff("app.properties", v1=1, v2=2, namespace="dev")
    print(f"  Diff v1 vs v2:\n{diff}")

    print("\n[8] Search configs:")
    results = store.search("app")
    print(f"  Search 'app': {len(results)} results")
    for r in results:
        print(f"    - {r}")

    print("\n" + "=" * 60)
    print("Part 2 Demo Complete")
    print("=" * 60)


if __name__ == "__main__":
    demo_part2()

#!/usr/bin/env python3
"""
nacos_native_part3.py — Part 3: Service Governance, Cluster, Load Balancer & Kernel
Nacos native reimplementation (alibaba/nacos). Pure Python, no external deps.
Sections: Load Balancer, Service Governance, Raft Consensus, Cluster Manager, NacosKernel, CLI + demo.
"""

import json
import math
import random
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3A — Load Balancer
# ═══════════════════════════════════════════════════════════════════════════════


class LoadBalancer(ABC):
    """Abstract load balancer for service instances."""

    @abstractmethod
    def select(self, instances: List[Any]) -> Optional[Any]:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


class RandomBalancer(LoadBalancer):
    """Random selection from healthy instances."""

    def select(self, instances: List[Any]) -> Optional[Any]:
        if not instances:
            return None
        return random.choice(instances)


class WeightedBalancer(LoadBalancer):
    """Weighted random selection based on instance weight."""

    def select(self, instances: List[Any]) -> Optional[Any]:
        if not instances:
            return None
        total_weight = sum(float(getattr(i, "weight", 1.0)) for i in instances)
        if total_weight <= 0:
            return random.choice(instances)
        pick = random.uniform(0, total_weight)
        current = 0.0
        for inst in instances:
            w = float(getattr(inst, "weight", 1.0))
            current += w
            if pick <= current:
                return inst
        return instances[-1]


class LeastActiveBalancer(LoadBalancer):
    """Select instance with least active requests (simulated)."""

    def __init__(self) -> None:
        self._active_counts: Dict[str, int] = {}
        self._lock = threading.Lock()

    def _key(self, inst: Any) -> str:
        return getattr(inst, "instance_id", str(id(inst)))

    def select(self, instances: List[Any]) -> Optional[Any]:
        if not instances:
            return None
        with self._lock:
            candidates = sorted(
                instances,
                key=lambda i: self._active_counts.get(self._key(i), 0)
            )
            chosen = candidates[0]
            self._active_counts[self._key(chosen)] = self._active_counts.get(self._key(chosen), 0) + 1
            return chosen

    def release(self, inst: Any) -> None:
        with self._lock:
            k = self._key(inst)
            if k in self._active_counts and self._active_counts[k] > 0:
                self._active_counts[k] -= 1


class RoundRobinBalancer(LoadBalancer):
    """Round-robin selection across instances."""

    def __init__(self) -> None:
        self._counter = 0
        self._lock = threading.Lock()

    def select(self, instances: List[Any]) -> Optional[Any]:
        if not instances:
            return None
        with self._lock:
            idx = self._counter % len(instances)
            self._counter += 1
            return instances[idx]


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3B — Service Metadata & Traffic Management
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class RouteRule:
    """Traffic routing rule for service governance."""
    rule_id: str
    priority: int = 0
    match_condition: Dict[str, str] = field(default_factory=dict)
    target_cluster: str = "DEFAULT"
    weight: float = 100.0
    enabled: bool = True

    def __repr__(self) -> str:
        return f"<RouteRule {self.rule_id} cluster={self.target_cluster}>"

    def matches(self, request_metadata: Dict[str, str]) -> bool:
        if not self.enabled:
            return False
        for key, val in self.match_condition.items():
            if request_metadata.get(key) != val:
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ruleId": self.rule_id, "priority": self.priority,
            "matchCondition": self.match_condition,
            "targetCluster": self.target_cluster,
            "weight": self.weight, "enabled": self.enabled,
        }


@dataclass
class RateLimitRule:
    """Rate limiting configuration."""
    resource: str
    qps: float = 1000.0
    burst: int = 100
    strategy: str = "fast_reject"  # fast_reject, warm_up
    enabled: bool = True

    def __repr__(self) -> str:
        return f"<RateLimitRule {self.resource} qps={self.qps}>"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource": self.resource, "qps": self.qps,
            "burst": self.burst, "strategy": self.strategy,
            "enabled": self.enabled,
        }


class RateLimiter:
    """Token-bucket rate limiter simulation."""

    def __init__(self) -> None:
        self._buckets: Dict[str, float] = {}
        self._last_fill: Dict[str, float] = {}
        self._rules: Dict[str, RateLimitRule] = {}
        self._lock = threading.Lock()

    def __repr__(self) -> str:
        return f"<RateLimiter rules={len(self._rules)}>"

    def add_rule(self, rule: RateLimitRule) -> None:
        with self._lock:
            self._rules[rule.resource] = rule
            self._buckets[rule.resource] = rule.burst
            self._last_fill[rule.resource] = time.time()

    def allow(self, resource: str) -> bool:
        with self._lock:
            rule = self._rules.get(resource)
            if not rule or not rule.enabled:
                return True
            now = time.time()
            elapsed = now - self._last_fill.get(resource, now)
            self._last_fill[resource] = now
            # Add tokens
            self._buckets[resource] = min(
                rule.burst,
                self._buckets.get(resource, 0) + elapsed * rule.qps
            )
            if self._buckets[resource] >= 1.0:
                self._buckets[resource] -= 1.0
                return True
            return False

    def get_state(self, resource: str) -> Dict[str, Any]:
        with self._lock:
            return {
                "resource": resource,
                "tokens": self._buckets.get(resource, 0),
                "rule": self._rules.get(resource, RateLimitRule(resource)).to_dict(),
            }


class ServiceGovernance:
    """Service governance: routing, rate limiting, metadata."""

    def __init__(self) -> None:
        self._route_rules: Dict[str, List[RouteRule]] = {}
        self._rate_limiter = RateLimiter()
        self._metadata: Dict[str, Dict[str, str]] = {}
        self._lock = threading.Lock()

    def __repr__(self) -> str:
        total_rules = sum(len(v) for v in self._route_rules.values())
        return f"<ServiceGovernance rules={total_rules}>"

    def add_route_rule(self, service_name: str, rule: RouteRule) -> None:
        with self._lock:
            self._route_rules.setdefault(service_name, []).append(rule)
            self._route_rules[service_name].sort(key=lambda r: r.priority, reverse=True)

    def get_route_rules(self, service_name: str) -> List[RouteRule]:
        return list(self._route_rules.get(service_name, []))

    def route(self, service_name: str, request_metadata: Dict[str, str],
              instances: List[Any]) -> List[Any]:
        """Filter instances based on route rules."""
        rules = self.get_route_rules(service_name)
        for rule in rules:
            if rule.matches(request_metadata):
                filtered = [i for i in instances if getattr(i, "cluster_name", "DEFAULT") == rule.target_cluster]
                return filtered if filtered else instances
        return instances

    def get_rate_limiter(self) -> RateLimiter:
        return self._rate_limiter

    def set_metadata(self, service_name: str, metadata: Dict[str, str]) -> None:
        with self._lock:
            self._metadata[service_name] = metadata

    def get_metadata(self, service_name: str) -> Dict[str, str]:
        return dict(self._metadata.get(service_name, {}))


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3C — Raft Consensus Simulation
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ClusterNode:
    """A node in the Nacos cluster."""
    node_id: str
    ip: str
    port: int
    status: str = "up"  # up, down, joining, leaving
    raft_role: str = "follower"  # follower, candidate, leader
    term: int = 0
    vote_for: Optional[str] = None
    last_heartbeat: float = 0.0
    metadata: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.last_heartbeat == 0.0:
            self.last_heartbeat = time.time()

    def __repr__(self) -> str:
        return f"<ClusterNode {self.node_id} {self.raft_role} term={self.term}>"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodeId": self.node_id, "ip": self.ip, "port": self.port,
            "status": self.status, "raftRole": self.raft_role,
            "term": self.term, "voteFor": self.vote_for,
            "lastHeartbeat": self.last_heartbeat,
            "metadata": self.metadata,
        }


class RaftConsensus:
    """Simplified Raft consensus simulation for cluster management."""

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self._nodes: Dict[str, ClusterNode] = {}
        self._leader: Optional[str] = None
        self._term = 0
        self._voted_for: Optional[str] = None
        self._log: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def __repr__(self) -> str:
        return f"<RaftConsensus node={self.node_id} leader={self._leader} term={self._term}>"

    def add_node(self, node: ClusterNode) -> None:
        with self._lock:
            self._nodes[node.node_id] = node

    def remove_node(self, node_id: str) -> bool:
        with self._lock:
            if node_id in self._nodes:
                del self._nodes[node_id]
                if self._leader == node_id:
                    self._leader = None
                return True
            return False

    def get_node(self, node_id: str) -> Optional[ClusterNode]:
        return self._nodes.get(node_id)

    def get_all_nodes(self) -> List[ClusterNode]:
        return list(self._nodes.values())

    def get_leader(self) -> Optional[ClusterNode]:
        if self._leader:
            return self._nodes.get(self._leader)
        return None

    def _heartbeat(self, from_node: str) -> None:
        with self._lock:
            node = self._nodes.get(from_node)
            if node:
                node.last_heartbeat = time.time()
                if node.raft_role == "leader":
                    self._leader = from_node
                    self._term = max(self._term, node.term)

    def simulate_election(self) -> Optional[str]:
        """Simulate leader election."""
        with self._lock:
            healthy_nodes = [
                n for n in self._nodes.values()
                if n.status == "up" and (time.time() - n.last_heartbeat) < 5.0
            ]
            if not healthy_nodes:
                return None
            # Random leader election
            leader = random.choice(healthy_nodes)
            self._term += 1
            self._leader = leader.node_id
            leader.raft_role = "leader"
            leader.term = self._term
            for n in self._nodes.values():
                if n.node_id != leader.node_id:
                    n.raft_role = "follower"
                    n.term = self._term
            return leader.node_id

    def replicate_log(self, entry: Dict[str, Any]) -> bool:
        """Simulate log replication to followers."""
        with self._lock:
            if self._leader != self.node_id:
                return False
            entry["term"] = self._term
            entry["index"] = len(self._log)
            self._log.append(entry)
            # Simulate replication to all followers
            replicated = 1  # leader
            for node in self._nodes.values():
                if node.node_id != self.node_id and node.status == "up":
                    replicated += 1
            # Simple majority check
            if replicated > len(self._nodes) // 2:
                entry["committed"] = True
                return True
            return False

    def get_log(self) -> List[Dict[str, Any]]:
        return list(self._log)


class ClusterManager:
    """Manages Nacos cluster nodes and Raft consensus."""

    def __init__(self, local_node_id: str) -> None:
        self.local_node_id = local_node_id
        self.raft = RaftConsensus(local_node_id)
        self._running = False
        self._heartbeat_thread: Optional[threading.Thread] = None

    def __repr__(self) -> str:
        return f"<ClusterManager node={self.local_node_id} nodes={len(self.raft.get_all_nodes())}>"

    def join_node(self, node: ClusterNode) -> None:
        self.raft.add_node(node)

    def leave_node(self, node_id: str) -> bool:
        return self.raft.remove_node(node_id)

    def get_cluster_state(self) -> Dict[str, Any]:
        leader = self.raft.get_leader()
        return {
            "localNode": self.local_node_id,
            "leader": leader.node_id if leader else None,
            "term": self.raft._term,
            "nodes": [n.to_dict() for n in self.raft.get_all_nodes()],
            "log_length": len(self.raft.get_log()),
        }

    def start_heartbeat(self, interval_ms: int = 1000) -> None:
        if not self._running:
            self._running = True
            self._heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop, args=(interval_ms,), daemon=True
            )
            self._heartbeat_thread.start()

    def stop_heartbeat(self) -> None:
        self._running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=2.0)

    def _heartbeat_loop(self, interval_ms: int) -> None:
        while self._running:
            for node in self.raft.get_all_nodes():
                if node.node_id != self.local_node_id:
                    self.raft._heartbeat(node.node_id)
            time.sleep(interval_ms / 1000.0)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3D — NacosKernel & CLI
# ═══════════════════════════════════════════════════════════════════════════════


class NacosKernel:
    """Main kernel integrating all Nacos subsystems."""

    def __init__(self, data_dir: str = "./nacos_data") -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        # Note: Part1 and Part2 classes would be imported here in real usage
        # For standalone demo, we stub the key interfaces
        self.governance = ServiceGovernance()
        self.cluster = ClusterManager("nacos-1")
        self.balancer_registry: Dict[str, LoadBalancer] = {
            "random": RandomBalancer(),
            "weighted": WeightedBalancer(),
            "least_active": LeastActiveBalancer(),
            "round_robin": RoundRobinBalancer(),
        }

    def __repr__(self) -> str:
        return f"<NacosKernel data={self.data_dir}>"

    def set_balancer(self, service_name: str, balancer_type: str) -> bool:
        if balancer_type not in self.balancer_registry:
            return False
        # In real impl, attach to naming service
        return True

    def add_rate_limit(self, resource: str, qps: float, burst: int = 100) -> None:
        rule = RateLimitRule(resource=resource, qps=qps, burst=burst)
        self.governance.get_rate_limiter().add_rule(rule)

    def cli_register(self, service_name: str, ip: str, port: int,
                     weight: float = 1.0, metadata: Optional[Dict[str, str]] = None) -> str:
        return f"Registered {service_name}@{ip}:{port} weight={weight}"

    def cli_discover(self, service_name: str) -> List[str]:
        return [f"{service_name}@192.168.1.{i}:8080" for i in range(1, 4)]

    def cli_publish_config(self, data_id: str, content: str) -> str:
        return f"Published config {data_id} ({len(content)} bytes)"

    def cli_get_config(self, data_id: str) -> Optional[str]:
        return f"timeout=5000\nretry=3"

    def cli_list_services(self) -> List[str]:
        return ["order-service", "payment-service", "inventory-service"]

    def cli_cluster_status(self) -> Dict[str, Any]:
        return self.cluster.get_cluster_state()

    def cli_route_add(self, service_name: str, rule: RouteRule) -> str:
        self.governance.add_route_rule(service_name, rule)
        return f"Added route rule {rule.rule_id} for {service_name}"


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO — Part 3
# ═══════════════════════════════════════════════════════════════════════════════


def demo_part3() -> None:
    print("=" * 60)
    print("NACOS PART 3 — Service Governance, Cluster & Kernel Demo")
    print("=" * 60)

    kernel = NacosKernel(data_dir="./nacos_demo_kernel")

    # Stub instances for load balancer demo
    @dataclass
    class StubInstance:
        instance_id: str
        ip: str
        port: int
        weight: float = 1.0
        cluster_name: str = "DEFAULT"

    instances = [
        StubInstance("i1", "192.168.1.10", 8080, weight=1.0, cluster_name="A"),
        StubInstance("i2", "192.168.1.11", 8080, weight=2.0, cluster_name="A"),
        StubInstance("i3", "192.168.1.12", 8080, weight=3.0, cluster_name="B"),
    ]

    print("\n[1] Load Balancers:")
    for name, balancer in kernel.balancer_registry.items():
        picks: Dict[str, int] = {}
        for _ in range(1000):
            selected = balancer.select(instances)
            if selected:
                picks[selected.instance_id] = picks.get(selected.instance_id, 0) + 1
        print(f"  {name}: {dict(picks)}")

    print("\n[2] Service Governance — Route Rules:")
    rule = RouteRule(
        rule_id="r1", priority=10,
        match_condition={"region": "us-east"},
        target_cluster="A", weight=100.0
    )
    kernel.governance.add_route_rule("order-service", rule)
    routed = kernel.governance.route("order-service", {"region": "us-east"}, instances)
    print(f"  Route 'order-service' with region=us-east -> {[i.instance_id for i in routed]}")
    routed_all = kernel.governance.route("order-service", {}, instances)
    print(f"  Route 'order-service' no match -> {[i.instance_id for i in routed_all]}")

    print("\n[3] Rate Limiter:")
    kernel.add_rate_limit("order-service", qps=10.0, burst=5)
    rl = kernel.governance.get_rate_limiter()
    allowed = sum(1 for _ in range(20) if rl.allow("order-service"))
    print(f"  Rate limit order-service: {allowed}/20 requests allowed (qps=10, burst=5)")

    print("\n[4] Cluster Manager:")
    node1 = ClusterNode("nacos-1", "10.0.0.1", 8848, raft_role="follower")
    node2 = ClusterNode("nacos-2", "10.0.0.2", 8848, raft_role="follower")
    node3 = ClusterNode("nacos-3", "10.0.0.3", 8848, raft_role="follower")
    kernel.cluster.join_node(node1)
    kernel.cluster.join_node(node2)
    kernel.cluster.join_node(node3)
    print(f"  Nodes: {[n.node_id for n in kernel.cluster.raft.get_all_nodes()]}")

    leader_id = kernel.cluster.raft.simulate_election()
    print(f"  Elected leader: {leader_id}")
    leader = kernel.cluster.raft.get_leader()
    print(f"  Leader state: {leader}")

    # Log replication
    entry = {"operation": "register", "service": "order-service", "timestamp": time.time()}
    replicated = kernel.cluster.raft.replicate_log(entry)
    print(f"  Log replication success: {replicated}")
    print(f"  Log entries: {len(kernel.cluster.raft.get_log())}")

    print("\n[5] Cluster state:")
    state = kernel.cli_cluster_status()
    print(f"  Local node: {state['localNode']}")
    print(f"  Leader: {state['leader']}")
    print(f"  Term: {state['term']}")
    print(f"  Node count: {len(state['nodes'])}")

    print("\n[6] CLI Commands:")
    print(f"  {kernel.cli_register('payment-service', '192.168.1.20', 9090, weight=2.0)}")
    print(f"  Services: {kernel.cli_list_services()}")
    print(f"  Discover order-service: {kernel.cli_discover('order-service')}")
    print(f"  Publish config: {kernel.cli_publish_config('db.yaml', 'host: localhost\\nport: 3306')}")
    config = kernel.cli_get_config("db.yaml")
    print(f"  Get config: {config[:30] if config else 'None'}...")

    print("\n[7] Route add via CLI:")
    route_rule = RouteRule(
        rule_id="canary-1", priority=5,
        match_condition={"version": "v2"},
        target_cluster="canary", weight=50.0
    )
    print(f"  {kernel.cli_route_add('order-service', route_rule)}")

    print("\n" + "=" * 60)
    print("Part 3 Demo Complete")
    print("=" * 60)


if __name__ == "__main__":
    demo_part3()
