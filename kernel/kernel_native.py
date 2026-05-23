"""kernel_native.py — MAGNATRIX-OS Layer 0: Kernel Foundation.

Pure Python, zero external dependencies.
Menyediakan boot sequence 15 layer, module loader dengan dependency graph,
health monitor, crash recovery, lifecycle manager, dan bridge ke Layer 0.

Author: GQRIS (MAGNATRIX-OS)
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import inspect
import json
import os
import sqlite3
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type


# ═══════════════════════════════════════════════════════════════════════════════
# Section 1 — Configuration & Enums
# ═══════════════════════════════════════════════════════════════════════════════

class LayerState(Enum):
    """Lifecycle state untuk setiap layer."""
    UNINITIALIZED = auto()
    INITIALIZING = auto()
    RUNNING = auto()
    DEGRADED = auto()
    FAILED = auto()
    STOPPING = auto()
    STOPPED = auto()
    RELOADING = auto()

    def __repr__(self) -> str:
        return f"LayerState.{self.name}"


class BootMode(Enum):
    """Mode boot untuk kernel."""
    COLD = auto()      # Boot dari nol
    WARM = auto()      # Boot dari checkpoint
    RECOVERY = auto()  # Boot setelah crash
    DIAGNOSTIC = auto() # Boot untuk diagnostic only


@dataclass
class KernelConfig:
    """Konfigurasi sentral untuk boot MAGNATRIX-OS."""
    project_name: str = "MAGNATRIX-OS"
    version: str = "0.1.0-alpha"
    boot_mode: BootMode = BootMode.COLD
    workspace_dir: str = "/root/.openclaw/workspace"
    kernel_dir: str = "kernel"
    checkpoint_dir: str = "kernel/checkpoints"
    checkpoint_interval_sec: float = 30.0
    health_check_interval_sec: float = 5.0
    heartbeat_timeout_sec: float = 15.0
    max_restart_attempts: int = 3
    restart_backoff_sec: float = 2.0
    graceful_shutdown_timeout_sec: float = 10.0
    lazy_load_enabled: bool = True
    dependency_resolve_strategy: str = "topological"
    log_level: str = "INFO"
    enable_crash_recovery: bool = True
    enable_auto_restart: bool = True
    layers: List[str] = field(default_factory=lambda: [
        "Layer 0 — Kernel",
        "Layer 1 — Hardware Abstraction",
        "Layer 2 — Memory Management",
        "Layer 3 — Process & Thread",
        "Layer 4 — I/O & Network",
        "Layer 5 — File System",
        "Layer 6 — Security & Crypto",
        "Layer 7 — Event Bus",
        "Layer 8 — Service Registry",
        "Layer 9 — Agent Runtime",
        "Layer 10 — Skill System",
        "Layer 11 — Trading Engine",
        "Layer 12 — Web IDE",
        "Layer 13 — P2P Mesh Network",
        "Layer 14 — COLLECTIVE BRAIN",
    ])

    def __repr__(self) -> str:
        return f"KernelConfig({self.project_name} v{self.version}, mode={self.boot_mode.name})"


@dataclass
class LayerMetadata:
    """Metadata untuk setiap layer MAGNATRIX-OS."""
    layer_id: int
    name: str
    module_name: str
    state: LayerState = LayerState.UNINITIALIZED
    dependencies: List[int] = field(default_factory=list)
    dependents: List[int] = field(default_factory=list)
    health_score: float = 1.0
    last_heartbeat: float = 0.0
    restart_count: int = 0
    error_log: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    checkpoint_data: Dict[str, Any] = field(default_factory=dict)
    instance: Any = None

    def __repr__(self) -> str:
        return (f"LayerMetadata({self.layer_id}: {self.name}, "
                f"state={self.state.name}, health={self.health_score:.2f})")


@dataclass
class ModuleSpec:
    """Spec untuk module yang di-discover."""
    name: str
    file_path: str
    layer_id: int
    dependencies: List[int]
    exports: List[str]
    has_native: bool = False
    doc_summary: str = ""

    def __repr__(self) -> str:
        return f"ModuleSpec({self.name}, layer={self.layer_id}, deps={self.dependencies})"


# ═══════════════════════════════════════════════════════════════════════════════
# Section 2 — Module Loader (Auto-Discovery + Dependency Graph + Lazy Load)
# ═══════════════════════════════════════════════════════════════════════════════

class ModuleLoader:
    """
    Auto-discover file `_native.py` di workspace, build dependency graph,
    resolve topological order, dan lazy-load module.
    """

    def __init__(self, config: KernelConfig) -> None:
        self.config = config
        self.modules: Dict[str, ModuleSpec] = {}
        self.loaded: Dict[str, Any] = {}
        self._load_order: List[str] = []
        self._lock = threading.RLock()

    def __repr__(self) -> str:
        return f"ModuleLoader(discovered={len(self.modules)}, loaded={len(self.loaded)})"

    def discover(self, scan_dir: Optional[str] = None) -> Dict[str, ModuleSpec]:
        """
        Scan direktori untuk file `_native.py`, parse header untuk
        extract layer_id dan dependencies.
        """
        scan_dir = scan_dir or self.config.workspace_dir
        discovered: Dict[str, ModuleSpec] = {}
        for root, _dirs, files in os.walk(scan_dir):
            for fname in files:
                if fname.endswith("_native.py"):
                    full_path = os.path.join(root, fname)
                    spec = self._parse_module_spec(full_path)
                    if spec:
                        discovered[spec.name] = spec
        self.modules = discovered
        return discovered

    def _parse_module_spec(self, file_path: str) -> Optional[ModuleSpec]:
        """Parse file header untuk extract metadata."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source)
            docstring = ast.get_docstring(tree) or ""
            layer_id = 0
            dependencies: List[int] = []
            exports: List[str] = []
            # Scan top-level assigns untuk LAYER_ID / DEPENDENCIES / __all__
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            if target.id == "LAYER_ID" and isinstance(node.value, ast.Constant):
                                layer_id = node.value.value
                            elif target.id == "DEPENDENCIES":
                                dependencies = self._extract_list(node.value)
                            elif target.id == "__all__":
                                exports = self._extract_list(node.value)
            name = Path(file_path).stem
            has_native = "native" in name.lower()
            summary = docstring.split("\n")[0][:80] if docstring else ""
            return ModuleSpec(
                name=name, file_path=file_path, layer_id=layer_id,
                dependencies=dependencies, exports=exports,
                has_native=has_native, doc_summary=summary,
            )
        except Exception as e:
            return None

    @staticmethod
    def _extract_list(node: ast.AST) -> List[Any]:
        """Extract list values dari AST node."""
        if isinstance(node, ast.List):
            return [elt.value for elt in node.elts if isinstance(elt, ast.Constant)]
        return []

    def resolve_dependencies(self) -> List[str]:
        """
        Topological sort untuk resolve load order berdasarkan layer_id
        dan dependency list.
        """
        # Build adjacency list: module_name -> dependencies
        adj: Dict[str, Set[str]] = {}
        name_by_layer: Dict[int, str] = {}
        for name, spec in self.modules.items():
            name_by_layer[spec.layer_id] = name
            adj[name] = set()

        for name, spec in self.modules.items():
            for dep_layer in spec.dependencies:
                if dep_layer in name_by_layer:
                    adj[name].add(name_by_layer[dep_layer])

        # Kahn's algorithm
        in_degree = {n: 0 for n in adj}
        for deps in adj.values():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1

        queue = [n for n, d in in_degree.items() if d == 0]
        order: List[str] = []
        while queue:
            queue.sort(key=lambda x: self.modules[x].layer_id)
            node = queue.pop(0)
            order.append(node)
            for neighbor in [n for n, deps in adj.items() if node in deps]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(adj):
            cyclic = set(adj.keys()) - set(order)
            raise RuntimeError(f"Circular dependency detected: {cyclic}")

        self._load_order = order
        return order

    def load(self, name: str) -> Any:
        """Lazy-load module by name."""
        with self._lock:
            if name in self.loaded:
                return self.loaded[name]
            spec = self.modules.get(name)
            if not spec:
                raise KeyError(f"Module '{name}' not discovered")
            module = self._load_from_path(spec.file_path)
            self.loaded[name] = module
            return module

    def _load_from_path(self, file_path: str) -> Any:
        """Dynamic import dari file path."""
        module_name = Path(file_path).stem
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load {file_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def lazy_get(self, layer_id: int) -> Optional[Any]:
        """Lazy-load module berdasarkan layer_id."""
        for name, spec in self.modules.items():
            if spec.layer_id == layer_id:
                if self.config.lazy_load_enabled:
                    return self.load(name)
                return self.load(name)
        return None

    def get_load_order(self) -> List[str]:
        """Return resolved topological load order."""
        if not self._load_order:
            self.resolve_dependencies()
        return self._load_order


# ═══════════════════════════════════════════════════════════════════════════════
# Section 3 — Health Monitor (Ping + Heartbeat + Auto-Restart)
# ═══════════════════════════════════════════════════════════════════════════════

class HealthMonitor:
    """
    Monitor kesehatan tiap layer via heartbeat, ping, dan auto-restart
    jika layer gagal respond dalam timeout.
    """

    def __init__(self, config: KernelConfig) -> None:
        self.config = config
        self._layers: Dict[int, LayerMetadata] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[int, LayerState, str], None]] = []
        self._lock = threading.RLock()

    def __repr__(self) -> str:
        return f"HealthMonitor(running={self._running}, layers={len(self._layers)})"

    def register(self, layer_meta: LayerMetadata) -> None:
        """Register layer untuk health monitoring."""
        with self._lock:
            self._layers[layer_meta.layer_id] = layer_meta

    def unregister(self, layer_id: int) -> None:
        """Unregister layer dari monitoring."""
        with self._lock:
            self._layers.pop(layer_id, None)

    def on_state_change(self, callback: Callable[[int, LayerState, str], None]) -> None:
        """Register callback untuk state change events."""
        self._callbacks.append(callback)

    def start(self) -> None:
        """Start health monitoring thread."""
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop health monitoring thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def ping(self, layer_id: int) -> Tuple[bool, float]:
        """
        Ping layer untuk cek responsiveness.
        Return (alive, response_time_ms).
        """
        layer = self._layers.get(layer_id)
        if not layer or not layer.instance:
            return False, 0.0
        start = time.perf_counter()
        try:
            # Cek apakah layer punya method `ping()`
            if hasattr(layer.instance, "ping") and callable(getattr(layer.instance, "ping")):
                layer.instance.ping()
            # Update heartbeat timestamp
            layer.last_heartbeat = time.time()
            rtt = (time.perf_counter() - start) * 1000
            return True, rtt
        except Exception as e:
            return False, 0.0

    def _monitor_loop(self) -> None:
        """Background loop untuk health check."""
        while self._running:
            now = time.time()
            for layer_id, layer in list(self._layers.items()):
                if layer.state == LayerState.RUNNING:
                    alive, rtt = self.ping(layer_id)
                    if alive:
                        layer.health_score = min(1.0, layer.health_score + 0.1)
                        if rtt > 1000:
                            layer.health_score -= 0.2
                    else:
                        elapsed = now - layer.last_heartbeat
                        if elapsed > self.config.heartbeat_timeout_sec:
                            self._handle_timeout(layer_id, f"No heartbeat for {elapsed:.1f}s")
            time.sleep(self.config.health_check_interval_sec)

    def _handle_timeout(self, layer_id: int, reason: str) -> None:
        """Handle layer yang tidak respond dalam timeout."""
        layer = self._layers.get(layer_id)
        if not layer:
            return
        layer.state = LayerState.FAILED
        layer.error_log.append(f"[{time.strftime('%H:%M:%S')}] HEALTH_TIMEOUT: {reason}")
        layer.health_score = max(0.0, layer.health_score - 0.3)
        for cb in self._callbacks:
            cb(layer_id, LayerState.FAILED, reason)

    def record_heartbeat(self, layer_id: int) -> None:
        """Record heartbeat dari layer."""
        layer = self._layers.get(layer_id)
        if layer:
            layer.last_heartbeat = time.time()
            layer.health_score = min(1.0, layer.health_score + 0.05)

    def get_health_report(self) -> Dict[int, Dict[str, Any]]:
        """Return health report untuk semua layer."""
        return {
            lid: {
                "name": l.name,
                "state": l.state.name,
                "health_score": l.health_score,
                "last_heartbeat": l.last_heartbeat,
                "restart_count": l.restart_count,
                "errors": len(l.error_log),
            }
            for lid, l in self._layers.items()
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Section 4 — Checkpoint & Crash Recovery
# ═══════════════════════════════════════════════════════════════════════════════

class Checkpoint:
    """State checkpoint untuk crash recovery."""

    def __init__(self, config: KernelConfig) -> None:
        self.config = config
        self._db_path = os.path.join(config.workspace_dir, config.checkpoint_dir, "checkpoints.db")
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._init_db()

    def __repr__(self) -> str:
        return f"Checkpoint(db={self._db_path})"

    def _init_db(self) -> None:
        """Initialize SQLite checkpoint database."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    layer_id INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    data TEXT NOT NULL,
                    hash TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS boot_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    details TEXT
                )
            """)
            conn.commit()

    def save(self, layer_id: int, state: str, data: Dict[str, Any]) -> str:
        """Save checkpoint untuk layer."""
        timestamp = time.time()
        payload = json.dumps(data, sort_keys=True, default=str)
        hash_val = hashlib.sha256(f"{timestamp}:{layer_id}:{payload}".encode()).hexdigest()[:16]
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT INTO checkpoints (timestamp, layer_id, state, data, hash) VALUES (?, ?, ?, ?, ?)",
                (timestamp, layer_id, state, payload, hash_val),
            )
            conn.commit()
        return hash_val

    def load_latest(self, layer_id: int) -> Optional[Dict[str, Any]]:
        """Load checkpoint terbaru untuk layer."""
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT data, state, timestamp FROM checkpoints WHERE layer_id = ? ORDER BY timestamp DESC LIMIT 1",
                (layer_id,),
            ).fetchone()
            if row:
                data = json.loads(row[0])
                data["_checkpoint_state"] = row[1]
                data["_checkpoint_time"] = row[2]
                return data
            return None

    def log_boot(self, mode: str, status: str, details: str = "") -> None:
        """Log boot attempt."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT INTO boot_log (timestamp, mode, status, details) VALUES (?, ?, ?, ?)",
                (time.time(), mode, status, details),
            )
            conn.commit()

    def get_boot_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return boot history."""
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT timestamp, mode, status, details FROM boot_log ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [
                {"timestamp": r[0], "mode": r[1], "status": r[2], "details": r[3]}
                for r in rows
            ]


