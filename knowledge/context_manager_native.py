#!/usr/bin/env python3
"""
================================================================================
MAGNATRIX-OS — Context Manager (Layer 5 Extension)
Inspired by: agiresearch/AIOS aios/context/
Conversation context lifecycle: creation, truncation, summarization,
compression, and recovery. Handles token budget management across sessions.
================================================================================
Zero-dependency context manager with sliding window and smart truncation.
================================================================================
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple


# =============================================================================
# Constants
# =============================================================================
DEFAULT_MAX_TOKENS = 4096
DEFAULT_CONTEXT_WINDOW = 8192
SUMMARY_TRIGGER_RATIO = 0.75


# =============================================================================
# Data Types
# =============================================================================
class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ContextMessage:
    role: MessageRole
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    token_count: int = 0
    message_id: str = ""

    def __post_init__(self) -> None:
        if not self.message_id:
            self.message_id = hashlib.sha256(f"{self.role.value}:{self.content}:{self.timestamp}".encode()).hexdigest()[:12]
        if self.token_count == 0:
            self.token_count = self._estimate_tokens()

    def _estimate_tokens(self) -> int:
        # Rough estimate: 1 token ≈ 4 chars for English, 1 per word
        words = len(re.findall(r"\b\w+\b", self.content))
        return max(1, int(words * 1.3))


@dataclass
class ContextSummary:
    summary_id: str
    original_range: Tuple[int, int]  # start_idx, end_idx
    content: str
    token_count: int
    created_at: float = field(default_factory=time.time)


@dataclass
class ConversationContext:
    context_id: str
    agent_id: str
    messages: List[ContextMessage] = field(default_factory=list)
    summaries: List[ContextSummary] = field(default_factory=list)
    max_tokens: int = DEFAULT_MAX_TOKENS
    current_tokens: int = 0
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    system_prompt: str = ""


# =============================================================================
# Token Counter
# =============================================================================
class TokenCounter:
    """Estimate token counts for text."""

    @staticmethod
    def count(text: str) -> int:
        # Simple heuristic: English ≈ 4 chars/token, code ≈ 3.5 chars/token
        if not text:
            return 0
        code_chars = sum(1 for c in text if c in "{}[]();:.,=+-*/<>!&|")
        ratio = 3.5 if code_chars > len(text) * 0.1 else 4.0
        return max(1, int(len(text) / ratio))

    @staticmethod
    def count_messages(messages: List[ContextMessage]) -> int:
        return sum(m.token_count for m in messages)


# =============================================================================
# Summarizer
# =============================================================================
class Summarizer:
    """Compress message history into summaries."""

    def __init__(self, max_summary_tokens: int = 200) -> None:
        self.max_summary_tokens = max_summary_tokens

    def summarize(self, messages: List[ContextMessage]) -> str:
        """Create a condensed summary of messages."""
        if not messages:
            return ""
        # Extract key points
        points = []
        for m in messages:
            # First sentence or first 100 chars
            excerpt = m.content[:100].strip()
            if excerpt:
                points.append(f"[{m.role.value}] {excerpt}")
        summary = " | ".join(points[:5])
        return summary[:500]  # Cap length

    def create_summary(self, messages: List[ContextMessage], start_idx: int, end_idx: int) -> ContextSummary:
        slice_msgs = messages[start_idx:end_idx]
        content = self.summarize(slice_msgs)
        return ContextSummary(
            summary_id=hashlib.sha256(f"{start_idx}:{end_idx}:{time.time()}".encode()).hexdigest()[:12],
            original_range=(start_idx, end_idx),
            content=content,
            token_count=TokenCounter.count(content),
        )


# =============================================================================
# Truncation Strategies
# =============================================================================
class TruncationStrategy:
    @staticmethod
    def sliding_window(messages: List[ContextMessage], max_tokens: int, keep_last: int = 4) -> List[ContextMessage]:
        """Keep last N messages, summarize older ones."""
        if not messages:
            return []
        total = TokenCounter.count_messages(messages)
        if total <= max_tokens:
            return messages
        # Keep system + last N
        system_msgs = [m for m in messages if m.role == MessageRole.SYSTEM]
        non_system = [m for m in messages if m.role != MessageRole.SYSTEM]
        keep = non_system[-keep_last:] if len(non_system) > keep_last else non_system
        result = system_msgs + keep
        # If still over budget, truncate keep
        while TokenCounter.count_messages(result) > max_tokens and len(keep) > 1:
            keep.pop(0)
            result = system_msgs + keep
        return result

    @staticmethod
    def oldest_first(messages: List[ContextMessage], max_tokens: int) -> List[ContextMessage]:
        """Remove oldest non-system messages until under budget."""
        if not messages:
            return []
        result = list(messages)
        while TokenCounter.count_messages(result) > max_tokens and len(result) > 1:
            # Find oldest non-system
            for i, m in enumerate(result):
                if m.role != MessageRole.SYSTEM:
                    result.pop(i)
                    break
            else:
                break
        return result

    @staticmethod
    def priority_based(messages: List[ContextMessage], max_tokens: int) -> List[ContextMessage]:
        """Keep high-priority messages, drop low-priority."""
        if not messages:
            return []
        # Score each message
        scored = []
        for i, m in enumerate(messages):
            score = 0
            if m.role == MessageRole.SYSTEM:
                score = 1000
            elif m.role == MessageRole.USER:
                score = 100 - i
            elif m.role == MessageRole.ASSISTANT:
                score = 50 - i
            elif m.role == MessageRole.TOOL:
                score = 10 - i
            scored.append((score, m))
        scored.sort(key=lambda x: x[0], reverse=True)
        result = []
        total = 0
        for _, m in scored:
            if total + m.token_count <= max_tokens:
                result.append(m)
                total += m.token_count
        # Re-sort by timestamp
        result.sort(key=lambda m: m.timestamp)
        return result


# =============================================================================
# Context Manager
# =============================================================================
class ContextManager:
    """Manage conversation contexts with budget-aware lifecycle."""

    def __init__(self, default_max_tokens: int = DEFAULT_MAX_TOKENS) -> None:
        self.default_max_tokens = default_max_tokens
        self._contexts: Dict[str, ConversationContext] = {}
        self._lock = threading.Lock()
        self._summarizer = Summarizer()
        self._callbacks: Dict[str, List[Callable[[ConversationContext], None]]] = {
            "created": [],
            "truncated": [],
            "summarized": [],
            "closed": [],
        }

    def on(self, event: str, callback: Callable[[ConversationContext], None]) -> None:
        self._callbacks.setdefault(event, []).append(callback)

    def _emit(self, event: str, ctx: ConversationContext) -> None:
        for cb in self._callbacks.get(event, []):
            cb(ctx)

    def create(self, agent_id: str, system_prompt: str = "", max_tokens: Optional[int] = None, metadata: Optional[Dict[str, Any]] = None) -> ConversationContext:
        ctx_id = hashlib.sha256(f"{agent_id}:{time.time()}".encode()).hexdigest()[:16]
        ctx = ConversationContext(
            context_id=ctx_id,
            agent_id=agent_id,
            max_tokens=max_tokens or self.default_max_tokens,
            system_prompt=system_prompt,
            metadata=metadata or {},
        )
        if system_prompt:
            ctx.messages.append(ContextMessage(role=MessageRole.SYSTEM, content=system_prompt))
            ctx.current_tokens = ctx.messages[0].token_count
        with self._lock:
            self._contexts[ctx_id] = ctx
        self._emit("created", ctx)
        return ctx

    def add_message(self, context_id: str, role: MessageRole, content: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[ContextMessage]:
        ctx = self._contexts.get(context_id)
        if not ctx:
            return None
        msg = ContextMessage(role=role, content=content, metadata=metadata or {})
        ctx.messages.append(msg)
        ctx.current_tokens += msg.token_count
        ctx.last_accessed = time.time()
        # Check if we need truncation
        if ctx.current_tokens > ctx.max_tokens * SUMMARY_TRIGGER_RATIO:
            self._compact(ctx)
        return msg

    def _compact(self, ctx: ConversationContext) -> None:
        """Compact context by summarizing old messages."""
        if len(ctx.messages) <= 3:
            return
        # Find oldest messages to summarize
        non_system = [i for i, m in enumerate(ctx.messages) if m.role != MessageRole.SYSTEM]
        if len(non_system) < 4:
            return
        to_summarize = non_system[:-3]  # Keep last 3
        if len(to_summarize) < 2:
            return
        start_idx = to_summarize[0]
        end_idx = to_summarize[-1] + 1
        summary = self._summarizer.create_summary(ctx.messages, start_idx, end_idx)
        # Replace summarized range with summary message
        new_msg = ContextMessage(role=MessageRole.SYSTEM, content=f"[Previous context summary: {summary.content}]")
        ctx.messages = ctx.messages[:start_idx] + [new_msg] + ctx.messages[end_idx:]
        ctx.summaries.append(summary)
        ctx.current_tokens = TokenCounter.count_messages(ctx.messages)
        self._emit("summarized", ctx)

    def truncate(self, context_id: str, strategy: str = "sliding_window") -> bool:
        ctx = self._contexts.get(context_id)
        if not ctx:
            return False
        if strategy == "sliding_window":
            ctx.messages = TruncationStrategy.sliding_window(ctx.messages, ctx.max_tokens)
        elif strategy == "oldest_first":
            ctx.messages = TruncationStrategy.oldest_first(ctx.messages, ctx.max_tokens)
        elif strategy == "priority_based":
            ctx.messages = TruncationStrategy.priority_based(ctx.messages, ctx.max_tokens)
        ctx.current_tokens = TokenCounter.count_messages(ctx.messages)
        self._emit("truncated", ctx)
        return True

    def get_messages(self, context_id: str, limit: Optional[int] = None) -> List[ContextMessage]:
        ctx = self._contexts.get(context_id)
        if not ctx:
            return []
        msgs = ctx.messages
        if limit:
            msgs = msgs[-limit:]
        return msgs

    def get_context(self, context_id: str) -> Optional[ConversationContext]:
        return self._contexts.get(context_id)

    def list_contexts(self, agent_id: Optional[str] = None) -> List[ConversationContext]:
        result = list(self._contexts.values())
        if agent_id:
            result = [c for c in result if c.agent_id == agent_id]
        return sorted(result, key=lambda c: c.last_accessed, reverse=True)

    def close(self, context_id: str) -> bool:
        ctx = self._contexts.pop(context_id, None)
        if ctx:
            self._emit("closed", ctx)
            return True
        return False

    def fork(self, context_id: str, new_agent_id: str) -> Optional[ConversationContext]:
        """Create a new context branching from existing one."""
        ctx = self._contexts.get(context_id)
        if not ctx:
            return None
        new_ctx = ConversationContext(
            context_id=hashlib.sha256(f"fork:{context_id}:{time.time()}".encode()).hexdigest()[:16],
            agent_id=new_agent_id,
            messages=list(ctx.messages),
            summaries=list(ctx.summaries),
            max_tokens=ctx.max_tokens,
            current_tokens=ctx.current_tokens,
            system_prompt=ctx.system_prompt,
            metadata={"forked_from": context_id, **ctx.metadata},
        )
        with self._lock:
            self._contexts[new_ctx.context_id] = new_ctx
        self._emit("created", new_ctx)
        return new_ctx

    def export(self, context_id: str) -> Optional[Dict[str, Any]]:
        ctx = self._contexts.get(context_id)
        if not ctx:
            return None
        return {
            "context_id": ctx.context_id,
            "agent_id": ctx.agent_id,
            "message_count": len(ctx.messages),
            "token_count": ctx.current_tokens,
            "max_tokens": ctx.max_tokens,
            "summary_count": len(ctx.summaries),
            "created_at": ctx.created_at,
            "last_accessed": ctx.last_accessed,
            "system_prompt": ctx.system_prompt,
        }

    def prune_inactive(self, max_age_sec: float = 3600.0) -> int:
        """Close contexts that haven't been accessed recently."""
        now = time.time()
        to_remove = [cid for cid, ctx in self._contexts.items() if now - ctx.last_accessed > max_age_sec]
        for cid in to_remove:
            self.close(cid)
        return len(to_remove)


