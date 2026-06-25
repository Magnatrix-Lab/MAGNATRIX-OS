#!/usr/bin/env python3
"""
State Persistence & Serialization Engine for MAGNATRIX-OS
Auto-save/load module state, snapshot versioning, crash recovery, migration.
Pure stdlib — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


@dataclass
class StateSnapshot:
    """A point-in-time snapshot of system state."""
    id: str
    timestamp: float
    version: str
    modules: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MigrationStep:
    """A single migration from one version to another."""
    from_version: str
    to_version: str
    transformer: Callable[[Dict[str, Any]], Dict[str, Any]]
    description: str = ""


class Serializer:
    """Multi-format serializer with fallback."""

    @staticmethod
    def to_json(data: Any, indent: int = 2) -> str:
        """Serialize to JSON with custom encoder for common types."""
        class _Encoder(json.JSONEncoder):
            def default(self, obj: Any) -> Any:
                if hasattr(obj, "__dict__"):
                    return obj.__dict__
                if hasattr(obj, "value"):
                    return obj.value
                if isinstance(obj, set):
                    return list(obj)
                if isinstance(obj, bytes):
                    return {"__type__": "bytes", "data": obj.decode("utf-8", errors="replace")}
                return str(obj)
        return json.dumps(data, cls=_Encoder, indent=indent, ensure_ascii=False)

    @staticmethod
    def from_json(text: str) -> Any:
        """Deserialize from JSON."""
        def _decoder(obj: Dict[str, Any]) -> Any:
            if "__type__" in obj and obj["__type__"] == "bytes":
                return obj.get("data", "").encode("utf-8", errors="replace")
            return obj
        return json.loads(text, object_hook=_decoder)

    @staticmethod
    def to_bytes(data: Any) -> bytes:
        return Serializer.to_json(data).encode("utf-8")

    @staticmethod
    def from_bytes(data: bytes) -> Any:
        return Serializer.from_json(data.decode("utf-8"))


class CheckpointManager:
    """Manages periodic checkpoints and snapshots."""

    def __init__(self, store_dir: str, max_snapshots: int = 10) -> None:
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.max_snapshots = max_snapshots
        self._lock = threading.RLock()
        self._snapshots: List[StateSnapshot] = []
        self._current_version = "1.0.0"

    def save(self, modules: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> str:
        """Save current state as a new snapshot."""
        with self._lock:
            snap_id = f"snap_{int(time.time() * 1000)}"
            snapshot = StateSnapshot(
                id=snap_id,
                timestamp=time.time(),
                version=self._current_version,
                modules=copy.deepcopy(modules),
                metadata=metadata or {},
            )
            # Save to disk
            path = self.store_dir / f"{snap_id}.json"
            path.write_text(Serializer.to_json(asdict(snapshot)), encoding="utf-8")
            self._snapshots.append(snapshot)
            # Prune old snapshots
            self._prune()
            return snap_id

    def load(self, snap_id: Optional[str] = None) -> Optional[StateSnapshot]:
        """Load a snapshot by ID, or latest if none specified."""
        with self._lock:
            if snap_id:
                path = self.store_dir / f"{snap_id}.json"
                if path.exists():
                    data = Serializer.from_json(path.read_text(encoding="utf-8"))
                    return StateSnapshot(**data)
                # Check memory cache
                for s in self._snapshots:
                    if s.id == snap_id:
                        return s
            elif self._snapshots:
                return self._snapshots[-1]
            # Try loading from disk
            files = sorted(self.store_dir.glob("snap_*.json"), key=lambda p: p.stat().st_mtime)
            if files:
                data = Serializer.from_json(files[-1].read_text(encoding="utf-8"))
                return StateSnapshot(**data)
            return None

    def list_snapshots(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [{"id": s.id, "timestamp": s.timestamp, "version": s.version} for s in self._snapshots]

    def delete(self, snap_id: str) -> bool:
        with self._lock:
            path = self.store_dir / f"{snap_id}.json"
            if path.exists():
                path.unlink()
            self._snapshots = [s for s in self._snapshots if s.id != snap_id]
            return True

    def _prune(self) -> None:
        if len(self._snapshots) > self.max_snapshots:
            to_remove = self._snapshots[:-self.max_snapshots]
            self._snapshots = self._snapshots[-self.max_snapshots:]
            for s in to_remove:
                path = self.store_dir / f"{s.id}.json"
                if path.exists():
                    path.unlink()

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total_size = sum((self.store_dir / f"{s.id}.json").stat().st_size for s in self._snapshots if (self.store_dir / f"{s.id}.json").exists())
            return {
                "snapshots": len(self._snapshots),
                "max_snapshots": self.max_snapshots,
                "store_dir": str(self.store_dir),
                "total_size_bytes": total_size,
            }


class MigrationEngine:
    """Handle state migration between versions."""

    def __init__(self) -> None:
        self._migrations: List[MigrationStep] = []
        self._lock = threading.Lock()

    def register(self, step: MigrationStep) -> None:
        with self._lock:
            self._migrations.append(step)
            self._migrations.sort(key=lambda m: m.from_version)

    def migrate(self, state: Dict[str, Any], from_version: str, to_version: str) -> Dict[str, Any]:
        """Migrate state from one version to another."""
        current = from_version
        current_state = copy.deepcopy(state)
        applied = []

        while current != to_version:
            # Find next applicable migration
            found = False
            for step in self._migrations:
                if step.from_version == current:
                    try:
                        current_state = step.transformer(current_state)
                        current = step.to_version
                        applied.append(f"{step.from_version} -> {step.to_version}")
                        found = True
                        break
                    except Exception as e:
                        raise RuntimeError(f"Migration failed at {step.from_version} -> {step.to_version}: {e}")
            if not found:
                raise RuntimeError(f"No migration path from {current} to {to_version}")

        current_state["__migrated__"] = True
        current_state["__migration_path__"] = applied
        return current_state

    def get_path(self, from_version: str, to_version: str) -> List[str]:
        """Get migration path without applying."""
        current = from_version
        path = []
        visited = set()
        while current != to_version:
            if current in visited:
                return []
            visited.add(current)
            for step in self._migrations:
                if step.from_version == current:
                    path.append(f"{step.from_version} -> {step.to_version}")
                    current = step.to_version
                    break
            else:
                return []
        return path


class StatePersistenceEngine:
    """Main engine for persisting and restoring all module state."""

    def __init__(self, repo_root: str, auto_save_interval: int = 60) -> None:
        self.root = Path(repo_root).resolve()
        self.store_dir = self.root / "data" / "state"
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint = CheckpointManager(str(self.store_dir))
        self.migration = MigrationEngine()
        self._module_serializers: Dict[str, Callable[[], Any]] = {}
        self._module_deserializers: Dict[str, Callable[[Any], None]] = {}
        self._auto_save_interval = auto_save_interval
        self._auto_save_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.RLock()

    def register_module(self, name: str, serializer: Callable[[], Any], deserializer: Callable[[Any], None]) -> None:
        """Register a module's state save/restore functions."""
        with self._lock:
            self._module_serializers[name] = serializer
            self._module_deserializers[name] = deserializer

    def snapshot(self) -> str:
        """Take a snapshot of all registered modules."""
        with self._lock:
            modules = {}
            for name, serializer in self._module_serializers.items():
                try:
                    modules[name] = serializer()
                except Exception as e:
                    modules[name] = {"__error__": str(e)}
            return self.checkpoint.save(modules)

    def restore(self, snap_id: Optional[str] = None) -> Dict[str, Any]:
        """Restore all modules from a snapshot."""
        snapshot = self.checkpoint.load(snap_id)
        if not snapshot:
            return {"success": False, "error": "No snapshot found"}

        # Check version migration
        state = snapshot.modules
        if snapshot.version != self.checkpoint._current_version and "__migrated__" not in state:
            try:
                state = self.migration.migrate(state, snapshot.version, self.checkpoint._current_version)
            except Exception as e:
                return {"success": False, "error": f"Migration failed: {e}"}

        results = {}
        with self._lock:
            for name, data in state.items():
                if name.startswith("__"):
                    continue
                deserializer = self._module_deserializers.get(name)
                if deserializer:
                    try:
                        deserializer(data)
                        results[name] = "restored"
                    except Exception as e:
                        results[name] = f"error: {e}"
                else:
                    results[name] = "no deserializer"

        return {"success": True, "restored": results, "snapshot_id": snapshot.id}

    def auto_save_start(self) -> None:
        """Start background auto-save thread."""
        self._running = True
        def _loop():
            while self._running:
                time.sleep(self._auto_save_interval)
                if self._running:
                    try:
                        snap_id = self.snapshot()
                        print(f"[StateEngine] Auto-saved snapshot: {snap_id}")
                    except Exception as e:
                        print(f"[StateEngine] Auto-save failed: {e}")
        self._auto_save_thread = threading.Thread(target=_loop, daemon=True, name="StateAutoSave")
        self._auto_save_thread.start()

    def auto_save_stop(self) -> None:
        self._running = False

    def crash_recovery(self) -> Dict[str, Any]:
        """Attempt to recover from last snapshot after crash."""
        snapshot = self.checkpoint.load()
        if not snapshot:
            return {"success": False, "error": "No snapshot available for recovery"}
        return self.restore(snapshot.id)

    def list_snapshots(self) -> List[Dict[str, Any]]:
        return self.checkpoint.list_snapshots()

    def delete_snapshot(self, snap_id: str) -> bool:
        return self.checkpoint.delete(snap_id)

    def stats(self) -> Dict[str, Any]:
        return {
            "checkpoint": self.checkpoint.stats(),
            "registered_modules": len(self._module_serializers),
            "auto_save_interval": self._auto_save_interval,
            "auto_save_running": self._running,
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== State Persistence & Serialization Engine Demo ===\n")
    engine = StatePersistenceEngine(repo_root="/tmp/magnatrix_state_demo")

    # Register some mock modules
    module_a_state = {"counter": 0, "items": ["a", "b"]}
    module_b_state = {"config": {"key": "value"}}

    engine.register_module("module_a", lambda: module_a_state, lambda data: module_a_state.update(data))
    engine.register_module("module_b", lambda: module_b_state, lambda data: module_b_state.update(data))

    # Take snapshot
    print("Taking snapshot...")
    snap_id = engine.snapshot()
    print(f"Snapshot ID: {snap_id}")
    print(f"Stats: {engine.stats()}")
    print(f"Snapshots: {engine.list_snapshots()}")

    # Modify state
    module_a_state["counter"] = 42
    print(f"\nModified state: {module_a_state}")

    # Restore
    print("\nRestoring...")
    result = engine.restore(snap_id)
    print(f"Restore result: {result}")
    print(f"Restored state: {module_a_state}")

    # Migration demo
    print("\nMigration demo...")
    engine.migration.register(MigrationStep(
        from_version="1.0.0", to_version="2.0.0",
        transformer=lambda s: {**s, "__version__": "2.0.0", "migrated_field": True},
        description="Add migrated_field",
    ))
    migrated = engine.migration.migrate({"key": "val"}, "1.0.0", "2.0.0")
    print(f"Migrated state: {migrated}")

    print(f"\nFinal stats: {engine.stats()}")


if __name__ == "__main__":
    _demo()
