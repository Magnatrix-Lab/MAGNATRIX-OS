"""Tokenizer Manager — Token counting, truncation, encoding strategies, and budget management.

Modul ini menyediakan:
- TokenCounter untuk estimate token counts dari text
- TruncationEngine untuk smart truncation strategies
- TokenBudgetManager untuk manage token budgets per request
- EncodingOptimizer untuk encoding efficiency
- TokenizerManager untuk centralized token management
"""

from __future__ import annotations

import json
import time
import uuid
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class TruncationStrategy(Enum):
    HEAD = "head"  # Keep last N tokens
    TAIL = "tail"  # Keep first N tokens
    MIDDLE = "middle"  # Keep head + tail, drop middle
    COMPRESSION = "compression"  # Summarize then fit
    PRIORITY = "priority"  # Keep important tokens


@dataclass
class TokenSegment:
    """Segmented text with token information."""
    segment_id: str
    text: str
    token_count: int = 0
    importance: float = 1.0
    can_drop: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.token_count == 0:
            self.token_count = max(1, len(self.text) // 4)


class TokenCounter:
    """Estimate token counts from text."""

    def __init__(self, chars_per_token: float = 4.0, overhead: int = 3):
        self.chars_per_token = chars_per_token
        self.overhead = overhead

    def count(self, text: str) -> int:
        if not text:
            return 0
        # Approximate: English ~4 chars/token, code ~3 chars/token
        words = text.split()
        code_tokens = len(re.findall(r'[{}();,=+\-*/<>]', text))
        return max(1, int(len(text) / self.chars_per_token) + self.overhead + code_tokens // 2)

    def count_batch(self, texts: List[str]) -> List[int]:
        return [self.count(t) for t in texts]

    def count_conversation(self, messages: List[Dict[str, str]]) -> int:
        total = 0
        for msg in messages:
            total += self.count(msg.get("content", ""))
            total += 4  # Role + format overhead per message
        return total + 2  # Base overhead


class TruncationEngine:
    """Smart truncation strategies."""

    def __init__(self, counter: TokenCounter):
        self.counter = counter

    def truncate(self, text: str, max_tokens: int, strategy: TruncationStrategy = TruncationStrategy.HEAD) -> str:
        current = self.counter.count(text)
        if current <= max_tokens:
            return text
        if strategy == TruncationStrategy.HEAD:
            return self._truncate_head(text, max_tokens)
        elif strategy == TruncationStrategy.TAIL:
            return self._truncate_tail(text, max_tokens)
        elif strategy == TruncationStrategy.MIDDLE:
            return self._truncate_middle(text, max_tokens)
        elif strategy == TruncationStrategy.COMPRESSION:
            return self._truncate_compression(text, max_tokens)
        return self._truncate_head(text, max_tokens)

    def _truncate_head(self, text: str, max_tokens: int) -> str:
        # Keep last N tokens
        words = text.split()
        approx_tokens = max_tokens * 4 // 5  # Conservative estimate
        keep_words = words[-approx_tokens:]
        return " ".join(keep_words)

    def _truncate_tail(self, text: str, max_tokens: int) -> str:
        # Keep first N tokens
        words = text.split()
        approx_tokens = max_tokens * 4 // 5
        keep_words = words[:approx_tokens]
        return " ".join(keep_words)

    def _truncate_middle(self, text: str, max_tokens: int) -> str:
        # Keep head and tail, drop middle
        words = text.split()
        approx_tokens = max_tokens * 4 // 5
        if len(words) <= approx_tokens:
            return text
        half = approx_tokens // 2
        return " ".join(words[:half]) + " ... [truncated] ... " + " ".join(words[-half:])

    def _truncate_compression(self, text: str, max_tokens: int) -> str:
        # Summarize to fit
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) <= 2:
            return self._truncate_head(text, max_tokens)
        # Keep first sentence and last sentence, compress middle
        first = sentences[0]
        last = sentences[-1]
        middle = sentences[1:-1]
        compressed = f"{first} [+{len(middle)} sentences] {last}"
        if self.counter.count(compressed) > max_tokens:
            return f"{first} [truncated]"
        return compressed

    def truncate_segments(self, segments: List[TokenSegment], max_tokens: int) -> List[TokenSegment]:
        # Sort by importance, drop least important first
        sorted_segs = sorted(segments, key=lambda s: s.importance, reverse=True)
        kept = []
        total = 0
        for seg in sorted_segs:
            if total + seg.token_count <= max_tokens or not seg.can_drop:
                kept.append(seg)
                total += seg.token_count
        return sorted(kept, key=lambda s: s.segment_id)


class TokenBudgetManager:
    """Manage token budgets per request/session."""

    def __init__(self, max_tokens: int = 8192, reserve_for_output: int = 2048):
        self.max_tokens = max_tokens
        self.reserve_for_output = reserve_for_output
        self._budgets: Dict[str, Dict[str, int]] = {}
        self._usage: Dict[str, int] = {}

    def allocate(self, session_id: str, prompt_tokens: int) -> Dict[str, int]:
        available = self.max_tokens - self.reserve_for_output
        if prompt_tokens > available:
            return {
                "allowed": 0,
                "available": available,
                "requested": prompt_tokens,
                "status": "exceeded",
            }
        output_budget = min(self.reserve_for_output, self.max_tokens - prompt_tokens)
        self._budgets[session_id] = {
            "prompt": prompt_tokens,
            "output": output_budget,
            "total": prompt_tokens + output_budget,
        }
        return {
            "allowed": output_budget,
            "available": available,
            "requested": prompt_tokens,
            "status": "ok",
        }

    def record_usage(self, session_id: str, tokens: int) -> None:
        self._usage[session_id] = self._usage.get(session_id, 0) + tokens

    def get_remaining(self, session_id: str) -> int:
        budget = self._budgets.get(session_id, {})
        used = self._usage.get(session_id, 0)
        total = budget.get("total", self.max_tokens)
        return max(0, total - used)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "max_tokens": self.max_tokens,
            "reserve": self.reserve_for_output,
            "active_sessions": len(self._budgets),
            "total_usage": sum(self._usage.values()),
        }


