"""Inference Scheduler — Request scheduling, priority queues, and load balancing for inference.

Modul ini menyediakan:
- InferenceRequest untuk inference requests dengan priority
- PriorityQueue untuk priority-based request scheduling
- LoadBalancer untuk distribute requests across workers
- RateLimiter untuk rate limiting per user/model
- InferenceScheduler untuk end-to-end scheduling
"""

from __future__ import annotations

import json
import time
import uuid
import heapq
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class RequestPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    BACKGROUND = 4


class RequestStatus(Enum):
    PENDING = auto()
    SCHEDULED = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class InferenceRequest:
    """Single inference request."""
    request_id: str
    prompt: str
    model_id: str
    max_tokens: int = 256
    priority: RequestPriority = RequestPriority.MEDIUM
    user_id: str = "anonymous"
    status: RequestStatus = RequestStatus.PENDING
    submitted_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[str] = None
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Worker:
    """Inference worker."""
    worker_id: str
    name: str
    capacity: int = 1
    active_requests: int = 0
    supported_models: Set[str] = field(default_factory=set)
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    enabled: bool = True

    def can_accept(self, model_id: str) -> bool:
        return self.enabled and self.active_requests < self.capacity and model_id in self.supported_models

    def score(self, request: InferenceRequest) -> float:
        if not self.can_accept(request.model_id):
            return -1.0
        return (self.capacity - self.active_requests) * 10 - self.avg_latency_ms * 0.01 + self.success_rate * 5


class PriorityQueue:
    """Priority queue for inference requests."""

    def __init__(self):
        self._queue: List[Tuple[int, float, InferenceRequest]] = []
        self._counter = 0

    def enqueue(self, request: InferenceRequest) -> None:
        self._counter += 1
        heapq.heappush(self._queue, (request.priority.value, request.submitted_at, self._counter, request))

    def dequeue(self) -> Optional[InferenceRequest]:
        while self._queue:
            _, _, _, request = heapq.heappop(self._queue)
            if request.status == RequestStatus.PENDING:
                return request
        return None

    def peek(self) -> Optional[InferenceRequest]:
        for _, _, _, request in self._queue:
            if request.status == RequestStatus.PENDING:
                return request
        return None

    def remove(self, request_id: str) -> bool:
        new_queue = []
        found = False
        for item in self._queue:
            if item[3].request_id == request_id:
                found = True
                continue
            new_queue.append(item)
        self._queue = new_queue
        heapq.heapify(self._queue)
        return found

    def count(self) -> int:
        return sum(1 for _, _, _, r in self._queue if r.status == RequestStatus.PENDING)

    def list_pending(self) -> List[InferenceRequest]:
        return [r for _, _, _, r in self._queue if r.status == RequestStatus.PENDING]


class LoadBalancer:
    """Distribute requests across workers."""

    def __init__(self, strategy: str = "best_fit"):
        self.strategy = strategy
        self._workers: Dict[str, Worker] = {}
        self._round_robin: int = 0

    def add_worker(self, worker: Worker) -> None:
        self._workers[worker.worker_id] = worker

    def remove_worker(self, worker_id: str) -> None:
        self._workers.pop(worker_id, None)

    def select(self, request: InferenceRequest) -> Optional[Worker]:
        candidates = [w for w in self._workers.values() if w.can_accept(request.model_id)]
        if not candidates:
            return None
        if self.strategy == "best_fit":
            return max(candidates, key=lambda w: w.score(request))
        elif self.strategy == "round_robin":
            eligible = [w for w in candidates if w.worker_id in self._workers]
            if eligible:
                self._round_robin = (self._round_robin + 1) % len(eligible)
                return eligible[self._round_robin]
            return None
        elif self.strategy == "least_loaded":
            return min(candidates, key=lambda w: w.active_requests / max(w.capacity, 1))
        return candidates[0]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._workers)
        active = sum(w.active_requests for w in self._workers.values())
        capacity = sum(w.capacity for w in self._workers.values())
        return {
            "workers": total,
            "active_requests": active,
            "capacity": capacity,
            "utilization": active / max(capacity, 1),
        }


