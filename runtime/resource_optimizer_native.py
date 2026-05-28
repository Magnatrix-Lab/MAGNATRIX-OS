#!/usr/bin/env python3
"""Resource Optimizer — MAGNATRIX-OS ASI Expansion
Path: runtime/resource_optimizer_native.py
License: AGPL-3.0
Depends: Python 3.11+ stdlib only.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class Resource:
    name: str
    capacity: float
    used: float = 0.0
    cost_per_unit: float = 1.0
    priority: float = 1.0

    @property
    def available(self) -> float:
        return max(0.0, self.capacity - self.used)

    @property
    def utilization(self) -> float:
        return self.used / self.capacity if self.capacity > 0 else 0.0


@dataclass
class Task:
    task_id: str
    name: str
    cpu: float
    memory: float
    gpu: float
    deadline: float  # relative time units
    value: float  # business value


class ResourceOptimizer:
    def __init__(self):
        self.resources: Dict[str, Resource] = {}
        self.allocations: Dict[str, Dict[str, float]] = {}
        self.history: List[Dict] = []

    def register(self, r: Resource) -> None:
        self.resources[r.name] = r

    def allocate(self, task: Task) -> Tuple[bool, Dict[str, float]]:
        """Knapsack-style greedy allocation by value/demand ratio."""
        req = {"cpu": task.cpu, "memory": task.memory, "gpu": task.gpu}
        for name, need in req.items():
            if name not in self.resources or self.resources[name].available < need:
                return False, {}
        # Allocate
        for name, need in req.items():
            self.resources[name].used += need
        self.allocations[task.task_id] = req
        return True, req

    def release(self, task_id: str) -> None:
        if task_id in self.allocations:
            for name, amount in self.allocations[task_id].items():
                if name in self.resources:
                    self.resources[name].used = max(0.0, self.resources[name].used - amount)
            del self.allocations[task_id]

    def optimize_pareto(self, tasks: List[Task]) -> List[Task]:
        """Select subset maximizing value with resource constraints."""
        sorted_tasks = sorted(tasks, key=lambda t: t.value / (t.cpu + t.memory + t.gpu + 0.001), reverse=True)
        selected = []
        for t in sorted_tasks:
            ok, _ = self.allocate(t)
            if ok:
                selected.append(t)
        return selected

    def rebalance(self) -> Dict[str, float]:
        """Suggest rebalancing based on utilization."""
        suggestions = {}
        for name, r in self.resources.items():
            if r.utilization > 0.85:
                suggestions[name] = f"Scale up: {r.utilization:.1%} util"
            elif r.utilization < 0.3:
                suggestions[name] = f"Scale down: {r.utilization:.1%} util"
        return suggestions


def _self_test():
    print("=" * 55)
    print("Resource Optimizer — Self Test")
    print("=" * 55)
    passed = 0
    total = 4

    opt = ResourceOptimizer()
    opt.register(Resource("cpu", 100.0, cost_per_unit=0.5))
    opt.register(Resource("memory", 1000.0, cost_per_unit=0.1))
    opt.register(Resource("gpu", 10.0, cost_per_unit=2.0))

    t1 = Task("t1", "Model Training", cpu=40, memory=300, gpu=4, deadline=10, value=100)
    t2 = Task("t2", "Inference", cpu=10, memory=100, gpu=1, deadline=5, value=50)
    t3 = Task("t3", "Data Pipeline", cpu=60, memory=600, gpu=0, deadline=8, value=80)

    ok, _ = opt.allocate(t1)
    print(f"[Test 1] Allocate t1: {ok} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    ok2, _ = opt.allocate(t2)
    print(f"[Test 2] Allocate t2: {ok2} — {'PASS' if ok2 else 'FAIL'}")
    passed += ok2

    ok3, _ = opt.allocate(t3)
    print(f"[Test 3] Reject t3 (over-capacity): {not ok3} — {'PASS' if not ok3 else 'FAIL'}")
    passed += (not ok3)

    opt.release("t1")
    ok4, _ = opt.allocate(t3)
    print(f"[Test 4] After release, t3 fits: {ok4} — {'PASS' if ok4 else 'FAIL'}")
    passed += ok4

    print(f"PASS: {passed}/{total}")
    print("=" * 55)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