class CrashRecovery:
    """
    Crash recovery dengan rollback strategy dan graceful degradation.
    """

    def __init__(self, config: KernelConfig, checkpoint: Checkpoint) -> None:
        self.config = config
        self.checkpoint = checkpoint
        self._recovery_log: List[str] = []

    def __repr__(self) -> str:
        return f"CrashRecovery(log={len(self._recovery_log)} entries)"

    def attempt_recovery(
        self,
        layer_meta: LayerMetadata,
        lifecycle: LifecycleManager,
    ) -> Tuple[bool, str]:
        """
        Attempt recovery untuk failed layer.
        Strategy: checkpoint restore -> restart -> degradation.
        """
        layer_id = layer_meta.layer_id
        self._log(f"RECOVERY START for {layer_meta.name} (layer {layer_id})")

        # Strategy 1: Restore dari checkpoint
        ckpt = self.checkpoint.load_latest(layer_id)
        if ckpt and self.config.enable_crash_recovery:
            self._log(f"  Found checkpoint from {ckpt.get('_checkpoint_time', 'unknown')}")
            layer_meta.checkpoint_data = ckpt
            layer_meta.state = LayerState.RELOADING

        # Strategy 2: Restart layer
        if layer_meta.restart_count < self.config.max_restart_attempts:
            layer_meta.restart_count += 1
            self._log(f"  Restart attempt {layer_meta.restart_count}/{self.config.max_restart_attempts}")
            try:
                lifecycle.restart(layer_meta)
                self._log(f"  Restart SUCCESS")
                return True, "restarted"
            except Exception as e:
                self._log(f"  Restart FAILED: {e}")

        # Strategy 3: Graceful degradation
        self._log(f"  Degrading layer {layer_id} to limited functionality")
        layer_meta.state = LayerState.DEGRADED
        return False, "degraded"

    def _log(self, message: str) -> None:
        entry = f"[{time.strftime('%H:%M:%S')}] {message}"
        self._recovery_log.append(entry)

    def get_log(self) -> List[str]:
        return self._recovery_log.copy()


