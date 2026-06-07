#!/usr/bin/env python3
"""
Performance Profiler & Optimizer for MAGNATRIX-OS
Startup time profiler, memory leak detector, lazy-load optimizer,
module dependency graph analyzer, hot-reload critical path.
Pure stdlib — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import gc
import importlib
import inspect
import json
import os
import sys
import threading
import time
import tracemalloc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set


@dataclass
class ProfileResult:
    """Result of profiling a single module."""
    name: str
    import_time_ms: float
    init_time_ms: float
    memory_kb: int
    file_size_kb: int
    class_count: int
    method_count: int
    has_main: bool
    lines_of_code: int


@dataclass
class Bottleneck:
    """Identified performance bottleneck."""
    module: str
    type: str  # slow_import, memory_heavy, large_file, complex_init
    severity: str  # low, medium, high, critical
    value: float
    recommendation: str


class StartupProfiler:
    """Profile system startup time module by module."""

    MODULES = [
        "core.config_manager_native",
        "core.logging_engine_native",
        "core.cache_engine_native",
        "core.rate_limiter_native",
        "core.auth_engine_native",
        "core.session_manager_native",
        "core.monitor_alerting_native",
        "core.event_streaming_native",
        "core.workflow_engine_native",
        "core.knowledge_graph_engine_native",
        "core.advanced_rag_pipeline_native",
        "core.memory_learning_system_native",
        "core.local_llm_manager_native",
        "core.multi_model_llm_adapter_native",
        "core.distributed_mesh_engine_native",
        "core.genesis_integration_hub_native",
        "core.web_dashboard_server_native",
        "core.dashboard_frontend_native",
        "core.document_intelligence_native",
        "core.websocket_engine_native",
        "core.agent_orchestrator_native",
    ]

    def __init__(self, repo_root: str) -> None:
        self.root = Path(repo_root).resolve()
        self._results: List[ProfileResult] = []

    def profile_all(self) -> List[ProfileResult]:
        """Profile all modules."""
        sys.path.insert(0, str(self.root))
        self._results = []

        for mod_path in self.MODULES:
            result = self._profile_module(mod_path)
            self._results.append(result)

        sys.path.pop(0)
        return self._results

    def _profile_module(self, mod_path: str) -> ProfileResult:
        file_path = self.root / (mod_path.replace(".", "/") + ".py")

        # File stats
        file_size_kb = file_path.stat().st_size // 1024 if file_path.exists() else 0
        lines = len(file_path.read_text().splitlines()) if file_path.exists() else 0

        # Import time
        t0 = time.time()
        if mod_path in sys.modules:
            del sys.modules[mod_path]
        try:
            mod = importlib.import_module(mod_path)
            import_time = (time.time() - t0) * 1000
        except Exception as e:
            import_time = 0
            mod = None

        # Init time + class/method analysis
        init_time = 0.0
        class_count = 0
        method_count = 0
        has_main = False

        if mod:
            t0 = time.time()
            # Find all classes and count methods
            for name in dir(mod):
                obj = getattr(mod, name)
                if inspect.isclass(obj):
                    class_count += 1
                    method_count += len([m for m in dir(obj) if not m.startswith("_") and callable(getattr(obj, m, None))])
            init_time = (time.time() - t0) * 1000
            has_main = hasattr(mod, "__main_guard") or "if __name__ ==" in (file_path.read_text() if file_path.exists() else "")

        # Memory (approximate via file size + overhead)
        memory_kb = file_size_kb + 50  # rough overhead estimate

        return ProfileResult(
            name=mod_path.split(".")[-1],
            import_time_ms=round(import_time, 2),
            init_time_ms=round(init_time, 2),
            memory_kb=memory_kb,
            file_size_kb=file_size_kb,
            class_count=class_count,
            method_count=method_count,
            has_main=has_main,
            lines_of_code=lines,
        )

    def get_slowest(self, n: int = 5) -> List[ProfileResult]:
        return sorted(self._results, key=lambda r: r.import_time_ms + r.init_time_ms, reverse=True)[:n]

    def get_heaviest(self, n: int = 5) -> List[ProfileResult]:
        return sorted(self._results, key=lambda r: r.memory_kb, reverse=True)[:n]


class MemoryLeakDetector:
    """Detect memory leaks by tracking object counts over time."""

    def __init__(self) -> None:
        self._snapshots: List[Tuple[float, Dict[str, int]]] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _take_snapshot(self) -> Dict[str, int]:
        gc.collect()
        counts = {}
        for obj in gc.get_objects():
            t = type(obj).__name__
            counts[t] = counts.get(t, 0) + 1
        return counts

    def start_monitoring(self, interval: int = 10) -> None:
        self._running = True
        def monitor():
            while self._running:
                snap = self._take_snapshot()
                self._snapshots.append((time.time(), snap))
                if len(self._snapshots) > 100:
                    self._snapshots = self._snapshots[-50:]
                time.sleep(interval)
        self._thread = threading.Thread(target=monitor, daemon=True, name="MemoryMonitor")
        self._thread.start()

    def stop_monitoring(self) -> None:
        self._running = False

    def detect_leaks(self, growth_threshold: float = 1.5) -> List[Dict[str, Any]]:
        """Detect object types that grew significantly."""
        if len(self._snapshots) < 2:
            return []

        first = self._snapshots[0][1]
        last = self._snapshots[-1][1]

        leaks = []
        for obj_type, last_count in last.items():
            first_count = first.get(obj_type, 0)
            if first_count > 100 and last_count > first_count * growth_threshold:
                leaks.append({
                    "type": obj_type,
                    "initial": first_count,
                    "current": last_count,
                    "growth": round(last_count / first_count, 2) if first_count > 0 else float("inf"),
                    "delta": last_count - first_count,
                })

        return sorted(leaks, key=lambda x: x["delta"], reverse=True)[:20]

    def get_stats(self) -> Dict[str, Any]:
        if not self._snapshots:
            return {"snapshots": 0, "total_objects": 0}
        latest = self._snapshots[-1][1]
        return {
            "snapshots": len(self._snapshots),
            "total_objects": sum(latest.values()),
            "unique_types": len(latest),
            "top_types": sorted(latest.items(), key=lambda x: x[1], reverse=True)[:10],
        }


class DependencyAnalyzer:
    """Analyze module dependency graph for circular deps and load order."""

    def __init__(self, repo_root: str) -> None:
        self.root = Path(repo_root).resolve()

    def analyze(self) -> Dict[str, Any]:
        """Analyze all core module dependencies."""
        core_dir = self.root / "core"
        if not core_dir.exists():
            return {"error": "Core directory not found"}

        imports: Dict[str, Set[str]] = {}
        all_modules = set()

        for f in sorted(core_dir.glob("*_native.py")):
            name = f.stem
            all_modules.add(name)
            imports[name] = set()
            text = f.read_text()
            # Find all import statements
            for match in re.finditer(r"(?:from|import)\s+([\w.]+)", text):
                imp = match.group(1)
                if "core." in imp or "native" in imp:
                    dep_name = imp.split(".")[-1]
                    if dep_name != name and "native" in dep_name:
                        imports[name].add(dep_name)

        # Detect circular dependencies
        cycles = self._find_cycles(imports)

        # Calculate load order (topological sort)
        load_order = self._topological_sort(imports)

        # Find orphaned modules (no imports, no one imports them)
        imported_by = {m: set() for m in all_modules}
        for mod, deps in imports.items():
            for dep in deps:
                if dep in imported_by:
                    imported_by[dep].add(mod)

        orphans = [m for m in all_modules if not imports[m] and not imported_by[m]]

        return {
            "total_modules": len(all_modules),
            "dependency_map": {k: sorted(v) for k, v in imports.items()},
            "cycles": cycles,
            "cycles_count": len(cycles),
            "load_order": load_order,
            "orphans": sorted(orphans),
            "most_depended_on": sorted(imported_by.items(), key=lambda x: len(x[1]), reverse=True)[:10],
            "most_dependencies": sorted(imports.items(), key=lambda x: len(x[1]), reverse=True)[:10],
        }

    def _find_cycles(self, imports: Dict[str, Set[str]]) -> List[List[str]]:
        """Find all circular dependency cycles."""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in imports.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)

            path.pop()
            rec_stack.remove(node)

        for node in imports:
            if node not in visited:
                dfs(node)

        # Remove duplicate cycles (same set of nodes)
        unique = []
        seen = set()
        for cycle in cycles:
            key = tuple(sorted(set(cycle)))
            if key not in seen:
                seen.add(key)
                unique.append(cycle)

        return unique

    def _topological_sort(self, imports: Dict[str, Set[str]]) -> List[str]:
        """Kahn's algorithm for topological sort."""
        in_degree = {m: 0 for m in imports}
        for deps in imports.values():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1

        queue = [m for m, d in in_degree.items() if d == 0]
        order = []

        while queue:
            node = queue.pop(0)
            order.append(node)
            for other, deps in imports.items():
                if node in deps:
                    in_degree[other] -= 1
                    if in_degree[other] == 0:
                        queue.append(other)

        return order


