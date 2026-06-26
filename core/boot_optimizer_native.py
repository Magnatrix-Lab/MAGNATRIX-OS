#!/usr/bin/env python3
"""
Boot Optimizer for MAGNATRIX-OS
================================
Reduces boot time via lazy loading, async parallel init,
and dependency graph-aware boot sequence. Pure stdlib only.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations
import importlib, inspect, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


@dataclass
class ModuleDependency:
    """Dependency declaration for a module."""
    name: str
    requires: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)
    lazy: bool = False
    priority: int = 50


class DependencyGraph:
    """Builds and resolves module dependency graph."""

    def __init__(self, modules: List[Tuple[str, str, str]]) -> None:
        self.modules = {m[0]: m for m in modules}
        self._deps: Dict[str, ModuleDependency] = {}
        self._build_graph()

    def _build_graph(self) -> None:
        for name, mod_path, cls_name in self.modules.values():
            requires: List[str] = []
            lazy = False
            priority = 50
            try:
                mod = importlib.import_module(mod_path)
                cls = getattr(mod, cls_name)
                if hasattr(cls, "MAGNATRIX_DEPS"):
                    requires = list(getattr(cls, "MAGNATRIX_DEPS", []))
                if hasattr(cls, "MAGNATRIX_LAZY"):
                    lazy = bool(getattr(cls, "MAGNATRIX_LAZY", False))
                if hasattr(cls, "MAGNATRIX_PRIORITY"):
                    priority = int(getattr(cls, "MAGNATRIX_PRIORITY", 50))
            except Exception:
                pass
            self._deps[name] = ModuleDependency(name, requires, [name], lazy, priority)

    def topological_sort(self) -> List[List[str]]:
        """Return tiers: each tier can be loaded in parallel."""
        in_degree: Dict[str, int] = {name: 0 for name in self.modules}
        adj: Dict[str, List[str]] = {name: [] for name in self.modules}
        for dep in self._deps.values():
            for req in dep.requires:
                if req in self.modules and dep.name in self.modules:
                    adj[req].append(dep.name)
                    in_degree[dep.name] += 1
        tiers: List[List[str]] = []
        remaining = set(self.modules.keys())
        while remaining:
            tier = [name for name in remaining if in_degree[name] == 0]
            if not tier:
                break
            tier.sort(key=lambda n: self._deps[n].priority)
            tiers.append(tier)
            for name in tier:
                remaining.remove(name)
                for dependent in adj[name]:
                    in_degree[dependent] -= 1
        if remaining:
            tiers.append(sorted(remaining))
        return tiers

    def get_lazy_modules(self) -> List[str]:
        return [d.name for d in self._deps.values() if d.lazy]

    def get_priority(self, name: str) -> int:
        return self._deps.get(name, ModuleDependency(name)).priority


class BootOptimizer:
    """Optimizes MAGNATRIX-OS boot sequence."""

    ESSENTIAL_MODULES = {
        "config", "logging", "auth", "cache", "database_abstraction",
        "event_bus", "integration", "system_bootstrap", "module_registry",
    }

    LAZY_MODULES = {
        "hft_trading", "grpc_transport", "docker_compose", "quantum_safe", "wasm",
        "intent", "temporal", "code_reasoning", "audit_forensics", "anomaly_viz",
        "test_suite", "dashboard_pro", "edge", "gesture", "voice_1", "mobile",
        "gguf", "bluegreen_deploy", "canary", "chaos", "etl", "data_lake",
        "stream_processing", "data_quality_engine", "compression_engine",
        "encryption_engine", "replication_engine", "snapshot_engine", "log_analysis",
        "slo", "federation_sync", "distributed", "autonomy", "awareness", "ego",
        "follow", "outreach", "email", "pwa", "i18n", "hot_reload", "cost",
    }

    def __init__(self, registry: Any, max_workers: int = 8) -> None:
        self.registry = registry
        self.max_workers = max_workers
        self._lazy_loaded: Set[str] = set()
        self._dependency_graph: Optional[DependencyGraph] = None
        self._lock = threading.RLock()

    def build_dependency_graph(self, modules: List[Tuple[str, str, str]]) -> None:
        self._dependency_graph = DependencyGraph(modules)

    def optimized_boot(self, quick: bool = False) -> Dict[str, Any]:
        """Boot with parallel loading and dependency resolution."""
        registry = self.registry
        registry._running = True
        start_all = time.time()
        results = {"loaded": 0, "failed": 0, "skipped": 0, "total": len(registry.CORE_MODULES), "details": [], "parallel_tiers": 0}

        for hook in registry._hooks.get("pre_boot", []):
            try:
                hook()
            except Exception:
                pass

        if self._dependency_graph is None:
            self.build_dependency_graph(registry.CORE_MODULES)

        lazy_modules = set(self._dependency_graph.get_lazy_modules())
        lazy_modules = lazy_modules | self.LAZY_MODULES

        if quick:
            all_names = set(entry[0] for entry in registry.CORE_MODULES)
            lazy_modules = lazy_modules | (all_names - self.ESSENTIAL_MODULES)

        essential = self.ESSENTIAL_MODULES
        normal = []
        for name, _, _ in registry.CORE_MODULES:
            if name not in essential and name not in lazy_modules:
                normal.append(name)

        tiers = [sorted(essential), sorted(normal)]

        for tier in tiers:
            if not tier:
                continue
            with ThreadPoolExecutor(max_workers=min(len(tier), self.max_workers)) as executor:
                futures = {executor.submit(self._load_single, name, registry): name for name in tier}
                for future in as_completed(futures):
                    name, info = future.result()
                    if info is not None:
                        with registry._lock:
                            registry._modules[name] = info
                        if info.state == "active":
                            results["loaded"] += 1
                        elif info.state == "error":
                            results["failed"] += 1
                        results["details"].append({
                            "name": name, "state": info.state, "load_ms": round(info.load_time_ms, 1),
                            "error": info.error,
                        })
            results["parallel_tiers"] += 1

        for name in lazy_modules:
            results["skipped"] += 1
            with registry._lock:
                info = registry._modules.get(name)
                if info is None:
                    from magnatrix import ModuleInfo
                    info = ModuleInfo(name=name, path="", class_name="")
                    info.state = "lazy"
                    info.load_time_ms = 0.0
                    info.error = None
                    registry._modules[name] = info
            results["details"].append({
                "name": name, "state": "lazy", "load_ms": 0.0, "error": None,
            })

        total_ms = (time.time() - start_all) * 1000
        results["boot_time_ms"] = round(total_ms, 1)
        results["lazy_count"] = len(lazy_modules)

        for hook in registry._hooks.get("post_boot", []):
            try:
                hook()
            except Exception:
                pass

        return results

    def _load_single(self, name: str, registry: Any) -> Tuple[str, Any]:
        for entry in registry.CORE_MODULES:
            if entry[0] == name:
                mod_path, cls_name = entry[1], entry[2]
                break
        else:
            return name, None

        from magnatrix import ModuleInfo
        info = ModuleInfo(name=name, path=mod_path, class_name=cls_name)
        info.state = "loading"
        info.load_time_ms = 0.0
        info.error = None
        info.instance = None
        info.provides = []

        t0 = time.time()
        instance = registry._load_module(name, mod_path, cls_name)
        info.load_time_ms = (time.time() - t0) * 1000
        if instance is not None:
            info.instance = instance
            info.state = "active"
            info.provides = [name]
        else:
            info.state = "error"
            info.error = "Failed to load"

        return name, info

    def lazy_load(self, name: str) -> Optional[Any]:
        """Load a lazy module on demand."""
        registry = self.registry
        info = registry._modules.get(name)
        if info and info.state == "lazy":
            for entry in registry.CORE_MODULES:
                if entry[0] == name:
                    mod_path, cls_name = entry[1], entry[2]
                    instance = registry._load_module(name, mod_path, cls_name)
                    if instance is not None:
                        with registry._lock:
                            info.instance = instance
                            info.state = "active"
                            info.provides = [name]
                    else:
                        with registry._lock:
                            info.state = "error"
                            info.error = "Failed to lazy load"
                    return instance
        return registry.get_module(name) if hasattr(registry, "get_module") else None

    def get_boot_stats(self) -> Dict[str, Any]:
        if self._dependency_graph is None:
            return {}
        tiers = self._dependency_graph.topological_sort()
        return {
            "total_modules": len(self.registry.CORE_MODULES),
            "parallel_tiers": len(tiers),
            "max_parallel": max(len(t) for t in tiers) if tiers else 0,
            "lazy_modules": self._dependency_graph.get_lazy_modules(),
            "avg_priority": sum(self._dependency_graph.get_priority(n) for n in self.registry.CORE_MODULES) / len(self.registry.CORE_MODULES) if self.registry.CORE_MODULES else 0,
        }


class LazyModuleProxy:
    """Proxy that auto-loads lazy modules on first access."""

    def __init__(self, optimizer: BootOptimizer, name: str) -> None:
        self._optimizer = optimizer
        self._name = name
        self._instance: Optional[Any] = None

    def __getattr__(self, attr: str) -> Any:
        if self._instance is None:
            self._instance = self._optimizer.lazy_load(self._name)
        if self._instance is None:
            raise AttributeError(f"Module {self._name} not available")
        return getattr(self._instance, attr)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if self._instance is None:
            self._instance = self._optimizer.lazy_load(self._name)
        if self._instance is None:
            raise RuntimeError(f"Module {self._name} not available")
        return self._instance(*args, **kwargs)
