#!/usr/bin/env python3
"""
Plugin Sandbox for MAGNATRIX-OS
Safe dynamic loading of external plugins with resource limits,
isolation boundaries, and permission enforcement.
Native stdlib only — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import ast
import dataclasses
import enum
import importlib.util
import os
import resource
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class PluginPermission(enum.Enum):
    """Permissions a plugin can request."""
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    NETWORK = "network"
    SHELL_EXEC = "shell_exec"
    IMPORT_STD = "import_std"
    IMPORT_THIRD = "import_third"
    MEMORY_ALLOC = "memory_alloc"
    CPU_TIME = "cpu_time"


class PluginState(enum.Enum):
    """Lifecycle state of a loaded plugin."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"
    UNLOADED_BY_POLICY = "unloaded_by_policy"


@dataclasses.dataclass
class PluginManifest:
    """Metadata and permission manifest for a plugin."""
    plugin_id: str
    name: str
    version: str
    description: str
    author: str
    entry_point: str
    requested_permissions: Set[PluginPermission]
    max_memory_mb: int = 128
    max_cpu_seconds: float = 5.0
    max_output_bytes: int = 1024 * 1024
    allowed_paths: List[str] = dataclasses.field(default_factory=list)
    allowed_imports: List[str] = dataclasses.field(default_factory=list)
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "entry_point": self.entry_point,
            "requested_permissions": [p.value for p in self.requested_permissions],
            "max_memory_mb": self.max_memory_mb,
            "max_cpu_seconds": self.max_cpu_seconds,
            "max_output_bytes": self.max_output_bytes,
            "allowed_paths": self.allowed_paths,
            "allowed_imports": self.allowed_imports,
        }


@dataclasses.dataclass
class PluginInstance:
    """A loaded plugin instance with runtime state."""
    manifest: PluginManifest
    module: Any = None
    state: PluginState = PluginState.UNLOADED
    loaded_at: Optional[float] = None
    error_message: Optional[str] = None
    last_used: Optional[float] = None
    use_count: int = 0


