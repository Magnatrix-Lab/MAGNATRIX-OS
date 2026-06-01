"""Conversation State Manager — Advanced context window management, summarization, memory hierarchy.

Modul ini menyediakan:
- ConversationThread untuk manage messages dengan token budgeting
- ContextWindow untuk sliding window dengan token counting
- Summarizer untuk progressive summarization
- MemoryHierarchy untuk short-term / long-term / episodic memory
- TokenBudgetManager untuk enforce limits per user / session
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum, auto


class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class MemoryLevel(Enum):
    SHORT_TERM = auto()
    LONG_TERM = auto()
    EPISODIC = auto()


@dataclass
class Message:
    """Single conversation message."""
    message_id: str
    role: MessageRole
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    token_count: int = 0

    def __post_init__(self):
        if self.token_count == 0:
            # Approximate: 1 token ~ 4 chars for English
            self.token_count = max(1, len(self.content) // 4)


@dataclass
class Summary:
    """Generated summary of conversation segment."""
    summary_id: str
    start_message_id: str
    end_message_id: str
    content: str
    token_count: int = 0
    created_at: float = field(default_factory=time.time)
    level: MemoryLevel = MemoryLevel.LONG_TERM


@dataclass
class TokenBudget:
    """Budget allocation for a conversation."""
    max_total: int = 8192
    reserved_for_response: int = 2048
    reserved_for_system: int = 512
    available_for_history: int = 0

    def __post_init__(self):
        self.available_for_history = self.max_total - self.reserved_for_response - self.reserved_for_system


class ConversationThread:
    """Full conversation with message management."""

    def __init__(self, thread_id: str, title: str = "", budget: Optional[TokenBudget] = None):
        self.thread_id = thread_id
        self.title = title
        self.budget = budget or TokenBudget()
        self._messages: List[Message] = []
        self._summaries: List[Summary] = []
        self._created_at = time.time()
        self._last_active = time.time()

    def add_message(self, role: MessageRole, content: str, metadata: Optional[Dict[str, Any]] = None) -> Message:
        msg = Message(
            message_id=str(uuid.uuid4())[:12],
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self._messages.append(msg)
        self._last_active = time.time()
        return msg

    def get_messages(self) -> List[Message]:
        return list(self._messages)

    def get_recent(self, n: int = 10) -> List[Message]:
        return self._messages[-n:]

    def total_tokens(self) -> int:
        return sum(m.token_count for m in self._messages) + sum(s.token_count for s in self._summaries)

    def is_over_budget(self) -> bool:
        return self.total_tokens() > self.budget.max_total

    def prune_to_budget(self, keep_recent: int = 5) -> List[Message]:
        """Remove oldest messages while keeping recent ones and summaries."""
        if self.total_tokens() <= self.budget.max_total:
            return self._messages
        # Keep recent messages
        keep = self._messages[-keep_recent:]
        removed = self._messages[:-keep_recent]
        self._messages = keep
        return removed

    def add_summary(self, summary: Summary) -> None:
        self._summaries.append(summary)

    def get_context_for_model(self) -> List[Dict[str, str]]:
        """Build context array for LLM API call."""
        result = []
        # Include summaries as system context
        for s in self._summaries:
            result.append({"role": "system", "content": f"[Summary]: {s.content}"})
        # Include messages
        for m in self._messages:
            result.append({"role": m.role.value, "content": m.content})
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "thread_id": self.thread_id,
            "title": self.title,
            "message_count": len(self._messages),
            "summary_count": len(self._summaries),
            "total_tokens": self.total_tokens(),
            "budget": {"max": self.budget.max_total, "available": self.budget.available_for_history},
            "created_at": self._created_at,
            "last_active": self._last_active,
        }


class Summarizer:
    """Progressive summarization of conversation segments."""

    def __init__(self, trigger_threshold: int = 3000, summary_ratio: float = 0.3):
        self.trigger_threshold = trigger_threshold
        self.summary_ratio = summary_ratio

    def should_summarize(self, thread: ConversationThread) -> bool:
        return thread.total_tokens() > self.trigger_threshold

    def summarize(self, messages: List[Message], summarizer_fn: Optional[Callable[[List[Message]], str]] = None) -> Summary:
        summarizer_fn = summarizer_fn or self._default_summarizer
        content = summarizer_fn(messages)
        return Summary(
            summary_id=str(uuid.uuid4())[:12],
            start_message_id=messages[0].message_id,
            end_message_id=messages[-1].message_id,
            content=content,
            token_count=max(1, len(content) // 4)
        )

    def _default_summarizer(self, messages: List[Message]) -> str:
        # Extractive summarization: key topics and decisions
        topics = []
        for m in messages:
            if m.role == MessageRole.USER:
                # Extract first 30 chars as topic
                topics.append(m.content[:60].strip())
        # Build summary
        user_count = sum(1 for m in messages if m.role == MessageRole.USER)
        assistant_count = sum(1 for m in messages if m.role == MessageRole.ASSISTANT)
        summary = f"Conversation with {user_count} user messages and {assistant_count} assistant responses. Topics: " + "; ".join(topics[:3])
        return summary

    def progressive_summarize(self, thread: ConversationThread) -> Optional[Summary]:
        if not self.should_summarize(thread):
            return None
        # Summarize oldest half of messages
        mid = len(thread._messages) // 2
        to_summarize = thread._messages[:mid]
        if not to_summarize:
            return None
        summary = self.summarize(to_summarize)
        thread._messages = thread._messages[mid:]
        thread.add_summary(summary)
        return summary


class MemoryHierarchy:
    """Multi-tier memory: short-term (active), long-term (summaries), episodic (archived)."""

    def __init__(self, max_short_term: int = 20, max_long_term: int = 50):
        self.max_short_term = max_short_term
        self.max_long_term = max_long_term
        self._short_term: Dict[str, ConversationThread] = {}
        self._long_term: Dict[str, List[Summary]] = {}
        self._episodic: Dict[str, List[Dict[str, Any]]] = {}  # archived threads

    def create_thread(self, title: str = "", budget: Optional[TokenBudget] = None) -> ConversationThread:
        tid = str(uuid.uuid4())[:12]
        thread = ConversationThread(tid, title, budget)
        self._short_term[tid] = thread
        return thread

    def get_thread(self, thread_id: str) -> Optional[ConversationThread]:
        return self._short_term.get(thread_id)

    def archive_thread(self, thread_id: str) -> bool:
        thread = self._short_term.pop(thread_id, None)
        if not thread:
            return False
        # Move to episodic memory
        self._episodic[thread_id] = {
            "title": thread.title,
            "summaries": [{"id": s.summary_id, "content": s.content} for s in thread._summaries],
            "message_count": len(thread._messages),
            "total_tokens": thread.total_tokens(),
            "archived_at": time.time(),
        }
        return True

    def promote_summaries(self, thread_id: str) -> bool:
        thread = self._short_term.get(thread_id)
        if not thread:
            return False
        self._long_term[thread_id] = list(thread._summaries)
        return True

    def search_episodic(self, keyword: str) -> List[Dict[str, Any]]:
        results = []
        for tid, ep in self._episodic.items():
            if keyword.lower() in ep.get("title", "").lower():
                results.append(ep)
                continue
            for s in ep.get("summaries", []):
                if keyword.lower() in s.get("content", "").lower():
                    results.append(ep)
                    break
        return results

    def get_stats(self) -> Dict[str, int]:
        return {
            "short_term_threads": len(self._short_term),
            "long_term_summaries": sum(len(v) for v in self._long_term.values()),
            "episodic_archives": len(self._episodic),
        }


class TokenBudgetManager:
    """Manage token budgets across users / sessions."""

    def __init__(self, default_budget: TokenBudget = None):
        self.default_budget = default_budget or TokenBudget()
        self._user_budgets: Dict[str, TokenBudget] = {}
        self._usage: Dict[str, int] = {}  # user_id -> total tokens used

    def set_user_budget(self, user_id: str, budget: TokenBudget) -> None:
        self._user_budgets[user_id] = budget

    def get_budget(self, user_id: str) -> TokenBudget:
        return self._user_budgets.get(user_id, self.default_budget)

    def record_usage(self, user_id: str, tokens: int) -> None:
        self._usage[user_id] = self._usage.get(user_id, 0) + tokens

    def get_remaining(self, user_id: str) -> int:
        budget = self.get_budget(user_id)
        return budget.max_total - self._usage.get(user_id, 0)

    def is_over_budget(self, user_id: str) -> bool:
        return self.get_remaining(user_id) <= 0


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("CONVERSATION STATE MANAGER DEMO")
    print("=" * 70)

    # 1. Create thread with budget
    print("\n[1] Create Thread")
    thread = ConversationThread("thread-1", "Python Tutorial", TokenBudget(max_total=4096, reserved_for_response=1024))
    print(f"  Thread: {thread.thread_id}, Budget available: {thread.budget.available_for_history} tokens")

    # Add messages
    messages = [
        (MessageRole.USER, "How do I define a function in Python?"),
        (MessageRole.ASSISTANT, "You define a function using the `def` keyword followed by the function name and parentheses."),
        (MessageRole.USER, "Can you show me with parameters?"),
        (MessageRole.ASSISTANT, "Sure! Here's an example: def greet(name): return f'Hello, {name}!'"),
        (MessageRole.USER, "What about default arguments?"),
        (MessageRole.ASSISTANT, "Default arguments are specified in the function definition: def greet(name='World'): ..."),
        (MessageRole.USER, "Can functions return multiple values?"),
        (MessageRole.ASSISTANT, "Yes, Python functions can return multiple values as a tuple: def stats(): return 1, 2, 3"),
    ]
    for role, content in messages:
        thread.add_message(role, content)
    print(f"  Messages added: {len(messages)}")
    print(f"  Total tokens: {thread.total_tokens()}")

    # 2. Context for model
    print("\n[2] Context for Model")
    ctx = thread.get_context_for_model()
    print(f"  Context length: {len(ctx)} messages")
    for m in ctx[:3]:
        print(f"    [{m['role']}] {m['content'][:50]}...")

    # 3. Summarizer
    print("\n[3] Summarization")
    summarizer = Summarizer(trigger_threshold=100, summary_ratio=0.3)
    summary = summarizer.progressive_summarize(thread)
    if summary:
        print(f"  Summary generated: {summary.content[:80]}...")
        print(f"  Summary tokens: {summary.token_count}")
        print(f"  Remaining messages: {len(thread._messages)}")
    else:
        print("  No summarization needed yet")

    # Force summarize by adding more messages
    for i in range(20):
        thread.add_message(MessageRole.USER, f"Question {i}: How does Python handle memory management in detail with examples?" * 2)
    print(f"  After 20 more messages: {thread.total_tokens()} tokens, {len(thread._messages)} messages")
    summary = summarizer.progressive_summarize(thread)
    if summary:
        print(f"  Summary: {summary.content[:80]}... (tokens={summary.token_count})")
        print(f"  Messages after summarize: {len(thread._messages)}")
        print(f"  Summaries in thread: {len(thread._summaries)}")

    # 4. Memory Hierarchy
    print("\n[4] Memory Hierarchy")
    memory = MemoryHierarchy()
    t1 = memory.create_thread("Shopping List")
    t1.add_message(MessageRole.USER, "Buy milk and eggs")
    t1.add_message(MessageRole.ASSISTANT, "Added to your shopping list.")
    t2 = memory.create_thread("Travel Planning")
    t2.add_message(MessageRole.USER, "Plan a trip to Japan")
    t2.add_message(MessageRole.ASSISTANT, "Japan is a great destination! Here are some tips...")
    print(f"  Short-term threads: {len(memory._short_term)}")
    print(f"  Stats: {memory.get_stats()}")

    # Archive
    memory.archive_thread(t1.thread_id)
    print(f"  After archive: {memory.get_stats()}")
    # Search episodic
    results = memory.search_episodic("Japan")
    print(f"  Search 'Japan' in episodic: {len(results)} results")

    # 5. Token Budget Manager
    print("\n[5] Token Budget Manager")
    budget_mgr = TokenBudgetManager(TokenBudget(max_total=10000))
    budget_mgr.set_user_budget("alice", TokenBudget(max_total=5000))
    budget_mgr.record_usage("alice", 2000)
    budget_mgr.record_usage("alice", 1500)
    budget_mgr.record_usage("bob", 3000)
    print(f"  Alice remaining: {budget_mgr.get_remaining('alice')} tokens")
    print(f"  Alice over budget? {budget_mgr.is_over_budget('alice')}")
    print(f"  Bob remaining: {budget_mgr.get_remaining('bob')} tokens")
    print(f"  Bob over budget? {budget_mgr.is_over_budget('bob')}")

    # 6. Prune to budget
    print("\n[6] Prune to Budget")
    thread3 = ConversationThread("t3", "Big Thread", TokenBudget(max_total=200, reserved_for_response=50))
    for i in range(10):
        thread3.add_message(MessageRole.USER, f"Message {i} with some content that takes tokens " * 5)
    print(f"  Before prune: {thread3.total_tokens()} tokens, {len(thread3._messages)} messages")
    removed = thread3.prune_to_budget(keep_recent=3)
    print(f"  After prune: {thread3.total_tokens()} tokens, {len(thread3._messages)} messages, removed {len(removed)}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
