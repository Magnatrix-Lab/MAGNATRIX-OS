"""
MAGNATRIX — Core Kernel Engine
═══════════════════════════════
Layer 0: Kernel — orchestrator utama seluruh MAGNATRIX OS.

Responsibilities:
- Service lifecycle management (start, stop, health check)
- Inter-process message bus (async pub/sub)
- Configuration loading & hot-reload
- Plugin/module discovery & loading
- Graceful shutdown coordination
- Resource monitoring (CPU, memory, file descriptors)

Author: MAGNATRIX-OS
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import json
import os
import signal
import sys
import time
import tomllib
import traceback
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type


class ServiceState(Enum):
    STOPPED = auto()
    STARTING = auto()
    RUNNING = auto()
    DEGRADED = auto()
    STOPPING = auto()
    FAILED = auto()


@dataclass
class ServiceDescriptor:
    name: str
    module_path: str
    class_name: str
    depends_on: List[str] = field(default_factory=list)
    critical: bool = False
    restart_policy: str = "always"  # always, never, on-failure
    max_restarts: int = 3
    healthcheck_interval: float = 30.0


@dataclass
class ServiceInstance:
    descriptor: ServiceDescriptor
    instance: Any = None
    state: ServiceState = ServiceState.STOPPED
    task: Optional[asyncio.Task] = None
    restarts: int = 0
    last_healthcheck: float = 0.0
    error: Optional[str] = None


class MessageBus:
    """Async pub/sub message bus untuk komunikasi antar service/layer."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = asyncio.Lock()
        self._history: asyncio.Queue = asyncio.Queue(maxsize=1000)

    async def publish(self, topic: str, payload: Dict[str, Any]) -> None:
        msg = {
            "topic": topic,
            "payload": payload,
            "timestamp": time.time(),
            "id": f"msg-{uuid.uuid4().hex[:8]}",
        }
        # Store in history
        try:
            self._history.put_nowait(msg)
        except asyncio.QueueFull:
            try:
                self._history.get_nowait()
            except asyncio.QueueEmpty:
                pass
            self._history.put_nowait(msg)

        # Notify subscribers
        async with self._lock:
            handlers = list(self._subscribers.get(topic, []))
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(msg))
                else:
                    handler(msg)
            except Exception as e:
                print(f"[MessageBus] Handler error on {topic}: {e}")

    async def subscribe(self, topic: str, handler: Callable) -> None:
        async with self._lock:
            self._subscribers.setdefault(topic, []).append(handler)

    async def unsubscribe(self, topic: str, handler: Callable) -> None:
        async with self._lock:
            if topic in self._subscribers and handler in self._subscribers[topic]:
                self._subscribers[topic].remove(handler)

    def get_history(self, topic: Optional[str] = None, n: int = 100) -> List[Dict[str, Any]]:
        items = list(self._history._queue)
        if topic:
            items = [m for m in items if m["topic"] == topic]
        return items[-n:]


