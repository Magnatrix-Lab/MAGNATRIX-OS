#!/usr/bin/env python3
"""
================================================================================
MAGNATRIX-OS — Agent Scheduler (Layer 0 Extension)
Inspired by: agiresearch/AIOS aios/scheduler/
FIFO + Round-Robin + Priority agent scheduling with time quantum,
context switch, and preemption.
================================================================================
Zero-dependency scheduler with multiple scheduling algorithms.
================================================================================
"""
from __future__ import annotations

import heapq
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# =============================================================================
# Constants
# =============================================================================
DEFAULT_QUANTUM_MS = 100.0
DEFAULT_PRIORITY_BOOST_INTERVAL = 5.0


# =============================================================================
# Data Types
# =============================================================================
class AgentState(Enum):
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    BLOCKED = "blocked"
    TERMINATED = "terminated"


class SchedulingAlgorithm(Enum):
    FIFO = "fifo"
    ROUND_ROBIN = "round_robin"
    PRIORITY = "priority"
    MULTI_LEVEL_FEEDBACK = "mlfq"


@dataclass
class AgentProcess:
    pid: str
    name: str
    priority: int = 5  # 1-10, lower = higher priority
    state: AgentState = AgentState.READY
    arrival_time: float = field(default_factory=time.time)
    burst_time_ms: float = 0.0
    remaining_time_ms: float = 0.0
    quantum_ms: float = DEFAULT_QUANTUM_MS
    waiting_time_ms: float = 0.0
    turnaround_time_ms: float = 0.0
    context_switches: int = 0
    agent_type: str = "general"
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Scheduler Base
# =============================================================================
class BaseScheduler(ABC):
    def __init__(self, algorithm: SchedulingAlgorithm) -> None:
        self.algorithm = algorithm
        self._queue: List[AgentProcess] = []
        self._running: Optional[AgentProcess] = None
        self._lock = threading.Lock()
        self._history: List[Dict[str, Any]] = []
        self._on_context_switch: List[Callable[[AgentProcess, Optional[AgentProcess]], None]] = []

    def on_context_switch(self, callback: Callable[[AgentProcess, Optional[AgentProcess]], None]) -> None:
        self._on_context_switch.append(callback)

    def _emit_switch(self, new_process: AgentProcess, old_process: Optional[AgentProcess]) -> None:
        for cb in self._on_context_switch:
            cb(new_process, old_process)

    @abstractmethod
    def enqueue(self, process: AgentProcess) -> None: ...

    @abstractmethod
    def dequeue(self) -> Optional[AgentProcess]: ...

    @abstractmethod
    def tick(self, elapsed_ms: float) -> Optional[AgentProcess]: ...

    def get_queue_snapshot(self) -> List[AgentProcess]:
        with self._lock:
            return list(self._queue)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._queue) + (1 if self._running else 0)
            avg_wait = sum(p.waiting_time_ms for p in self._queue) / max(len(self._queue), 1)
            return {
                "algorithm": self.algorithm.value,
                "queued": len(self._queue),
                "running": 1 if self._running else 0,
                "total": total,
                "avg_waiting_ms": avg_wait,
            }


# =============================================================================
# FIFO Scheduler
# =============================================================================
class FIFOScheduler(BaseScheduler):
    """First-In-First-Out scheduler."""

    def __init__(self) -> None:
        super().__init__(SchedulingAlgorithm.FIFO)

    def enqueue(self, process: AgentProcess) -> None:
        with self._lock:
            process.state = AgentState.READY
            self._queue.append(process)

    def dequeue(self) -> Optional[AgentProcess]:
        with self._lock:
            if not self._queue:
                return None
            return self._queue.pop(0)

    def tick(self, elapsed_ms: float) -> Optional[AgentProcess]:
        with self._lock:
            # Update waiting times
            for p in self._queue:
                p.waiting_time_ms += elapsed_ms
            if self._running and self._running.state == AgentState.RUNNING:
                self._running.burst_time_ms += elapsed_ms
                self._running.remaining_time_ms -= elapsed_ms
                if self._running.remaining_time_ms <= 0:
                    old = self._running
                    old.state = AgentState.TERMINATED
                    old.turnaround_time_ms = time.time() - old.arrival_time
                    self._running = None
                    next_p = self.dequeue()
                    if next_p:
                        next_p.state = AgentState.RUNNING
                        self._running = next_p
                        self._emit_switch(next_p, old)
                    return next_p
                return self._running
            elif not self._running:
                next_p = self.dequeue()
                if next_p:
                    next_p.state = AgentState.RUNNING
                    self._running = next_p
                    self._emit_switch(next_p, None)
                return next_p
            return self._running


