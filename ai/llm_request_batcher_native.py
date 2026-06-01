"""Request Batcher — Batch LLM requests for efficiency, cost reduction, throughput optimization.

Modul ini menyediakan:
- RequestBatch: collect multiple requests into a batch
- BatchScheduler: schedule batch execution with timing policies
- BatchExecutor: execute batches with result mapping
- DynamicBatcher: auto-batch based on request rate
- BatchMetrics: track batch efficiency and savings
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum, auto


class BatchPolicy(Enum):
    FIXED_SIZE = auto()
    FIXED_TIME = auto()
    DYNAMIC = auto()
    HYBRID = auto()


@dataclass
class BatchRequest:
    """Single request in a batch."""
    request_id: str
    prompt: str
    priority: int = 0
    max_tokens: int = 256
    temperature: float = 0.7
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class BatchResult:
    """Result of a single request in a batch."""
    request_id: str
    response: str = ""
    tokens_used: int = 0
    latency: float = 0.0
    error: Optional[str] = None


@dataclass
class RequestBatch:
    """A batch of requests."""
    batch_id: str
    requests: List[BatchRequest]
    created_at: float = field(default_factory=time.time)
    submitted_at: Optional[float] = None
    completed_at: Optional[float] = None
    results: List[BatchResult] = field(default_factory=list)
    status: str = "pending"  # pending, running, completed, failed

    def size(self) -> int:
        return len(self.requests)

    def total_tokens(self) -> int:
        return sum(len(r.prompt.split()) for r in self.requests)

    def avg_priority(self) -> float:
        return sum(r.priority for r in self.requests) / max(len(self.requests), 1)


class BatchScheduler:
    """Schedule batch execution with timing policies."""

    def __init__(self, policy: BatchPolicy = BatchPolicy.HYBRID,
                 max_size: int = 10, max_wait_ms: float = 100.0):
        self.policy = policy
        self.max_size = max_size
        self.max_wait = max_wait_ms / 1000.0
        self._queue: List[BatchRequest] = []
        self._batches: List[RequestBatch] = []
        self._last_batch_time: float = 0.0

    def add(self, request: BatchRequest) -> Optional[RequestBatch]:
        self._queue.append(request)
        return self._check_flush()

    def add_many(self, requests: List[BatchRequest]) -> Optional[RequestBatch]:
        self._queue.extend(requests)
        return self._check_flush()

    def _check_flush(self) -> Optional[RequestBatch]:
        if not self._queue:
            return None
        should_flush = False
        if self.policy == BatchPolicy.FIXED_SIZE and len(self._queue) >= self.max_size:
            should_flush = True
        elif self.policy == BatchPolicy.FIXED_TIME and time.time() - self._last_batch_time >= self.max_wait:
            should_flush = True
        elif self.policy == BatchPolicy.DYNAMIC and len(self._queue) >= self.max_size:
            should_flush = True
        elif self.policy == BatchPolicy.HYBRID:
            if len(self._queue) >= self.max_size:
                should_flush = True
            elif self._queue and time.time() - self._last_batch_time >= self.max_wait:
                should_flush = True
        if should_flush:
            return self._flush()
        return None

    def _flush(self) -> RequestBatch:
        batch = RequestBatch(
            batch_id=str(uuid.uuid4())[:12],
            requests=list(self._queue)
        )
        self._queue.clear()
        self._last_batch_time = time.time()
        self._batches.append(batch)
        return batch

    def force_flush(self) -> Optional[RequestBatch]:
        if self._queue:
            return self._flush()
        return None

    def get_pending_count(self) -> int:
        return len(self._queue)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "policy": self.policy.name,
            "pending": len(self._queue),
            "batches": len(self._batches),
            "max_size": self.max_size,
            "max_wait_ms": self.max_wait * 1000
        }


class BatchExecutor:
    """Execute batches with result mapping."""

    def __init__(self, execute_fn: Optional[Callable[[List[BatchRequest]], List[BatchResult]]] = None):
        self.execute_fn = execute_fn or self._default_execute
        self._history: List[RequestBatch] = []

    def execute(self, batch: RequestBatch) -> RequestBatch:
        batch.status = "running"
        batch.submitted_at = time.time()
        try:
            results = self.execute_fn(batch.requests)
            batch.results = results
            batch.status = "completed"
        except Exception as e:
            batch.status = "failed"
            for req in batch.requests:
                batch.results.append(BatchResult(req.request_id, error=str(e)))
        batch.completed_at = time.time()
        self._history.append(batch)
        return batch

    def _default_execute(self, requests: List[BatchRequest]) -> List[BatchResult]:
        # Simulated batch execution
        results = []
        for req in requests:
            start = time.time()
            response = f"[Response to: {req.prompt[:40]}...]"
            latency = time.time() - start
            results.append(BatchResult(
                request_id=req.request_id,
                response=response,
                tokens_used=len(req.prompt.split()) + 20,
                latency=latency
            ))
        return results

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._history)
        completed = sum(1 for b in self._history if b.status == "completed")
        total_latency = sum((b.completed_at or 0) - (b.submitted_at or 0) for b in self._history)
        return {
            "total_batches": total,
            "completed": completed,
            "failed": total - completed,
            "avg_batch_latency": round(total_latency / max(total, 1), 4)
        }


class DynamicBatcher:
    """Auto-batch based on request rate and system load."""

    def __init__(self, min_size: int = 2, max_size: int = 32, target_latency_ms: float = 200.0):
        self.min_size = min_size
        self.max_size = max_size
        self.target_latency = target_latency_ms / 1000.0
        self._scheduler = BatchScheduler(BatchPolicy.DYNAMIC, max_size, target_latency_ms)
        self._executor = BatchExecutor()
        self._request_times: List[float] = []
        self._latency_history: List[float] = []

    def submit(self, request: BatchRequest) -> Optional[RequestBatch]:
        self._request_times.append(time.time())
        # Adjust max_size based on rate
        self._adjust_batch_size()
        batch = self._scheduler.add(request)
        if batch:
            return self._executor.execute(batch)
        return None

    def _adjust_batch_size(self) -> None:
        # Calculate recent request rate
        recent = [t for t in self._request_times if time.time() - t < 1.0]
        rate = len(recent)
        if rate > 50:  # High rate -> larger batches
            self._scheduler.max_size = min(self.max_size, self._scheduler.max_size + 1)
        elif rate < 10:  # Low rate -> smaller batches
            self._scheduler.max_size = max(self.min_size, self._scheduler.max_size - 1)
        # Adjust based on latency
        if self._latency_history:
            avg_latency = sum(self._latency_history) / len(self._latency_history)
            if avg_latency > self.target_latency:
                self._scheduler.max_size = max(self.min_size, self._scheduler.max_size - 2)

    def flush(self) -> Optional[RequestBatch]:
        batch = self._scheduler.force_flush()
        if batch:
            result = self._executor.execute(batch)
            if result.completed_at and result.submitted_at:
                self._latency_history.append(result.completed_at - result.submitted_at)
                self._latency_history = self._latency_history[-20:]  # Keep last 20
            return result
        return None

    def get_stats(self) -> Dict[str, Any]:
        return {
            "scheduler": self._scheduler.get_stats(),
            "executor": self._executor.get_stats(),
            "current_max_size": self._scheduler.max_size,
            "avg_latency": round(sum(self._latency_history) / max(len(self._latency_history), 1), 4)
        }


class BatchMetrics:
    """Track batch efficiency and cost savings."""

    def __init__(self):
        self._batches: List[RequestBatch] = []

    def record(self, batch: RequestBatch) -> None:
        self._batches.append(batch)

    def compute_savings(self) -> Dict[str, Any]:
        """Estimate cost savings from batching."""
        total_requests = sum(b.size() for b in self._batches)
        total_batches = len(self._batches)
        # Assume single-request overhead = 100%, batch overhead = 50% per request
        single_cost = total_requests * 1.0
        batch_cost = total_requests * 0.5 + total_batches * 0.3
        savings = single_cost - batch_cost
        return {
            "total_requests": total_requests,
            "total_batches": total_batches,
            "avg_batch_size": round(total_requests / max(total_batches, 1), 2),
            "estimated_savings": round(savings, 2),
            "savings_percent": round(savings / max(single_cost, 1) * 100, 2)
        }

    def get_latency_stats(self) -> Dict[str, float]:
        latencies = []
        for b in self._batches:
            if b.completed_at and b.submitted_at:
                latencies.append(b.completed_at - b.submitted_at)
        if not latencies:
            return {}
        return {
            "avg": round(sum(latencies) / len(latencies), 4),
            "min": round(min(latencies), 4),
            "max": round(max(latencies), 4)
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "savings": self.compute_savings(),
            "latency": self.get_latency_stats()
        }


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("REQUEST BATCHER DEMO")
    print("=" * 70)

    # 1. Fixed size batching
    print("\n[1] Fixed Size Batching")
    scheduler = BatchScheduler(BatchPolicy.FIXED_SIZE, max_size=3)
    for i in range(7):
        req = BatchRequest(f"req-{i}", f"Prompt {i}", priority=i)
        batch = scheduler.add(req)
        if batch:
            print(f"  Batch flushed: {batch.batch_id} with {batch.size()} requests")
    # Force flush remaining
    remaining = scheduler.force_flush()
    if remaining:
        print(f"  Final flush: {remaining.size()} requests")
    print(f"  Stats: {scheduler.get_stats()}")

    # 2. Batch execution
    print("\n[2] Batch Execution")
    executor = BatchExecutor()
    batch = RequestBatch("b1", [
        BatchRequest("r1", "What is Python?"),
        BatchRequest("r2", "Explain loops"),
        BatchRequest("r3", "How to use dicts?")
    ])
    result = executor.execute(batch)
    print(f"  Batch status: {result.status}")
    for r in result.results:
        print(f"    {r.request_id}: {r.tokens_used} tokens, {r.latency:.4f}s")
    print(f"  Executor stats: {executor.get_stats()}")

    # 3. Dynamic batcher
    print("\n[3] Dynamic Batcher")
    db = DynamicBatcher(min_size=2, max_size=8)
    for i in range(12):
        req = BatchRequest(f"dyn-{i}", f"Dynamic prompt {i}")
        result = db.submit(req)
        if result:
            print(f"  Batch executed: {result.size()} requests")
    # Flush remaining
    final = db.flush()
    if final:
        print(f"  Final flush: {final.size()} requests")
    print(f"  Stats: {db.get_stats()}")

    # 4. Metrics
    print("\n[4] Batch Metrics")
    metrics = BatchMetrics()
    for b in executor._history:
        metrics.record(b)
    for b in db._executor._history:
        metrics.record(b)
    print(f"  Stats: {metrics.get_stats()}")

    # 5. Hybrid policy
    print("\n[5] Hybrid Policy (time + size)")
    hybrid = BatchScheduler(BatchPolicy.HYBRID, max_size=5, max_wait_ms=50.0)
    for i in range(4):
        hybrid.add(BatchRequest(f"h-{i}", f"Hybrid {i}"))
    time.sleep(0.06)  # Trigger time-based flush
    batch = hybrid.add(BatchRequest("h-4", "Trigger"))
    if batch:
        print(f"  Time-triggered batch: {batch.size()} requests")
    print(f"  Stats: {hybrid.get_stats()}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
