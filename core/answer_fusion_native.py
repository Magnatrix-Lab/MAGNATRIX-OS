#!/usr/bin/env python3
"""answer_fusion_native.py — MAGNATRIX-OS Multi-Model Answer Fusion Engine"""
from __future__ import annotations
import json, threading, time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

@dataclass
class FusionQuery:
    query: str; context: str = ""; max_tokens: int = 1024
    temperature: float = 0.7; metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class FusionResponse:
    model: str; text: str; latency: float = 0.0; status: str = "success"
    error_reason: str = ""; usage: Dict[str, int] = field(default_factory=dict)

@dataclass
class SynthesisResult:
    final_answer: str; sources: List[str] = field(default_factory=list)
    confidence: float = 0.0; method: str = "single"
    fusion_responses: List[FusionResponse] = field(default_factory=list)
    latency: float = 0.0; timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

class AnswerFusionNative:
    def __init__(self, workspace: str = "./fusion", master_model: str = "default", max_fusion_models: int = 3) -> None:
        self.workspace = Path(workspace); self.workspace.mkdir(parents=True, exist_ok=True)
        self.master_model = master_model; self.max_fusion_models = max_fusion_models
        self._fusion_models: List[str] = []; self._query_history: List[Dict[str, Any]] = []
        self._lock = threading.RLock(); self._db_path = self.workspace / "history.json"
        self._load()

    def _load(self) -> None:
        if self._db_path.exists():
            try:
                with open(self._db_path, "r", encoding="utf-8") as f: self._query_history = json.load(f)
            except Exception: pass

    def _save(self) -> None:
        with open(self._db_path, "w", encoding="utf-8") as f: json.dump(self._query_history[-500:], f, indent=2, default=str)

    def register_fusion_models(self, models: List[str]) -> None:
        with self._lock: self._fusion_models = models[:self.max_fusion_models]; self._save()

    def set_master_model(self, model: str) -> None:
        with self._lock: self.master_model = model; self._save()

    def _query_model(self, model: str, query: FusionQuery, timeout: float = 30.0) -> FusionResponse:
        start = time.time()
        return FusionResponse(model=model, text=f"[Simulated response from {model} for: {query.query[:50]}...]", latency=time.time() - start, status="success")

    def _query_all_parallel(self, query: FusionQuery) -> List[FusionResponse]:
        responses: List[FusionResponse] = []
        threads = []; results = {}
        def query_worker(model: str, idx: int):
            try: results[idx] = self._query_model(model, query)
            except Exception as e: results[idx] = FusionResponse(model=model, text="", status="error", error_reason=str(e), latency=0.0)
        with self._lock: models = list(self._fusion_models)
        for i, model in enumerate(models):
            t = threading.Thread(target=query_worker, args=(model, i)); threads.append(t); t.start()
        for t in threads: t.join(timeout=query.max_tokens / 100)
        for i in range(len(models)):
            if i in results: responses.append(results[i])
            else: responses.append(FusionResponse(model=models[i], text="", status="timeout", error_reason="Thread timeout", latency=0.0))
        return responses

    def _check_consensus(self, texts: List[str]) -> bool:
        if len(texts) < 2: return True
        from collections import Counter
        words_list = [set(t.lower().split()) for t in texts]
        if not words_list: return False
        base = words_list[0]
        for words in words_list[1:]:
            if not base: return False
            overlap = len(base & words) / len(base)
            if overlap < 0.5: return False
        return True

    def _combine_responses(self, query: FusionQuery, responses: List[FusionResponse]) -> str:
        lines = [f"Synthesized answer based on {len(responses)} models:", ""]
        for i, r in enumerate(responses, 1):
            lines.append(f"[Source {i}: {r.model}]")
            lines.append(r.text[:500] if len(r.text) > 500 else r.text); lines.append("")
        lines.append("--- Combined Answer ---")
        combined = " ".join(r.text for r in responses)
        lines.append(combined[:1000] + ("..." if len(combined) > 1000 else ""))
        return "
".join(lines)

    def fuse(self, query: str, context: str = "", max_tokens: int = 1024, temperature: float = 0.7) -> SynthesisResult:
        fq = FusionQuery(query=query, context=context, max_tokens=max_tokens, temperature=temperature)
        start = time.time()
        responses = self._query_all_parallel(fq)
        successful = [r for r in responses if r.status == "success"]
        if not successful:
            master_resp = self._query_model(self.master_model, fq)
            result = SynthesisResult(final_answer=master_resp.text, sources=[self.master_model], confidence=0.3, method="fallback", fusion_responses=responses, latency=sum(r.latency for r in responses) + master_resp.latency)
        elif len(successful) == 1:
            result = SynthesisResult(final_answer=successful[0].text, sources=[successful[0].model], confidence=0.5, method="single", fusion_responses=responses, latency=sum(r.latency for r in responses))
        elif self._check_consensus([r.text for r in successful]):
            best = max(successful, key=lambda r: len(r.text))
            result = SynthesisResult(final_answer=best.text, sources=[r.model for r in successful], confidence=0.8, method="consensus", fusion_responses=responses, latency=sum(r.latency for r in responses))
        else:
            synthesis = self._combine_responses(fq, successful)
            result = SynthesisResult(final_answer=synthesis, sources=[r.model for r in successful], confidence=0.6, method="synthesis", fusion_responses=responses, latency=sum(r.latency for r in responses))
        result.latency = time.time() - start
        with self._lock:
            self._query_history.append({"timestamp": time.time(), "query": query[:200], "context": context[:200], "result_method": result.method, "sources": result.sources, "confidence": result.confidence, "latency": result.latency})
            self._save()
        return result

    def fuse_simple(self, query: str) -> str: return self.fuse(query).final_answer

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._lock: return self._query_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._query_history)
            if not total: return {"total_queries": 0}
            methods = {}
            for h in self._query_history:
                m = h.get("result_method", "unknown"); methods[m] = methods.get(m, 0) + 1
            avg_latency = sum(h.get("latency", 0) for h in self._query_history) / total
            return {"total_queries": total, "methods": methods, "avg_latency": round(avg_latency, 2), "fusion_models": self._fusion_models}

if __name__ == "__main__":
    engine = AnswerFusionNative()
    engine.register_fusion_models(["model_a", "model_b", "model_c"])
    result = engine.fuse("What is the best approach to microservices?")
    print("Method:", result.method); print("Answer:", result.final_answer[:200])