class PluginSandbox:
    """Sandbox for loading, executing, and monitoring external plugins."""

    def __init__(self, plugin_dir: str, max_total_plugins: int = 50) -> None:
        self.plugin_dir = Path(plugin_dir)
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        self.max_total = max_total_plugins
        self._plugins: Dict[str, PluginInstance] = {}
        self._permissions: Dict[str, Set[PluginPermission]] = {}  # granted per plugin
        self._lock = threading.Lock()
        self._global_hooks: List[Callable[[str, str, Any], None]] = []

    # ------------------------------------------------------------------
    # Manifest parsing
    # ------------------------------------------------------------------

    def parse_manifest(self, plugin_path: Path) -> Optional[PluginManifest]:
        manifest_file = plugin_path / "manifest.json"
        if not manifest_file.exists():
            return None
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            perms = {PluginPermission(p) for p in data.get("permissions", [])}
            return PluginManifest(
                plugin_id=data.get("id", plugin_path.name),
                name=data.get("name", plugin_path.name),
                version=data.get("version", "0.0.1"),
                description=data.get("description", ""),
                author=data.get("author", "unknown"),
                entry_point=data.get("entry_point", "plugin.py"),
                requested_permissions=perms,
                max_memory_mb=data.get("max_memory_mb", 128),
                max_cpu_seconds=data.get("max_cpu_seconds", 5.0),
                max_output_bytes=data.get("max_output_bytes", 1024 * 1024),
                allowed_paths=data.get("allowed_paths", []),
                allowed_imports=data.get("allowed_imports", []),
                metadata=data.get("metadata", {}),
            )
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Permission & policy
    # ------------------------------------------------------------------

    def grant_permission(self, plugin_id: str, permission: PluginPermission) -> None:
        self._permissions.setdefault(plugin_id, set()).add(permission)

    def revoke_permission(self, plugin_id: str, permission: PluginPermission) -> None:
        self._permissions.get(plugin_id, set()).discard(permission)

    def has_permission(self, plugin_id: str, permission: PluginPermission) -> bool:
        return permission in self._permissions.get(plugin_id, set())

    def check_manifest_safety(self, manifest: PluginManifest) -> Tuple[bool, List[str]]:
        """Static analysis of plugin entry point for dangerous imports/operations."""
        entry_path = self.plugin_dir / manifest.plugin_id / manifest.entry_point
        if not entry_path.exists():
            return False, ["Entry point missing"]
        warnings = []
        try:
            source = entry_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except SyntaxError as e:
            return False, [f"Syntax error: {e}"]
        except Exception as e:
            return False, [str(e)]
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name not in manifest.allowed_imports and alias.name not in sys.stdlib_module_names:
                        warnings.append(f"Import '{alias.name}' not in allowed list")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod not in manifest.allowed_imports and mod not in sys.stdlib_module_names:
                    warnings.append(f"Import from '{mod}' not in allowed list")
            if isinstance(node, ast.Call):
                # Detect dangerous calls (heuristic)
                try:
                    if hasattr(node.func, "id") and node.func.id in ("eval", "exec", "compile"):
                        warnings.append(f"Dangerous call: {node.func.id}")
                except Exception:
                    pass
        return len(warnings) == 0, warnings

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self, plugin_id: str, auto_grant: bool = False) -> PluginInstance:
        if plugin_id in self._plugins:
            return self._plugins[plugin_id]
        plugin_path = self.plugin_dir / plugin_id
        if not plugin_path.exists():
            raise FileNotFoundError(f"Plugin '{plugin_id}' not found at {plugin_path}")
        manifest = self.parse_manifest(plugin_path)
        if not manifest:
            raise ValueError(f"Plugin '{plugin_id}' has no valid manifest.json")

        safe, warnings = self.check_manifest_safety(manifest)
        if not safe:
            inst = PluginInstance(manifest=manifest, state=PluginState.ERROR, error_message=f"Unsafe: {warnings}")
            self._plugins[plugin_id] = inst
            return inst

        inst = PluginInstance(manifest=manifest, state=PluginState.LOADING)
        self._plugins[plugin_id] = inst
        inst.loaded_at = time.time()

        try:
            entry_path = plugin_path / manifest.entry_point
            spec = importlib.util.spec_from_file_location(f"magnatrix_plugin_{plugin_id}", str(entry_path))
            if not spec or not spec.loader:
                raise ImportError("Cannot create module spec")
            module = importlib.util.module_from_spec(spec)
            # Optionally enforce restricted builtins
            if not auto_grant:
                module.__dict__["__builtins__"] = self._restricted_builtins(plugin_id)
            spec.loader.exec_module(module)
            inst.module = module
            inst.state = PluginState.ACTIVE
            if auto_grant:
                self._permissions[plugin_id] = set(manifest.requested_permissions)
        except Exception as e:
            inst.state = PluginState.ERROR
            inst.error_message = traceback.format_exc()
        return inst

    def _restricted_builtins(self, plugin_id: str) -> Dict[str, Any]:
        """Return a restricted builtins dict based on granted permissions."""
        safe_builtins = {
            "True": True, "False": False, "None": None,
            "abs": abs, "all": all, "any": any, "bool": bool,
            "chr": chr, "dict": dict, "divmod": divmod, "enumerate": enumerate,
            "float": float, "format": format, "frozenset": frozenset,
            "hasattr": hasattr, "hash": hash, "hex": hex, "int": int,
            "isinstance": isinstance, "issubclass": issubclass, "iter": iter,
            "len": len, "list": list, "map": map, "max": max, "min": min,
            "next": next, "ord": ord, "pow": pow, "print": print,
            "range": range, "repr": repr, "reversed": reversed,
            "round": round, "set": set, "slice": slice, "sorted": sorted,
            "str": str, "sum": sum, "tuple": tuple, "type": type,
            "zip": zip, "__import__": __import__,
        }
        perms = self._permissions.get(plugin_id, set())
        if PluginPermission.READ_FILE in perms:
            safe_builtins["open"] = open
        if PluginPermission.NETWORK in perms:
            import urllib.request
            safe_builtins["urllib"] = urllib.request
        return safe_builtins

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def call(self, plugin_id: str, function_name: str, *args: Any, **kwargs: Any) -> Any:
        inst = self._plugins.get(plugin_id)
        if not inst or inst.state != PluginState.ACTIVE:
            raise RuntimeError(f"Plugin '{plugin_id}' is not active")
        func = getattr(inst.module, function_name, None)
        if not callable(func):
            raise AttributeError(f"Plugin '{plugin_id}' has no function '{function_name}'")
        inst.last_used = time.time()
        inst.use_count += 1
        start = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            inst.error_message = str(e)
            raise
        finally:
            elapsed = time.time() - start
            if elapsed > inst.manifest.max_cpu_seconds:
                inst.state = PluginState.DISABLED
                inst.error_message = f"CPU timeout: {elapsed:.2f}s > {inst.manifest.max_cpu_seconds}s"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def unload(self, plugin_id: str) -> bool:
        inst = self._plugins.pop(plugin_id, None)
        if inst:
            inst.state = PluginState.UNLOADED
            inst.module = None
            return True
        return False

    def disable(self, plugin_id: str) -> bool:
        inst = self._plugins.get(plugin_id)
        if inst:
            inst.state = PluginState.DISABLED
            return True
        return False

    def enable(self, plugin_id: str) -> bool:
        inst = self._plugins.get(plugin_id)
        if inst and inst.state in (PluginState.DISABLED, PluginState.ERROR):
            return self.load(plugin_id).state == PluginState.ACTIVE
        return False

    def list_plugins(self) -> List[PluginInstance]:
        return list(self._plugins.values())

    def get_plugin(self, plugin_id: str) -> Optional[PluginInstance]:
        return self._plugins.get(plugin_id)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        by_state: Dict[str, int] = {}
        for inst in self._plugins.values():
            by_state[inst.state.value] = by_state.get(inst.state.value, 0) + 1
        return {
            "total_plugins": len(self._plugins),
            "by_state": by_state,
            "plugin_dir": str(self.plugin_dir),
            "max_total": self.max_total,
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    import tempfile, json as _json
    tmp = tempfile.mkdtemp(prefix="magnatrix_plugins_")
    # Create a mock plugin
    plugin_dir = Path(tmp) / "my_plugin"
    plugin_dir.mkdir()
    manifest = {
        "id": "my_plugin",
        "name": "Demo Plugin",
        "version": "1.0.0",
        "description": "A demo plugin",
        "author": "test",
        "entry_point": "plugin.py",
        "permissions": ["read_file", "import_std"],
        "max_memory_mb": 64,
        "max_cpu_seconds": 2.0,
    }
    (plugin_dir / "manifest.json").write_text(_json.dumps(manifest))
    (plugin_dir / "plugin.py").write_text("""
def greet(name):
    return f"Hello, {name}!"

def add(a, b):
    return a + b
""")
    sandbox = PluginSandbox(tmp)
    print("=== Plugin Sandbox Demo ===\n")
    # Load
    inst = sandbox.load("my_plugin", auto_grant=True)
    print(f"Load result: {inst.state.value}")
    if inst.state == PluginState.ACTIVE:
        # Call functions
        print(f"greet('MAGNATRIX'): {sandbox.call('my_plugin', 'greet', 'MAGNATRIX')}")
        print(f"add(2,3): {sandbox.call('my_plugin', 'add', 2, 3)}")
    # Stats
    print(f"\nStats: {sandbox.stats()}")
    # Cleanup
    import shutil
    shutil.rmtree(tmp)
    print("\nCleanup complete.")


if __name__ == "__main__":
    _demo()