# =============================================================================
# Round-Robin Scheduler
# =============================================================================
class RoundRobinScheduler(BaseScheduler):
    """Round-robin with configurable time quantum."""

    def __init__(self, quantum_ms: float = DEFAULT_QUANTUM_MS) -> None:
        super().__init__(SchedulingAlgorithm.ROUND_ROBIN)
        self.quantum_ms = quantum_ms
        self._current_quantum_used = 0.0

    def enqueue(self, process: AgentProcess) -> None:
        with self._lock:
            process.state = AgentState.READY
            process.quantum_ms = self.quantum_ms
            self._queue.append(process)

    def dequeue(self) -> Optional[AgentProcess]:
        with self._lock:
            if not self._queue:
                return None
            return self._queue.pop(0)

    def tick(self, elapsed_ms: float) -> Optional[AgentProcess]:
        with self._lock:
            for p in self._queue:
                p.waiting_time_ms += elapsed_ms
            if self._running:
                self._running.burst_time_ms += elapsed_ms
                self._running.remaining_time_ms -= elapsed_ms
                self._current_quantum_used += elapsed_ms
                if self._current_quantum_used >= self.quantum_ms:
                    # Preempt
                    old = self._running
                    old.state = AgentState.READY
                    old.context_switches += 1
                    self._queue.append(old)
                    self._running = None
                    self._current_quantum_used = 0.0
                    next_p = self.dequeue()
                    if next_p:
                        next_p.state = AgentState.RUNNING
                        self._running = next_p
                        self._emit_switch(next_p, old)
                    return next_p
                if self._running.remaining_time_ms <= 0:
                    old = self._running
                    old.state = AgentState.TERMINATED
                    old.turnaround_time_ms = time.time() - old.arrival_time
                    self._running = None
                    self._current_quantum_used = 0.0
                    next_p = self.dequeue()
                    if next_p:
                        next_p.state = AgentState.RUNNING
                        self._running = next_p
                        self._emit_switch(next_p, old)
                    return next_p
                return self._running
            else:
                next_p = self.dequeue()
                if next_p:
                    next_p.state = AgentState.RUNNING
                    self._running = next_p
                    self._current_quantum_used = 0.0
                    self._emit_switch(next_p, None)
                return next_p


# =============================================================================
# Priority Scheduler
# =============================================================================
class PriorityScheduler(BaseScheduler):
    """Priority-based preemptive scheduler."""

    def __init__(self) -> None:
        super().__init__(SchedulingAlgorithm.PRIORITY)
        self._counter = 0  # Tie-breaker for FIFO within same priority

    def enqueue(self, process: AgentProcess) -> None:
        with self._lock:
            process.state = AgentState.READY
            self._counter += 1
            # Heap: (priority, arrival_order, process)
            heapq.heappush(self._queue, (process.priority, self._counter, process))

    def dequeue(self) -> Optional[AgentProcess]:
        with self._lock:
            if not self._queue:
                return None
            return heapq.heappop(self._queue)[2]

    def tick(self, elapsed_ms: float) -> Optional[AgentProcess]:
        with self._lock:
            for p in self._queue:
                p.waiting_time_ms += elapsed_ms
            # Check if higher priority process arrived
            if self._queue and self._running:
                top_priority = self._queue[0][2].priority
                if top_priority < self._running.priority:
                    # Preempt
                    old = self._running
                    old.state = AgentState.READY
                    old.context_switches += 1
                    self._counter += 1
                    heapq.heappush(self._queue, (old.priority, self._counter, old))
                    self._running = None
                    next_p = self.dequeue()
                    if next_p:
                        next_p.state = AgentState.RUNNING
                        self._running = next_p
                        self._emit_switch(next_p, old)
                    return next_p
            if self._running:
                self._running.burst_time_ms += elapsed_ms
                self._running.remaining_time_ms -= elapsed_ms
                if self._running.remaining_time_ms <= 0:
                    old = self._running
                    old.state = AgentState.TERMINATED
                    old.turnaround_time_ms = time.time() - old.arrival_time
                    self._running = None
                    next_p = self.dequeue()
                    if next_p:
                        next_p.state = AgentState.RUNNING
                        self._running = next_p
                        self._emit_switch(next_p, old)
                    return next_p
                return self._running
            else:
                next_p = self.dequeue()
                if next_p:
                    next_p.state = AgentState.RUNNING
                    self._running = next_p
                    self._emit_switch(next_p, None)
                return next_p