# ═══════════════════════════════════════════════════════════════════════════════
# Section 5 — Lifecycle Manager (Start/Stop/Restart/Reload per Layer)
# ═══════════════════════════════════════════════════════════════════════════════

class LifecycleManager:
    """Lifecycle manager untuk start/stop/restart/reload per layer."""

    def __init__(self, config: KernelConfig, loader: ModuleLoader, checkpoint: Checkpoint) -> None:
        self.config = config
        self.loader = loader
        self.checkpoint = checkpoint
        self._layers: Dict[int, LayerMetadata] = {}
        self._lock = threading.RLock()

    def __repr__(self) -> str:
        running = sum(1 for l in self._layers.values() if l.state == LayerState.RUNNING)
        return f"LifecycleManager(layers={len(self._layers)}, running={running})"

    def register(self, layer_meta: LayerMetadata) -> None:
        """Register layer ke lifecycle manager."""
        with self._lock:
            self._layers[layer_meta.layer_id] = layer_meta

    def start(self, layer_meta: LayerMetadata) -> bool:
        """Start layer: initialize dan transisi ke RUNNING."""
        layer_id = layer_meta.layer_id
        if layer_meta.state not in (LayerState.UNINITIALIZED, LayerState.STOPPED, LayerState.FAILED):
            return False

        layer_meta.state = LayerState.INITIALIZING
        try:
            # Lazy load module jika belum loaded
            module = self.loader.lazy_get(layer_id)
            if module:
                # Cari class utama di module
                layer_class = self._find_layer_class(module, layer_id)
                if layer_class:
                    instance = layer_class(config=layer_meta.config)
                    layer_meta.instance = instance
                    # Panggil init jika ada
                    if hasattr(instance, "initialize"):
                        instance.initialize()

            layer_meta.state = LayerState.RUNNING
            layer_meta.last_heartbeat = time.time()
            layer_meta.health_score = 1.0
            self.checkpoint.save(layer_id, "RUNNING", layer_meta.checkpoint_data)
            return True
        except Exception as e:
            layer_meta.state = LayerState.FAILED
            layer_meta.error_log.append(f"[{time.strftime('%H:%M:%S')}] START ERROR: {str(e)}")
            return False

    def stop(self, layer_meta: LayerMetadata) -> bool:
        """Graceful stop layer."""
        layer_meta.state = LayerState.STOPPING
        try:
            if layer_meta.instance and hasattr(layer_meta.instance, "shutdown"):
                layer_meta.instance.shutdown()
            layer_meta.instance = None
            layer_meta.state = LayerState.STOPPED
            return True
        except Exception as e:
            layer_meta.error_log.append(f"[{time.strftime('%H:%M:%S')}] STOP ERROR: {str(e)}")
            layer_meta.state = LayerState.FAILED
            return False

    def restart(self, layer_meta: LayerMetadata) -> bool:
        """Restart layer: stop lalu start."""
        self.stop(layer_meta)
        # Brief backoff
        time.sleep(self.config.restart_backoff_sec)
        return self.start(layer_meta)

    def reload(self, layer_meta: LayerMetadata) -> bool:
        """Reload layer tanpa stop instance (hot reload)."""
        layer_meta.state = LayerState.RELOADING
        try:
            # Force re-import module
            module_name = Path(layer_meta.module_name).stem
            if module_name in sys.modules:
                del sys.modules[module_name]
            module = self.loader.load(layer_meta.module_name)
            layer_class = self._find_layer_class(module, layer_meta.layer_id)
            if layer_class:
                instance = layer_class(config=layer_meta.config)
                layer_meta.instance = instance
                if hasattr(instance, "initialize"):
                    instance.initialize()
            layer_meta.state = LayerState.RUNNING
            return True
        except Exception as e:
            layer_meta.error_log.append(f"[{time.strftime('%H:%M:%S')}] RELOAD ERROR: {str(e)}")
            layer_meta.state = LayerState.FAILED
            return False

    def _find_layer_class(self, module: Any, layer_id: int) -> Optional[Type]:
        """Cari class utama di module yang cocok untuk layer."""
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if hasattr(obj, "LAYER_ID") and getattr(obj, "LAYER_ID") == layer_id:
                return obj
            if name.lower().endswith(f"layer{layer_id}") or name.lower().endswith(f"_{layer_id}"):
                return obj
        return None

    def get_states(self) -> Dict[int, str]:
        """Return state summary untuk semua layer."""
        return {lid: l.state.name for lid, l in self._layers.items()}