class EncodingOptimizer:
    """Optimize encoding for token efficiency."""

    @staticmethod
    def compress_whitespace(text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip()

    @staticmethod
    def remove_redundant_punctuation(text: str) -> str:
        return re.sub(r'([.!?])\1+', r'\1', text)

    @staticmethod
    def optimize_code(text: str) -> str:
        # Remove extra newlines in code
        lines = text.split('\n')
        optimized = []
        prev_empty = False
        for line in lines:
            is_empty = not line.strip()
            if is_empty and prev_empty:
                continue
            optimized.append(line)
            prev_empty = is_empty
        return '\n'.join(optimized)

    @staticmethod
    def optimize(text: str) -> str:
        text = EncodingOptimizer.compress_whitespace(text)
        text = EncodingOptimizer.remove_redundant_punctuation(text)
        return text


class TokenizerManager:
    """Centralized token management."""

    def __init__(self, max_tokens: int = 8192):
        self.counter = TokenCounter()
        self.truncator = TruncationEngine(self.counter)
        self.budget = TokenBudgetManager(max_tokens)
        self.optimizer = EncodingOptimizer()
        self._history: List[Dict[str, Any]] = []

    def analyze(self, text: str) -> Dict[str, Any]:
        tokens = self.counter.count(text)
        return {
            "text_length": len(text),
            "estimated_tokens": tokens,
            "words": len(text.split()),
            "lines": len(text.split('\n')),
        }

    def optimize_and_truncate(self, text: str, max_tokens: int, strategy: TruncationStrategy = TruncationStrategy.HEAD) -> Tuple[str, Dict[str, Any]]:
        optimized = self.optimizer.optimize(text)
        truncated = self.truncator.truncate(optimized, max_tokens, strategy)
        before = self.counter.count(text)
        after = self.counter.count(truncated)
        return truncated, {
            "original_tokens": before,
            "optimized_tokens": self.counter.count(optimized),
            "final_tokens": after,
            "tokens_saved": before - after,
            "strategy": strategy.value,
        }

    def manage_conversation(self, messages: List[Dict[str, str]], max_tokens: int) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
        total = self.counter.count_conversation(messages)
        if total <= max_tokens:
            return messages, {"truncated": False, "total_tokens": total}
        # Truncate oldest messages
        kept = []
        current = 0
        for msg in reversed(messages):
            msg_tokens = self.counter.count(msg.get("content", "")) + 4
            if current + msg_tokens > max_tokens and kept:
                break
            kept.append(msg)
            current += msg_tokens
        kept = list(reversed(kept))
        return kept, {
            "truncated": True,
            "original_messages": len(messages),
            "kept_messages": len(kept),
            "total_tokens": current,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self.budget.get_stats(),
            "history_entries": len(self._history),
        }


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("TOKENIZER MANAGER DEMO")
    print("=" * 70)

    manager = TokenizerManager(max_tokens=4096)

    # 1. Token counting
    print("\n[1] Token Counting")
    texts = [
        "Hello world",
        "The quick brown fox jumps over the lazy dog.",
        "def hello():\n    print('world')\n    return 42",
        "This is a very long sentence that contains many words and might take up more tokens than expected. " * 20,
    ]
    for t in texts:
        analysis = manager.analyze(t)
        print(f"  Length={analysis['text_length']:4d}, Tokens={analysis['estimated_tokens']:4d}, Words={analysis['words']}")

    # 2. Truncation
    print("\n[2] Truncation Strategies")
    long_text = "This is sentence one. " * 50 + "This is the final important sentence."
    for strategy in [TruncationStrategy.HEAD, TruncationStrategy.TAIL, TruncationStrategy.MIDDLE, TruncationStrategy.COMPRESSION]:
        truncated, info = manager.optimize_and_truncate(long_text, max_tokens=50, strategy=strategy)
        print(f"  {strategy.value:12s}: {info['final_tokens']} tokens (saved {info['tokens_saved']}), preview: {truncated[:50]}...")

    # 3. Budget management
    print("\n[3] Token Budget")
    budget = manager.budget
    result = budget.allocate("session-1", 1000)
    print(f"  Allocated: {result}")
    budget.record_usage("session-1", 800)
    print(f"  Remaining: {budget.get_remaining('session-1')}")
    result2 = budget.allocate("session-2", 7000)
    print(f"  Large prompt: {result2}")

    # 4. Conversation management
    print("\n[4] Conversation Truncation")
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you!"},
        {"role": "user", "content": "What is the weather like today?"},
        {"role": "assistant", "content": "I don't have real-time weather data."},
        {"role": "user", "content": "Tell me about Python programming."},
        {"role": "assistant", "content": "Python is a high-level programming language." * 20},
    ]
    kept, info = manager.manage_conversation(messages, max_tokens=200)
    print(f"  Original: {info['original_messages']} messages, Kept: {info['kept_messages']}, Tokens: {info['total_tokens']}")
    for m in kept:
        print(f"    [{m['role']}] {m['content'][:40]}...")

    # 5. Encoding optimization
    print("\n[5] Encoding Optimization")
    messy = "  This   has    too   much   whitespace   and  ..  redundant  punctuation!!!  "
    optimized = EncodingOptimizer.optimize(messy)
    print(f"  Before: '{messy[:50]}...'")
    print(f"  After:  '{optimized[:50]}...'")
    print(f"  Tokens saved: {manager.counter.count(messy) - manager.counter.count(optimized)}")

    # 6. Code optimization
    print("\n[6] Code Optimization")
    code = "def f():\n\n\n    x = 1\n\n\n    return x\n\n\n"
    opt_code = EncodingOptimizer.optimize_code(code)
    print(f"  Lines before: {len(code.splitlines())}, after: {len(opt_code.splitlines())}")

    # 7. Segment truncation
    print("\n[7] Segment Truncation")
    segments = [
        TokenSegment("s1", "Important context about the user", importance=1.0, can_drop=False),
        TokenSegment("s2", "Previous conversation history", importance=0.5),
        TokenSegment("s3", "System instructions", importance=0.9, can_drop=False),
        TokenSegment("s4", "Retrieved documents", importance=0.3),
        TokenSegment("s5", "Current user query", importance=1.0, can_drop=False),
    ]
    kept = manager.truncator.truncate_segments(segments, max_tokens=100)
    print(f"  Kept {len(kept)}/{len(segments)} segments:")
    for s in kept:
        print(f"    {s.segment_id}: importance={s.importance}, tokens={s.token_count}")

    # 8. Stats
    print(f"\n[8] Stats")
    print(f"  {manager.get_stats()}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