# =============================================================================
# Multi-Level Feedback Queue
# =============================================================================
class MLFQScheduler(BaseScheduler):
    """Multi-level feedback queue with aging."""

    def __init__(self, num_queues: int = 3, base_quantum: float = 50.0) -> None:
        super().__init__(SchedulingAlgorithm.MULTI_LEVEL_FEEDBACK)
        self.num_queues = num_queues
        self.base_quantum = base_quantum
        self._queues: List[List[AgentProcess]] = [[] for _ in range(num_queues)]
        self._quantums = [base_quantum * (2 ** i) for i in range(num_queues)]
        self._last_boost = time.time()

    def enqueue(self, process: AgentProcess) -> None:
        with self._lock:
            process.state = AgentState.READY
            # New processes start at highest priority queue
            self._queues[0].append(process)

    def dequeue(self) -> Optional[AgentProcess]:
        with self._lock:
            for q in self._queues:
                if q:
                    return q.pop(0)
            return None

    def tick(self, elapsed_ms: float) -> Optional[AgentProcess]:
        with self._lock:
            # Priority boost to prevent starvation
            if time.time() - self._last_boost > DEFAULT_PRIORITY_BOOST_INTERVAL:
                for i in range(1, self.num_queues):
                    for p in self._queues[i]:
                        p.priority = max(1, p.priority - 1)
                    self._queues[0].extend(self._queues[i])
                    self._queues[i].clear()
                self._last_boost = time.time()
            # Update waiting times
            for q in self._queues:
                for p in q:
                    p.waiting_time_ms += elapsed_ms
            if self._running:
                self._running.burst_time_ms += elapsed_ms
                self._running.remaining_time_ms -= elapsed_ms
                # Check quantum expiration
                queue_idx = self._running.metadata.get("queue_idx", 0)
                used = self._running.metadata.get("quantum_used", 0.0) + elapsed_ms
                if used >= self._quantums[queue_idx] or self._running.remaining_time_ms <= 0:
                    old = self._running
                    if self._running.remaining_time_ms > 0:
                        # Demote to lower queue
                        new_idx = min(queue_idx + 1, self.num_queues - 1)
                        old.state = AgentState.READY
                        old.metadata["queue_idx"] = new_idx
                        old.metadata["quantum_used"] = 0.0
                        self._queues[new_idx].append(old)
                    else:
                        old.state = AgentState.TERMINATED
                        old.turnaround_time_ms = time.time() - old.arrival_time
                    self._running = None
                    next_p = self.dequeue()
                    if next_p:
                        next_p.state = AgentState.RUNNING
                        next_p.metadata["quantum_used"] = 0.0
                        self._running = next_p
                        self._emit_switch(next_p, old)
                    return next_p
                else:
                    self._running.metadata["quantum_used"] = used
                return self._running
            else:
                next_p = self.dequeue()
                if next_p:
                    next_p.state = AgentState.RUNNING
                    next_p.metadata["quantum_used"] = 0.0
                    self._running = next_p
                    self._emit_switch(next_p, None)
                return next_p


# =============================================================================
# Scheduler Factory
# =============================================================================
class SchedulerFactory:
    @staticmethod
    def create(algorithm: SchedulingAlgorithm, **kwargs: Any) -> BaseScheduler:
        if algorithm == SchedulingAlgorithm.FIFO:
            return FIFOScheduler()
        elif algorithm == SchedulingAlgorithm.ROUND_ROBIN:
            return RoundRobinScheduler(kwargs.get("quantum_ms", DEFAULT_QUANTUM_MS))
        elif algorithm == SchedulingAlgorithm.PRIORITY:
            return PriorityScheduler()
        elif algorithm == SchedulingAlgorithm.MULTI_LEVEL_FEEDBACK:
            return MLFQScheduler(
                kwargs.get("num_queues", 3),
                kwargs.get("base_quantum", DEFAULT_QUANTUM_MS),
            )
        return FIFOScheduler()