# =============================================================================
# Context Kernel Bridge
# =============================================================================
class ContextKernelBridge:
    def __init__(self, manager: ContextManager, event_bus: Any = None) -> None:
        self.manager = manager
        self.bus = event_bus
        manager.on("created", self._on_created)
        manager.on("summarized", self._on_summarized)
        manager.on("closed", self._on_closed)

    def _on_created(self, ctx: ConversationContext) -> None:
        if self.bus:
            self.bus.publish("context.created", {"context_id": ctx.context_id, "agent_id": ctx.agent_id})

    def _on_summarized(self, ctx: ConversationContext) -> None:
        if self.bus:
            self.bus.publish("context.summarized", {
                "context_id": ctx.context_id,
                "token_count": ctx.current_tokens,
                "summary_count": len(ctx.summaries),
            })

    def _on_closed(self, ctx: ConversationContext) -> None:
        if self.bus:
            self.bus.publish("context.closed", {"context_id": ctx.context_id, "agent_id": ctx.agent_id})


# =============================================================================
# Demo
# =============================================================================
def run_demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Context Manager Demo")
    print("=" * 60)
    mgr = ContextManager(default_max_tokens=500)
    ctx = mgr.create("agent-1", system_prompt="You are a helpful coding assistant.", max_tokens=300)
    print(f"Created context: {ctx.context_id} ({ctx.current_tokens} tokens)")

    # Add messages
    for i in range(10):
        mgr.add_message(ctx.context_id, MessageRole.USER, f"Explain concept {i} in detail with examples and edge cases.")
        mgr.add_message(ctx.context_id, MessageRole.ASSISTANT, f"Here is a detailed explanation of concept {i}: " + "x " * 50)

    print(f"After 20 messages: {ctx.current_tokens} tokens, {len(ctx.messages)} messages")
    print(f"Summaries created: {len(ctx.summaries)}")

    # Test truncation
    mgr.truncate(ctx.context_id, "sliding_window")
    print(f"After sliding_window: {ctx.current_tokens} tokens, {len(ctx.messages)} messages")

    # Fork
    forked = mgr.fork(ctx.context_id, "agent-2")
    if forked:
        print(f"Forked context: {forked.context_id} ({len(forked.messages)} messages)")

    # Export
    print(f"Export: {mgr.export(ctx.context_id)}")

    # Prune
    mgr.prune_inactive(max_age_sec=0.1)
    print(f"Contexts after prune: {len(mgr.list_contexts())}")
    print("Demo complete.")


if __name__ == "__main__":
    run_demo()
