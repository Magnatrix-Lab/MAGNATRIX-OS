"""Batch Inference Engine — Optimized batch processing for LLM inference.

Modul ini menyediakan:
- BatchRequest untuk batch inference requests
- BatchBuilder untuk dynamic batching dengan padding
- BatchExecutor untuk parallel execution dalam batch
- BatchOptimizer untuk padding optimization dan batch size tuning
- BatchInferenceEngine untuk end-to-end batch inference
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class BatchStatus(Enum):
    PENDING = auto()
    BUILDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    PARTIAL = auto()
    FAILED = auto()


@dataclass
class InferenceRequest:
    """Single inference request."""
    request_id: str
    prompt: str
    max_tokens: int = 256
    temperature: float = 0.7
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    submitted_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    result: Optional[str] = None
    latency_ms: float = 0.0


@dataclass
class Batch:
    """Batch of inference requests."""
    batch_id: str
    requests: List[InferenceRequest] = field(default_factory=list)
    status: BatchStatus = BatchStatus.PENDING
    max_tokens: int = 0
    padding_tokens: int = 0
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    total_latency_ms: float = 0.0


class BatchBuilder:
    """Build optimal batches from incoming requests."""

    def __init__(self, max_batch_size: int = 8, max_tokens_per_batch: int = 4096, timeout_ms: float = 50.0):
        self.max_batch_size = max_batch_size
        self.max_tokens_per_batch = max_tokens_per_batch
        self.timeout_ms = timeout_ms
        self._pending: List[InferenceRequest] = []

    def add_request(self, request: InferenceRequest) -> None:
        self._pending.append(request)

    def build(self) -> Optional[Batch]:
        if not self._pending:
            return None
        # Sort by priority then timestamp
        self._pending.sort(key=lambda r: (-r.priority, r.submitted_at))
        # Take requests up to max batch size
        batch_requests = self._pending[:self.max_batch_size]
        # Check token budget
        total_tokens = sum(r.max_tokens for r in batch_requests)
        if total_tokens > self.max_tokens_per_batch:
            # Trim to fit token budget
            cumsum = 0
            trimmed = []
            for r in batch_requests:
                if cumsum + r.max_tokens <= self.max_tokens_per_batch:
                    trimmed.append(r)
                    cumsum += r.max_tokens
                else:
                    break
            batch_requests = trimmed
        if not batch_requests:
            return None
        # Remove from pending
        self._pending = self._pending[len(batch_requests):]
        batch = Batch(
            batch_id=str(uuid.uuid4())[:12],
            requests=batch_requests,
            max_tokens=max(r.max_tokens for r in batch_requests),
        )
        # Calculate padding waste
        batch.padding_tokens = sum(batch.max_tokens - r.max_tokens for r in batch_requests)
        return batch

    def get_pending_count(self) -> int:
        return len(self._pending)

    def should_build(self) -> bool:
        if len(self._pending) >= self.max_batch_size:
            return True
        if self._pending and (time.time() - self._pending[0].submitted_at) * 1000 >= self.timeout_ms:
            return True
        return False


class BatchExecutor:
    """Execute batches with parallel processing."""

    def __init__(self, executor_fn: Optional[Callable[[List[InferenceRequest]], List[str]]] = None):
        self.executor_fn = executor_fn or self._default_executor

    def execute(self, batch: Batch) -> Batch:
        batch.status = BatchStatus.RUNNING
        batch.started_at = time.time()
        start = time.time()
        results = self.executor_fn(batch.requests)
        for i, result in enumerate(results):
            if i < len(batch.requests):
                batch.requests[i].result = result
                batch.requests[i].completed_at = time.time()
        batch.completed_at = time.time()
        batch.total_latency_ms = (batch.completed_at - start) * 1000
        batch.status = BatchStatus.COMPLETED if all(r.result for r in batch.requests) else BatchStatus.PARTIAL
        return batch

    def _default_executor(self, requests: List[InferenceRequest]) -> List[str]:
        # Simulated batch execution
        return [f"Result for: {r.prompt[:30]}..." for r in requests]


class BatchOptimizer:
    """Optimize batch configuration based on performance."""

    def __init__(self):
        self._history: List[Dict[str, Any]] = []

    def analyze(self, batch: Batch) -> Dict[str, Any]:
        if not batch.requests:
            return {}
        avg_latency = batch.total_latency_ms / len(batch.requests)
        throughput = len(batch.requests) / max(batch.total_latency_ms / 1000, 0.001)
        padding_ratio = batch.padding_tokens / max(sum(r.max_tokens for r in batch.requests), 1)
        return {
            "batch_size": len(batch.requests),
            "avg_latency_ms": round(avg_latency, 2),
            "throughput_rps": round(throughput, 2),
            "padding_ratio": round(padding_ratio, 3),
            "efficiency": round(1.0 - padding_ratio, 3),
        }

    def recommend(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not history:
            return {"max_batch_size": 8, "max_tokens_per_batch": 4096}
        avg_size = sum(h["batch_size"] for h in history) / len(history)
        avg_padding = sum(h["padding_ratio"] for h in history) / len(history)
        recommendation = {}
        if avg_padding > 0.3:
            recommendation["suggestion"] = "Reduce batch size or use dynamic padding"
            recommendation["max_batch_size"] = max(2, int(avg_size * 0.8))
        else:
            recommendation["suggestion"] = "Current config is efficient"
            recommendation["max_batch_size"] = int(avg_size)
        recommendation["max_tokens_per_batch"] = 4096
        return recommendation

    def record(self, batch: Batch) -> None:
        self._history.append(self.analyze(batch))

    def get_history(self) -> List[Dict[str, Any]]:
        return self._history


class BatchInferenceEngine:
    """End-to-end batch inference engine."""

    def __init__(self, max_batch_size: int = 8, max_tokens_per_batch: int = 4096, timeout_ms: float = 50.0):
        self.builder = BatchBuilder(max_batch_size, max_tokens_per_batch, timeout_ms)
        self.executor = BatchExecutor()
        self.optimizer = BatchOptimizer()
        self._completed_batches: List[Batch] = []
        self._request_stats: Dict[str, Dict[str, Any]] = {}

    def submit(self, prompt: str, max_tokens: int = 256, temperature: float = 0.7, priority: int = 0) -> InferenceRequest:
        request = InferenceRequest(
            request_id=str(uuid.uuid4())[:12],
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            priority=priority,
        )
        self.builder.add_request(request)
        return request

    def process(self) -> Optional[Batch]:
        if not self.builder.should_build():
            return None
        batch = self.builder.build()
        if not batch:
            return None
        self.executor.execute(batch)
        self.optimizer.record(batch)
        self._completed_batches.append(batch)
        for r in batch.requests:
            self._request_stats[r.request_id] = {
                "latency_ms": (r.completed_at - r.submitted_at) * 1000 if r.completed_at else 0,
                "batch_id": batch.batch_id,
            }
        return batch

    def process_all(self) -> List[Batch]:
        batches = []
        while self.builder.get_pending_count() > 0:
            batch = self.process()
            if batch:
                batches.append(batch)
            else:
                break
        return batches

    def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        return self._request_stats.get(request_id)

    def get_stats(self) -> Dict[str, Any]:
        total_requests = sum(len(b.requests) for b in self._completed_batches)
        total_batches = len(self._completed_batches)
        return {
            "total_requests": total_requests,
            "total_batches": total_batches,
            "avg_batch_size": total_requests / max(total_batches, 1),
            "avg_latency_ms": sum(b.total_latency_ms for b in self._completed_batches) / max(total_batches, 1),
            "pending": self.builder.get_pending_count(),
            "optimization": self.optimizer.recommend(self.optimizer.get_history()),
        }

    def export_stats(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.get_stats(), f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("BATCH INFERENCE ENGINE DEMO")
    print("=" * 70)

    # 1. Submit requests
    print("\n[1] Submit Requests")
    engine = BatchInferenceEngine(max_batch_size=4, timeout_ms=100.0)
    requests = [
        engine.submit("What is AI?", max_tokens=100, priority=1),
        engine.submit("Explain quantum computing", max_tokens=150),
        engine.submit("Write a Python function", max_tokens=80, priority=2),
        engine.submit("Summarize this article", max_tokens=120),
        engine.submit("Translate to French", max_tokens=50),
    ]
    print(f"  Submitted: {len(requests)} requests")
    for r in requests:
        print(f"    {r.request_id[:8]}: {r.prompt[:30]}... (tokens={r.max_tokens}, priority={r.priority})")

    # 2. Process batches
    print("\n[2] Process Batches")
    batches = engine.process_all()
    for batch in batches:
        print(f"  Batch {batch.batch_id}: {len(batch.requests)} requests, {batch.total_latency_ms:.1f}ms, {batch.status.name}")
        for r in batch.requests:
            print(f"    {r.request_id[:8]}: {r.result[:40]}...")

    # 3. Optimization analysis
    print("\n[3] Optimization Analysis")
    for batch in batches:
        analysis = engine.optimizer.analyze(batch)
        print(f"  Batch {batch.batch_id}: {analysis}")

    # 4. Recommendations
    print("\n[4] Recommendations")
    rec = engine.optimizer.recommend(engine.optimizer.get_history())
    print(f"  {rec}")

    # 5. Stats
    print(f"\n[5] Stats")
    print(f"  {engine.get_stats()}")

    # 6. Export
    print("\n[6] Export")
    engine.export_stats("/tmp/batch_stats.json")
    print("  Exported to /tmp/batch_stats.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
