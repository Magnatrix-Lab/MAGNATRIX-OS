#!/usr/bin/env python3
"""
Boot Optimizer v2 for MAGNATRIX-OS
===================================
Tiered lazy loading, topological dependency sorting, async parallel init.
Targets: sub-1-second boot for 160+ modules.
Pure stdlib.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations
import importlib, inspect, threading, time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class BootTier(Enum):
    ESSENTIAL = 0  # Must boot first (logging, config, auth)
    CORE = 1       # Core system (database, cache, mesh)
    FEATURE = 2    # Feature modules (analytics, search, training)
    OPTIONAL = 3   # Optional / lazy (dashboard, benchmark, test)


@dataclass
class ModuleDep:
    """Module dependency info."""
    name: str
    module_path: str
    class_name: str
    tier: BootTier = BootTier.FEATURE
    depends_on: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)
    lazy: bool = False
    load_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["tier"] = self.tier.name
        return d


class DependencyGraph:
    """Topological dependency graph for boot ordering."""

    def __init__(self) -> None:
        self.modules: Dict[str, ModuleDep] = {}
        self._graph: Dict[str, Set[str]] = {}

    def add(self, dep: ModuleDep) -> None:
        self.modules[dep.name] = dep
        if dep.name not in self._graph:
            self._graph[dep.name] = set()
        for d in dep.depends_on:
            self._graph[dep.name].add(d)

    def topological_sort(self) -> List[str]:
        """Kahn's algorithm for topological sort."""
        in_degree = {n: 0 for n in self._graph}
        for deps in self._graph.values():
            for d in deps:
                if d in in_degree:
                    in_degree[d] += 0
        for deps in self._graph.values():
            for d in deps:
                if d in in_degree:
                    in_degree[d] += 1
        queue = [n for n, d in in_degree.items() if d == 0]
        result = []
        while queue:
            queue.sort(key=lambda n: self.modules.get(n, ModuleDep(n, "", "")).tier.value)
            node = queue.pop(0)
            result.append(node)
            for neighbor in self._graph:
                if node in self._graph[neighbor]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0 and neighbor not in result:
                        queue.append(neighbor)
        # Add any missing nodes
        for n in self._graph:
            if n not in result:
                result.append(n)
        return result

    def get_parallel_groups(self) -> List[List[str]]:
        """Group modules that can boot in parallel."""
        sorted_names = self.topological_sort()
        groups = []
        loaded = set()
        remaining = set(sorted_names)
        while remaining:
            group = []
            for name in sorted(remaining, key=lambda n: self.modules.get(n, ModuleDep(n, "", "")).tier.value):
                deps = self._graph.get(name, set())
                if all(d in loaded or d not in self._graph for d in deps):
                    group.append(name)
            if not group:
                group = [remaining.pop()]
            else:
                for g in group:
                    remaining.remove(g)
            groups.append(group)
            loaded.update(group)
        return groups

    def to_dict(self) -> Dict[str, Any]:
        return {
            "modules": {k: v.to_dict() for k, v in self.modules.items()},
            "groups": self.get_parallel_groups(),
        }


class LazyModuleProxy:
    """Proxy that defers actual module loading until first access."""

    def __init__(self, name: str, mod_path: str, cls_name: str, loader: Callable) -> None:
        self._name = name
        self._mod_path = mod_path
        self._cls_name = cls_name
        self._loader = loader
        self._instance: Optional[Any] = None
        self._loaded = False
        self._lock = threading.RLock()

    def __getattr__(self, name: str) -> Any:
        with self._lock:
            if not self._loaded:
                self._instance = self._loader(self._name, self._mod_path, self._cls_name)
                self._loaded = True
            if self._instance is None:
                raise AttributeError(f"Module {self._name} failed to load")
            return getattr(self._instance, name)

    def __call__(self, *args, **kwargs) -> Any:
        with self._lock:
            if not self._loaded:
                self._instance = self._loader(self._name, self._mod_path, self._cls_name)
                self._loaded = True
            if self._instance is None:
                raise RuntimeError(f"Module {self._name} failed to load")
            return self._instance(*args, **kwargs)

    def is_loaded(self) -> bool:
        return self._loaded

    def force_load(self) -> Any:
        with self._lock:
            if not self._loaded:
                self._instance = self._loader(self._name, self._mod_path, self._cls_name)
                self._loaded = True
            return self._instance

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self._name,
            "loaded": self._loaded,
            "has_instance": self._instance is not None,
        }


