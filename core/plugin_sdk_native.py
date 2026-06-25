#!/usr/bin/env python3
"""
Plugin SDK + Extension API for MAGNATRIX-OS
Documented hook registry, manifest format, sandboxed execution, hot-plug/unplug.
Pure stdlib — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import sys
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


@dataclass
class PluginManifest:
    """Plugin manifest defining metadata and capabilities."""
    name: str
    version: str
    description: str = ""
    author: str = ""
    license: str = "MIT"
    entry_point: str = "plugin.py"
    hooks: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    min_os_version: str = "1.0.0"
    max_os_version: str = ""
    permissions: List[str] = field(default_factory=list)
    sandboxed: bool = True


@dataclass
class PluginInstance:
    """A loaded plugin instance."""
    manifest: PluginManifest
    path: str
    module: Any = None
    instance: Any = None
    state: str = "registered"  # registered, loaded, active, error, disabled
    error: Optional[str] = None
    load_time_ms: float = 0.0


class HookRegistry:
    """Central registry for plugin hooks."""

    def __init__(self) -> None:
        self._hooks: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()

    def register(self, hook_name: str, callback: Callable) -> None:
        with self._lock:
            self._hooks.setdefault(hook_name, []).append(callback)

    def unregister(self, hook_name: str, callback: Callable) -> None:
        with self._lock:
            if hook_name in self._hooks:
                self._hooks[hook_name] = [c for c in self._hooks[hook_name] if c != callback]

    def invoke(self, hook_name: str, *args: Any, **kwargs: Any) -> List[Any]:
        """Invoke all callbacks for a hook, return results."""
        with self._lock:
            callbacks = list(self._hooks.get(hook_name, []))
        results = []
        for cb in callbacks:
            try:
                result = cb(*args, **kwargs)
                results.append({"callback": cb.__name__, "result": result, "error": None})
            except Exception as e:
                results.append({"callback": cb.__name__, "result": None, "error": str(e)})
        return results

    def list_hooks(self) -> List[str]:
        with self._lock:
            return sorted(self._hooks.keys())

    def get_subscribers(self, hook_name: str) -> int:
        with self._lock:
            return len(self._hooks.get(hook_name, []))


class Sandbox:
    """Restricted execution environment for plugins."""

    ALLOWED_BUILTINS = {
        "abs", "all", "any", "ascii", "bin", "bool", "bytearray", "bytes",
        "chr", "complex", "dict", "dir", "divmod", "enumerate", "filter",
        "float", "format", "frozenset", "hasattr", "hash", "hex", "int",
        "isinstance", "issubclass", "iter", "len", "list", "map", "max",
        "min", "next", "oct", "ord", "pow", "print", "range", "repr",
        "reversed", "round", "set", "slice", "sorted", "str", "sum",
        "tuple", "type", "vars", "zip", "__import__", "open", "input",
    }

    BLOCKED_IMPORTS = {"os", "sys", "subprocess", "socket", "urllib", "http", "ftplib", "smtplib"}

    def __init__(self, plugin_dir: str) -> None:
        self.plugin_dir = Path(plugin_dir)
        self._globals: Dict[str, Any] = {}

    def _safe_import(self, name: str, *args: Any, **kwargs: Any) -> Any:
        top = name.split(".")[0]
        if top in self.BLOCKED_IMPORTS:
            raise ImportError(f"Import of {name} is blocked in sandbox")
        return __import__(name, *args, **kwargs)

    def execute(self, code: str, locals_dict: Optional[Dict[str, Any]] = None) -> Any:
        """Execute code in sandbox."""
        safe_globals = {
            "__builtins__": {k: __builtins__[k] for k in self.ALLOWED_BUILTINS if k in __builtins__},
            "__import__": self._safe_import,
        }
        safe_globals.update(self._globals)
        exec(code, safe_globals, locals_dict or {})
        return safe_globals

    def load_module(self, module_path: str) -> Any:
        """Load a module in sandbox."""
        spec = importlib.util.spec_from_file_location("sandbox_plugin", module_path)
        if not spec or not spec.loader:
            raise ImportError(f"Cannot load module: {module_path}")
        mod = importlib.util.module_from_spec(spec)
        # Restrict builtins
        mod.__builtins__ = {k: __builtins__[k] for k in self.ALLOWED_BUILTINS if k in __builtins__}
        mod.__builtins__["__import__"] = self._safe_import
        spec.loader.exec_module(mod)
        return mod


class PluginManager:
    """Main plugin manager for MAGNATRIX-OS."""

    def __init__(self, repo_root: str) -> None:
        self.root = Path(repo_root).resolve()
        self.plugins_dir = self.root / "plugins"
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self._plugins: Dict[str, PluginInstance] = {}
        self._hooks = HookRegistry()
        self._lock = threading.RLock()
        self._scan_plugins()

    def _scan_plugins(self) -> None:
        """Scan plugins directory for manifests."""
        for plugin_dir in self.plugins_dir.iterdir():
            if plugin_dir.is_dir():
                manifest_path = plugin_dir / "manifest.json"
                if manifest_path.exists():
                    try:
                        data = json.loads(manifest_path.read_text(encoding="utf-8"))
                        manifest = PluginManifest(**data)
                        instance = PluginInstance(
                            manifest=manifest, path=str(plugin_dir), state="registered",
                        )
                        self._plugins[manifest.name] = instance
                    except Exception as e:
                        pass

    def load(self, name: str) -> bool:
        """Load a plugin by name."""
        with self._lock:
            plugin = self._plugins.get(name)
            if not plugin:
                return False
            if plugin.state == "active":
                return True
            t0 = time.time()
            try:
                entry_path = Path(plugin.path) / plugin.manifest.entry_point
                if not entry_path.exists():
                    raise FileNotFoundError(f"Entry point not found: {entry_path}")
                if plugin.manifest.sandboxed:
                    sandbox = Sandbox(plugin.path)
                    plugin.module = sandbox.load_module(str(entry_path))
                else:
                    spec = importlib.util.spec_from_file_location(name, str(entry_path))
                    plugin.module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(plugin.module)
                # Look for Plugin class or setup function
                if hasattr(plugin.module, "Plugin"):
                    plugin.instance = plugin.module.Plugin()
                    # Register hooks
                    if hasattr(plugin.instance, "register_hooks"):
                        plugin.instance.register_hooks(self._hooks)
                elif hasattr(plugin.module, "setup"):
                    plugin.module.setup(self._hooks)
                plugin.state = "active"
                plugin.load_time_ms = (time.time() - t0) * 1000
                return True
            except Exception as e:
                plugin.state = "error"
                plugin.error = str(e)
                return False

    def unload(self, name: str) -> bool:
        """Unload a plugin."""
        with self._lock:
            plugin = self._plugins.get(name)
            if not plugin or plugin.state != "active":
                return False
            try:
                if plugin.instance and hasattr(plugin.instance, "cleanup"):
                    plugin.instance.cleanup()
                plugin.instance = None
                plugin.module = None
                plugin.state = "disabled"
                return True
            except Exception as e:
                plugin.error = str(e)
                return False

    def reload(self, name: str) -> bool:
        """Hot-reload a plugin."""
        self.unload(name)
        return self.load(name)

    def enable(self, name: str) -> bool:
        return self.load(name)

    def disable(self, name: str) -> bool:
        return self.unload(name)

    def create_template(self, name: str, author: str = "") -> str:
        """Create a new plugin template."""
        plugin_dir = self.plugins_dir / name
        plugin_dir.mkdir(parents=True, exist_ok=True)
        # Manifest
        manifest = PluginManifest(
            name=name, version="1.0.0", description=f"Plugin: {name}",
            author=author, entry_point="plugin.py",
            hooks=["system.boot", "system.shutdown"],
            provides=[f"plugin.{name}"],
        )
        (plugin_dir / "manifest.json").write_text(
            json.dumps({
                "name": manifest.name, "version": manifest.version,
                "description": manifest.description, "author": manifest.author,
                "license": manifest.license, "entry_point": manifest.entry_point,
                "hooks": manifest.hooks, "provides": manifest.provides,
                "depends_on": manifest.depends_on, "sandboxed": manifest.sandboxed,
            }, indent=2), encoding="utf-8"
        )
        # Plugin code
        plugin_code = f"""# Plugin: {name}
