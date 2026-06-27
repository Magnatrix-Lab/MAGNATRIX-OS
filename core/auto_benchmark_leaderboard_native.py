#!/usr/bin/env python3
"""
Auto Benchmark + Leaderboard for MAGNATRIX-OS
============================================
Benchmark all 179 modules, score, rank, auto-regression detection.
Continuous quality monitoring. Pure stdlib.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations
import importlib, inspect, json, time, traceback
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple


@dataclass
class BenchmarkResult:
    """Result of benchmarking a module."""
    module_name: str
    class_name: str
    load_time_ms: float = 0.0
    instantiate_time_ms: float = 0.0
    methods_tested: int = 0
    methods_passed: int = 0
    methods_failed: int = 0
    memory_estimate_kb: float = 0.0
    score: float = 0.0
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LeaderboardEntry:
    """Entry on the module leaderboard."""
    module_name: str
    class_name: str
    overall_score: float = 0.0
    rank: int = 0
    category: str = "general"
    trend: str = "stable"  # "improving", "stable", "degrading"
    previous_score: Optional[float] = None
    history: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ModuleBenchmarker:
    """Benchmarks individual modules."""

    def __init__(self) -> None:
        self._results: Dict[str, BenchmarkResult] = {}

    def benchmark(self, module_name: str, module_path: str, class_name: str) -> BenchmarkResult:
        """Benchmark a single module."""
        result = BenchmarkResult(module_name=module_name, class_name=class_name)
        t0 = time.time()
        try:
            # Load module
            mod = importlib.import_module(module_path)
            load_time = (time.time() - t0) * 1000
            result.load_time_ms = load_time
            
            # Get class
            cls = getattr(mod, class_name, None)
            if cls is None:
                result.error = f"Class {class_name} not found in {module_path}"
                result.score = 0.0
                self._results[module_name] = result
                return result
            
            # Instantiate
            t0 = time.time()
            sig = inspect.signature(cls.__init__)
            kwargs = {}
            if "repo_root" in sig.parameters:
                kwargs["repo_root"] = "."
            if "root" in sig.parameters:
                kwargs["root"] = "."
            try:
                instance = cls(**kwargs) if kwargs else cls()
                result.instantiate_time_ms = (time.time() - t0) * 1000
            except Exception as e:
                result.error = f"Instantiation failed: {e}"
                result.score = 0.2
                self._results[module_name] = result
                return result
            
            # Test methods
            methods = [m for m in dir(instance) if not m.startswith("_") and callable(getattr(instance, m))]
            result.methods_tested = len(methods)
            for method_name in methods:
                try:
                    method = getattr(instance, method_name)
                    # Call with no args if possible
                    method()
                    result.methods_passed += 1
                except Exception:
                    result.methods_failed += 1
            
            # Calculate score
            load_score = max(0, 1.0 - result.load_time_ms / 1000)  # Penalize slow load
            inst_score = max(0, 1.0 - result.instantiate_time_ms / 1000)
            method_score = result.methods_passed / result.methods_tested if result.methods_tested > 0 else 0.5
            result.score = (load_score + inst_score + method_score * 2) / 4
            result.memory_estimate_kb = len(inspect.getsource(mod).encode()) / 1024
            
        except Exception as e:
            result.error = f"Benchmark failed: {e}"
            result.score = 0.0
        
        self._results[module_name] = result
        return result

    def benchmark_all(self, modules: List[Tuple[str, str, str]]) -> Dict[str, BenchmarkResult]:
        """Benchmark all modules."""
        for name, mod_path, cls_name in modules:
            self.benchmark(name, mod_path, cls_name)
        return self._results

    def get_result(self, module_name: str) -> Optional[BenchmarkResult]:
        return self._results.get(module_name)


class Leaderboard:
    """Leaderboard for module quality scores."""

    def __init__(self, baseline_path: str = "benchmark_baseline.json") -> None:
        self.baseline_path = baseline_path
        self.entries: Dict[str, LeaderboardEntry] = {}
        self._load_baseline()

    def _load_baseline(self) -> None:
        try:
            with open(self.baseline_path, "r") as f:
                data = json.load(f)
                for mod_name, entry_data in data.items():
                    self.entries[mod_name] = LeaderboardEntry(**entry_data)
        except Exception:
            pass

    def _save_baseline(self) -> None:
        try:
            with open(self.baseline_path, "w") as f:
                json.dump({k: v.to_dict() for k, v in self.entries.items()}, f, indent=2)
        except Exception:
            pass

    def update(self, results: Dict[str, BenchmarkResult]) -> None:
        """Update leaderboard with new benchmark results."""
        for module_name, result in results.items():
            if module_name in self.entries:
                entry = self.entries[module_name]
                entry.previous_score = entry.overall_score
                entry.history.append(entry.overall_score)
                if len(entry.history) > 10:
                    entry.history = entry.history[-10:]
                entry.overall_score = result.score
                # Determine trend
                if entry.previous_score is not None:
                    diff = entry.overall_score - entry.previous_score
                    if diff > 0.05:
                        entry.trend = "improving"
                    elif diff < -0.05:
                        entry.trend = "degrading"
                    else:
                        entry.trend = "stable"
            else:
                self.entries[module_name] = LeaderboardEntry(
                    module_name=module_name,
                    class_name=result.class_name,
                    overall_score=result.score,
                    history=[result.score],
                )
        
        # Rank all entries
        sorted_entries = sorted(self.entries.values(), key=lambda e: e.overall_score, reverse=True)
        for i, entry in enumerate(sorted_entries, 1):
            entry.rank = i
        
        self._save_baseline()

    def get_top(self, n: int = 10) -> List[LeaderboardEntry]:
        return sorted(self.entries.values(), key=lambda e: e.overall_score, reverse=True)[:n]

    def get_bottom(self, n: int = 10) -> List[LeaderboardEntry]:
        return sorted(self.entries.values(), key=lambda e: e.overall_score)[:n]

    def get_regression(self, threshold: float = -0.1) -> List[LeaderboardEntry]:
        """Get modules that have regressed."""
        regressions = []
        for entry in self.entries.values():
            if entry.previous_score is not None and (entry.overall_score - entry.previous_score) < threshold:
                regressions.append(entry)
        return regressions

    def get_improving(self, threshold: float = 0.1) -> List[LeaderboardEntry]:
        """Get modules that are improving."""
        improving = []
        for entry in self.entries.values():
            if entry.previous_score is not None and (entry.overall_score - entry.previous_score) > threshold:
                improving.append(entry)
        return improving

    def get_category(self, category: str) -> List[LeaderboardEntry]:
        return [e for e in self.entries.values() if e.category == category]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_modules": len(self.entries),
            "top_10": [e.to_dict() for e in self.get_top(10)],
            "regressions": [e.to_dict() for e in self.get_regression()],
            "improving": [e.to_dict() for e in self.get_improving()],
        }


class RegressionDetector:
    """Detects performance regressions."""

    def __init__(self) -> None:
        self._history: Dict[str, List[Dict[str, Any]]] = {}

    def record(self, module_name: str, metrics: Dict[str, Any]) -> None:
        if module_name not in self._history:
            self._history[module_name] = []
        self._history[module_name].append(metrics)
        if len(self._history[module_name]) > 50:
            self._history[module_name] = self._history[module_name][-25:]

    def detect(self, module_name: str, current: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        history = self._history.get(module_name, [])
        if len(history) < 5:
            return None
        # Compare with rolling average
        recent = history[-10:]
        avg_score = sum(h.get("score", 0) for h in recent) / len(recent)
        current_score = current.get("score", 0)
        if current_score < avg_score * 0.8:  # 20% drop
            return {
                "module": module_name,
                "type": "regression",
                "severity": "high" if current_score < avg_score * 0.5 else "medium",
                "current_score": current_score,
                "expected_score": avg_score,
                "drop_pct": round((avg_score - current_score) / avg_score * 100, 1) if avg_score > 0 else 0,
            }
        return None

    def detect_all(self, current_results: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        regressions = []
        for module_name, metrics in current_results.items():
            self.record(module_name, metrics)
            reg = self.detect(module_name, metrics)
            if reg:
                regressions.append(reg)
        return regressions


class AutoBenchmarkEngine:
    """Top-level auto benchmark engine."""

    def __init__(self, repo_root: str = ".") -> None:
        self.repo_root = repo_root
        self.benchmarker = ModuleBenchmarker()
        self.leaderboard = Leaderboard()
        self.regression = RegressionDetector()
        self._last_run: Optional[float] = None

    def run(self, modules: List[Tuple[str, str, str]]) -> Dict[str, Any]:
        """Run full benchmark suite."""
        self._last_run = time.time()
        results = self.benchmarker.benchmark_all(modules)
        self.leaderboard.update(results)
        
        # Regression detection
        current_metrics = {name: {"score": r.score, "load_time": r.load_time_ms} for name, r in results.items()}
        regressions = self.regression.detect_all(current_metrics)
        
        return {
            "total_modules": len(results),
            "avg_score": sum(r.score for r in results.values()) / len(results) if results else 0,
            "top_module": self.leaderboard.get_top(1)[0].module_name if self.leaderboard.get_top(1) else None,
            "bottom_module": self.leaderboard.get_bottom(1)[0].module_name if self.leaderboard.get_bottom(1) else None,
            "regressions": len(regressions),
            "regression_details": regressions,
            "improving": len(self.leaderboard.get_improving()),
        }

    def get_leaderboard(self, top_n: int = 10) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self.leaderboard.get_top(top_n)]

    def get_regressions(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self.leaderboard.get_regression()]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "last_run": self._last_run,
            "total_benchmarked": len(self.leaderboard.entries),
            "top_10": self.get_leaderboard(10),
            "regressions": len(self.leaderboard.get_regression()),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()