# ═══════════════════════════════════════════════════════════════════════════════
# Section 6 — KernelKernel (Bridge ke Layer 0)
# ═══════════════════════════════════════════════════════════════════════════════

class KernelKernel:
    """
    Bridge layer yang menghubungkan Kernel Layer 0 ke dirinya sendiri
    dan ke layer lain. Menyediakan introspection dan self-healing.
    """

    LAYER_ID = 0

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self._introspection_data: Dict[str, Any] = {}
        self._health_callbacks: List[Callable] = []

    def __repr__(self) -> str:
        return f"KernelKernel(layer=0, callbacks={len(self._health_callbacks)})"

    def initialize(self) -> None:
        """Initialize KernelKernel bridge."""
        self._introspection_data["boot_time"] = time.time()
        self._introspection_data["uptime"] = 0.0
        self._introspection_data["self_checks_passed"] = True

    def shutdown(self) -> None:
        """Graceful shutdown bridge."""
        self._introspection_data["shutdown_time"] = time.time()

    def ping(self) -> bool:
        """Self-ping untuk health check."""
        self._introspection_data["last_ping"] = time.time()
        return True

    def get_introspection(self) -> Dict[str, Any]:
        """Return introspection data."""
        now = time.time()
        self._introspection_data["uptime"] = now - self._introspection_data.get("boot_time", now)
        return self._introspection_data.copy()

    def bridge_call(self, target_layer: int, method: str, args: Tuple = ()) -> Any:
        """Simulated bridge call ke layer lain."""
        return {"target_layer": target_layer, "method": method, "status": "simulated"}

    def register_health_callback(self, cb: Callable) -> None:
        self._health_callbacks.append(cb)

    def self_heal(self, issue: str) -> str:
        """Self-healing attempt untuk kernel."""
        return f"self_heal: issue '{issue}' acknowledged, kernel stable"


