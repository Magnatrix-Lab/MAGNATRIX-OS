#!/usr/bin/env python3
"""
System Bootstrap for MAGNATRIX-OS
Initializes, wires, and starts all core infrastructure modules.
Provides dependency injection, lifecycle management, and graceful shutdown.
Native stdlib only — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import importlib
import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type


class ModuleState(enum.Enum):
    UNLOADED = "unloaded"
    LOADING = "loading"
    ACTIVE = "active"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclasses.dataclass
class ModuleInfo:
    name: str
    module_class: str
    module_path: str
    dependencies: List[str]
    state: ModuleState = ModuleState.UNLOADED
    instance: Any = None
    error: Optional[str] = None
    load_time_ms: float = 0.0


class SystemBootstrap:
    """Central bootstrap and dependency injection for MAGNATRIX-OS."""

    def __init__(self, repo_root: str) -> None:
        self.root = Path(repo_root).resolve()
        self._modules: Dict[str, ModuleInfo] = {}
        self._registry: Dict[str, Any] = {}
        self._hooks: Dict[str, List[Callable]] = {
            "pre_load": [],
            "post_load": [],
            "pre_shutdown": [],
            "post_shutdown": [],
        }
        self._start_time: Optional[float] = None

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, name: str, module_class: str, module_path: str, dependencies: Optional[List[str]] = None) -> None:
        self._modules[name] = ModuleInfo(
            name=name,
            module_class=module_class,
            module_path=module_path,
            dependencies=dependencies or [],
        )

    def _default_registry(self) -> None:
        """Register all known core modules."""
        core = self.root / "core"
        modules = [
            ("event_bus", "EventBus", "event_bus_native", []),
            ("config", "ConfigManager", "config_manager_native", []),
            ("secret", "SecretManager", "secret_manager_native", ["config"]),
            ("cache", "CacheManager", "cache_manager_native", ["config"]),
            ("context", "ContextManager", "context_manager_native", ["config"]),
            ("auth", "AuthManager", "auth_authorization_native", ["config"]),
            ("rate_limiter", "RateLimiter", "rate_limiter_native", []),
            ("prompt_guard", "PromptInjectionGuard", "prompt_injection_guard_native", []),
            ("logger", "LoggingManager", "logging_tracing_native", ["config"]),
            ("session", "SessionManager", "session_manager_native", ["config"]),
            ("tool_registry", "ToolRegistry", "tool_registry_native", []),
            ("module_registry", "ModuleRegistry", "module_registry_native", []),
            ("task_queue", "TaskQueueScheduler", "task_queue_scheduler_native", []),
            ("model_router", "ModelRouter", "model_router_native", ["config"]),
            ("llm_adapter", "MultiModelLLMAdapter", "multi_model_llm_adapter_native", ["config"]),
            ("plugin_sandbox", "PluginSandbox", "plugin_sandbox_native", ["config"]),
            ("web_api", "WebAPIGateway", "web_api_gateway_native", ["config", "auth"]),
            ("metrics", "HealthDashboard", "metrics_health_native", []),
            ("orchestrator", "UnifiedOrchestrator", "unified_orchestrator_native", [
                "event_bus", "config", "auth", "session", "tool_registry", "model_router"
            ]),
            ("http_client", "HTTPClient", "http_client_native", []),
            ("db", "DatabaseManager", "database_layer_native", ["config"]),
            ("fs", "FileSystemManager", "filesystem_manager_native", ["config"]),
            ("crypto", "CryptoUtilities", "crypto_utilities_native", []),
            ("process", "ProcessManager", "process_manager_native", []),
            ("monitor", "ResourceMonitor", "resource_monitor_native", []),
            ("template", "TemplateEngine", "template_engine_native", []),
            ("email", "EmailClient", "email_client_native", ["config"]),
            ("search", "SearchEngine", "search_engine_native", []),
            ("pipeline", "DataPipeline", "data_pipeline_native", []),
            ("backup", "BackupSnapshotManager", "backup_snapshot_native", ["config"]),
            ("alerts", "AlertNotificationManager", "alert_notification_native", ["config"]),
        ]
        for name, cls, path, deps in modules:
            self.register(name, cls, f"core.{path}", deps)

    # ------------------------------------------------------------------
    # Dependency resolution
    # ------------------------------------------------------------------

    def _resolve_order(self) -> List[str]:
        """Topological sort of module dependencies."""
        visited: Set[str] = set()
        order: List[str] = []
        temp_mark: Set[str] = set()

        def visit(name: str) -> None:
            if name in temp_mark:
                raise ValueError(f"Circular dependency detected involving {name}")
            if name in visited:
                return
            temp_mark.add(name)
            for dep in self._modules.get(name, ModuleInfo(name, "", "", [])).dependencies:
                if dep in self._modules:
                    visit(dep)
            temp_mark.remove(name)
            visited.add(name)
            order.append(name)

        for name in self._modules:
            visit(name)
        return order

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _load_module(self, name: str) -> bool:
        info = self._modules[name]
        if info.state in (ModuleState.ACTIVE, ModuleState.LOADING):
            return True
        info.state = ModuleState.LOADING
        start = time.perf_counter()
        try:
            # Import module
            module = importlib.import_module(info.module_path)
            cls = getattr(module, info.module_class)
            # Try to instantiate with known signatures
            instance = None
            try:
                instance = cls()
            except TypeError:
                try:
                    instance = cls(str(self.root))
                except TypeError:
                    instance = cls(repo_root=str(self.root))
            info.instance = instance
            info.state = ModuleState.ACTIVE
            self._registry[name] = instance
            info.load_time_ms = (time.perf_counter() - start) * 1000
            return True
        except Exception as e:
            info.state = ModuleState.ERROR
            info.error = traceback.format_exc()
            info.load_time_ms = (time.perf_counter() - start) * 1000
            return False

    def boot(self) -> Dict[str, Any]:
        """Bootstrap the entire system."""
        self._start_time = time.time()
        self._default_registry()
        order = self._resolve_order()
        results = {}
        for name in order:
            for hook in self._hooks["pre_load"]:
                try:
                    hook(name)
                except Exception:
                    pass
            ok = self._load_module(name)
            results[name] = {"state": self._modules[name].state.value, "time_ms": self._modules[name].load_time_ms}
            for hook in self._hooks["post_load"]:
                try:
                    hook(name, ok)
                except Exception:
                    pass
        return results

    def shutdown(self) -> Dict[str, Any]:
        """Graceful shutdown."""
        results = {}
        for name in reversed(list(self._modules.keys())):
            info = self._modules[name]
            if info.state != ModuleState.ACTIVE:
                continue
            for hook in self._hooks["pre_shutdown"]:
                try:
                    hook(name)
                except Exception:
                    pass
            try:
                if hasattr(info.instance, "close"):
                    info.instance.close()
                elif hasattr(info.instance, "stop"):
                    info.instance.stop()
                info.state = ModuleState.SHUTDOWN
                results[name] = "shutdown"
            except Exception as e:
                results[name] = f"error: {e}"
            for hook in self._hooks["post_shutdown"]:
                try:
                    hook(name)
                except Exception:
                    pass
        return results

    def get_module(self, name: str) -> Any:
        return self._registry.get(name)

    def add_hook(self, event: str, callback: Callable) -> None:
        if event in self._hooks:
            self._hooks[event].append(callback)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        by_state = {}
        for info in self._modules.values():
            by_state[info.state.value] = by_state.get(info.state.value, 0) + 1
        total_time = sum(info.load_time_ms for info in self._modules.values())
        return {
            "total_modules": len(self._modules),
            "by_state": by_state,
            "total_load_time_ms": round(total_time, 2),
            "uptime_seconds": round(time.time() - self._start_time, 2) if self._start_time else 0,
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.exists(os.path.join(repo, "governance")):
        repo = os.getcwd()
    boot = SystemBootstrap(repo)
    print("=== System Bootstrap Demo ===\n")
    print(f"Registered modules: {len(boot._modules)}")
    order = boot._resolve_order()
    print(f"Load order: {order[:5]}...")
    print(f"\nStats: {boot.stats()}")


if __name__ == "__main__":
    _demo()