# =============================================================================
# Scheduler Engine
# =============================================================================
class SchedulerEngine:
    """Top-level scheduler with auto-tick and process lifecycle."""

    def __init__(self, algorithm: SchedulingAlgorithm = SchedulingAlgorithm.ROUND_ROBIN) -> None:
        self.scheduler = SchedulerFactory.create(algorithm)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._tick_ms = 10.0
        self._processes: Dict[str, AgentProcess] = {}
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[AgentProcess], None]] = []

    def on_complete(self, callback: Callable[[AgentProcess], None]) -> None:
        self._callbacks.append(callback)

    def spawn(self, pid: str, name: str, burst_ms: float, priority: int = 5, agent_type: str = "general", metadata: Optional[Dict[str, Any]] = None) -> AgentProcess:
        proc = AgentProcess(
            pid=pid,
            name=name,
            priority=priority,
            burst_time_ms=0.0,
            remaining_time_ms=burst_ms,
            agent_type=agent_type,
            metadata=metadata or {},
        )
        with self._lock:
            self._processes[pid] = proc
        self.scheduler.enqueue(proc)
        return proc

    def kill(self, pid: str) -> bool:
        with self._lock:
            proc = self._processes.get(pid)
        if proc:
            proc.state = AgentState.TERMINATED
            proc.remaining_time_ms = 0
            return True
        return False

    def block(self, pid: str) -> bool:
        with self._lock:
            proc = self._processes.get(pid)
        if proc and proc.state == AgentState.RUNNING:
            proc.state = AgentState.BLOCKED
            return True
        return False

    def unblock(self, pid: str) -> bool:
        with self._lock:
            proc = self._processes.get(pid)
        if proc and proc.state == AgentState.BLOCKED:
            proc.state = AgentState.READY
            self.scheduler.enqueue(proc)
            return True
        return False

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while self._running:
            self.scheduler.tick(self._tick_ms)
            # Check for completed processes
            for pid, proc in list(self._processes.items()):
                if proc.state == AgentState.TERMINATED:
                    for cb in self._callbacks:
                        cb(proc)
                    with self._lock:
                        if self._processes.get(pid) and self._processes[pid].state == AgentState.TERMINATED:
                            pass  # Keep for stats
            time.sleep(self._tick_ms / 1000.0)

    def stop(self) -> None:
        self._running = False

    def get_processes(self, state: Optional[AgentState] = None) -> List[AgentProcess]:
        with self._lock:
            procs = list(self._processes.values())
        if state:
            procs = [p for p in procs if p.state == state]
        return procs

    def __enter__(self) -> SchedulerEngine:
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.stop()


# =============================================================================
# Scheduler Kernel Bridge
# =============================================================================
class SchedulerKernelBridge:
    def __init__(self, engine: SchedulerEngine, event_bus: Any = None) -> None:
        self.engine = engine
        self.bus = event_bus
        engine.scheduler.on_context_switch(self._on_switch)
        engine.on_complete(self._on_complete)

    def _on_switch(self, new_proc: AgentProcess, old_proc: Optional[AgentProcess]) -> None:
        if self.bus:
            self.bus.publish("scheduler.context_switch", {
                "new_pid": new_proc.pid,
                "old_pid": old_proc.pid if old_proc else None,
                "new_name": new_proc.name,
            })

    def _on_complete(self, proc: AgentProcess) -> None:
        if self.bus:
            self.bus.publish("scheduler.completed", {
                "pid": proc.pid,
                "name": proc.name,
                "turnaround_ms": proc.turnaround_time_ms * 1000,
                "burst_ms": proc.burst_time_ms,
                "waits": proc.waiting_time_ms,
            })


# =============================================================================
# Demo
# =============================================================================
def run_demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Agent Scheduler Demo")
    print("=" * 60)
    for algo in [SchedulingAlgorithm.FIFO, SchedulingAlgorithm.ROUND_ROBIN, SchedulingAlgorithm.PRIORITY]:
        print(f"\n--- {algo.value.upper()} ---")
        engine = SchedulerEngine(algo)
        engine.spawn("p1", "agent-alpha", burst_ms=200, priority=3)
        engine.spawn("p2", "agent-beta", burst_ms=150, priority=1)
        engine.spawn("p3", "agent-gamma", burst_ms=100, priority=5)
        # Manual ticks
        for _ in range(50):
            engine.scheduler.tick(10.0)
        stats = engine.scheduler.stats()
        print(f"Stats: {stats}")
        procs = engine.get_processes()
        for p in procs:
            print(f"  {p.pid}: {p.name} — state={p.state.value}, burst={p.burst_time_ms:.0f}ms, wait={p.waiting_time_ms:.0f}ms")
    print("\nDemo complete.")


if __name__ == "__main__":
    run_demo()