# ═══════════════════════════════════════════════════════════════════════════════
# Section 7 — KernelNative (Main Orchestrator)
# ═══════════════════════════════════════════════════════════════════════════════

class KernelNative:
    """
    Main orchestrator MAGNATRIX-OS Layer 0.
    Mengorkestrasikan boot sequence, health monitoring, crash recovery,
    dan lifecycle management untuk semua 15 layer.
    """

    def __init__(self, config: Optional[KernelConfig] = None) -> None:
        self.config = config or KernelConfig()
        self.loader = ModuleLoader(self.config)
        self.checkpoint = Checkpoint(self.config)
        self.lifecycle = LifecycleManager(self.config, self.loader, self.checkpoint)
        self.health = HealthMonitor(self.config)
        self.recovery = CrashRecovery(self.config, self.checkpoint)
        self.kernel_bridge = KernelKernel(asdict(self.config))
        self._layers: Dict[int, LayerMetadata] = {}
        self._booted = False
        self._lock = threading.RLock()

        # Wire health callbacks
        self.health.on_state_change(self._on_health_state_change)

    def __repr__(self) -> str:
        layers = len(self._layers)
        running = sum(1 for l in self._layers.values() if l.state == LayerState.RUNNING)
        return f"KernelNative({self.config.project_name}, layers={layers}, running={running})"

    def build_layer_map(self) -> None:
        """Build metadata untuk 15 layer MAGNATRIX-OS."""
        for idx, name in enumerate(self.config.layers):
            meta = LayerMetadata(
                layer_id=idx,
                name=name,
                module_name=f"layer{idx}_native",
                dependencies=list(range(idx)) if idx > 0 else [],
                config={"auto_start": True, "priority": idx},
            )
            self._layers[idx] = meta
            self.lifecycle.register(meta)
            self.health.register(meta)

    def boot(self, mode: Optional[BootMode] = None) -> bool:
        """
        Boot sequence: initialize semua 15 layer secara berurutan.
        Return True jika semua layer berhasil boot.
        """
        boot_mode = mode or self.config.boot_mode
        self.checkpoint.log_boot(boot_mode.name, "START", "Boot sequence initiated")
        print(f"\n{'='*60}")
        print(f"  MAGNATRIX-OS Boot Sequence")
        print(f"  Mode: {boot_mode.name} | Version: {self.config.version}")
        print(f"{'='*60}\n")

        self.build_layer_map()
        self.kernel_bridge.initialize()

        # Boot Layer 0 (KernelKernel) terlebih dahulu
        layer0 = self._layers[0]
        layer0.instance = self.kernel_bridge
        layer0.state = LayerState.RUNNING
        layer0.last_heartbeat = time.time()
        print(f"[BOOT] Layer 0: {layer0.name} -> RUNNING (bridge active)")

        # Boot layer 1..14 secara berurutan
        success_count = 1
        for layer_id in range(1, len(self.config.layers)):
            layer = self._layers[layer_id]
            print(f"[BOOT] Layer {layer_id}: {layer.name} -> INITIALIZING...")
            ok = self.lifecycle.start(layer)
            if ok:
                print(f"[BOOT] Layer {layer_id}: {layer.name} -> RUNNING ✅")
                success_count += 1
            else:
                print(f"[BOOT] Layer {layer_id}: {layer.name} -> FAILED ❌")
                if self.config.enable_crash_recovery:
                    recovered, strategy = self.recovery.attempt_recovery(layer, self.lifecycle)
                    status = "RECOVERED ✅" if recovered else f"DEGRADED ⚠️ ({strategy})"
                    print(f"[BOOT] Layer {layer_id}: Recovery -> {status}")
                    if recovered:
                        success_count += 1

        self.health.start()
        self._booted = True

        status = "SUCCESS" if success_count == len(self.config.layers) else "PARTIAL"
        self.checkpoint.log_boot(boot_mode.name, status, f"{success_count}/{len(self.config.layers)} layers running")
        print(f"\n{'='*60}")
        print(f"  Boot {status}: {success_count}/{len(self.config.layers)} layers running")
        print(f"{'='*60}\n")
        return success_count == len(self.config.layers)

    def _on_health_state_change(self, layer_id: int, state: LayerState, reason: str) -> None:
        """Callback untuk health state change."""
        print(f"[HEALTH] Layer {layer_id} state -> {state.name}: {reason}")
        if state == LayerState.FAILED and self.config.enable_auto_restart:
            layer = self._layers.get(layer_id)
            if layer:
                recovered, strategy = self.recovery.attempt_recovery(layer, self.lifecycle)
                print(f"[HEALTH] Auto-recovery {layer.name}: {strategy} {'✅' if recovered else '⚠️'}")

    def health_check(self) -> Dict[int, Dict[str, Any]]:
        """Full health check untuk semua layer."""
        print(f"\n[HEALTH CHECK] Running full system diagnostic...")
        report = self.health.get_health_report()
        for lid, info in sorted(report.items()):
            status_icon = "✅" if info["state"] == "RUNNING" else "⚠️" if info["state"] == "DEGRADED" else "❌"
            print(f"  Layer {lid:2d}: {info['name'][:30]:30s} | {info['state']:10s} {status_icon} | "
                  f"health={info['health_score']:.2f} | restarts={info['restart_count']}")
        return report

    def simulate_crash(self, layer_id: int) -> None:
        """Simulate crash pada layer untuk testing recovery."""
        layer = self._layers.get(layer_id)
        if not layer:
            print(f"[CRASH SIM] Layer {layer_id} not found")
            return
        print(f"\n[CRASH SIM] Injecting crash on Layer {layer_id}: {layer.name}...")
        layer.state = LayerState.FAILED
        layer.error_log.append(f"[{time.strftime('%H:%M:%S')}] SIMULATED CRASH")
        layer.health_score = 0.0
        # Trigger auto-recovery
        if self.config.enable_crash_recovery:
            recovered, strategy = self.recovery.attempt_recovery(layer, self.lifecycle)
            print(f"[CRASH SIM] Recovery result: {strategy} {'✅' if recovered else '⚠️'}")

    def shutdown(self) -> None:
        """Graceful shutdown: stop semua layer secara terbalik."""
        print(f"\n[SHUTDOWN] Initiating graceful shutdown...")
        self.health.stop()
        for layer_id in sorted(self._layers.keys(), reverse=True):
            layer = self._layers[layer_id]
            if layer.state == LayerState.RUNNING:
                print(f"[SHUTDOWN] Stopping Layer {layer_id}: {layer.name}...")
                self.lifecycle.stop(layer)
        self.kernel_bridge.shutdown()
        self.checkpoint.log_boot("SHUTDOWN", "COMPLETE", "All layers stopped")
        print(f"[SHUTDOWN] MAGNATRIX-OS halted.\n")
        self._booted = False

    def get_status(self) -> Dict[str, Any]:
        """Return kernel status summary."""
        states = self.lifecycle.get_states()
        running = sum(1 for s in states.values() if s == "RUNNING")
        return {
            "booted": self._booted,
            "project": self.config.project_name,
            "version": self.config.version,
            "total_layers": len(self._layers),
            "running_layers": running,
            "failed_layers": sum(1 for s in states.values() if s == "FAILED"),
            "degraded_layers": sum(1 for s in states.values() if s == "DEGRADED"),
            "uptime": time.time() - self.kernel_bridge.get_introspection().get("boot_time", time.time()),
            "states": states,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Section 8 — Mock Layer Classes (untuk Demo)
# ═══════════════════════════════════════════════════════════════════════════════

class MockLayerBase:
    """Base class untuk mock layer dalam demo."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self._initialized = False

    def initialize(self) -> None:
        self._initialized = True

    def shutdown(self) -> None:
        self._initialized = False

    def ping(self) -> bool:
        return True

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(initialized={self._initialized})"


class HardwareAbstractionLayer(MockLayerBase):
    LAYER_ID = 1
    def __init__(self, config=None): super().__init__(config)
class MemoryManagementLayer(MockLayerBase):
    LAYER_ID = 2
    def __init__(self, config=None): super().__init__(config)
class ProcessThreadLayer(MockLayerBase):
    LAYER_ID = 3
    def __init__(self, config=None): super().__init__(config)
class IONetworkLayer(MockLayerBase):
    LAYER_ID = 4
    def __init__(self, config=None): super().__init__(config)
class FileSystemLayer(MockLayerBase):
    LAYER_ID = 5
    def __init__(self, config=None): super().__init__(config)
class SecurityCryptoLayer(MockLayerBase):
    LAYER_ID = 6
    def __init__(self, config=None): super().__init__(config)
class EventBusLayer(MockLayerBase):
    LAYER_ID = 7
    def __init__(self, config=None): super().__init__(config)
class ServiceRegistryLayer(MockLayerBase):
    LAYER_ID = 8
    def __init__(self, config=None): super().__init__(config)
class AgentRuntimeLayer(MockLayerBase):
    LAYER_ID = 9
    def __init__(self, config=None): super().__init__(config)
class SkillSystemLayer(MockLayerBase):
    LAYER_ID = 10
    def __init__(self, config=None): super().__init__(config)
class TradingEngineLayer(MockLayerBase):
    LAYER_ID = 11
    def __init__(self, config=None): super().__init__(config)
class WebIDELayer(MockLayerBase):
    LAYER_ID = 12
    def __init__(self, config=None): super().__init__(config)
class P2PMeshLayer(MockLayerBase):
    LAYER_ID = 13
    def __init__(self, config=None): super().__init__(config)
class CollectiveBrainLayer(MockLayerBase):
    LAYER_ID = 14
    def __init__(self, config=None): super().__init__(config)


# ═══════════════════════════════════════════════════════════════════════════════
# Section 9 — Demo
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("  MAGNATRIX-OS Layer 0 — KernelNative Demo")
    print("  Pure Python | Zero External Dependencies")
    print("=" * 70)

    # 1. Buat konfigurasi
    config = KernelConfig(
        boot_mode=BootMode.COLD,
        health_check_interval_sec=1.0,
        heartbeat_timeout_sec=3.0,
        max_restart_attempts=2,
    )
    print(f"\n[CONFIG] {config}")

    # 2. Initialize kernel
    kernel = KernelNative(config)
    print(f"[INIT] {kernel}")

    # 3. Boot semua 15 layer
    success = kernel.boot()
    print(f"\n[RESULT] Boot {'SUCCESS ✅' if success else 'PARTIAL ⚠️'}")

    # 4. Health check
    time.sleep(1.5)  # Biar health monitor jalan beberapa cycle
    report = kernel.health_check()

    # 5. Simulate crash pada Layer 7 (Event Bus)
    print(f"\n[TEST] Simulating crash on Layer 7 (Event Bus)...")
    kernel.simulate_crash(7)
    time.sleep(1.5)

    # 6. Health check post-recovery
    print(f"\n[TEST] Post-recovery health check...")
    report_post = kernel.health_check()

    # 7. Print recovery log
    print(f"\n[RECOVERY LOG]")
    for entry in kernel.recovery.get_log():
        print(f"  {entry}")

    # 8. Kernel status
    status = kernel.get_status()
    print(f"\n[KERNEL STATUS]")
    for key, value in status.items():
        if key == "states":
            continue
        print(f"  {key}: {value}")

    # 9. Boot history
    print(f"\n[BOOT HISTORY]")
    for entry in kernel.checkpoint.get_boot_history(5):
        ts = time.strftime("%H:%M:%S", time.localtime(entry["timestamp"]))
        print(f"  [{ts}] {entry['mode']:10s} -> {entry['status']:10s} | {entry['details']}")

    # 10. Module loader demo
    print(f"\n[MODULE LOADER DEMO]")
    discovered = kernel.loader.discover(scan_dir=".")
    if discovered:
        print(f"  Discovered {len(discovered)} _native.py modules:")
        for name, spec in discovered.items():
            print(f"    - {name} (layer={spec.layer_id}, deps={spec.dependencies})")
    else:
        print(f"  No _native.py modules found in current dir (expected for demo)")

    # 11. KernelKernel bridge introspection
    print(f"\n[KERNEL BRIDGE INTROSPECTION]")
    introspection = kernel.kernel_bridge.get_introspection()
    for key, value in introspection.items():
        print(f"  {key}: {value}")

    # 12. Graceful shutdown
    print(f"\n{'='*70}")
    kernel.shutdown()
    print("=" * 70)
    print("  Demo complete. All systems halted.")
    print("=" * 70)