class HotReloadOptimizer:
    """Optimize critical path for hot reload."""

    def __init__(self, repo_root: str) -> None:
        self.root = Path(repo_root).resolve()
        self._cache: Dict[str, Any] = {}

    def analyze_critical_path(self) -> Dict[str, Any]:
        """Identify which modules are on the critical path for startup."""
        # The critical path is: config -> logging -> event_bus -> web_dashboard
        critical_chain = [
            "config_manager_native",
            "logging_engine_native",
            "event_bus_native",
            "web_dashboard_server_native",
        ]

        core_dir = self.root / "core"
        chain_times = []
        for mod_name in critical_chain:
            f = core_dir / mod_name / "native.py"
            if not f.exists():
                f = core_dir / f"{mod_name}.py"
            if f.exists():
                size = f.stat().st_size
                chain_times.append({"module": mod_name, "size_bytes": size, "estimated_ms": size // 500})

        total_estimated = sum(m["estimated_ms"] for m in chain_times)

        return {
            "critical_chain": chain_times,
            "total_estimated_ms": total_estimated,
            "recommendations": [
                "Lazy-load non-critical modules after dashboard is ready",
                "Pre-compile .py to .pyc for faster import",
                "Consider __slots__ for memory-heavy classes",
                "Defer RAG and LLM init until first query",
            ],
        }

    def get_lazy_load_candidates(self) -> List[str]:
        """Identify modules that can be lazy-loaded."""
        # These are modules that don't need to be loaded at startup
        return [
            "advanced_rag_pipeline_native",
            "distributed_mesh_engine_native",
            "voice_audio_pipeline_native",
            "email_client_native",
            "pwa_desktop_wrapper_native",
            "auto_deployment_native",
            "cli_tui_manager_native",
        ]


class PerformanceProfiler:
    """Main profiler combining all tools."""

    def __init__(self, repo_root: str) -> None:
        self.root = Path(repo_root).resolve()
        self.startup = StartupProfiler(repo_root)
        self.memory = MemoryLeakDetector()
        self.dependency = DependencyAnalyzer(repo_root)
        self.hotreload = HotReloadOptimizer(repo_root)
        self._bottlenecks: List[Bottleneck] = []

    def run_full_profile(self) -> Dict[str, Any]:
        """Run complete performance profiling."""
        print("[Profiler] Starting full system profile...")

        # 1. Startup profile
        print("[Profiler] Profiling module imports...")
        startup_results = self.startup.profile_all()

        # 2. Memory baseline
        print("[Profiler] Taking memory baseline...")
        self.memory.start_monitoring(interval=5)
        time.sleep(1)  # Quick snapshot
        self.memory.stop_monitoring()

        # 3. Dependency analysis
        print("[Profiler] Analyzing dependencies...")
        dep_analysis = self.dependency.analyze()

        # 4. Critical path
        print("[Profiler] Analyzing critical path...")
        critical_path = self.hotreload.analyze_critical_path()

        # 5. Identify bottlenecks
        self._bottlenecks = self._identify_bottlenecks(startup_results, dep_analysis)

        return {
            "startup": {
                "modules_profiled": len(startup_results),
                "slowest": [
                    {"name": r.name, "import_ms": r.import_time_ms, "init_ms": r.init_time_ms}
                    for r in self.startup.get_slowest(10)
                ],
                "heaviest": [
                    {"name": r.name, "memory_kb": r.memory_kb, "lines": r.lines_of_code}
                    for r in self.startup.get_heaviest(10)
                ],
            },
            "memory": self.memory.get_stats(),
            "dependencies": dep_analysis,
            "critical_path": critical_path,
            "bottlenecks": [
                {"module": b.module, "type": b.type, "severity": b.severity, "value": b.value, "fix": b.recommendation}
                for b in self._bottlenecks
            ],
            "lazy_load_candidates": self.hotreload.get_lazy_load_candidates(),
            "timestamp": time.time(),
        }

    def _identify_bottlenecks(self, startup_results: List[ProfileResult], deps: Dict[str, Any]) -> List[Bottleneck]:
        """Identify performance bottlenecks."""
        bottlenecks = []

        # Slow imports
        for r in startup_results:
            total = r.import_time_ms + r.init_time_ms
            if total > 500:
                bottlenecks.append(Bottleneck(
                    module=r.name, type="slow_import", severity="high" if total > 1000 else "medium",
                    value=total, recommendation=f"Consider lazy-loading {r.name} or pre-compiling",
                ))

        # Heavy memory
        for r in startup_results:
            if r.memory_kb > 500:
                bottlenecks.append(Bottleneck(
                    module=r.name, type="memory_heavy", severity="medium",
                    value=r.memory_kb, recommendation=f"Review {r.name} for __slots__ or data cleanup",
                ))

        # Large files
        for r in startup_results:
            if r.file_size_kb > 50:
                bottlenecks.append(Bottleneck(
                    module=r.name, type="large_file", severity="low",
                    value=r.file_size_kb, recommendation=f"Split {r.name} into smaller modules",
                ))

        # Circular dependencies
        for cycle in deps.get("cycles", []):
            bottlenecks.append(Bottleneck(
                module=" -> ".join(cycle[:3]), type="circular_dep", severity="critical",
                value=len(cycle), recommendation="Break circular dependency with interface abstraction",
            ))

        return sorted(bottlenecks, key=lambda b: {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(b.severity, 0), reverse=True)

    def save_report(self, path: str) -> str:
        report = self.run_full_profile()
        Path(path).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def print_summary(self) -> None:
        report = self.run_full_profile()
        print("=" * 60)
        print("  PERFORMANCE PROFILE SUMMARY")
        print("=" * 60)
        print(f"  Modules profiled: {report['startup']['modules_profiled']}")
        print(f"  Slowest module: {report['startup']['slowest'][0]['name'] if report['startup']['slowest'] else 'N/A'}")
        print(f"  Circular deps: {report['dependencies']['cycles_count']}")
        print(f"  Bottlenecks: {len(report['bottlenecks'])}")
        print(f"  Lazy-load candidates: {len(report['lazy_load_candidates'])}")
        print("=" * 60)
        if report['bottlenecks']:
            print("  TOP BOTTLENECKS:")
            for b in report['bottlenecks'][:5]:
                icon = "🔴" if b['severity'] == 'critical' else "🟡" if b['severity'] == 'high' else "🟢"
                print(f"    {icon} {b['module']}: {b['type']} ({b['severity']})")
                print(f"       Fix: {b['fix']}")
        print("=" * 60)


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== Performance Profiler & Optimizer Demo ===\n")
    profiler = PerformanceProfiler(repo_root="/mnt/agents/MAGNATRIX-OS")
    report = profiler.run_full_profile()
    profiler.print_summary()
    print(f"\nDetailed report saved to: {profiler.save_report('/tmp/performance_report.json')}")


if __name__ == "__main__":
    _demo()
