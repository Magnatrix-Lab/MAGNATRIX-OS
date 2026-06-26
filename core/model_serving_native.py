#!/usr/bin/env python3
"""Model Serving Engine for MAGNATRIX-OS — Serve trained models with queue management."""
from __future__ import annotations
import json, queue, threading, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

@dataclass
class InferenceRequest:
    id: str
    model_id: str
    input_data: Any
    priority: int = 5
    submitted_at: float = field(default_factory=time.time)
    callback: Optional[Callable] = None

class ModelServingEngine:
    def __init__(self, max_queue: int = 100) -> None:
        self._queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=max_queue)
        self._results: Dict[str, Any] = {}
        self._running = False
        self._workers: List[threading.Thread] = []
        self._models: Dict[str, Callable] = {}

    def register_model(self, model_id: str, inference_fn: Callable) -> None:
        self._models[model_id] = inference_fn

    def predict(self, model_id: str, input_data: Any, priority: int = 5) -> str:
        req_id = f"req_{int(time.time()*1000)}"
        req = InferenceRequest(id=req_id, model_id=model_id, input_data=input_data, priority=priority)
        self._queue.put((priority, req))
        return req_id

    def get_result(self, req_id: str) -> Optional[Any]:
        return self._results.pop(req_id, None)

    def start(self, num_workers: int = 2) -> None:
        self._running = True
        for _ in range(num_workers):
            t = threading.Thread(target=self._worker_loop, daemon=True)
            t.start()
            self._workers.append(t)

    def _worker_loop(self) -> None:
        while self._running:
            try:
                _, req = self._queue.get(timeout=1)
                model_fn = self._models.get(req.model_id)
                if model_fn:
                    result = model_fn(req.input_data)
                    self._results[req.id] = {"status": "success", "result": result}
                else:
                    self._results[req.id] = {"status": "error", "error": "Model not found"}
            except queue.Empty:
                continue

    def stop(self) -> None:
        self._running = False

    def stats(self) -> Dict[str, Any]:
        return {"models": len(self._models), "queue_size": self._queue.qsize(), "results": len(self._results)}
