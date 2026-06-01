"""Context Window Manager — Token budgeting, summarization, sliding window, priority.

Modul ini menyediakan:
- TokenBudget untuk tracking token usage per window
- Message prioritization dengan importance scoring
- SlidingWindow eviction dengan FIFO/LRU/strategy
- ContextSummarizer untuk condensing old messages
- ContextComposer untuk menggabungkan semua strategi
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class EvictionStrategy(Enum):
    FIFO = auto()
    LRU = auto()
    IMPORTANCE = auto()
    SUMMARIZE = auto()


@dataclass
class ContextMessage:
    """Single message dalam context window."""
    message_id: str
    role: MessageRole
    content: str
    tokens: int = 0
    timestamp: float = field(default_factory=time.time)
    importance: float = 1.0  # 0.0 - 10.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""  # If this message was summarized

    def __post_init__(self):
        if not self.tokens:
            self.tokens = len(self.content) // 4 + 1  # Simple estimate


@dataclass
class TokenBudget:
    """Budget tracking untuk token limits."""
    max_tokens: int = 4096
    system_reserve: int = 500
    response_reserve: int = 1024
    _used: int = 0
    _history: List[Tuple[float, int]] = field(default_factory=list)  # (time, tokens)

    def available(self) -> int:
        return self.max_tokens - self.system_reserve - self.response_reserve - self._used

    def allocate(self, tokens: int) -> bool:
        if tokens <= self.available():
            self._used += tokens
            self._history.append((time.time(), tokens))
            return True
        return False

    def free(self, tokens: int) -> None:
        self._used = max(0, self._used - tokens)

    def get_usage(self) -> Dict[str, int]:
        return {
            "max": self.max_tokens,
            "reserved": self.system_reserve + self.response_reserve,
            "used": self._used,
            "available": self.available()
        }

    def set_max(self, max_tokens: int) -> None:
        self.max_tokens = max_tokens


class Summarizer:
    """Summarize messages untuk menghemat token."""

    def __init__(self, compression_ratio: float = 0.3):
        self.compression_ratio = compression_ratio

    def summarize(self, message: ContextMessage) -> str:
        # Simulated summarization: truncate dan extract key points
        content = message.content
        target_len = max(20, int(len(content) * self.compression_ratio))
        if len(content) <= target_len:
            return content
        # Take first sentence + key words hint
        sentences = content.split(". ")
        if len(sentences) > 1:
            return sentences[0] + ". (Summary: " + content[:target_len] + "...)"
        return content[:target_len] + "..."

    def summarize_batch(self, messages: List[ContextMessage]) -> str:
        combined = " | ".join(m.content[:100] for m in messages)
        return f"[Summary of {len(messages)} messages]: {combined[:200]}..."


class SlidingWindow:
    """Manage context window dengan eviction strategies."""

    def __init__(self, budget: TokenBudget, strategy: EvictionStrategy = EvictionStrategy.FIFO):
        self.budget = budget
        self.strategy = strategy
        self._messages: List[ContextMessage] = []
        self._summarizer = Summarizer()
        self._access_times: Dict[str, float] = {}

    def add(self, message: ContextMessage) -> ContextMessage:
        # If adding exceeds budget, evict first
        while not self.budget.allocate(message.tokens) and self._messages:
            self._evict_one()
        self._messages.append(message)
        self._access_times[message.message_id] = time.time()
        return message

    def _evict_one(self) -> None:
        if not self._messages:
            return
        if self.strategy == EvictionStrategy.FIFO:
            removed = self._messages.pop(0)
        elif self.strategy == EvictionStrategy.LRU:
            oldest = min(self._messages, key=lambda m: self._access_times.get(m.message_id, 0))
            self._messages.remove(oldest)
            removed = oldest
        elif self.strategy == EvictionStrategy.IMPORTANCE:
            lowest = min(self._messages, key=lambda m: m.importance)
            self._messages.remove(lowest)
            removed = lowest
        elif self.strategy == EvictionStrategy.SUMMARIZE:
            oldest = self._messages[0]
            if oldest.summary:
                # Already summarized, remove it
                removed = self._messages.pop(0)
                self.budget.free(removed.tokens)
                return
            summary = self._summarizer.summarize(oldest)
            new_tokens = len(summary) // 4 + 1
            old_tokens = oldest.tokens
            if new_tokens >= old_tokens:
                # No savings, remove the message
                removed = self._messages.pop(0)
                self.budget.free(old_tokens)
                return
            oldest.summary = summary
            oldest.tokens = new_tokens
            oldest.content = summary
            self.budget.free(old_tokens - new_tokens)
            return
        else:
            removed = self._messages.pop(0)
        self.budget.free(removed.tokens)

    def get_context(self, include_summaries: bool = True) -> List[Dict[str, Any]]:
        result = []
        for m in self._messages:
            if m.summary and include_summaries:
                result.append({"role": m.role.value, "content": m.summary})
            else:
                result.append({"role": m.role.value, "content": m.content})
        return result

    def get_token_count(self) -> int:
        return sum(m.tokens for m in self._messages)

    def update_importance(self, message_id: str, importance: float) -> None:
        for m in self._messages:
            if m.message_id == message_id:
                m.importance = importance
                break

    def touch(self, message_id: str) -> None:
        self._access_times[message_id] = time.time()

    def clear(self) -> None:
        for m in self._messages:
            self.budget.free(m.tokens)
        self._messages.clear()
        self._access_times.clear()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "messages": len(self._messages),
            "tokens": self.get_token_count(),
            "budget": self.budget.get_usage(),
            "strategy": self.strategy.name
        }


class PriorityQueue:
    """Priority-based message ordering untuk context composition."""

    def __init__(self):
        self._messages: List[ContextMessage] = []

    def add(self, message: ContextMessage) -> None:
        self._messages.append(message)
        self._messages.sort(key=lambda m: (-m.importance, m.timestamp))

    def get_top(self, n: int) -> List[ContextMessage]:
        return self._messages[:n]

    def remove_lowest(self) -> Optional[ContextMessage]:
        if not self._messages:
            return None
        return self._messages.pop()


class ContextComposer:
    """Compose final context dengan multiple strategies."""

    def __init__(self, budget: TokenBudget, strategy: EvictionStrategy = EvictionStrategy.FIFO):
        self.window = SlidingWindow(budget, strategy)
        self.system_messages: List[ContextMessage] = []
        self.priority_queue = PriorityQueue()

    def set_system(self, content: str) -> ContextMessage:
        msg = ContextMessage(
            message_id=str(uuid.uuid4())[:8],
            role=MessageRole.SYSTEM,
            content=content,
            importance=10.0
        )
        self.system_messages = [msg]
        return msg

    def add_user(self, content: str, importance: float = 5.0) -> ContextMessage:
        msg = ContextMessage(
            message_id=str(uuid.uuid4())[:8],
            role=MessageRole.USER,
            content=content,
            importance=importance
        )
        self.window.add(msg)
        self.priority_queue.add(msg)
        return msg

    def add_assistant(self, content: str, importance: float = 4.0) -> ContextMessage:
        msg = ContextMessage(
            message_id=str(uuid.uuid4())[:8],
            role=MessageRole.ASSISTANT,
            content=content,
            importance=importance
        )
        self.window.add(msg)
        self.priority_queue.add(msg)
        return msg

    def add_tool(self, content: str, importance: float = 3.0) -> ContextMessage:
        msg = ContextMessage(
            message_id=str(uuid.uuid4())[:8],
            role=MessageRole.TOOL,
            content=content,
            importance=importance
        )
        self.window.add(msg)
        self.priority_queue.add(msg)
        return msg

    def compose(self) -> List[Dict[str, str]]:
        """Compose final context: system + window messages."""
        result = []
        for m in self.system_messages:
            result.append({"role": m.role.value, "content": m.content})
        for m in self.window._messages:
            result.append({"role": m.role.value, "content": m.content})
        return result

    def compose_priority(self, max_messages: int = 10) -> List[Dict[str, str]]:
        """Compose using priority queue instead of window order."""
        result = []
        for m in self.system_messages:
            result.append({"role": m.role.value, "content": m.content})
        for m in self.priority_queue.get_top(max_messages):
            result.append({"role": m.role.value, "content": m.content})
        return result

    def get_stats(self) -> Dict[str, Any]:
        return {
            "system_messages": len(self.system_messages),
            "window": self.window.get_stats(),
            "priority_queue": len(self.priority_queue._messages),
            "total_tokens": sum(m.tokens for m in self.system_messages) + self.window.get_token_count()
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "context": self.compose(),
                "stats": self.get_stats()
            }, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("CONTEXT WINDOW MANAGER DEMO")
    print("=" * 70)

    # 1. Token Budget
    print("\n[1] Token Budget")
    budget = TokenBudget(max_tokens=1000, system_reserve=100, response_reserve=200)
    print(f"  Available: {budget.available()}")
    budget.allocate(300)
    print(f"  After 300: used={budget._used}, available={budget.available()}")
    budget.allocate(400)
    print(f"  After 700: used={budget._used}, available={budget.available()}")
    print(f"  Usage: {budget.get_usage()}")

    # 2. Sliding Window with FIFO
    print("\n[2] Sliding Window (FIFO)")
    window = SlidingWindow(budget, EvictionStrategy.FIFO)
    for i in range(10):
        msg = ContextMessage(str(i), MessageRole.USER, f"Message number {i} with some content", tokens=80)
        window.add(msg)
    print(f"  Messages: {len(window._messages)}, Tokens: {window.get_token_count()}")
    print(f"  Stats: {window.get_stats()}")

    # 3. Sliding Window with SUMMARIZE
    print("\n[3] Sliding Window (SUMMARIZE)")
    budget2 = TokenBudget(max_tokens=1000, system_reserve=100, response_reserve=200)
    window2 = SlidingWindow(budget2, EvictionStrategy.SUMMARIZE)
    for i in range(10):
        msg = ContextMessage(str(i), MessageRole.USER, f"This is a longer message number {i} that should be summarized when the window gets full and needs eviction strategy to work", tokens=100)
        window2.add(msg)
    print(f"  Messages: {len(window2._messages)}, Tokens: {window2.get_token_count()}")
    summarized = [m for m in window2._messages if m.summary]
    print(f"  Summarized messages: {len(summarized)}")

    # 4. Context Composer
    print("\n[4] Context Composer")
    composer = ContextComposer(TokenBudget(max_tokens=2000, system_reserve=100, response_reserve=300))
    composer.set_system("You are a helpful AI assistant.")
    composer.add_user("What is Python?")
    composer.add_assistant("Python is a programming language.")
    composer.add_user("How do I write a loop?", importance=8.0)
    composer.add_assistant("You can use for or while loops.")
    composer.add_user("What about recursion?", importance=6.0)
    ctx = composer.compose()
    print(f"  Composed {len(ctx)} messages")
    for msg in ctx:
        print(f"    [{msg['role']}] {msg['content'][:50]}...")
    print(f"  Stats: {composer.get_stats()}")

    # 5. Priority-based composition
    print("\n[5] Priority Composition")
    priority_ctx = composer.compose_priority(max_messages=3)
    print(f"  Top 3 priority messages:")
    for msg in priority_ctx:
        print(f"    [{msg['role']}] {msg['content'][:50]}...")

    # 6. Summarizer
    print("\n[6] Summarizer")
    summ = Summarizer(compression_ratio=0.3)
    long_msg = ContextMessage("l1", MessageRole.USER, "This is a very long message that contains multiple sentences. It talks about Python programming and how to write good code. The key points are: use clear variable names, write comments, and test your code.", tokens=200)
    summary = summ.summarize(long_msg)
    print(f"  Original: {long_msg.content[:60]}...")
    print(f"  Summary: {summary}")
    batch_summary = summ.summarize_batch(composer.window._messages[:3])
    print(f"  Batch summary: {batch_summary}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
