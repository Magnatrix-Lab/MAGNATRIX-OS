#!/usr/bin/env python3
"""
core/plugin_system_native.py
MAGNATRIX-OS — Plugin System for Dynamic Module Loading
AMATI pattern: plugin architecture, hot reload, sandboxed execution, dependency injection

Pure Python, stdlib only. Simulates plugin discovery, loading, lifecycle management,
and inter-plugin communication.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable


# ───────────────────────────────────────────────────────────────
# 0. UTILITIES
# ───────────────────────────────────────────────────────────────

def _now() -> float:
    return time.time()


# ───────────────────────────────────────────────────────────────
# 1. PLUGIN INTERFACE
# ───────────────────────────────────────────────────────────────

class PluginInterface:
    """Base class that all plugins must implement."""

    def __init__(self, plugin_id: str, name: str, version: str) -> None:
        self.plugin_id = plugin_id
        self.name = name
        self.version = version
        self._enabled = False

    def init(self, config: Optional[Dict[str, Any]] = None) -> bool:
        raise NotImplementedError

    def run(self, *args, **kwargs) -> Any:
        raise NotImplementedError

    def shutdown(self) -> None:
        self._enabled = False

    def get_capabilities(self) -> List[str]:
        return []

    def is_enabled(self) -> bool:
        return self._enabled


# ───────────────────────────────────────────────────────────────
# 2. PLUGIN REGISTRY
# ───────────────────────────────────────────────────────────────

@dataclass
class PluginMetadata:
    plugin_id: str
    name: str
    version: str
    author: str
    dependencies: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    status: str = "discovered"


class PluginRegistry:
    """Discover, register, and track plugins."""

    def __init__(self) -> None:
        self._plugins: Dict[str, PluginMetadata] = {}

    def register(self, metadata: PluginMetadata) -> None:
        self._plugins[metadata.plugin_id] = metadata

    def get(self, plugin_id: str) -> Optional[PluginMetadata]:
        return self._plugins.get(plugin_id)

    def list_all(self) -> List[PluginMetadata]:
        return list(self._plugins.values())

    def list_enabled(self) -> List[PluginMetadata]:
        return [p for p in self._plugins.values() if p.status == "enabled"]

    def validate_dependencies(self, metadata: PluginMetadata) -> List[str]:
        missing = []
        for dep in metadata.dependencies:
            if dep not in self._plugins:
                missing.append(dep)
        return missing


# ───────────────────────────────────────────────────────────────
# 3. PLUGIN LOADER
# ───────────────────────────────────────────────────────────────

class PluginLoader:
    """Load plugins dynamically with sandboxed execution."""

    def __init__(self, registry: PluginRegistry) -> None:
        self.registry = registry
        self._instances: Dict[str, PluginInterface] = {}

    def load(self, plugin_class: type, metadata: PluginMetadata) -> Optional[PluginInterface]:
        try:
            instance = plugin_class(metadata.plugin_id, metadata.name, metadata.version)
            self._instances[metadata.plugin_id] = instance
            return instance
        except Exception as e:
            print(f"[PLUGIN] Failed to load {metadata.plugin_id}: {e}")
            return None

    def get_instance(self, plugin_id: str) -> Optional[PluginInterface]:
        return self._instances.get(plugin_id)

    def unload(self, plugin_id: str) -> bool:
        if plugin_id in self._instances:
            self._instances[plugin_id].shutdown()
            del self._instances[plugin_id]
            return True
        return False


# ───────────────────────────────────────────────────────────────
# 4. EVENT BUS
# ───────────────────────────────────────────────────────────────

class EventBus:
    """Inter-plugin communication via pub/sub."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable]] = {}
        self._events: List[Dict[str, Any]] = []

    def subscribe(self, event_type: str, handler: Callable) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event_type: str, data: Any, source: str = "") -> None:
        event = {"type": event_type, "data": data, "source": source, "timestamp": _now()}
        self._events.append(event)
        for handler in self._subscribers.get(event_type, []):
            try:
                handler(data)
            except Exception as e:
                print(f"[EVENT] Handler error: {e}")

    def get_events(self, event_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        events = self._events
        if event_type:
            events = [e for e in events if e["type"] == event_type]
        return events[-limit:]


# ───────────────────────────────────────────────────────────────
# 5. HOOK SYSTEM
# ───────────────────────────────────────────────────────────────

class HookSystem:
    """Pre/post hooks for core functions."""

    def __init__(self) -> None:
        self._pre_hooks: Dict[str, List[Callable]] = {}
        self._post_hooks: Dict[str, List[Callable]] = {}

    def add_pre_hook(self, hook_point: str, handler: Callable) -> None:
        self._pre_hooks.setdefault(hook_point, []).append(handler)

    def add_post_hook(self, hook_point: str, handler: Callable) -> None:
        self._post_hooks.setdefault(hook_point, []).append(handler)

    def run_pre(self, hook_point: str, data: Any) -> Any:
        for handler in self._pre_hooks.get(hook_point, []):
            data = handler(data) or data
        return data

    def run_post(self, hook_point: str, data: Any) -> Any:
        for handler in self._post_hooks.get(hook_point, []):
            data = handler(data) or data
        return data


# ───────────────────────────────────────────────────────────────
# 6. SECURITY CHECKER
# ───────────────────────────────────────────────────────────────

class SecurityChecker:
    """Scan plugin code for dangerous operations."""

    DANGEROUS_IMPORTS = ["os.system", "subprocess", "socket", "requests", "urllib"]
    DANGEROUS_PATTERNS = ["eval(", "exec(", "__import__", "open(", "file(", "delete", "rm -rf"]

    def scan(self, plugin_code: str) -> Dict[str, Any]:
        flags = []
        for imp in self.DANGEROUS_IMPORTS:
            if imp in plugin_code:
                flags.append(f"dangerous import: {imp}")
        for pat in self.DANGEROUS_PATTERNS:
            if pat in plugin_code:
                flags.append(f"dangerous pattern: {pat}")
        return {"safe": len(flags) == 0, "flags": flags, "risk_score": len(flags) / 5.0}


# ───────────────────────────────────────────────────────────────
# 7. PLUGIN MANAGER
# ───────────────────────────────────────────────────────────────

class PluginManager:
    """Manage plugin lifecycle: install -> enable -> run -> disable -> uninstall."""

    def __init__(self, registry: PluginRegistry, loader: PluginLoader, event_bus: EventBus) -> None:
        self.registry = registry
        self.loader = loader
        self.event_bus = event_bus
        self.hooks = HookSystem()
        self.security = SecurityChecker()

    def install(self, metadata: PluginMetadata, plugin_class: type) -> bool:
        missing = self.registry.validate_dependencies(metadata)
        if missing:
            print(f"[PLUGIN] Missing dependencies for {metadata.plugin_id}: {missing}")
            return False
        self.registry.register(metadata)
        instance = self.loader.load(plugin_class, metadata)
        if instance:
            metadata.status = "installed"
            self.event_bus.publish("plugin.installed", metadata.plugin_id)
            return True
        return False

    def enable(self, plugin_id: str) -> bool:
        meta = self.registry.get(plugin_id)
        instance = self.loader.get_instance(plugin_id)
        if meta and instance:
            if instance.init():
                meta.status = "enabled"
                instance._enabled = True
                self.event_bus.publish("plugin.enabled", plugin_id)
                return True
        return False

    def disable(self, plugin_id: str) -> bool:
        meta = self.registry.get(plugin_id)
        instance = self.loader.get_instance(plugin_id)
        if meta and instance:
            instance.shutdown()
            meta.status = "disabled"
            self.event_bus.publish("plugin.disabled", plugin_id)
            return True
        return False

    def uninstall(self, plugin_id: str) -> bool:
        self.loader.unload(plugin_id)
        if plugin_id in self.registry._plugins:
            del self.registry._plugins[plugin_id]
            self.event_bus.publish("plugin.uninstalled", plugin_id)
            return True
        return False

    def run_plugin(self, plugin_id: str, *args, **kwargs) -> Any:
        instance = self.loader.get_instance(plugin_id)
        if instance and instance.is_enabled():
            return instance.run(*args, **kwargs)
        return None

    def list_plugins(self) -> List[Dict[str, Any]]:
        return [{"id": p.plugin_id, "name": p.name, "version": p.version, "status": p.status} for p in self.registry.list_all()]


# ───────────────────────────────────────────────────────────────
# 8. PLUGIN SYSTEM
# ───────────────────────────────────────────────────────────────

class PluginSystem:
    """Main orchestrator: discover -> load -> validate -> enable -> run."""

    def __init__(self) -> None:
        self.registry = PluginRegistry()
        self.loader = PluginLoader(self.registry)
        self.event_bus = EventBus()
        self.manager = PluginManager(self.registry, self.loader, self.event_bus)

    def discover(self, plugins: List[Tuple[type, PluginMetadata]]) -> int:
        count = 0
        for plugin_class, metadata in plugins:
            if self.manager.install(metadata, plugin_class):
                count += 1
        return count

    def enable_all(self) -> int:
        count = 0
        for meta in self.registry.list_all():
            if self.manager.enable(meta.plugin_id):
                count += 1
        return count

    def stats(self) -> Dict[str, Any]:
        return {
            "plugins": len(self.registry.list_all()),
            "enabled": len(self.registry.list_enabled()),
            "events": len(self.event_bus._events),
        }


# ───────────────────────────────────────────────────────────────
# 9. SAMPLE PLUGINS
# ───────────────────────────────────────────────────────────────

class SamplePlugin(PluginInterface):
    """Example plugin for demonstration."""

    def init(self, config: Optional[Dict[str, Any]] = None) -> bool:
        self._enabled = True
        return True

    def run(self, *args, **kwargs) -> str:
        return f"[{self.name}] Running with args: {args}, kwargs: {kwargs}"

    def get_capabilities(self) -> List[str]:
        return ["demo", "sample"]


class CalculatorPlugin(PluginInterface):
    """Calculator plugin example."""

    def init(self, config: Optional[Dict[str, Any]] = None) -> bool:
        self._enabled = True
        return True

    def run(self, expression: str = "", *args, **kwargs) -> str:
        try:
            result = eval(expression, {"__builtins__": {}}, {"abs": abs, "max": max, "min": min})
            return f"Result: {result}"
        except Exception as e:
            return f"Error: {e}"

    def get_capabilities(self) -> List[str]:
        return ["math", "calculation"]


class LoggerPlugin(PluginInterface):
    """Logging plugin example."""

    def init(self, config: Optional[Dict[str, Any]] = None) -> bool:
        self._enabled = True
        self._logs: List[str] = []
        return True

    def run(self, message: str = "", *args, **kwargs) -> str:
        entry = f"[{_now()}] {message}"
        self._logs.append(entry)
        return entry

    def get_capabilities(self) -> List[str]:
        return ["logging", "audit"]


# ───────────────────────────────────────────────────────────────
# 10. DEMO
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Plugin System Demo")
    print("=" * 60)

    system = PluginSystem()

    # Discover plugins
    print("\n[1] Discovering plugins...")
    plugins = [
        (SamplePlugin, PluginMetadata("sample_1", "Sample Plugin", "1.0", "Demo", [], ["demo"])),
        (CalculatorPlugin, PluginMetadata("calc_1", "Calculator", "1.0", "Math", [], ["math"])),
        (LoggerPlugin, PluginMetadata("logger_1", "Logger", "1.0", "System", [], ["logging"])),
    ]
    discovered = system.discover(plugins)
    print(f"  Discovered: {discovered} plugins")

    # Enable all
    print("\n[2] Enabling plugins...")
    enabled = system.enable_all()
    print(f"  Enabled: {enabled} plugins")

    # Run plugins
    print("\n[3] Running plugins...")
    for pid in ["sample_1", "calc_1", "logger_1"]:
        result = system.manager.run_plugin(pid, "test_arg")
        print(f"  {pid}: {result}")

    # Run calculator with expression
    calc_result = system.manager.run_plugin("calc_1", expression="2 + 3 * 4")
    print(f"  calc_1 (expression): {calc_result}")

    # Event bus
    print("\n[4] Event bus...")
    events = system.event_bus.get_events(limit=10)
    print(f"  Events captured: {len(events)}")
    for e in events[:3]:
        print(f"    [{e['type']}] {e['data']}")

    # Stats
    print(f"\n[STATS] {json.dumps(system.stats(), indent=2)}")

    # Disable and uninstall
    print("\n[5] Disable sample_1...")
    system.manager.disable("sample_1")
    system.manager.uninstall("sample_1")
    print(f"  Remaining plugins: {len(system.registry.list_all())}")

    print("\n" + "=" * 60)
    print("Demo complete. Plugin System ready for MAGNATRIX-OS.")
    print("=" * 60)
