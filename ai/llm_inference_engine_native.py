"""Inference Engine — Optimized LLM inference with batching, KV-cache, and speculative decoding.

Modul ini menyediakan:
- InferenceEngine untuk single/batch inference dengan scheduling
- KVCacheManager untuk key-value cache management
- BatchScheduler untuk dynamic batching
- SpeculativeDecoder untuk draft-then-verify decoding
- QuantizationEngine untuk INT8/FP16 inference
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class InferenceStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class QuantMode(Enum):
    FP32 = "fp32"
    FP16 = "fp16"
    INT8 = "int8"
    INT4 = "int4"


@dataclass
class InferenceRequest:
    """Single inference request."""
    request_id: str
    prompt: str
    max_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.95
    top_k: int = 50
    stop_sequences: List[str] = field(default_factory=list)
    priority: int = 1
    stream: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    status: InferenceStatus = InferenceStatus.PENDING
    output: str = ""
    tokens_generated: int = 0
    prompt_tokens: int = 0


@dataclass
class KVCache:
    """KV cache entry for a sequence."""
    sequence_id: str
    keys: List[List[float]] = field(default_factory=list)
    values: List[List[float]] = field(default_factory=list)
    max_length: int = 2048
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)

    def append(self, key: List[float], value: List[float]) -> bool:
        if len(self.keys) >= self.max_length:
            return False
        self.keys.append(key)
        self.values.append(value)
        self.last_accessed = time.time()
        return True

    def get_kv(self, start: int = 0) -> Tuple[List[List[float]], List[List[float]]]:
        self.last_accessed = time.time()
        return self.keys[start:], self.values[start:]

    def token_count(self) -> int:
        return len(self.keys)


class KVCacheManager:
    """Manage KV caches for multiple sequences."""

    def __init__(self, max_entries: int = 100, max_length: int = 2048, ttl: float = 300.0):
        self.max_entries = max_entries
        self.max_length = max_length
        self.ttl = ttl
        self._caches: Dict[str, KVCache] = {}

    def create(self, sequence_id: str) -> KVCache:
        cache = KVCache(
            sequence_id=sequence_id,
            max_length=self.max_length,
        )
        self._caches[sequence_id] = cache
        self._evict_if_needed()
        return cache

    def get(self, sequence_id: str) -> Optional[KVCache]:
        cache = self._caches.get(sequence_id)
        if cache:
            cache.last_accessed = time.time()
        return cache

    def delete(self, sequence_id: str) -> bool:
        return self._caches.pop(sequence_id, None) is not None

    def _evict_if_needed(self) -> None:
        now = time.time()
        # Remove stale
        stale = [sid for sid, c in self._caches.items() if now - c.last_accessed > self.ttl]
        for sid in stale:
            del self._caches[sid]
        # Remove oldest if still over limit
        while len(self._caches) > self.max_entries:
            oldest = min(self._caches.keys(), key=lambda k: self._caches[k].last_accessed)
            del self._caches[oldest]

    def get_stats(self) -> Dict[str, Any]:
        total_tokens = sum(c.token_count() for c in self._caches.values())
        return {
            "entries": len(self._caches),
            "total_cached_tokens": total_tokens,
            "avg_tokens_per_seq": total_tokens / max(len(self._caches), 1),
        }


class BatchScheduler:
    """Dynamic batching for efficient inference."""

    def __init__(self, max_batch_size: int = 8, max_wait_ms: float = 50.0):
        self.max_batch_size = max_batch_size
        self.max_wait_ms = max_wait_ms
        self._queue: List[InferenceRequest] = []
        self._batches: List[List[InferenceRequest]] = []

    def submit(self, request: InferenceRequest) -> None:
        self._queue.append(request)
        self._queue.sort(key=lambda r: r.priority, reverse=True)

    def form_batch(self) -> List[InferenceRequest]:
        if not self._queue:
            return []
        batch_size = min(len(self._queue), self.max_batch_size)
        batch = self._queue[:batch_size]
        self._queue = self._queue[batch_size:]
        return batch

    def get_queue_stats(self) -> Dict[str, Any]:
        return {
            "queued": len(self._queue),
            "avg_wait_time": sum(time.time() - r.created_at for r in self._queue) / max(len(self._queue), 1),
        }


class SpeculativeDecoder:
    """Draft-then-verify speculative decoding."""

    def __init__(self, draft_tokens: int = 5, acceptance_threshold: float = 0.8):
        self.draft_tokens = draft_tokens
        self.acceptance_threshold = acceptance_threshold
        self._draft_model: Optional[Callable[[str], str]] = None

    def set_draft_model(self, model_fn: Callable[[str], str]) -> None:
        self._draft_model = model_fn

    def decode(self, prompt: str, target_fn: Callable[[str], str]) -> Tuple[str, int, int]:
        """Return (output, accepted_tokens, total_draft_tokens)."""
        if not self._draft_model:
            output = target_fn(prompt)
            return output, 0, 0
        # Draft
        draft = self._draft_model(prompt)
        draft_tokens = draft.split()[:self.draft_tokens]
        # Verify with target
        target_output = target_fn(prompt)
        # Simulate acceptance
        accepted = []
        for i, token in enumerate(draft_tokens):
            if i < len(target_output.split()) and token in target_output.split()[i]:
                accepted.append(token)
            else:
                break
        final = target_fn(prompt + " ".join(accepted))
        return final, len(accepted), len(draft_tokens)


class QuantizationEngine:
    """Quantization for faster inference."""

    def __init__(self, mode: QuantMode = QuantMode.FP16):
        self.mode = mode

    def quantize_weights(self, weights: List[float]) -> List[float]:
        if self.mode == QuantMode.INT8:
            max_val = max(abs(w) for w in weights) or 1.0
            return [int(w / max_val * 127) for w in weights]
        elif self.mode == QuantMode.INT4:
            max_val = max(abs(w) for w in weights) or 1.0
            return [int(w / max_val * 7) for w in weights]
        return weights

    def get_speedup_factor(self) -> float:
        return {"fp32": 1.0, "fp16": 1.5, "int8": 2.0, "int4": 3.0}.get(self.mode.value, 1.0)

    def get_memory_reduction(self) -> float:
        return {"fp32": 1.0, "fp16": 0.5, "int8": 0.25, "int4": 0.125}.get(self.mode.value, 1.0)


class InferenceEngine:
    """End-to-end optimized inference engine."""

    def __init__(self, max_batch_size: int = 8, quant_mode: QuantMode = QuantMode.FP16):
        self.kv_cache = KVCacheManager()
        self.scheduler = BatchScheduler(max_batch_size)
        self.speculative = SpeculativeDecoder()
        self.quantizer = QuantizationEngine(quant_mode)
        self._requests: Dict[str, InferenceRequest] = {}
        self._history: List[Dict[str, Any]] = []
        self._total_tokens = 0

    def submit(self, prompt: str, max_tokens: int = 512, **kwargs) -> InferenceRequest:
        req = InferenceRequest(
            request_id=str(uuid.uuid4())[:12],
            prompt=prompt,
            max_tokens=max_tokens,
            **kwargs,
        )
        self._requests[req.request_id] = req
        self.scheduler.submit(req)
        return req

    def run_inference(self, request_id: str, inference_fn: Optional[Callable[[InferenceRequest], str]] = None) -> InferenceRequest:
        req = self._requests.get(request_id)
        if not req:
            raise ValueError("Request not found")
        req.status = InferenceStatus.RUNNING
        req.started_at = time.time()

        inference_fn = inference_fn or self._default_inference

        # Check KV cache
        cache = self.kv_cache.get(request_id)
        if not cache:
            cache = self.kv_cache.create(request_id)

        # Generate output
        output = inference_fn(req)
        req.output = output
        req.tokens_generated = len(output.split())
        req.prompt_tokens = len(req.prompt.split())
        req.status = InferenceStatus.COMPLETED
        req.completed_at = time.time()
        self._total_tokens += req.tokens_generated + req.prompt_tokens

        self._history.append({
            "request_id": request_id,
            "prompt_tokens": req.prompt_tokens,
            "generated_tokens": req.tokens_generated,
            "duration": req.completed_at - req.started_at,
        })
        return req

    def run_batch(self, request_ids: List[str], inference_fn: Optional[Callable[[InferenceRequest], str]] = None) -> List[InferenceRequest]:
        return [self.run_inference(rid, inference_fn) for rid in request_ids]

    def _default_inference(self, req: InferenceRequest) -> str:
        # Simulated inference
        words = req.prompt.split()[:10]
        if req.temperature > 0.8:
            return f"Generated text from: {' '.join(words)}... [creative]"
        return f"Generated text from: {' '.join(words)}... [deterministic]"

    def get_stats(self) -> Dict[str, Any]:
        completed = [r for r in self._requests.values() if r.status == InferenceStatus.COMPLETED]
        avg_latency = sum(r.completed_at - r.started_at for r in completed if r.completed_at and r.started_at) / max(len(completed), 1)
        return {
            "total_requests": len(self._requests),
            "completed": len(completed),
            "pending": len(self.scheduler._queue),
            "avg_latency": round(avg_latency, 3),
            "total_tokens": self._total_tokens,
            "kv_cache": self.kv_cache.get_stats(),
            "quant_speedup": self.quantizer.get_speedup_factor(),
            "quant_memory": self.quantizer.get_memory_reduction(),
        }

    def export_report(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "stats": self.get_stats(),
                "history": self._history,
            }, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("INFERENCE ENGINE DEMO")
    print("=" * 70)

    engine = InferenceEngine(max_batch_size=4, quant_mode=QuantMode.INT8)

    # 1. Submit requests
    print("\n[1] Submit Requests")
    r1 = engine.submit("Explain quantum computing", max_tokens=100, temperature=0.9, priority=2)
    r2 = engine.submit("What is Python?", max_tokens=50, temperature=0.3, priority=1)
    r3 = engine.submit("Summarize AI history", max_tokens=80, priority=3)
    r4 = engine.submit("How does DNA work?", max_tokens=60, priority=1)
    print(f"  Submitted: {len(engine._requests)} requests")
    for r in [r1, r2, r3, r4]:
        print(f"    {r.request_id}: priority={r.priority}, tokens={r.max_tokens}")

    # 2. Single inference
    print("\n[2] Single Inference")
    result = engine.run_inference(r1.request_id)
    print(f"  Request: {result.request_id}")
    print(f"  Output: {result.output[:60]}...")
    print(f"  Tokens: prompt={result.prompt_tokens}, gen={result.tokens_generated}")
    print(f"  Status: {result.status.name}")

    # 3. Batch inference
    print("\n[3] Batch Inference")
    batch = engine.scheduler.form_batch()
    print(f"  Batch size: {len(batch)}")
    results = engine.run_batch([r.request_id for r in batch])
    for r in results:
        print(f"    {r.request_id}: {r.output[:40]}...")

    # 4. KV Cache
    print("\n[4] KV Cache")
    cache = engine.kv_cache.create("session-1")
    for i in range(5):
        cache.append([i * 0.1] * 64, [i * 0.2] * 64)
    print(f"  Cache tokens: {cache.token_count()}")
    k, v = cache.get_kv(start=2)
    print(f"  Retrieved KV: {len(k)} entries")
    print(f"  Cache stats: {engine.kv_cache.get_stats()}")

    # 5. Speculative decoding
    print("\n[5] Speculative Decoding")
    def draft_fn(prompt):
        return "quick brown fox jumps over lazy dog"
    def target_fn(prompt):
        return "quick brown fox jumps over the lazy dog"
    engine.speculative.set_draft_model(draft_fn)
    output, accepted, total = engine.speculative.decode("The", target_fn)
    print(f"  Output: {output[:40]}...")
    print(f"  Accepted: {accepted}/{total}")

    # 6. Quantization
    print("\n[6] Quantization")
    weights = [0.123, -0.456, 0.789, -0.321, 0.555]
    print(f"  Original: {weights}")
    for mode in [QuantMode.FP16, QuantMode.INT8, QuantMode.INT4]:
        q = QuantizationEngine(mode)
        qw = q.quantize_weights(weights)
        print(f"  {mode.value}: {qw} (speedup={q.get_speedup_factor()}x)")

    # 7. Stats
    print(f"\n[7] Engine Stats")
    print(f"  {engine.get_stats()}")

    # 8. Export
    print("\n[8] Export Report")
    engine.export_report("/tmp/inference_report.json")
    print("  Exported to /tmp/inference_report.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