class KernelEngine:
    """Core kernel engine — manages all MAGNATRIX services and orchestration."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "magnatrix.toml"
        self.config: Dict[str, Any] = {}
        self.bus = MessageBus()
        self._services: Dict[str, ServiceInstance] = {}
        self._shutdown_event = asyncio.Event()
        self._lock = asyncio.Lock()
        self._health_task: Optional[asyncio.Task] = None
        self._start_time = time.time()

    # ── Configuration ───────────────────────────────────────────────────

    def load_config(self) -> Dict[str, Any]:
        path = Path(self.config_path)
        if path.exists():
            with open(path, "rb") as f:
                self.config = tomllib.load(f)
        else:
            self.config = self._default_config()
        return self.config

    def _default_config(self) -> Dict[str, Any]:
        return {
            "system": {"name": "MAGNATRIX", "version": "0.1.0", "mode": "local"},
            "collective_brain": {"enabled": True},
            "trading": {"mode": "paper"},
            "p2p": {"enabled": False},
        }

    # ── Service Lifecycle ──────────────────────────────────────────────

    def register_service(self, descriptor: ServiceDescriptor) -> None:
        self._services[descriptor.name] = ServiceInstance(descriptor=descriptor)

    async def start_service(self, name: str) -> bool:
        inst = self._services.get(name)
        if not inst:
            raise ValueError(f"Service '{name}' not registered")

        async with self._lock:
            if inst.state in (ServiceState.RUNNING, ServiceState.STARTING):
                return True
            inst.state = ServiceState.STARTING
            inst.error = None

        try:
            # Load module & instantiate
            mod = importlib.import_module(inst.descriptor.module_path)
            cls = getattr(mod, inst.descriptor.class_name)
            inst.instance = cls()

            # Start the service
            if hasattr(inst.instance, "start"):
                start_fn = inst.instance.start
                if asyncio.iscoroutinefunction(start_fn):
                    await start_fn()
                else:
                    start_fn()

            # Subscribe to bus if supported
            if hasattr(inst.instance, "on_bus_message"):
                await self.bus.subscribe(f"service.{name}.*", inst.instance.on_bus_message)

            inst.state = ServiceState.RUNNING
            await self.bus.publish("kernel.service.started", {"service": name, "state": "running"})
            return True

        except Exception as e:
            inst.state = ServiceState.FAILED
            inst.error = str(e)
            await self.bus.publish("kernel.service.failed", {"service": name, "error": str(e)})
            if inst.descriptor.critical:
                await self._handle_critical_failure(name, e)
            return False

    async def stop_service(self, name: str) -> bool:
        inst = self._services.get(name)
        if not inst or inst.state != ServiceState.RUNNING:
            return False

        inst.state = ServiceState.STOPPING
        try:
            if inst.instance and hasattr(inst.instance, "stop"):
                stop_fn = inst.instance.stop
                if asyncio.iscoroutinefunction(stop_fn):
                    await stop_fn()
                else:
                    stop_fn()
            if inst.task and not inst.task.done():
                inst.task.cancel()
                try:
                    await inst.task
                except asyncio.CancelledError:
                    pass
        except Exception as e:
            print(f"[Kernel] Error stopping {name}: {e}")
        finally:
            inst.state = ServiceState.STOPPED
            inst.instance = None
            await self.bus.publish("kernel.service.stopped", {"service": name})
        return True

    async def start_all(self) -> Dict[str, bool]:
        """Start all services dengan dependency resolution."""
        results = {}
        # Topological sort by dependencies
        started: Set[str] = set()
        pending = {name for name in self._services}

        while pending:
            ready = []
            for name in pending:
                deps = self._services[name].descriptor.depends_on
                if all(d in started for d in deps):
                    ready.append(name)

            if not ready:
                # Circular dependency or missing dependency
                for name in pending:
                    deps = self._services[name].descriptor.depends_on
                    missing = [d for d in deps if d not in self._services]
                    if missing:
                        results[name] = False
                        self._services[name].state = ServiceState.FAILED
                        self._services[name].error = f"Missing dependencies: {missing}"
                break

            for name in ready:
                results[name] = await self.start_service(name)
                started.add(name)
                pending.remove(name)

        return results

    async def stop_all(self) -> None:
        """Graceful shutdown — stop all services in reverse dependency order."""
        # Reverse topological order
        order = []
        visited: Set[str] = set()

        def visit(name: str):
            if name in visited:
                return
            visited.add(name)
            for dep in self._services[name].descriptor.depends_on:
                if dep in self._services:
                    visit(dep)
            order.append(name)

        for name in self._services:
            visit(name)

        # Stop in reverse (dependents first)
        for name in reversed(order):
            await self.stop_service(name)

        await self.bus.publish("kernel.shutdown.complete", {"uptime": time.time() - self._start_time})

    # ── Health Monitoring ───────────────────────────────────────────────

    async def _health_monitor_loop(self) -> None:
        while not self._shutdown_event.is_set():
            for name, inst in self._services.items():
                if inst.state != ServiceState.RUNNING:
                    continue
                try:
                    healthy = True
                    if inst.instance and hasattr(inst.instance, "healthcheck"):
                        check = inst.instance.healthcheck()
                        if asyncio.iscoroutinefunction(check.__class__.__call__ if callable(check) else lambda: check):
                            healthy = await check
                        else:
                            healthy = check() if callable(check) else check
                    inst.last_healthcheck = time.time()
                    if not healthy:
                        inst.state = ServiceState.DEGRADED
                        await self.bus.publish("kernel.service.degraded", {"service": name})
                        if inst.descriptor.restart_policy == "always":
                            if inst.restarts < inst.descriptor.max_restarts:
                                inst.restarts += 1
                                await self.stop_service(name)
                                await asyncio.sleep(1)
                                await self.start_service(name)
                except Exception as e:
                    await self.bus.publish("kernel.health.error", {"service": name, "error": str(e)})
            await asyncio.wait_for(self._shutdown_event.wait(), timeout=10)

    # ── Resource Monitoring ───────────────────────────────────────────────

    def get_resource_snapshot(self) -> Dict[str, Any]:
        try:
            import psutil
            mem = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=0.1)
            disk = psutil.disk_usage("/")
            return {
                "cpu_percent": cpu,
                "memory_used_mb": mem.used // (1024 * 1024),
                "memory_total_mb": mem.total // (1024 * 1024),
                "memory_percent": mem.percent,
                "disk_used_gb": disk.used // (1024 * 1024 * 1024),
                "disk_total_gb": disk.total // (1024 * 1024 * 1024),
                "disk_percent": disk.percent,
                "load_avg": os.getloadavg() if hasattr(os, "getloadavg") else None,
            }
        except ImportError:
            return {"error": "psutil not installed"}

    # ── Signal Handling ──────────────────────────────────────────────────

    def _setup_signals(self):
        for sig in (signal.SIGINT, signal.SIGTERM):
            asyncio.get_event_loop().add_signal_handler(sig, lambda: asyncio.create_task(self._signal_handler()))

    async def _signal_handler(self):
        print("\n[Kernel] Shutdown signal received...")
        self._shutdown_event.set()
        await self.stop_all()
        asyncio.get_event_loop().stop()

    async def _handle_critical_failure(self, name: str, error: Exception) -> None:
        print(f"[Kernel] CRITICAL: Service {name} failed: {error}")
        await self.bus.publish("kernel.critical", {"service": name, "error": str(error)})
        # In production, could trigger alert/notification here

    # ── Main Entry ─────────────────────────────────────────────────────

    async def run(self) -> None:
        self.load_config()
        self._setup_signals()
        self._health_task = asyncio.create_task(self._health_monitor_loop())

        await self.bus.publish("kernel.startup", {"version": self.config.get("system", {}).get("version", "0.1.0")})
        results = await self.start_all()

        print(f"[Kernel] Started {sum(results.values())}/{len(results)} services")
        for name, ok in results.items():
            status = "OK" if ok else "FAILED"
            print(f"  [{status}] {name}")

        # Wait for shutdown
        try:
            await self._shutdown_event.wait()
        except asyncio.CancelledError:
            pass

    def get_status(self) -> Dict[str, Any]:
        return {
            "uptime": time.time() - self._start_time,
            "services": {
                name: {
                    "state": inst.state.name,
                    "restarts": inst.restarts,
                    "last_healthcheck": inst.last_healthcheck,
                    "error": inst.error,
                }
                for name, inst in self._services.items()
            },
            "resources": self.get_resource_snapshot(),
            "bus_subscribers": {k: len(v) for k, v in self.bus._subscribers.items()},
        }


# ═══════════════════════════════════════════════════════════════════════════
# Standalone
# ═══════════════════════════════════════════════════════════════════════════

async def demo_kernel():
    print("═" * 60)
    print("MAGNATRIX — Kernel Engine Demo")
    print("═" * 60)

    kernel = KernelEngine()

    # Register dummy services
    kernel.register_service(ServiceDescriptor(
        name="protocol", module_path="protocol.grpc_server", class_name="ProtocolServer",
        critical=True, depends_on=[],
    ))
    kernel.register_service(ServiceDescriptor(
        name="identity", module_path="identity.auth_manager", class_name="IdentityManager",
        depends_on=["protocol"],
    ))
    kernel.register_service(ServiceDescriptor(
        name="trading", module_path="trading.ai_trader", class_name="AITrader",
        depends_on=["identity"],
    ))

    # Simulate startup
    kernel.load_config()
    print(f"[1] Config: {kernel.config.get('system', {}).get('name')}")

    print(f"[2] Registered {len(kernel._services)} services")
    for name, inst in kernel._services.items():
        print(f"    - {name}: depends={inst.descriptor.depends_on}, critical={inst.descriptor.critical}")

    print(f"[3] Status: {json.dumps(kernel.get_status(), indent=2, default=str)}")
    print("═" * 60)


if __name__ == "__main__":
    asyncio.run(demo_kernel())
