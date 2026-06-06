#!/usr/bin/env python3
"""
Benchmark Suite for MAGNATRIX-OS
Performance benchmarks, load testing, and stress testing
for all core infrastructure modules. Native stdlib only.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import importlib
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclasses.dataclass
class BenchmarkResult:
    benchmark_name: str
    module: str
    iterations: int
    total_time_ms: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    ops_per_sec: float
    memory_kb: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark": self.benchmark_name,
            "module": self.module,
            "iterations": self.iterations,
            "total_ms": round(self.total_time_ms, 2),
            "avg_ms": round(self.avg_time_ms, 4),
            "min_ms": round(self.min_time_ms, 4),
            "max_ms": round(self.max_time_ms, 4),
            "ops_per_sec": round(self.ops_per_sec, 2),
            "memory_kb": round(self.memory_kb, 2),
        }


class BenchmarkSuite:
    """Performance benchmark suite for MAGNATRIX-OS."""

    def __init__(self, repo_root: str) -> None:
        self.root = Path(repo_root).resolve()
        self._results: List[BenchmarkResult] = []

    def _import_module(self, path: str) -> Optional[Any]:
        try:
            sys.path.insert(0, str(self.root))
            mod = importlib.import_module(path)
            sys.path.pop(0)
            return mod
        except Exception:
            return None

    def _benchmark(self, fn: Callable, iterations: int = 1000) -> Tuple[float, float, float, float]:
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            fn()
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        return sum(times), min(times), max(times), sum(times) / len(times)

    def run_cache_benchmark(self) -> BenchmarkResult:
        mod = self._import_module("core.cache_manager_native")
        if not mod:
            return BenchmarkResult("cache_get_set", "cache", 0, 0, 0, 0, 0, 0, 0)
        tmp = tempfile.mkdtemp()
        cache = mod.CacheManager(max_memory_items=1000, disk_dir=tmp)
        total, mn, mx, avg = self._benchmark(lambda: cache.set("key", "value", ttl_seconds=60) or cache.get("key"), 1000)
        import shutil
        shutil.rmtree(tmp)
        return BenchmarkResult("cache_get_set", "cache", 1000, total, avg, mn, mx, 1000 / (total / 1000), 0)

    def run_crypto_benchmark(self) -> BenchmarkResult:
        mod = self._import_module("core.crypto_utilities_native")
        if not mod:
            return BenchmarkResult("sha256_hash", "crypto", 0, 0, 0, 0, 0, 0, 0)
        total, mn, mx, avg = self._benchmark(lambda: mod.CryptoUtilities.sha256("test_payload" * 100), 5000)
        return BenchmarkResult("sha256_hash", "crypto", 5000, total, avg, mn, mx, 5000 / (total / 1000), 0)

    def run_search_benchmark(self) -> BenchmarkResult:
        mod = self._import_module("core.search_engine_native")
        if not mod:
            return BenchmarkResult("search_query", "search", 0, 0, 0, 0, 0, 0, 0)
        tmp = tempfile.mkdtemp()
        engine = mod.SearchEngine(tmp)
        for i in range(100):
            engine.add_document(mod.Document(f"d{i}", f"Doc {i}", f"Content about topic {i} and Python programming"))
        total, mn, mx, avg = self._benchmark(lambda: engine.search("python"), 100)
        import shutil
        shutil.rmtree(tmp)
        return BenchmarkResult("search_query", "search", 100, total, avg, mn, mx, 100 / (total / 1000), 0)

    def run_context_benchmark(self) -> BenchmarkResult:
        mod = self._import_module("core.context_manager_native")
        if not mod:
            return BenchmarkResult("context_store", "context", 0, 0, 0, 0, 0, 0, 0)
        tmp = tempfile.mkdtemp()
        ctx = mod.ContextManager(tmp)
        total, mn, mx, avg = self._benchmark(
            lambda: ctx.store("benchmark content", mod.MemoryType.CONVERSATION), 500
        )
        import shutil
        shutil.rmtree(tmp)
        return BenchmarkResult("context_store", "context", 500, total, avg, mn, mx, 500 / (total / 1000), 0)

    def run_pipeline_benchmark(self) -> BenchmarkResult:
        mod = self._import_module("core.data_pipeline_native")
        if not mod:
            return BenchmarkResult("pipeline_map", "pipeline", 0, 0, 0, 0, 0, 0, 0)
        pipe = mod.DataPipeline("bench")
        pipe.map("increment", lambda x: x + 1)
        data = list(range(1000))
        total, mn, mx, avg = self._benchmark(lambda: pipe.run(data.copy()), 50)
        return BenchmarkResult("pipeline_map", "pipeline", 50, total, avg, mn, mx, 50 / (total / 1000), 0)

    def run_db_benchmark(self) -> BenchmarkResult:
        mod = self._import_module("core.database_layer_native")
        if not mod:
            return BenchmarkResult("db_insert", "db", 0, 0, 0, 0, 0, 0, 0)
        import os
        tmp = tempfile.mktemp(suffix=".db")
        db = mod.DatabaseManager(tmp)
        schema = mod.Schema("bench", [mod.Column("id", mod.ColumnType.INTEGER, primary_key=True), mod.Column("val", mod.ColumnType.TEXT)])
        db.create_table(schema)
        total, mn, mx, avg = self._benchmark(lambda: db.insert("bench", {"id": int(time.time() * 1000000) % 1000000, "val": "test"}), 500)
        db.close()
        os.remove(tmp)
        return BenchmarkResult("db_insert", "db", 500, total, avg, mn, mx, 500 / (total / 1000), 0)

    def run_guard_benchmark(self) -> BenchmarkResult:
        mod = self._import_module("core.prompt_injection_guard_native")
        if not mod:
            return BenchmarkResult("guard_scan", "guard", 0, 0, 0, 0, 0, 0, 0)
        guard = mod.PromptInjectionGuard()
        total, mn, mx, avg = self._benchmark(
            lambda: guard.scan("This is a normal user message with no harmful content"), 500
        )
        return BenchmarkResult("guard_scan", "guard", 500, total, avg, mn, mx, 500 / (total / 1000), 0)

    def run_all(self) -> List[BenchmarkResult]:
        print("=== MAGNATRIX-OS Benchmark Suite ===\n")
        benchmarks = [
            self.run_cache_benchmark,
            self.run_crypto_benchmark,
            self.run_search_benchmark,
            self.run_context_benchmark,
            self.run_pipeline_benchmark,
            self.run_db_benchmark,
            self.run_guard_benchmark,
        ]
        for bench_fn in benchmarks:
            result = bench_fn()
            self._results.append(result)
            print(f"  {result.benchmark_name}: {result.ops_per_sec:.0f} ops/sec | avg {result.avg_time_ms:.4f}ms")
        return self._results

    def summary(self) -> Dict[str, Any]:
        total_ops = sum(r.ops_per_sec for r in self._results)
        return {
            "benchmarks": len(self._results),
            "total_ops_per_sec": round(total_ops, 2),
            "results": [r.to_dict() for r in self._results],
        }

    def print_summary(self) -> None:
        print("\n" + "=" * 60)
        print("Benchmark Summary")
        print("=" * 60)
        for r in self._results:
            print(f"  {r.benchmark_name:20s} {r.ops_per_sec:8.0f} ops/sec  avg={r.avg_time_ms:.4f}ms")
        print("=" * 60)


# Load testing
class LoadTester:
    """Simple concurrent load tester."""

    def __init__(self) -> None:
        self._results: List[float] = []

    def run_concurrent(self, fn: Callable, workers: int = 10, iterations_per_worker: int = 100) -> Dict[str, Any]:
        errors = 0
        def worker():
            for _ in range(iterations_per_worker):
                try:
                    start = time.perf_counter()
                    fn()
                    self._results.append((time.perf_counter() - start) * 1000)
                except Exception:
                    nonlocal errors
                    errors += 1
        threads = [threading.Thread(target=worker) for _ in range(workers)]
        start = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total_time = (time.perf_counter() - start) * 1000
        total_reqs = workers * iterations_per_worker
        return {
            "workers": workers,
            "iterations_per_worker": iterations_per_worker,
            "total_requests": total_reqs,
            "total_time_ms": round(total_time, 2),
            "avg_latency_ms": round(sum(self._results) / max(1, len(self._results)), 4),
            "min_latency_ms": round(min(self._results), 4) if self._results else 0,
            "max_latency_ms": round(max(self._results), 4) if self._results else 0,
            "throughput_rps": round(total_reqs / (total_time / 1000), 2),
            "errors": errors,
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.exists(os.path.join(repo, "governance")):
        repo = os.getcwd()
    suite = BenchmarkSuite(repo)
    suite.run_all()
    suite.print_summary()

    # Load test
    print("\n--- Load Test ---")
    import hashlib
    tester = LoadTester()
    result = tester.run_concurrent(lambda: hashlib.sha256(b"test").hexdigest(), workers=4, iterations_per_worker=250)
    print(f"Load test: {result['throughput_rps']:.0f} req/sec, {result['avg_latency_ms']:.4f}ms avg, {result['errors']} errors")


if __name__ == "__main__":
    _demo()
