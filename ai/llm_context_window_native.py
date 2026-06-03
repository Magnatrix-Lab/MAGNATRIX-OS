"""
llm_context_window_native.py
MAGNATRIX-OS Context Window Engine
Native Python, stdlib only.
Provides context window management, token counting, truncation strategies, and relevance scoring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple


class TruncationStrategy(Enum):
    FIFO = "fifo"
    LIFO = "lifo"
    RELEVANCE = "relevance"
    SUMMARY = "summary"


@dataclass
class ContextSegment:
    content: str
    tokens: int
    priority: int = 0
    relevance_score: float = 1.0
    segment_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"content": self.content[:80], "tokens": self.tokens, "priority": self.priority, "relevance": self.relevance_score}


class ContextWindowEngine:
    """Context window management with token limits and truncation."""

    def __init__(self, max_tokens: int = 4096, chars_per_token: float = 4.0) -> None:
        self.max_tokens = max_tokens
        self.chars_per_token = chars_per_token
        self._segments: List[ContextSegment] = []
        self._system_prompt: str = ""
        self._system_tokens: int = 0

    def set_system_prompt(self, prompt: str) -> None:
        self._system_prompt = prompt
        self._system_tokens = self._estimate_tokens(prompt)

    def _estimate_tokens(self, text: str) -> int:
        return int(len(text) / self.chars_per_token)

    def add_segment(self, content: str, priority: int = 0, relevance: float = 1.0,
                    metadata: Optional[Dict[str, Any]] = None) -> ContextSegment:
        tokens = self._estimate_tokens(content)
        seg = ContextSegment(content, tokens, priority, relevance,
                             segment_id=f"seg_{len(self._segments)}", metadata=metadata or {})
        self._segments.append(seg)
        return seg

    def get_total_tokens(self) -> int:
        content_tokens = sum(s.tokens for s in self._segments)
        return self._system_tokens + content_tokens

    def is_within_limit(self) -> bool:
        return self.get_total_tokens() <= self.max_tokens

    def truncate(self, strategy: TruncationStrategy = TruncationStrategy.FIFO) -> List[ContextSegment]:
        if self.is_within_limit():
            return list(self._segments)

        available = self.max_tokens - self._system_tokens
        if available <= 0:
            return []

        if strategy == TruncationStrategy.FIFO:
            # Keep earliest that fit
            running = 0
            keep = []
            for seg in self._segments:
                if running + seg.tokens <= available:
                    keep.append(seg)
                    running += seg.tokens
                else:
                    break
            return keep

        elif strategy == TruncationStrategy.LIFO:
            # Keep latest that fit
            running = 0
            keep = []
            for seg in reversed(self._segments):
                if running + seg.tokens <= available:
                    keep.insert(0, seg)
                    running += seg.tokens
            return keep

        elif strategy == TruncationStrategy.RELEVANCE:
            # Sort by relevance, keep highest
            sorted_segs = sorted(self._segments, key=lambda s: s.relevance_score, reverse=True)
            running = 0
            keep = []
            for seg in sorted_segs:
                if running + seg.tokens <= available:
                    keep.append(seg)
                    running += seg.tokens
            return sorted(keep, key=lambda s: s.segment_id)

        elif strategy == TruncationStrategy.SUMMARY:
            # Keep high priority, summarize others
            high_priority = [s for s in self._segments if s.priority >= 5]
            others = [s for s in self._segments if s.priority < 5]
            running = sum(s.tokens for s in high_priority)
            keep = list(high_priority)
            for seg in others:
                if running + max(10, seg.tokens // 2) <= available:
                    # Simulate summary with shorter content
                    seg.content = seg.content[:50] + "..."
                    seg.tokens = self._estimate_tokens(seg.content)
                    keep.append(seg)
                    running += seg.tokens
            return keep

        return self._segments[:max(1, int(len(self._segments) * 0.5))]

    def get_context(self, strategy: TruncationStrategy = TruncationStrategy.FIFO) -> str:
        segments = self.truncate(strategy)
        parts = [self._system_prompt] if self._system_prompt else []
        parts.extend(s.content for s in segments)
        return "\n".join(parts)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "max_tokens": self.max_tokens, "system_tokens": self._system_tokens,
            "content_tokens": sum(s.tokens for s in self._segments),
            "total_tokens": self.get_total_tokens(),
            "segments": len(self._segments), "within_limit": self.is_within_limit(),
        }

    def clear(self) -> None:
        self._segments.clear()


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Context Window Engine")
    print("=" * 60)

    engine = ContextWindowEngine(max_tokens=100)
    engine.set_system_prompt("You are a helpful assistant.")

    for i in range(10):
        engine.add_segment(f"Message {i}: " + "x" * 20, priority=i % 3, relevance=1.0 - (i * 0.05))

    print("\n--- Stats before truncation ---")
    print(engine.get_stats())

    print("\n--- FIFO truncation ---")
    context = engine.get_context(TruncationStrategy.FIFO)
    print(f"  Length: {len(context)} chars, Est. tokens: {engine._estimate_tokens(context)}")

    print("\n--- LIFO truncation ---")
    context = engine.get_context(TruncationStrategy.LIFO)
    print(f"  Length: {len(context)} chars, Est. tokens: {engine._estimate_tokens(context)}")

    print("\n--- Relevance truncation ---")
    context = engine.get_context(TruncationStrategy.RELEVANCE)
    print(f"  Length: {len(context)} chars, Est. tokens: {engine._estimate_tokens(context)}")

    print("\nContext Window test complete.")


if __name__ == "__main__":
    run()
