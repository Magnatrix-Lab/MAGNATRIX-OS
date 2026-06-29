
"""
blackbox_teacher_adapter_native.py
MAGNATRIX-OS — Black-Box Teacher Adapter

Adapter for interacting with black-box LLM teachers (GPT-4, Claude, etc.)
where only API outputs are accessible. Implements sampling strategies,
response caching, and output normalization.

Pure Python standard library.
"""

import json
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TeacherResponse:
    input_text: str
    output_text: str
    model: str
    temperature: float
    timestamp: str
    latency_ms: float
    token_count: int = 0
    cached: bool = False


class BlackBoxTeacherAdapter:
    """Adapter for black-box LLM teachers with caching and sampling."""

    def __init__(self, model_name: str = "blackbox-teacher", cache_dir: str = "./teacher_cache"):
        self.model_name = model_name
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache: Dict[str, TeacherResponse] = {}
        self.stats = {"total_calls": 0, "cache_hits": 0, "avg_latency": 0.0}
        self._load_cache()

    def _cache_key(self, input_text: str, temperature: float = 1.0) -> str:
        content = f"{self.model_name}:{input_text}:{temperature}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _load_cache(self) -> None:
        cache_file = self.cache_dir / "cache.json"
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.items():
                    self.cache[k] = TeacherResponse(**v)

    def _save_cache(self) -> None:
        cache_file = self.cache_dir / "cache.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({k: v.__dict__ for k, v in self.cache.items()}, f, indent=2)

    def query(self, input_text: str, teacher_fn: Callable[[str], str],
              temperature: float = 1.0, use_cache: bool = True) -> TeacherResponse:
        """Query teacher with caching."""
        key = self._cache_key(input_text, temperature)
        if use_cache and key in self.cache:
            self.stats["cache_hits"] += 1
            self.stats["total_calls"] += 1
            return self.cache[key]
        start = time.time()
        try:
            output = teacher_fn(input_text)
            latency = (time.time() - start) * 1000
            response = TeacherResponse(
                input_text=input_text, output_text=output,
                model=self.model_name, temperature=temperature,
                timestamp=datetime.now().isoformat(), latency_ms=latency,
                token_count=len(output.split()),
            )
            self.cache[key] = response
            self._save_cache()
            self.stats["total_calls"] += 1
            # Update avg latency
            self.stats["avg_latency"] = (self.stats["avg_latency"] * (self.stats["total_calls"] - 1) + latency) / self.stats["total_calls"]
            return response
        except Exception as e:
            return TeacherResponse(
                input_text=input_text, output_text=str(e),
                model=self.model_name, temperature=temperature,
                timestamp=datetime.now().isoformat(), latency_ms=0.0,
            )

    def batch_query(self, inputs: List[str], teacher_fn: Callable[[str], str],
                    temperature: float = 1.0) -> List[TeacherResponse]:
        return [self.query(inp, teacher_fn, temperature) for inp in inputs]

    def self_consistency_sample(self, input_text: str, teacher_fn: Callable[[str], str],
                                n_samples: int = 5, temperature: float = 0.7) -> List[TeacherResponse]:
        """Self-consistency: sample multiple outputs and find consensus."""
        responses = []
        for _ in range(n_samples):
            # Slight temperature variation
            t = temperature + random.uniform(-0.1, 0.1)
            resp = self.query(input_text, teacher_fn, t, use_cache=False)
            responses.append(resp)
        return responses

    def majority_vote(self, responses: List[TeacherResponse]) -> str:
        """Select the most common response."""
        outputs = [r.output_text for r in responses]
        return max(set(outputs), key=outputs.count)

    def normalize_output(self, text: str) -> str:
        """Normalize teacher output for consistent training."""
        # Trim whitespace, normalize quotes, etc.
        text = text.strip()
        text = text.replace('""', '"').replace("''", "'")
        return text

    def to_dict(self) -> Dict:
        return {
            "model": self.model_name,
            "stats": self.stats,
            "cache_size": len(self.cache),
        }


import random

__all__ = ["BlackBoxTeacherAdapter", "TeacherResponse"]