class RateLimiter:
    """Rate limiting per user and model."""

    def __init__(self, requests_per_minute: int = 60, tokens_per_minute: int = 10000):
        self.rpm = requests_per_minute
        self.tpm = tokens_per_minute
        self._user_buckets: Dict[str, List[float]] = {}
        self._user_tokens: Dict[str, List[Tuple[float, int]]] = {}

    def check(self, user_id: str, tokens: int) -> Tuple[bool, str]:
        now = time.time()
        window = 60.0

        # Check requests
        bucket = self._user_buckets.get(user_id, [])
        bucket = [t for t in bucket if now - t < window]
        self._user_buckets[user_id] = bucket
        if len(bucket) >= self.rpm:
            return False, "Rate limit exceeded (requests)"

        # Check tokens
        token_bucket = self._user_tokens.get(user_id, [])
        token_bucket = [(t, n) for t, n in token_bucket if now - t < window]
        self._user_tokens[user_id] = token_bucket
        total_tokens = sum(n for _, n in token_bucket)
        if total_tokens + tokens > self.tpm:
            return False, "Rate limit exceeded (tokens)"

        return True, "OK"

    def record(self, user_id: str, tokens: int) -> None:
        self._user_buckets.setdefault(user_id, []).append(time.time())
        self._user_tokens.setdefault(user_id, []).append((time.time(), tokens))

    def get_remaining(self, user_id: str) -> Dict[str, int]:
        now = time.time()
        bucket = [t for t in self._user_buckets.get(user_id, []) if now - t < 60]
        token_bucket = [(t, n) for t, n in self._user_tokens.get(user_id, []) if now - t < 60]
        total_tokens = sum(n for _, n in token_bucket)
        return {
            "requests_remaining": max(0, self.rpm - len(bucket)),
            "tokens_remaining": max(0, self.tpm - total_tokens),
        }


