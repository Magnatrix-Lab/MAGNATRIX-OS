#!/usr/bin/env python3
"""
runtime/supervisor_native.py
==========================
Layer 3 — MAGNATRIX-OS Supervisor / Main Event Loop

Manages:
  - Asyncio event loop for I/O multiplexing
  - Periodic task scheduler (repo hunt, model sync, health check, garbage collect)
  - Thread pool for CPU-bound work
  - Graceful shutdown coordination
  - Signal handling

Usage:
  from runtime.supervisor_native import Supervisor
  sup = Supervisor(config)
  sup.start()  # Blocks until shutdown
"""

from __future__ import annotations

import asyncio
import importlib
import os
import signal
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set


@dataclass
class ScheduledTask:
    name: str
    interval_sec: float
    callback: Callable[[], Any]
    last_run: float = 0.0
    enabled: bool = True


@dataclass
class SupervisorConfig:
    max_workers: int = 4
    shutdown_timeout_sec: float = 10.0
    health_check_interval_sec: float = 30.0
    gc_interval_sec: float = 300.0
    repo_hunt_interval_sec: float = 3600.0
    model_sync_interval_sec: float = 7200.0
    log_flush_interval_sec: float = 5.0


class Supervisor:
    """Central supervisor that runs the MAGNATRIX-OS main event loop."""

    def __init__(self, config: Optional[SupervisorConfig] = None,
                 magnatrix_instance: Optional[Any] = None) -> None:
        self.config = config or SupervisorConfig()
        self.magnatrix = magnatrix_instance
        self._tasks: List[ScheduledTask] = []
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._shutdown_event = threading.Event()
        self._thread_pool = []
        self._layer_objects: Dict[str, Any] = {}  # name -> instantiated layer

    # ---- Layer Instantiation ----

    def _instantiate_layer(self, layer_name: str, module_path: str,
                           class_name: str, **kwargs) -> Optional[Any]:
        """Dynamically import and instantiate a layer class."""
        try:
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            instance = cls(**kwargs)
            self._layer_objects[layer_name] = instance
            print(f"[SUPERVISOR] Layer '{layer_name}' instantiated: {class_name}")
            return instance
        except Exception as e:
            print(f"[SUPERVISOR] Layer '{layer_name}' FAILED: {e}")
            return None

    def instantiate_all_layers(self, config: Dict[str, Any]) -> None:
        """Wire all 15 layers into real objects."""
        # Layer 0: Kernel (self)
        # Layer 1: Protocol
        self._instantiate_layer("protocol", "protocol.protocol_native", "ProtocolEngine",
                                config=config.get("protocol", {}))
        # Layer 1.5: API Router
        self._instantiate_layer("api_router", "api-router.api_router_native", "RouterKernel",
                                secret=os.urandom(32))
        # Layer 2: Identity / Crypto
        from identity.crypto_identity_native import CryptoEngine, IdentityRegistry
        self._layer_objects["crypto"] = CryptoEngine()
        self._layer_objects["identity_registry"] = IdentityRegistry(
            config.get("identity", {}).get("key_store", "/var/lib/magnatrix/identities")
        )
        # Layer 3: Runtime (self)
        # Layer 4: P2P Mesh
        self._instantiate_layer("p2p", "p2p-mesh.p2p_mesh_native", "P2PTransport",
                                listen_port=config.get("p2p_mesh", {}).get("listen_port", 8001))
        # Layer 5: Knowledge
        self._instantiate_layer("knowledge", "knowledge.knowledge_engine_native", "KnowledgeEngine")
        # Layer 6: Skills
        self._instantiate_layer("skills", "skills.skills_native", "SkillRegistry",
                                auto_discover=True)
        # Layer 7: Browser
        self._instantiate_layer("browser", "browser.browser_native", "BrowserAgent")
        # Layer 8: Trading
        self._instantiate_layer("trading", "trading.trading_native", "TradingEngine")
        # Layer 9: Security
        from security.sandbox_native import SandboxEngine
        self._layer_objects["sandbox"] = SandboxEngine()
        # Layer 10: AI
        from ai.uncensored_ai_native import InferenceEngine
        self._layer_objects["ai"] = InferenceEngine(
            vocab_size=32000,
            n_layers=32,
            n_heads=32,
            head_dim=128,
        )
        # Layer 11: Governance
        self._instantiate_layer("governance", "governance.governance_native", "GovernanceEngine")
        # Layer 12: IDE
        self._instantiate_layer("ide", "ide.terminal_multiplexer_native", "MultiplexerKernelBridge")
        # Layer 13: Offensive Security
        self._instantiate_layer("offensive", "security.offensive_native", "OffensiveSecurityEngine")
        # Layer 13.5: Repo Hunter
        self._instantiate_layer("repo_hunter", "runtime.repo_hunter_native", "HunterScheduler")
        # Layer 14: Observability
        from observability.metrics_native import ObservabilityEngine
        self._layer_objects["observability"] = ObservabilityEngine()
        # Layer 15: Consensus
        from consensus.raft_native import RaftNode, RaftConfig, KeyValueStateMachine
        cfg = RaftConfig(node_id="node-1", peers=[], data_dir="/var/lib/magnatrix/raft")
        self._layer_objects["raft"] = RaftNode(cfg, KeyValueStateMachine())

    # ---- Task Scheduling ----

    def add_task(self, name: str, interval_sec: float, callback: Callable[[], Any]) -> None:
        self._tasks.append(ScheduledTask(name, interval_sec, callback))

    def _run_periodic_tasks(self) -> None:
        while self._running:
            now = time.time()
            for task in self._tasks:
                if task.enabled and now - task.last_run >= task.interval_sec:
                    try:
                        task.callback()
                    except Exception as e:
                        print(f"[SUPERVISOR] Task '{task.name}' error: {e}")
                    task.last_run = now
            time.sleep(1.0)

    # ---- Event Loop ----

    def _async_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        # Setup async services here
        self._loop.run_until_complete(self._main_async())

    async def _main_async(self) -> None:
        while self._running:
            # Main async tick: process async I/O, P2P messages, API requests
            await asyncio.sleep(0.1)

    # ---- Lifecycle ----

    def start(self) -> None:
        print("[SUPERVISOR] Starting MAGNATRIX-OS...")
        self._running = True

        # Signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Start async loop in background
        self._async_thread = threading.Thread(target=self._async_loop, daemon=True)
        self._async_thread.start()

        # Start periodic task runner
        self._scheduler_thread = threading.Thread(target=self._run_periodic_tasks, daemon=True)
        self._scheduler_thread.start()

        # Register default periodic tasks
        self._register_default_tasks()

        print("[SUPERVISOR] Running. Press Ctrl+C to shutdown.")
        self._shutdown_event.wait()

    def _register_default_tasks(self) -> None:
        def _health_check():
            obs = self._layer_objects.get("observability")
            if obs:
                result = obs.run_health_check()
                if not result.get("healthy"):
                    print(f"[HEALTH] ALERT: {result}")

        def _log_flush():
            # Flush all pending logs
            pass

        def _gc():
            import gc
            gc.collect()
            print(f"[GC] Collected. Active objects: {len(gc.get_objects())}")

        self.add_task("health_check", self.config.health_check_interval_sec, _health_check)
        self.add_task("log_flush", self.config.log_flush_interval_sec, _log_flush)
        self.add_task("gc", self.config.gc_interval_sec, _gc)

    def _signal_handler(self, signum, frame) -> None:
        sig_name = signal.Signals(signum).name if hasattr(signal, "Signals") else str(signum)
        print(f"\n[SUPERVISOR] Received {sig_name}, shutting down...")
        self.shutdown()

    def shutdown(self) -> None:
        if not self._running:
            return
        self._running = False
        self._shutdown_event.set()

        # Shutdown layers in reverse order
        for name in reversed(list(self._layer_objects.keys())):
            obj = self._layer_objects[name]
            if hasattr(obj, "stop"):
                try:
                    obj.stop()
                    print(f"[SHUTDOWN] Layer '{name}' stopped.")
                except Exception as e:
                    print(f"[SHUTDOWN] Layer '{name}' error: {e}")

        # Stop threads
        if self._async_thread and self._async_thread.is_alive():
            if self._loop:
                self._loop.call_soon_threadsafe(self._loop.stop)
            self._async_thread.join(timeout=5.0)
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=5.0)

        print("[SUPERVISOR] Shutdown complete.")

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "layers": len(self._layer_objects),
            "tasks": len(self._tasks),
            "layer_names": list(self._layer_objects.keys()),
        }


def demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS  |  SUPERVISOR DEMO")
    print("=" * 60)
    sup = Supervisor()
    print(f"Stats: {sup.stats}")
    print("=" * 60)


if __name__ == "__main__":
    demo()
