"""
service_registry_native.py — Native Service Discovery Registry
Pure Python stdlib. Health check, load balancing, heartbeat, service mesh.
NativeServiceRegistry with run().
"""
from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional


class NativeServiceRegistry:
    """
    Native service discovery registry with health checks and load balancing.

    Simulates a lightweight service mesh. Services register with metadata,
    send periodic heartbeats, and consumers discover healthy instances.

    Attributes:
        services: name -> list of instance dicts.
        health_check_interval: Seconds between health check runs.
        heartbeat_timeout: Seconds before a service is marked unhealthy.
        load_balancer: Round-robin index per service.
    """

    def __init__(
        self,
        health_check_interval: float = 5.0,
        heartbeat_timeout: float = 15.0,
        persist_path: Optional[str] = None,
    ) -> None:
        self.services: Dict[str, List[Dict[str, Any]]] = {}
        self.lock = threading.RLock()
        self.health_check_interval = health_check_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.persist_path = persist_path
        self._load_balancer_index: Dict[str, int] = {}
        self._running = True
        self._health_thread = threading.Thread(target=self._health_loop, daemon=True)
        self._health_thread.start()
        if self.persist_path and os.path.exists(self.persist_path):
            self._load()

    def register(
        self,
        name: str,
        instance_id: str,
        host: str,
        port: int,
        meta: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Register a service instance.

        Args:
            name: Service name (e.g., 'payment-gateway').
            instance_id: Unique instance ID.
            host: Host address.
            port: Port number.
            meta: Optional metadata (e.g., version, region, weight).

        Returns:
            True if registered (or updated), False on conflict.
        """
        with self.lock:
            if name not in self.services:
                self.services[name] = []
                self._load_balancer_index[name] = 0

            for inst in self.services[name]:
                if inst["instance_id"] == instance_id:
                    # Update existing
                    inst["host"] = host
                    inst["port"] = port
                    inst["meta"] = meta or inst.get("meta", {})
                    inst["last_heartbeat"] = time.time()
                    inst["healthy"] = True
                    self._persist()
                    return True

            self.services[name].append({
                "instance_id": instance_id,
                "host": host,
                "port": port,
                "meta": meta or {},
                "registered_at": time.time(),
                "last_heartbeat": time.time(),
                "healthy": True,
            })
            self._persist()
            return True

    def deregister(self, name: str, instance_id: str) -> bool:
        """Remove a service instance."""
        with self.lock:
            if name not in self.services:
                return False
            before = len(self.services[name])
            self.services[name] = [i for i in self.services[name] if i["instance_id"] != instance_id]
            if len(self.services[name]) < before:
                self._persist()
                return True
            return False

    def heartbeat(self, name: str, instance_id: str) -> bool:
        """Send a heartbeat for an instance. Returns False if instance not found."""
        with self.lock:
            if name not in self.services:
                return False
            for inst in self.services[name]:
                if inst["instance_id"] == instance_id:
                    inst["last_heartbeat"] = time.time()
                    inst["healthy"] = True
                    self._persist()
                    return True
            return False

    def discover(self, name: str) -> List[Dict[str, Any]]:
        """Discover all healthy instances of a service."""
        now = time.time()
        with self.lock:
            if name not in self.services:
                return []
            return [
                {k: v for k, v in inst.items() if k != "last_heartbeat"}
                for inst in self.services[name]
                if inst.get("healthy") and now - inst["last_heartbeat"] < self.heartbeat_timeout
            ]

    def pick(self, name: str, strategy: str = "round_robin") -> Optional[Dict[str, Any]]:
        """
        Pick one healthy instance using a load-balancing strategy.

        Strategies: round_robin, random, least_connections (simulated).
        """
        healthy = self.discover(name)
        if not healthy:
            return None

        with self.lock:
            if strategy == "round_robin":
                idx = self._load_balancer_index.get(name, 0) % len(healthy)
                self._load_balancer_index[name] = idx + 1
                return healthy[idx]
            elif strategy == "random":
                import random
                return random.choice(healthy)
            elif strategy == "least_connections":
                # Simulate by picking the one with lowest simulated connection count
                return min(healthy, key=lambda i: i.get("meta", {}).get("connections", 0))
            else:
                return healthy[0]

    def _health_loop(self) -> None:
        """Background health check."""
        while self._running:
            time.sleep(self.health_check_interval)
            self._check_health()

    def _check_health(self) -> None:
        now = time.time()
        with self.lock:
            changed = False
            for instances in self.services.values():
                for inst in instances:
                    if now - inst["last_heartbeat"] > self.heartbeat_timeout:
                        if inst.get("healthy"):
                            inst["healthy"] = False
                            changed = True
            if changed:
                self._persist()

    def _persist(self) -> None:
        if not self.persist_path:
            return
        try:
            with open(self.persist_path, "w", encoding="utf-8") as f:
                json.dump(self.services, f, indent=2)
        except Exception:
            pass

    def _load(self) -> None:
        try:
            with open(self.persist_path, "r", encoding="utf-8") as f:
                self.services = json.load(f)
        except Exception:
            self.services = {}

    def list_services(self) -> Dict[str, Any]:
        """List all services with healthy/unhealthy counts."""
        with self.lock:
            result: Dict[str, Any] = {}
            for name, instances in self.services.items():
                healthy = sum(1 for i in instances if i.get("healthy"))
                result[name] = {
                    "total": len(instances),
                    "healthy": healthy,
                    "unhealthy": len(instances) - healthy,
                }
            return result

    def shutdown(self) -> None:
        """Graceful shutdown."""
        self._running = False
        self._health_thread.join(timeout=2)

    def run(self) -> Dict[str, Any]:
        """
        Self-test demo.

        Returns:
            Dict with test results and final registry state.
        """
        results: Dict[str, Any] = {"status": "ok", "tests": []}

        # Test 1: Register
        self.register("api-gateway", "api-1", "10.0.0.1", 8080, {"version": "1.2.0"})
        self.register("api-gateway", "api-2", "10.0.0.2", 8080, {"version": "1.2.0"})
        assert len(self.discover("api-gateway")) == 2, "Expected 2 instances"
        results["tests"].append({"name": "register", "pass": True})

        # Test 2: Deregister
        self.deregister("api-gateway", "api-1")
        assert len(self.discover("api-gateway")) == 1, "Expected 1 instance after deregister"
        results["tests"].append({"name": "deregister", "pass": True})

        # Test 3: Heartbeat timeout -> unhealthy
        self.register("api-gateway", "api-3", "10.0.0.3", 8080)
        time.sleep(0.05)
        # Without heartbeat, api-3 should become unhealthy after timeout
        # But our timeout is 15s, so force it by manipulating last_heartbeat
        with self.lock:
            for inst in self.services["api-gateway"]:
                if inst["instance_id"] == "api-3":
                    inst["last_heartbeat"] = time.time() - 20
        self._check_health()
        healthy = self.discover("api-gateway")
        assert all(i["instance_id"] != "api-3" for i in healthy), "Expired instance should be unhealthy"
        results["tests"].append({"name": "heartbeat_timeout", "pass": True})

        # Test 4: Load balancing round_robin
        self.register("lb-test", "lb-1", "10.0.1.1", 80)
        self.register("lb-test", "lb-2", "10.0.1.2", 80)
        picks = [self.pick("lb-test", "round_robin") for _ in range(4)]
        ids = [p["instance_id"] for p in picks if p]
        assert ids == ["lb-1", "lb-2", "lb-1", "lb-2"], f"Round-robin failed: {ids}"
        results["tests"].append({"name": "round_robin", "pass": True})

        # Test 5: Load balancing random
        pick_r = self.pick("lb-test", "random")
        assert pick_r is not None, "Random pick should return an instance"
        results["tests"].append({"name": "random_lb", "pass": True})

        # Test 6: Persistence
        tmp_path = "/tmp/native_service_registry_test.json"
        reg2 = NativeServiceRegistry(persist_path=tmp_path)
        reg2.register("persist", "p-1", "127.0.0.1", 9000)
        reg3 = NativeServiceRegistry(persist_path=tmp_path)
        assert len(reg3.discover("persist")) == 1, "Persistence load failed"
        os.remove(tmp_path)
        results["tests"].append({"name": "persistence", "pass": True})

        # Test 7: Thread safety
        errors: List[str] = []
        def worker():
            try:
                for i in range(20):
                    self.register("stress", f"s-{i}", "127.0.0.1", 8000 + i)
                    self.discover("stress")
            except Exception as e:
                errors.append(str(e))
        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        results["tests"].append({"name": "thread_safety", "pass": len(errors) == 0, "errors": errors})

        results["summary"] = f"{sum(1 for t in results['tests'] if t['pass'])}/{len(results['tests'])} tests passed"
        results["registry_state"] = self.list_services()
        return results


if __name__ == "__main__":
    registry = NativeServiceRegistry(
        health_check_interval=2.0,
        heartbeat_timeout=5.0,
        persist_path="/tmp/native_service_registry_demo.json",
    )
    try:
        print(registry.run())
    finally:
        registry.shutdown()