# Author: {author}

class Plugin:
    def __init__(self):
        self.name = "{name}"

    def register_hooks(self, registry):
        registry.register("system.boot", self.on_boot)
        registry.register("system.shutdown", self.on_shutdown)

    def on_boot(self, *args, **kwargs):
        print(f"[{{self.name}}] System booted!")
        return {{"status": "ok"}}

    def on_shutdown(self, *args, **kwargs):
        print(f"[{{self.name}}] System shutting down!")
        return {{"status": "ok"}}

    def cleanup(self):
        print(f"[{{self.name}}] Cleanup complete")
"""
        (plugin_dir / "plugin.py").write_text(plugin_code, encoding="utf-8")
        return str(plugin_dir)

    def invoke_hook(self, hook_name: str, *args: Any, **kwargs: Any) -> List[Any]:
        return self._hooks.invoke(hook_name, *args, **kwargs)

    def list_plugins(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "name": p.manifest.name, "version": p.manifest.version,
                    "state": p.state, "author": p.manifest.author,
                    "hooks": p.manifest.hooks, "provides": p.manifest.provides,
                    "load_ms": round(p.load_time_ms, 1),
                    "error": p.error,
                }
                for p in self._plugins.values()
            ]

    def list_hooks(self) -> List[str]:
        return self._hooks.list_hooks()

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            states = {}
            for p in self._plugins.values():
                states[p.state] = states.get(p.state, 0) + 1
            return {
                "plugins": len(self._plugins),
                "hooks": len(self._hooks.list_hooks()),
                "states": states,
                "plugins_dir": str(self.plugins_dir),
            }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== Plugin SDK + Extension API Demo ===\n")
    manager = PluginManager(repo_root="/tmp/magnatrix_plugin_demo")

    # Create template plugin
    print("Creating template plugin 'hello_world'...")
    path = manager.create_template("hello_world", author="Demo")
    print(f"Created at: {path}")

    # Load the plugin
    print("\nLoading plugin...")
    success = manager.load("hello_world")
    print(f"Load success: {success}")

    # Invoke hook
    print("\nInvoking system.boot hook...")
    results = manager.invoke_hook("system.boot")
    for r in results:
        print(f"  Result: {r}")

    # List plugins
    print(f"\nPlugins: {manager.list_plugins()}")
    print(f"Stats: {manager.stats()}")

    # Reload (hot-reload)
    print("\nHot-reloading plugin...")
    manager.reload("hello_world")
    print("Reloaded.")

    # Unload
    print("\nUnloading plugin...")
    manager.unload("hello_world")
    print(f"Stats after unload: {manager.stats()}")

    print("\nDone.")


if __name__ == "__main__":
    _demo()
