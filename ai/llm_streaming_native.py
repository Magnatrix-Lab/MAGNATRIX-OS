#!/usr/bin/env python3
"""
ai/llm_streaming_native.py
MAGNATRIX-OS — Real-time Streaming Engine for the LLM Arena
AMATI pattern: progressive token generation, live streaming, chunk assembly

Pure Python, stdlib only. Simulates token streaming, backpressure handling,
early termination, and partial rendering.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Generator, List, Optional, Tuple


# ───────────────────────────────────────────────────────────────
# 0. UTILITIES
# ───────────────────────────────────────────────────────────────

def _now() -> float:
    return time.time()


def _token_count(text: str) -> int:
    return len(text) // 4 + 1


# ───────────────────────────────────────────────────────────────
# 1. TOKEN STREAMER
# ───────────────────────────────────────────────────────────────

@dataclass
class TokenChunk:
    chunk_id: int
    tokens: int
    text: str
    confidence: float
    elapsed_ms: float
    is_final: bool


class TokenStreamer:
    """Simulate progressive token generation with configurable speed."""

    def __init__(self, tokens_per_sec: float = 50.0) -> None:
        self.tokens_per_sec = tokens_per_sec

    def stream(self, full_text: str, chunk_size: int = 8, confidence_threshold: float = 0.95) -> Generator[TokenChunk, None, None]:
        words = full_text.split()
        delivered = []
        chunk_id = 0
        t0 = _now()
        for i in range(0, len(words), chunk_size):
            chunk = words[i:i + chunk_size]
            delivered.extend(chunk)
            chunk_id += 1
            confidence = min(0.5 + (len(delivered) / len(words)) * 0.5, 1.0) if words else 1.0
            elapsed = (_now() - t0) * 1000
            is_final = len(delivered) >= len(words) or confidence >= confidence_threshold
            yield TokenChunk(
                chunk_id=chunk_id,
                tokens=len(chunk),
                text=" ".join(chunk),
                confidence=round(confidence, 3),
                elapsed_ms=round(elapsed, 1),
                is_final=is_final,
            )
            if is_final and len(delivered) < len(words):
                break

    def estimate_time(self, total_tokens: int) -> float:
        return round(total_tokens / self.tokens_per_sec, 2)


# ───────────────────────────────────────────────────────────────
# 2. STREAMING ROUTER
# ───────────────────────────────────────────────────────────────

class StreamingRouter:
    """Route streaming requests to appropriate model, handle backpressure."""

    MODEL_SPEEDS = {
        "claude-3-5-sonnet": 45.0,
        "gpt-4o": 60.0,
        "gpt-4o-mini": 120.0,
        "gemini-1.5-pro": 50.0,
        "gemini-1.5-flash": 150.0,
        "llama-3-70b": 35.0,
        "llama-3-8b": 200.0,
        "deepseek-v2": 55.0,
        "qwen-2-72b": 40.0,
        "magnatrix-7b": 100.0,
    }

    def __init__(self) -> None:
        self._queue_depth: Dict[str, int] = {m: 0 for m in self.MODEL_SPEEDS}

    def select(self, prompt: str, preferred: Optional[str] = None) -> Tuple[str, float]:
        if preferred and preferred in self.MODEL_SPEEDS:
            self._queue_depth[preferred] += 1
            return preferred, self.MODEL_SPEEDS[preferred]
        scored = [(m, s / (self._queue_depth[m] + 1)) for m, s in self.MODEL_SPEEDS.items()]
        scored.sort(key=lambda x: x[1], reverse=True)
        best = scored[0][0]
        self._queue_depth[best] += 1
        return best, self.MODEL_SPEEDS[best]

    def release(self, model_id: str) -> None:
        self._queue_depth[model_id] = max(0, self._queue_depth[model_id] - 1)

    def queue_status(self) -> Dict[str, int]:
        return self._queue_depth.copy()


# ───────────────────────────────────────────────────────────────
# 3. CHUNK ASSEMBLER
# ───────────────────────────────────────────────────────────────

class ChunkAssembler:
    """Assemble partial chunks into coherent text, handle sentence boundaries."""

    def __init__(self) -> None:
        self._buffer: List[str] = []
        self._completed_sentences: List[str] = []

    def add_chunk(self, chunk: TokenChunk) -> Optional[str]:
        self._buffer.append(chunk.text)
        text = " ".join(self._buffer)
        if chunk.is_final or text.endswith((".", "!", "?", "\n", ":")):
            sentence = text.strip()
            self._completed_sentences.append(sentence)
            self._buffer = []
            return sentence
        return None

    def get_partial(self) -> str:
        return " ".join(self._buffer)

    def get_all(self) -> str:
        return " ".join(self._completed_sentences + self._buffer)

    def reset(self) -> None:
        self._buffer = []
        self._completed_sentences = []


# ───────────────────────────────────────────────────────────────
# 4. PROGRESS TRACKER
# ───────────────────────────────────────────────────────────────

class ProgressTracker:
    """Track generation progress, estimate time remaining."""

    def __init__(self, total_tokens: int) -> None:
        self.total_tokens = total_tokens
        self.generated_tokens = 0
        self.start_time = _now()
        self.model_id = ""

    def update(self, tokens: int, model_id: str) -> Dict[str, Any]:
        self.generated_tokens += tokens
        self.model_id = model_id
        elapsed = _now() - self.start_time
        rate = self.generated_tokens / elapsed if elapsed > 0 else 0
        remaining_tokens = max(0, self.total_tokens - self.generated_tokens)
        eta = remaining_tokens / rate if rate > 0 else 0
        return {
            "generated": self.generated_tokens,
            "total": self.total_tokens,
            "progress_pct": round(self.generated_tokens / self.total_tokens * 100, 1),
            "elapsed_sec": round(elapsed, 2),
            "eta_sec": round(eta, 2),
            "tokens_per_sec": round(rate, 1),
            "model": model_id,
        }

    def is_complete(self) -> bool:
        return self.generated_tokens >= self.total_tokens


# ───────────────────────────────────────────────────────────────
# 5. EARLY TERMINATION
# ───────────────────────────────────────────────────────────────

class EarlyTermination:
    """Stop generation early if confidence threshold reached or answer complete."""

    def should_terminate(self, chunk: TokenChunk, min_tokens: int = 20) -> bool:
        if chunk.tokens < min_tokens:
            return False
        if chunk.confidence >= 0.95:
            return True
        if chunk.is_final:
            return True
        return False

    def estimate_savings(self, total_tokens: int, generated_tokens: int, cost_per_1k: float) -> float:
        saved = max(0, total_tokens - generated_tokens)
        return round(saved / 1000 * cost_per_1k, 6)


# ───────────────────────────────────────────────────────────────
# 6. PARTIAL RENDERER
# ───────────────────────────────────────────────────────────────

class PartialRenderer:
    """Render partial responses for UI with markdown-aware chunking."""

    def render(self, chunks: List[TokenChunk]) -> str:
        parts = []
        for c in chunks:
            parts.append(c.text)
        return " ".join(parts)

    def render_live(self, chunk: TokenChunk) -> str:
        return chunk.text

    def to_html(self, chunks: List[TokenChunk]) -> str:
        text = self.render(chunks)
        text = text.replace("\n\n", "</p><p>")
        text = text.replace("**", "<b>", 1).replace("**", "</b>", 1)
        return f"<p>{text}</p>"


# ───────────────────────────────────────────────────────────────
# 7. STREAMING ENGINE
# ───────────────────────────────────────────────────────────────

class StreamingEngine:
    """Main orchestrator: stream -> route -> assemble -> track -> terminate -> render."""

    def __init__(self) -> None:
        self.router = StreamingRouter()
        self.assembler = ChunkAssembler()
        self.tracker: Optional[ProgressTracker] = None
        self.terminator = EarlyTermination()
        self.renderer = PartialRenderer()

    def stream(self, prompt: str, response_text: str, preferred_model: Optional[str] = None, chunk_size: int = 6, confidence_threshold: float = 0.92) -> Dict[str, Any]:
        model_id, speed = self.router.select(prompt, preferred_model)
        streamer = TokenStreamer(speed)
        total_tokens = _token_count(response_text)
        self.tracker = ProgressTracker(total_tokens)

        chunks = []
        terminated = False
        for chunk in streamer.stream(response_text, chunk_size, confidence_threshold):
            chunks.append(chunk)
            self.assembler.add_chunk(chunk)
            progress = self.tracker.update(chunk.tokens, model_id)
            if self.terminator.should_terminate(chunk, min_tokens=15):
                terminated = True
                break

        self.router.release(model_id)

        return {
            "model_id": model_id,
            "chunks": len(chunks),
            "tokens_generated": self.tracker.generated_tokens if self.tracker else 0,
            "total_tokens": total_tokens,
            "terminated_early": terminated,
            "elapsed_sec": progress["elapsed_sec"] if self.tracker else 0,
            "tokens_per_sec": progress["tokens_per_sec"] if self.tracker else 0,
            "assembled_text": self.assembler.get_all(),
            "rendered": self.renderer.render(chunks),
            "queue_status": self.router.queue_status(),
        }

    def stream_multiple(self, items: List[Tuple[str, str]], chunk_size: int = 6) -> List[Dict[str, Any]]:
        return [self.stream(prompt, response, chunk_size=chunk_size) for prompt, response in items]

    def stats(self) -> Dict[str, Any]:
        return {"queue": self.router.queue_status()}


# ───────────────────────────────────────────────────────────────
# 8. DEMO
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Streaming Engine Demo")
    print("=" * 60)

    engine = StreamingEngine()

    tests = [
        (
            "What is the capital of France?",
            "The capital of France is Paris. It is located in the north-central part of the country.",
        ),
        (
            "Explain quantum computing in simple terms.",
            "Quantum computing uses quantum bits or qubits. Unlike classical bits that are 0 or 1, qubits can be both at once. This allows quantum computers to solve certain problems much faster than classical computers.",
        ),
        (
            "Write a Python function to reverse a string.",
            "def reverse_string(s): return s[::-1] This uses Python's slice notation to reverse the string efficiently.",
        ),
    ]

    for i, (prompt, response) in enumerate(tests, 1):
        print(f"\n[{i}] Streaming: {prompt[:40]}...")
        result = engine.stream(prompt, response, chunk_size=5, confidence_threshold=0.90)
        print(f"    Model: {result['model_id']}")
        print(f"    Chunks: {result['chunks']}")
        print(f"    Tokens: {result['tokens_generated']}/{result['total_tokens']}")
        print(f"    Early terminated: {result['terminated_early']}")
        print(f"    Speed: {result['tokens_per_sec']} tok/s")
        print(f"    Time: {result['elapsed_sec']:.2f}s")
        print(f"    Output: {result['assembled_text'][:80]}...")

    print("\n[Queue Status]")
    print(f"    {json.dumps(engine.stats()['queue'], indent=2)}")

    print("\n" + "=" * 60)
    print("Demo complete. Streaming Engine ready for LLM Arena.")
    print("=" * 60)
