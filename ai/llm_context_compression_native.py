"""Context Compression — Summarization, sliding window, token budget management.

Modul ini menyediakan:
- TokenBudget: manage token allocation across conversation turns
- SlidingWindowCompressor: maintain rolling context window
- HierarchicalSummarizer: multi-level summarization (turn -> section -> full)
- SemanticCompressor: extract key information vs filler removal
- ContextManager: full pipeline for context compression and retrieval
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum, auto


class CompressionLevel(Enum):
    NONE = 1.0
    LIGHT = 0.8
    MEDIUM = 0.5
    AGGRESSIVE = 0.3
    EXTREME = 0.1


@dataclass
class ConversationTurn:
    """Single turn in conversation."""
    turn_id: str
    role: str
    content: str
    timestamp: float
    token_count: int = 0
    importance: float = 1.0
    compressed: Optional[str] = None

    def __post_init__(self):
        if self.token_count == 0:
            self.token_count = len(self.content.split())


@dataclass
class SummaryNode:
    """Summary at a particular level."""
    summary_id: str
    level: int
    content: str
    token_count: int
    source_turns: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


class TokenBudget:
    """Manage token allocation across conversation components."""

    def __init__(self, max_tokens: int = 4096, reserve_tokens: int = 512):
        self.max_tokens = max_tokens
        self.reserve_tokens = reserve_tokens
        self.available = max_tokens - reserve_tokens
        self._used = 0
        self._allocations: Dict[str, int] = {}

    def allocate(self, component: str, requested: int) -> int:
        granted = min(requested, self.available - self._used)
        self._allocations[component] = granted
        self._used += granted
        return granted

    def free(self, component: str) -> int:
        freed = self._allocations.pop(component, 0)
        self._used -= freed
        return freed

    def get_remaining(self) -> int:
        return self.available - self._used

    def get_stats(self) -> Dict[str, Any]:
        return {
            "max": self.max_tokens,
            "reserve": self.reserve_tokens,
            "available": self.available,
            "used": self._used,
            "remaining": self.get_remaining(),
            "allocations": self._allocations
        }


class SlidingWindowCompressor:
    """Maintain a rolling window of recent turns, compress older ones."""

    def __init__(self, max_turns: int = 10, max_tokens: int = 2048):
        self.max_turns = max_turns
        self.max_tokens = max_tokens
        self._turns: List[ConversationTurn] = []
        self._summaries: List[SummaryNode] = []

    def add_turn(self, turn: ConversationTurn) -> None:
        self._turns.append(turn)
        self._enforce_limits()

    def _enforce_limits(self) -> None:
        # Compress oldest turns if over token limit
        total = sum(t.token_count for t in self._turns)
        while total > self.max_tokens and len(self._turns) > 2:
            oldest = self._turns.pop(0)
            if not oldest.compressed:
                compressed = self._compress_turn(oldest)
                if compressed:
                    oldest.compressed = compressed
                    oldest.token_count = len(compressed.split())
                    self._turns.insert(0, oldest)
                else:
                    # Drop if can't compress
                    self._summarize_turns([oldest])
            else:
                # Already compressed, drop it
                self._summarize_turns([oldest])
            total = sum(t.token_count for t in self._turns)
        # Drop oldest if over turn count
        while len(self._turns) > self.max_turns:
            removed = self._turns.pop(0)
            # Summarize removed turns
            summary = self._summarize_turns([removed])
            self._summaries.append(summary)

    def _compress_turn(self, turn: ConversationTurn) -> Optional[str]:
        # Extract key sentences: first and last, drop middle
        sentences = turn.content.split(". ")
        if len(sentences) <= 2:
            return turn.content
        key_sentences = [sentences[0], sentences[-1]]
        return ". ".join(key_sentences) + "."

    def _summarize_turns(self, turns: List[ConversationTurn]) -> SummaryNode:
        combined = " | ".join(t.content[:100] for t in turns)
        return SummaryNode(
            summary_id=str(uuid.uuid4())[:8],
            level=1,
            content=combined,
            token_count=len(combined.split()),
            source_turns=[t.turn_id for t in turns]
        )

    def get_context(self, include_summaries: bool = True) -> str:
        parts = []
        if include_summaries and self._summaries:
            parts.append(f"[Previous: {self._summaries[-1].content}]")
        for turn in self._turns:
            content = turn.compressed or turn.content
            parts.append(f"{turn.role}: {content}")
        return "\n".join(parts)

    def get_token_count(self) -> int:
        return sum(t.token_count for t in self._turns)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "turns": len(self._turns),
            "summaries": len(self._summaries),
            "current_tokens": self.get_token_count(),
            "max_tokens": self.max_tokens,
            "max_turns": self.max_turns
        }


class HierarchicalSummarizer:
    """Multi-level summarization: turn -> section -> full conversation."""

    def __init__(self, section_size: int = 5):
        self.section_size = section_size
        self._turns: List[ConversationTurn] = []
        self._sections: List[SummaryNode] = []
        self._full_summary: Optional[SummaryNode] = None

    def add_turn(self, turn: ConversationTurn) -> None:
        self._turns.append(turn)
        if len(self._turns) % self.section_size == 0:
            self._create_section()

    def _create_section(self) -> None:
        recent = self._turns[-self.section_size:]
        content = " | ".join(f"{t.role}: {t.content[:80]}" for t in recent)
        section = SummaryNode(
            summary_id=str(uuid.uuid4())[:8],
            level=2,
            content=content,
            token_count=len(content.split()),
            source_turns=[t.turn_id for t in recent]
        )
        self._sections.append(section)
        if len(self._sections) % 3 == 0:
            self._create_full_summary()

    def _create_full_summary(self) -> None:
        recent_sections = self._sections[-3:]
        content = " // ".join(s.content[:150] for s in recent_sections)
        self._full_summary = SummaryNode(
            summary_id=str(uuid.uuid4())[:8],
            level=3,
            content=content,
            token_count=len(content.split()),
            source_turns=[s.summary_id for s in recent_sections]
        )

    def get_summary(self, level: int = 2) -> Optional[SummaryNode]:
        if level == 3:
            return self._full_summary
        if level == 2 and self._sections:
            return self._sections[-1]
        return None

    def get_full_context(self, compression: CompressionLevel = CompressionLevel.MEDIUM) -> str:
        parts = []
        if self._full_summary:
            parts.append(f"[Summary: {self._full_summary.content}]")
        elif self._sections:
            parts.append(f"[Recent: {self._sections[-1].content}]")
        # Include recent uncompressed turns based on compression level
        keep_count = max(1, int(len(self._turns) * compression.value))
        for turn in self._turns[-keep_count:]:
            parts.append(f"{turn.role}: {turn.content}")
        return "\n".join(parts)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_turns": len(self._turns),
            "sections": len(self._sections),
            "has_full_summary": self._full_summary is not None,
            "full_summary_tokens": self._full_summary.token_count if self._full_summary else 0
        }


class SemanticCompressor:
    """Extract key information vs filler removal."""

    FILLER_WORDS = {
        "um", "uh", "like", "you know", "actually", "basically", "literally",
        "honestly", "seriously", "totally", "definitely", "probably", "maybe"
    }

    def __init__(self, compression_level: CompressionLevel = CompressionLevel.MEDIUM):
        self.level = compression_level

    def compress(self, text: str) -> str:
        # Remove filler words
        words = text.split()
        filtered = [w for w in words if w.lower().strip(",.!?:;") not in self.FILLER_WORDS]
        # Remove redundant spaces
        text = " ".join(filtered)
        # Extract sentences based on compression level
        sentences = text.split(". ")
        if len(sentences) <= 2:
            return text
        keep = max(1, int(len(sentences) * self.level.value))
        if keep == 1:
            return sentences[0] + "."
        # Keep first, last, and evenly distributed middle
        indices = [0] + [int(i * (len(sentences) - 1) / max(keep - 1, 1)) for i in range(1, keep)]
        selected = [sentences[i] for i in sorted(set(indices))]
        return ". ".join(selected) + "."

    def compress_conversation(self, turns: List[ConversationTurn]) -> List[ConversationTurn]:
        compressed = []
        for turn in turns:
            new_content = self.compress(turn.content)
            compressed.append(ConversationTurn(
                turn_id=turn.turn_id,
                role=turn.role,
                content=new_content,
                timestamp=turn.timestamp,
                token_count=len(new_content.split()),
                importance=turn.importance
            ))
        return compressed

    def get_stats(self, original: str, compressed: str) -> Dict[str, float]:
        orig_len = len(original.split())
        comp_len = len(compressed.split())
        return {
            "original_tokens": orig_len,
            "compressed_tokens": comp_len,
            "ratio": round(comp_len / max(orig_len, 1), 3),
            "saved": orig_len - comp_len
        }


class ContextManager:
    """Full pipeline for context compression and retrieval."""

    def __init__(self, max_tokens: int = 4096, max_turns: int = 20):
        self.budget = TokenBudget(max_tokens)
        self.window = SlidingWindowCompressor(max_turns=max_turns, max_tokens=max_tokens)
        self.hierarchical = HierarchicalSummarizer()
        self.semantic = SemanticCompressor(CompressionLevel.MEDIUM)
        self._turns: List[ConversationTurn] = []

    def add_message(self, role: str, content: str) -> ConversationTurn:
        turn = ConversationTurn(
            turn_id=str(uuid.uuid4())[:8],
            role=role,
            content=content,
            timestamp=time.time()
        )
        self._turns.append(turn)
        self.window.add_turn(turn)
        self.hierarchical.add_turn(turn)
        return turn

    def get_context(self, mode: str = "auto") -> str:
        if mode == "window":
            return self.window.get_context()
        elif mode == "hierarchical":
            return self.hierarchical.get_full_context()
        elif mode == "semantic":
            compressed = self.semantic.compress_conversation(self._turns[-10:])
            return "\n".join(f"{t.role}: {t.content}" for t in compressed)
        elif mode == "auto":
            # Auto-select based on token count
            total = sum(t.token_count for t in self._turns)
            if total > self.budget.available * 0.8:
                return self.hierarchical.get_full_context(CompressionLevel.AGGRESSIVE)
            elif total > self.budget.available * 0.5:
                return self.window.get_context()
            return self.window.get_context(include_summaries=False)
        return self.window.get_context()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_turns": len(self._turns),
            "total_tokens": sum(t.token_count for t in self._turns),
            "budget": self.budget.get_stats(),
            "window": self.window.get_stats(),
            "hierarchical": self.hierarchical.get_stats()
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "stats": self.get_stats(),
                "context_sample": self.get_context()[:500]
            }, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("CONTEXT COMPRESSION DEMO")
    print("=" * 70)

    # 1. Token Budget
    print("\n[1] Token Budget")
    budget = TokenBudget(max_tokens=4096, reserve_tokens=512)
    budget.allocate("system", 200)
    budget.allocate("history", 1500)
    budget.allocate("current", 800)
    print(f"  Stats: {budget.get_stats()}")

    # 2. Sliding Window
    print("\n[2] Sliding Window Compressor")
    sw = SlidingWindowCompressor(max_turns=5, max_tokens=100)
    for i in range(8):
        turn = ConversationTurn(
            turn_id=f"t{i}",
            role="user" if i % 2 == 0 else "assistant",
            content=f"This is turn number {i} with some discussion about topic {i}. It contains multiple sentences. Here is the conclusion of turn {i}.",
            timestamp=time.time()
        )
        sw.add_turn(turn)
    print(f"  Stats: {sw.get_stats()}")
    print(f"  Context:\n{sw.get_context()[:300]}...")

    # 3. Hierarchical Summarizer
    print("\n[3] Hierarchical Summarizer")
    hs = HierarchicalSummarizer(section_size=3)
    for i in range(10):
        turn = ConversationTurn(
            turn_id=f"t{i}",
            role="user" if i % 2 == 0 else "assistant",
            content=f"Discussion about topic {i} with details and examples. This is a longer message for testing summarization.",
            timestamp=time.time()
        )
        hs.add_turn(turn)
    print(f"  Stats: {hs.get_stats()}")
    summary = hs.get_summary(level=3)
    if summary:
        print(f"  Full summary: {summary.content[:150]}...")
    print(f"  Context:\n{hs.get_full_context()[:300]}...")

    # 4. Semantic Compressor
    print("\n[4] Semantic Compressor")
    sc = SemanticCompressor(CompressionLevel.MEDIUM)
    text = "The quick brown fox jumps over the lazy dog. Actually, this is basically just a test sentence. You know, honestly, we should probably focus on the important parts. The system is working correctly."
    compressed = sc.compress(text)
    stats = sc.get_stats(text, compressed)
    print(f"  Original: {text[:80]}...")
    print(f"  Compressed: {compressed[:80]}...")
    print(f"  Stats: {stats}")

    # 5. Full Context Manager
    print("\n[5] Full Context Manager")
    cm = ContextManager(max_tokens=2048, max_turns=10)
    cm.add_message("system", "You are a helpful AI assistant.")
    for i in range(6):
        cm.add_message("user", f"Question {i}: How does feature {i} work?")
        cm.add_message("assistant", f"Answer {i}: Feature {i} works by processing data through pipeline {i}. It handles input validation, transformation, and output generation. The feature is optimized for performance and reliability.")
    print(f"  Stats: {cm.get_stats()}")
    print(f"  Auto context (first 300 chars):\n{cm.get_context('auto')[:300]}...")
    print(f"  Hierarchical context (first 300 chars):\n{cm.get_context('hierarchical')[:300]}...")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
