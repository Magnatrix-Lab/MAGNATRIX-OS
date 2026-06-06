#!/usr/bin/env python3
"""
Performance Profiler for MAGNATRIX-OS
CPU and memory profiling per module, function-level timing,
and bottleneck detection. Native stdlib only (time, tracemalloc).

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import time
import tracemalloc
from typing import Any, Callable, Dict, List, Optional


@dataclasses.dataclass
class ProfileResult:
    module_name: str
    function_name: str
    call_count: int
    total_time_ms: float
    avg_time_ms: float
    max_time_ms: float
    memory_delta_kb: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module": self.module_name,
            "function": self.function_name,
            "calls": self.call_count,
            "total_ms": round(self.total_time_ms, 2),
            "avg_ms": round(self.avg_time_ms, 2),
            "max_ms": round(self.max_time_ms, 2),
            "memory_kb": round(self.memory_delta_kb, 2),
        }


class PerformanceProfiler:
    """Profiles module and function performance with memory tracking."""

    def __init__(self, top_n: int = 20) -> None:
        self.top_n = top_n
        self._profiles: Dict[str, ProfileResult] = {}
        self._active: Dict[str, Dict[str, Any]] = {}
        self._tracemalloc_started = False

    # ------------------------------------------------------------------
    # Profiling
    # ------------------------------------------------------------------

    def start(self) -> None:
        if not self._tracemalloc_started:
            tracemalloc.start()
            self._tracemalloc_started = True

    def stop(self) -> None:
        if self._tracemalloc_started:
            tracemalloc.stop()
            self._tracemalloc_started = False

    def profile(self, module_name: str, function_name: str) -> Callable:
        """Decorator to profile a function."""
        key = f"{module_name}.{function_name}"
        def decorator(fn: Callable) -> Callable:
            def wrapper(*args, **kwargs) -> Any:
                start = time.perf_counter()
                mem_start = 0
                if self._tracemalloc_started:
                    mem_start, _ = tracemalloc.get_traced_memory()
                result = fn(*args, **kwargs)
                elapsed = (time.perf_counter() - start) * 1000
                mem_delta = 0
                if self._tracemalloc_started:
                    mem_end, _ = tracemalloc.get_traced_memory()
                    mem_delta = (mem_end - mem_start) / 1024
                if key not in self._profiles:
                    self._profiles[key] = ProfileResult(module_name, function_name, 0, 0, 0, 0, 0)
                prof = self._profiles[key]
                prof.call_count += 1
                prof.total_time_ms += elapsed
                prof.avg_time_ms = prof.total_time_ms / prof.call_count
                prof.max_time_ms = max(prof.max_time_ms, elapsed)
                prof.memory_delta_kb += mem_delta
                return result
            return wrapper
        return decorator

    def profile_call(self, module_name: str, function_name: str, fn: Callable, *args: Any, **kwargs: Any) -> Tuple[Any, ProfileResult]:
        key = f"{module_name}.{function_name}"
        start = time.perf_counter()
        mem_start = 0
        if self._tracemalloc_started:
            mem_start, _ = tracemalloc.get_traced_memory()
        result = fn(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        mem_delta = 0
        if self._tracemalloc_started:
            mem_end, _ = tracemalloc.get_traced_memory()
            mem_delta = (mem_end - mem_start) / 1024
        if key not in self._profiles:
            self._profiles[key] = ProfileResult(module_name, function_name, 0, 0, 0, 0, 0)
        prof = self._profiles[key]
        prof.call_count += 1
        prof.total_time_ms += elapsed
        prof.avg_time_ms = prof.total_time_ms / prof.call_count
        prof.max_time_ms = max(prof.max_time_ms, elapsed)
        prof.memory_delta_kb += mem_delta
        return result, prof

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def get_slowest(self, limit: int = 10) -> List[ProfileResult]:
        return sorted(self._profiles.values(), key=lambda p: p.total_time_ms, reverse=True)[:limit]

    def get_highest_memory(self, limit: int = 10) -> List[ProfileResult]:
        return sorted(self._profiles.values(), key=lambda p: p.memory_delta_kb, reverse=True)[:limit]

    def get_most_called(self, limit: int = 10) -> List[ProfileResult]:
        return sorted(self._profiles.values(), key=lambda p: p.call_count, reverse=True)[:limit]

    def get_report(self) -> Dict[str, Any]:
        total_time = sum(p.total_time_ms for p in self._profiles.values())
        total_calls = sum(p.call_count for p in self._profiles.values())
        return {
            "total_functions": len(self._profiles),
            "total_calls": total_calls,
            "total_time_ms": round(total_time, 2),
            "avg_time_per_call_ms": round(total_time / max(1, total_calls), 2),
            "slowest": [p.to_dict() for p in self.get_slowest(self.top_n)],
            "highest_memory": [p.to_dict() for p in self.get_highest_memory(self.top_n)],
            "most_called": [p.to_dict() for p in self.get_most_called(self.top_n)],
        }

    def reset(self) -> None:
        self._profiles.clear()

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        return {
            "profiled_functions": len(self._profiles),
            "tracemalloc_active": self._tracemalloc_started,
            "top_n": self.top_n,
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    prof = PerformanceProfiler(top_n=5)
    prof.start()
    print("=== Performance Profiler Demo ===\n")
    @prof.profile("demo", "slow_function")
    def slow_function(n: int) -> int:
        time.sleep(0.01)
        return sum(range(n))
    @prof.profile("demo", "fast_function")
    def fast_function() -> str:
        return "hello"
    for i in range(10):
        slow_function(1000)
    for _ in range(100):
        fast_function()
    print(f"Report: {prof.get_report()}")
    print(f"Stats: {prof.stats()}")
    prof.stop()


if __name__ == "__main__":
    _demo()