class BootOptimizer:
    """Top-level boot optimizer."""

    TIER_MAP = {
        # Essential tier
        "auth": BootTier.ESSENTIAL, "config": BootTier.ESSENTIAL, "logging": BootTier.ESSENTIAL,
        "system_bootstrap": BootTier.ESSENTIAL, "module_registry": BootTier.ESSENTIAL,
        "cache": BootTier.ESSENTIAL, "security": BootTier.ESSENTIAL,
        # Core tier
        "database": BootTier.CORE, "distributed": BootTier.CORE, "message": BootTier.CORE,
        "event": BootTier.CORE, "filesystem": BootTier.CORE, "process": BootTier.CORE,
        "container": BootTier.CORE, "local": BootTier.CORE, "multi_model": BootTier.CORE,
        # Optional tier
        "benchmark": BootTier.OPTIONAL, "dashboard": BootTier.OPTIONAL, "test": BootTier.OPTIONAL,
        "performance": BootTier.OPTIONAL, "cli_tui": BootTier.OPTIONAL, "pwa": BootTier.OPTIONAL,
        "dashboard_pro": BootTier.OPTIONAL, "test_suite": BootTier.OPTIONAL,
    }

    def __init__(self, repo_root: str) -> None:
        self.repo_root = repo_root
        self.graph = DependencyGraph()
        self.proxies: Dict[str, LazyModuleProxy] = {}
        self.loaded_instances: Dict[str, Any] = {}
        self._tier_results: Dict[BootTier, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def classify_tier(self, name: str) -> BootTier:
        return self.TIER_MAP.get(name, BootTier.FEATURE)

    def build_graph(self, modules: List[Tuple[str, str, str]]) -> None:
        """Build dependency graph from CORE_MODULES list."""
        for name, mod_path, cls_name in modules:
            tier = self.classify_tier(name)
            lazy = tier == BootTier.OPTIONAL
            dep = ModuleDep(name=name, module_path=mod_path, class_name=cls_name, tier=tier, lazy=lazy)
            self.graph.add(dep)

    def optimize(self, modules: List[Tuple[str, str, str]], loader: Callable) -> Dict[str, Any]:
        """Optimized boot with tiered parallel loading."""
        self.build_graph(modules)
        results = {"loaded": 0, "failed": 0, "lazy": 0, "total": len(modules), "tiers": {}, "boot_time_ms": 0.0}
        start = time.time()

        groups = self.graph.get_parallel_groups()
        for group in groups:
            tier = self.classify_tier(group[0]) if group else BootTier.FEATURE
            tier_start = time.time()
            tier_loaded = 0
            tier_failed = 0

            if tier == BootTier.OPTIONAL:
                # Create lazy proxies for optional modules
                for name in group:
                    dep = self.graph.modules.get(name)
                    if dep:
                        proxy = LazyModuleProxy(name, dep.module_path, dep.class_name, loader)
                        self.proxies[name] = proxy
                        results["lazy"] += 1
                        tier_loaded += 1
            else:
                # Load in parallel
                with ThreadPoolExecutor(max_workers=min(len(group), 8)) as executor:
                    futures = {}
                    for name in group:
                        dep = self.graph.modules.get(name)
                        if dep:
                            future = executor.submit(loader, name, dep.module_path, dep.class_name)
                            futures[future] = name
                    for future in futures:
                        name = futures[future]
                        try:
                            instance = future.result(timeout=5.0)
                            if instance is not None:
                                self.loaded_instances[name] = instance
                                results["loaded"] += 1
                                tier_loaded += 1
                            else:
                                results["failed"] += 1
                                tier_failed += 1
                        except Exception:
                            results["failed"] += 1
                            tier_failed += 1

            tier_ms = (time.time() - tier_start) * 1000
            results["tiers"][tier.name] = {
                "loaded": tier_loaded,
                "failed": tier_failed,
                "time_ms": round(tier_ms, 1),
            }

        results["boot_time_ms"] = round((time.time() - start) * 1000, 1)
        return results

    def get_proxy(self, name: str) -> Optional[LazyModuleProxy]:
        return self.proxies.get(name)

    def force_load_all(self) -> Dict[str, Any]:
        """Force all lazy modules to load."""
        results = {"loaded": 0, "failed": 0}
        for name, proxy in list(self.proxies.items()):
            try:
                instance = proxy.force_load()
                if instance is not None:
                    self.loaded_instances[name] = instance
                    results["loaded"] += 1
                else:
                    results["failed"] += 1
            except Exception:
                results["failed"] += 1
        return results

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_modules": len(self.graph.modules),
            "loaded": len(self.loaded_instances),
            "lazy": len(self.proxies),
            "parallel_groups": len(self.graph.get_parallel_groups()),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()
