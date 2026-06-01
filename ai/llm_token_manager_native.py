"""Token Manager — Context window budgeting, compression, and overflow handling.

Modul ini menyediakan:
- TokenCounter untuk estimasi token usage (tiktoken-style approximation)
- ContextBudget untuk alokasi token antar komponen (system, user, assistant, tools)
- CompressionEngine untuk summarization dan truncation strategies
- OverflowHandler untuk graceful degradation saat context penuh
- TokenTracker untuk histori penggunaan dan prediksi
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum, auto


class CompressionStrategy(Enum):
    SUMMARIZE = auto()
    TRUNCATE_OLDEST = auto()
    TRUNCATE_LEAST_IMPORTANT = auto()
    SLIDING_WINDOW = auto()
    KEYPOINT_EXTRACT = auto()


class TokenTier(Enum):
    SYSTEM = 0
    TOOLS = 1
    USER = 2
    ASSISTANT = 3
    WORKING_MEMORY = 4


@dataclass
class TokenUsage:
    """Token usage record for a single message/segment."""
    segment_id: str
    tier: TokenTier
    tokens: int
    content: str = ""
    timestamp: float = field(default_factory=time.time)
    priority: int = 5  # 1-10, higher = more important


@dataclass
class BudgetAllocation:
    """Allocated budget per tier."""
    tier: TokenTier
    allocated: int
    used: int = 0
    reserved: int = 0

    @property
    def remaining(self) -> int:
        return self.allocated - self.used - self.reserved

    @property
    def percent_used(self) -> float:
        return self.used / max(self.allocated, 1) * 100


class TokenCounter:
    """Approximate token counting (no tiktoken dependency, pure stdlib)."""

    # Approximation: 1 token ≈ 0.75 words for English, 1.5 chars for mixed
    RATIO_WORDS = 0.75
    RATIO_CHARS = 1.5

    def __init__(self):
        self._custom_encoders: Dict[str, Callable[[str], int]] = {}

    def count(self, text: str) -> int:
        if not text:
            return 0
        # Hybrid approach: take max of word-based and char-based estimates
        words = len(text.split())
        chars = len(text)
        word_est = int(words / self.RATIO_WORDS)
        char_est = int(chars / self.RATIO_CHARS)
        # Use character estimate for CJK, word estimate for Latin
        if any(ord(c) > 0x3000 for c in text):
            return max(1, char_est)
        return max(1, word_est)

    def count_messages(self, messages: List[Dict[str, str]]) -> int:
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "")
            # Overhead per message: ~4 tokens for role + formatting
            total += self.count(content) + 4
        return total

    def set_custom_encoder(self, name: str, fn: Callable[[str], int]) -> None:
        self._custom_encoders[name] = fn


class ContextBudget:
    """Manage token budget allocation across tiers."""

    def __init__(self, total_budget: int = 8192, reserve_buffer: int = 256):
        self.total_budget = total_budget
        self.reserve_buffer = reserve_buffer
        self._allocations: Dict[TokenTier, BudgetAllocation] = {}
        self._setup_defaults()

    def _setup_defaults(self) -> None:
        available = self.total_budget - self.reserve_buffer
        self._allocations = {
            TokenTier.SYSTEM: BudgetAllocation(TokenTier.SYSTEM, int(available * 0.10)),
            TokenTier.TOOLS: BudgetAllocation(TokenTier.TOOLS, int(available * 0.15)),
            TokenTier.USER: BudgetAllocation(TokenTier.USER, int(available * 0.35)),
            TokenTier.ASSISTANT: BudgetAllocation(TokenTier.ASSISTANT, int(available * 0.30)),
            TokenTier.WORKING_MEMORY: BudgetAllocation(TokenTier.WORKING_MEMORY, int(available * 0.10)),
        }

    def allocate(self, tier: TokenTier, tokens: int) -> bool:
        alloc = self._allocations[tier]
        if alloc.remaining >= tokens:
            alloc.used += tokens
            return True
        return False

    def deallocate(self, tier: TokenTier, tokens: int) -> None:
        alloc = self._allocations[tier]
        alloc.used = max(0, alloc.used - tokens)

    def get_status(self) -> Dict[str, Any]:
        return {
            "total_budget": self.total_budget,
            "reserve_buffer": self.reserve_buffer,
            "tiers": {
                tier.name: {
                    "allocated": a.allocated,
                    "used": a.used,
                    "remaining": a.remaining,
                    "percent_used": round(a.percent_used, 1)
                }
                for tier, a in self._allocations.items()
            }
        }

    def set_allocation(self, tier: TokenTier, percentage: float) -> None:
        available = self.total_budget - self.reserve_buffer
        self._allocations[tier].allocated = int(available * percentage)

    def resize(self, new_total: int) -> None:
        self.total_budget = new_total
        self._setup_defaults()


class CompressionEngine:
    """Compress text to fit within token limits."""

    def __init__(self, counter: Optional[TokenCounter] = None):
        self.counter = counter or TokenCounter()
        self._strategies: Dict[CompressionStrategy, Callable[[str, int], str]] = {
            CompressionStrategy.SUMMARIZE: self._summarize,
            CompressionStrategy.TRUNCATE_OLDEST: self._truncate_oldest,
            CompressionStrategy.SLIDING_WINDOW: self._sliding_window,
            CompressionStrategy.KEYPOINT_EXTRACT: self._keypoint_extract,
        }

    def compress(self, text: str, target_tokens: int, strategy: CompressionStrategy = CompressionStrategy.SUMMARIZE) -> str:
        if strategy not in self._strategies:
            strategy = CompressionStrategy.SUMMARIZE
        current = self.counter.count(text)
        if current <= target_tokens:
            return text
        return self._strategies[strategy](text, target_tokens)

    def _summarize(self, text: str, target: int) -> str:
        # Simple extractive summarization: keep first sentence, key sentences, last sentence
        sentences = text.replace(". ", ".\n").split("\n")
        if len(sentences) <= 3:
            return text[:int(target * 1.5)]  # Rough char approximation
        keep = [sentences[0]]  # First sentence
        # Keep sentences with important keywords
        keywords = ["important", "key", "main", "critical", "result", "conclusion", "summary", "therefore", "thus"]
        for s in sentences[1:-1]:
            if any(k in s.lower() for k in keywords) and len(s) > 10:
                keep.append(s)
        keep.append(sentences[-1])  # Last sentence
        result = " ".join(keep)
        # If still too long, truncate
        if self.counter.count(result) > target:
            return result[:int(target * 1.5)]
        return result

    def _truncate_oldest(self, text: str, target: int) -> str:
        # Keep the most recent content
        approx_chars = int(target * 1.5)
        if len(text) > approx_chars:
            return "... " + text[-approx_chars:]
        return text

    def _sliding_window(self, text: str, target: int) -> str:
        # Keep context window around most recent content
        approx_chars = int(target * 1.5)
        if len(text) > approx_chars:
            return "[context summarized] " + text[-approx_chars:]
        return text

    def _keypoint_extract(self, text: str, target: int) -> str:
        # Extract bullet points
        lines = text.split("\n")
        bullets = [l for l in lines if l.strip().startswith(("-", "*", "•", "1.", "2.", "3."))]
        if not bullets:
            bullets = [l for l in lines if len(l.strip()) > 20]
        result = "\n".join(bullets[:max(3, target // 50)])
        if self.counter.count(result) > target:
            return result[:int(target * 1.5)]
        return result

    def add_strategy(self, name: CompressionStrategy, fn: Callable[[str, int], str]) -> None:
        self._strategies[name] = fn


class OverflowHandler:
    """Handle context window overflow gracefully."""

    def __init__(self, budget: ContextBudget, compressor: CompressionEngine):
        self.budget = budget
        self.compressor = compressor
        self._overflow_count = 0

    def handle(self, messages: List[Dict[str, str]], counter: TokenCounter) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
        total = counter.count_messages(messages)
        if total <= self.budget.total_budget - self.budget.reserve_buffer:
            return messages, {"action": "none", "total_tokens": total}

        self._overflow_count += 1
        available = self.budget.total_budget - self.budget.reserve_buffer

        # Strategy: compress oldest messages first, keep newest
        result = []
        current_tokens = 0
        compressed_any = False

        # Process from oldest to newest
        for i, msg in enumerate(messages):
            msg_tokens = counter.count(msg.get("content", "")) + 4
            if current_tokens + msg_tokens > available and i < len(messages) - 1:
                # Compress this message
                compressed = self.compressor.compress(msg.get("content", ""), max(20, available - current_tokens - 20))
                compressed_tokens = counter.count(compressed) + 4
                if current_tokens + compressed_tokens <= available:
                    result.append({**msg, "content": compressed, "_compressed": True})
                    current_tokens += compressed_tokens
                    compressed_any = True
                else:
                    # Skip old message entirely, keep just a summary marker
                    if i == 0 and msg.get("role") == "system":
                        # Never drop system entirely, compress aggressively
                        mini = counter.count(msg.get("content", "")) > 0 and self.compressor.compress(msg.get("content", ""), 50) or "[system]"
                        result.append({**msg, "content": mini, "_compressed": True})
                        current_tokens += counter.count(mini) + 4
                    # else: drop silently
            else:
                if current_tokens + msg_tokens <= available:
                    result.append(msg)
                    current_tokens += msg_tokens

        return result, {
            "action": "compress" if compressed_any else "drop",
            "original_count": len(messages),
            "final_count": len(result),
            "original_tokens": total,
            "final_tokens": current_tokens,
            "overflow_number": self._overflow_count,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {"overflow_count": self._overflow_count}


class TokenTracker:
    """Track historical token usage and predict future needs."""

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self._history: List[TokenUsage] = []
        self._tier_totals: Dict[TokenTier, int] = {t: 0 for t in TokenTier}

    def record(self, usage: TokenUsage) -> None:
        self._history.append(usage)
        self._tier_totals[usage.tier] += usage.tokens
        if len(self._history) > self.window_size:
            removed = self._history.pop(0)
            self._tier_totals[removed.tier] -= removed.tokens

    def predict_next(self, tier: TokenTier) -> int:
        """Simple moving average prediction."""
        tier_usages = [u.tokens for u in self._history if u.tier == tier]
        if not tier_usages:
            return 50  # Default estimate
        return int(sum(tier_usages) / len(tier_usages))

    def get_stats(self) -> Dict[str, Any]:
        total = sum(self._tier_totals.values())
        return {
            "total_recorded": total,
            "window_size": len(self._history),
            "tier_breakdown": {t.name: self._tier_totals[t] for t in TokenTier},
            "predictions": {t.name: self.predict_next(t) for t in TokenTier},
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([{
                "segment_id": u.segment_id,
                "tier": u.tier.name,
                "tokens": u.tokens,
                "timestamp": u.timestamp,
                "priority": u.priority,
            } for u in self._history], f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("TOKEN MANAGER DEMO")
    print("=" * 70)

    counter = TokenCounter()

    # 1. Token counting
    print("\n[1] Token Counting")
    texts = [
        "Hello world",
        "Python is a high-level programming language.",
        "人工智能（AI）是计算机科学的一个分支，致力于创造能够执行通常需要人类智能的任务的系统。",
    ]
    for t in texts:
        print(f"  {t[:40]}... -> {counter.count(t)} tokens")

    # 2. Message counting
    print("\n[2] Message Counting")
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain quantum computing in simple terms."},
        {"role": "assistant", "content": "Quantum computing uses quantum bits (qubits) that can exist in multiple states simultaneously, unlike classical bits."},
    ]
    print(f"  {len(messages)} messages -> {counter.count_messages(messages)} tokens")

    # 3. Budget allocation
    print("\n[3] Budget Allocation")
    budget = ContextBudget(total_budget=4096, reserve_buffer=256)
    print(f"  Total: {budget.total_budget}, Reserve: {budget.reserve_buffer}")
    for tier, alloc in budget._allocations.items():
        print(f"    {tier.name}: {alloc.allocated} tokens")
    budget.allocate(TokenTier.USER, 500)
    print(f"  After allocating 500 to USER: used={budget._allocations[TokenTier.USER].used}")

    # 4. Compression
    print("\n[4] Compression")
    compressor = CompressionEngine(counter)
    long_text = "This is a very long text. " * 100
    original_tokens = counter.count(long_text)
    print(f"  Original: {original_tokens} tokens")
    compressed = compressor.compress(long_text, 100, CompressionStrategy.SUMMARIZE)
    print(f"  Summarized: {counter.count(compressed)} tokens")
    truncated = compressor.compress(long_text, 50, CompressionStrategy.TRUNCATE_OLDEST)
    print(f"  Truncated: {counter.count(truncated)} tokens")

    # 5. Overflow handling
    print("\n[5] Overflow Handling")
    overflow = OverflowHandler(budget, compressor)
    big_messages = [
        {"role": "system", "content": "You are a helpful assistant with expertise in many fields."},
    ] + [{"role": "user", "content": f"Question {i}: " + "What is the meaning of life? " * 50} for i in range(20)]
    result, action = overflow.handle(big_messages, counter)
    print(f"  Action: {action['action']}")
    print(f"  Original: {action['original_count']} messages, {action['original_tokens']} tokens")
    print(f"  Final: {action['final_count']} messages, {action['final_tokens']} tokens")

    # 6. Token tracking
    print("\n[6] Token Tracking")
    tracker = TokenTracker(window_size=50)
    for i in range(10):
        tracker.record(TokenUsage(f"msg-{i}", TokenTier.USER, 100 + i * 10, f"Message {i}"))
    for i in range(5):
        tracker.record(TokenUsage(f"sys-{i}", TokenTier.SYSTEM, 50, f"System {i}"))
    stats = tracker.get_stats()
    print(f"  Total recorded: {stats['total_recorded']}")
    print(f"  Window: {stats['window_size']}")
    print(f"  Predictions: {stats['predictions']}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