class InferenceScheduler:
    """End-to-end inference scheduling."""

    def __init__(self, requests_per_minute: int = 60, tokens_per_minute: int = 10000):
        self.queue = PriorityQueue()
        self.load_balancer = LoadBalancer()
        self.rate_limiter = RateLimiter(requests_per_minute, tokens_per_minute)
        self._running: Dict[str, InferenceRequest] = {}
        self._completed: List[InferenceRequest] = []
        self._callbacks: List[Callable[[InferenceRequest], None]] = []

    def submit(self, prompt: str, model_id: str, max_tokens: int = 256,
               priority: RequestPriority = RequestPriority.MEDIUM, user_id: str = "anonymous") -> InferenceRequest:
        request = InferenceRequest(
            request_id=str(uuid.uuid4())[:12],
            prompt=prompt,
            model_id=model_id,
            max_tokens=max_tokens,
            priority=priority,
            user_id=user_id,
        )
        self.queue.enqueue(request)
        return request

    def schedule(self, executor_fn: Optional[Callable[[InferenceRequest, Worker], str]] = None) -> Optional[InferenceRequest]:
        request = self.queue.dequeue()
        if not request:
            return None

        # Rate limit check
        ok, msg = self.rate_limiter.check(request.user_id, request.max_tokens)
        if not ok:
            request.status = RequestStatus.FAILED
            request.result = msg
            self._completed.append(request)
            return request

        # Select worker
        worker = self.load_balancer.select(request)
        if not worker:
            request.status = RequestStatus.PENDING
            self.queue.enqueue(request)
            return None

        # Execute
        request.status = RequestStatus.RUNNING
        request.started_at = time.time()
        worker.active_requests += 1
        self._running[request.request_id] = request

        executor_fn = executor_fn or self._default_executor
        try:
            result = executor_fn(request, worker)
            request.result = result
            request.status = RequestStatus.COMPLETED
        except Exception as e:
            request.result = str(e)
            request.status = RequestStatus.FAILED

        request.completed_at = time.time()
        request.latency_ms = (request.completed_at - request.started_at) * 1000
        worker.active_requests -= 1
        worker.avg_latency_ms = worker.avg_latency_ms * 0.9 + request.latency_ms * 0.1

        self.rate_limiter.record(request.user_id, request.max_tokens)
        self._running.pop(request.request_id, None)
        self._completed.append(request)

        for cb in self._callbacks:
            try:
                cb(request)
            except Exception:
                pass

        return request

    def _default_executor(self, request: InferenceRequest, worker: Worker) -> str:
        time.sleep(0.01)
        return f"[{worker.name}] Result for {request.prompt[:30]}..."

    def add_worker(self, name: str, capacity: int, supported_models: Set[str]) -> Worker:
        worker = Worker(
            worker_id=str(uuid.uuid4())[:12],
            name=name,
            capacity=capacity,
            supported_models=supported_models,
        )
        self.load_balancer.add_worker(worker)
        return worker

    def process_all(self, executor_fn: Optional[Callable[[InferenceRequest, Worker], str]] = None) -> List[InferenceRequest]:
        results = []
        while self.queue.count() > 0:
            result = self.schedule(executor_fn)
            if result:
                results.append(result)
            else:
                break
        return results

    def get_stats(self) -> Dict[str, Any]:
        return {
            "pending": self.queue.count(),
            "running": len(self._running),
            "completed": len(self._completed),
            "workers": self.load_balancer.get_stats(),
        }

    def export_report(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "stats": self.get_stats(),
                "completed": [
                    {
                        "request_id": r.request_id,
                        "prompt": r.prompt[:50],
                        "latency_ms": r.latency_ms,
                        "status": r.status.name,
                    }
                    for r in self._completed[-20:]
                ],
            }, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("INFERENCE SCHEDULER DEMO")
    print("=" * 70)

    # 1. Setup workers
    print("\n[1] Setup Workers")
    scheduler = InferenceScheduler(requests_per_minute=100, tokens_per_minute=50000)
    w1 = scheduler.add_worker("GPU-1", capacity=2, supported_models={"gpt-4", "claude-3"})
    w2 = scheduler.add_worker("GPU-2", capacity=3, supported_models={"gpt-4", "llama-3"})
    w3 = scheduler.add_worker("CPU-1", capacity=1, supported_models={"llama-3"})
    print(f"  Workers: {len(scheduler.load_balancer._workers)}")

    # 2. Submit requests
    print("\n[2] Submit Requests")
    requests = [
        scheduler.submit("What is AI?", "gpt-4", priority=RequestPriority.HIGH),
        scheduler.submit("Code review", "gpt-4", priority=RequestPriority.MEDIUM),
        scheduler.submit("Story writing", "llama-3", priority=RequestPriority.LOW),
        scheduler.submit("Critical analysis", "claude-3", priority=RequestPriority.CRITICAL),
        scheduler.submit("Translate text", "gpt-4", priority=RequestPriority.HIGH),
    ]
    print(f"  Submitted: {len(requests)}")
    print(f"  Pending: {scheduler.queue.count()}")

    # 3. Schedule
    print("\n[3] Schedule Execution")
    results = scheduler.process_all()
    for r in results:
        print(f"  {r.request_id[:8]}: {r.status.name} in {r.latency_ms:.1f}ms -> {r.result[:50]}...")

    # 4. Rate limiting
    print("\n[4] Rate Limiting")
    for i in range(5):
        req = scheduler.submit(f"Request {i}", "gpt-4", max_tokens=1000, user_id="test-user")
    scheduler.process_all()
    remaining = scheduler.rate_limiter.get_remaining("test-user")
    print(f"  Remaining: {remaining}")

    # 5. Load balancer stats
    print(f"\n[5] Load Balancer Stats")
    print(f"  {scheduler.load_balancer.get_stats()}")

    # 6. Queue stats
    print(f"\n[6] Scheduler Stats")
    print(f"  {scheduler.get_stats()}")

    # 7. Export
    print("\n[7] Export Report")
    scheduler.export_report("/tmp/scheduler_report.json")
    print("  Exported to /tmp/scheduler_report.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
