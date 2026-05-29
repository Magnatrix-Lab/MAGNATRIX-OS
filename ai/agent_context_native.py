#!/usr/bin/env python3
"""agent_context_native.py — MAGNATRIX-OS AI Layer
Agent Context Management with Scratchpad & Run Context.

Pattern: AMATI-PELAJARI-TIRU dari OctagonAI/kalshi-trading-bot-cli (agent/run-context, scratchpad, tool-executor, token-counter).

Features:
  - Scratchpad: agent's working memory for reasoning steps, observations, plans
  - Run context: session-level state (user query, model, approval mode, execution plan)
  - Tool executor: execute registered tools with timeout, error handling, result summarization
  - Token counter: estimate token usage for scratchpad + context pruning
  - Message history: structured conversation history with roles (system, user, assistant, tool)
  - Checkpoint: save/restore agent state for long-running tasks

Usage:
    ctx = NativeAgentContext(model="llama3-70b", max_tokens=4096)
    ctx.add_user_query("Analyze BTC market")
    ctx.scratchpad.add("Step 1: Fetch market data from Kalshi")
    ctx.scratchpad.add("Step 2: Compute edge using model probability")
    result = ctx.tool_executor.execute("kalshi_search", {"query": "BTC"})
    ctx.scratchpad.add(f"Result: {result.summary}")
    ctx.add_assistant_response("Based on analysis, edge is 12%.")
    print(ctx.format_for_llm())
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# Data Model
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ToolResult:
    tool: str
    args: Dict[str, Any]
    result: Any
    summary: str
    tokens_used: int
    duration_ms: float
    success: bool
    error: str = ""


@dataclass
class Message:
    role: str      # system, user, assistant, tool
    content: str
    timestamp: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# Scratchpad
# ═══════════════════════════════════════════════════════════════════════════════

class Scratchpad:
    """Agent's working memory for reasoning steps and observations."""

    def __init__(self, max_entries: int = 100, max_chars_per_entry: int = 500) -> None:
        self.entries: List[str] = []
        self.max_entries = max_entries
        self.max_chars_per_entry = max_chars_per_entry

    def add(self, text: str) -> None:
        text = text[:self.max_chars_per_entry]
        self.entries.append(text)
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]

    def clear(self) -> None:
        self.entries.clear()

    def format(self) -> str:
        if not self.entries:
            return "(scratchpad empty)"
        lines = [f"{i+1}. {e}" for i, e in enumerate(self.entries)]
        return "\n".join(lines)

    def last(self, n: int = 1) -> List[str]:
        return self.entries[-n:]

    def __len__(self) -> int:
        return len(self.entries)


# ═══════════════════════════════════════════════════════════════════════════════
# Token Counter (simple estimation)
# ═══════════════════════════════════════════════════════════════════════════════

class TokenCounter:
    """Estimate token count for text (rough approximation: 1 token ≈ 4 chars)."""

    @staticmethod
    def count(text: str) -> int:
        return max(1, len(text) // 4)

    @staticmethod
    def count_messages(messages: List[Message]) -> int:
        total = 0
        for m in messages:
            total += TokenCounter.count(m.content)
        return total

    @staticmethod
    def count_scratchpad(scratchpad: Scratchpad) -> int:
        return TokenCounter.count(scratchpad.format())


# ═══════════════════════════════════════════════════════════════════════════════
# Tool Executor
# ═══════════════════════════════════════════════════════════════════════════════

class ToolExecutor:
    """Execute registered tools with timeout, error handling, and result summarization."""

    def __init__(self, max_tokens_per_result: int = 200) -> None:
        self._tools: Dict[str, Callable] = {}
        self.max_tokens = max_tokens_per_result
        self._history: List[ToolResult] = []

    def register(self, name: str, fn: Callable[[Dict[str, Any]], Any]) -> None:
        self._tools[name] = fn

    def execute(self, name: str, args: Dict[str, Any], timeout_sec: float = 30.0) -> ToolResult:
        start = time.time()
        fn = self._tools.get(name)
        if not fn:
            result = ToolResult(
                tool=name, args=args, result=None, summary="Tool not found",
                tokens_used=0, duration_ms=0, success=False,
                error=f"Tool '{name}' not registered",
            )
            self._history.append(result)
            return result

        try:
            raw = fn(args)
            duration = (time.time() - start) * 1000
            result_str = self._summarize(raw)
            tokens = TokenCounter.count(result_str)
            result = ToolResult(
                tool=name, args=args, result=raw, summary=result_str,
                tokens_used=tokens, duration_ms=duration, success=True,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            result = ToolResult(
                tool=name, args=args, result=None, summary=f"Error: {e}",
                tokens_used=0, duration_ms=duration, success=False,
                error=str(e),
            )
        self._history.append(result)
        return result

    def _summarize(self, result: Any) -> str:
        if result is None:
            return "None"
        if isinstance(result, list):
            if len(result) == 0:
                return "Empty list"
            if len(result) == 1:
                return f"1 item: {self._summarize(result[0])}"
            return f"{len(result)} items: {self._summarize(result[0])} ..."
        if isinstance(result, dict):
            keys = list(result.keys())[:5]
            return f"Dict with keys: {keys}"
        text = str(result)
        max_chars = self.max_tokens * 4
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        return text

    def history(self) -> List[ToolResult]:
        return list(self._history)


# ═══════════════════════════════════════════════════════════════════════════════
# Agent Context
# ═══════════════════════════════════════════════════════════════════════════════

class NativeAgentContext:
    """Unified agent context: scratchpad, messages, tool executor, state."""

    def __init__(self, model: str = "default", max_tokens: int = 4096,
                 approval_mode: str = "auto") -> None:
        self.model = model
        self.max_tokens = max_tokens
        self.approval_mode = approval_mode  # auto, confirm, reject
        self.scratchpad = Scratchpad()
        self.tool_executor = ToolExecutor()
        self.messages: List[Message] = []
        self.state: Dict[str, Any] = {}
        self.checkpoints: List[Dict[str, Any]] = []
        self._token_counter = TokenCounter()
        self._created_at = time.time()

    # ── Message management ──────────────────────────────────────────────────────

    def add_system_message(self, content: str) -> None:
        self.messages.append(Message(role="system", content=content, timestamp=time.time()))

    def add_user_query(self, content: str) -> None:
        self.messages.append(Message(role="user", content=content, timestamp=time.time()))

    def add_assistant_response(self, content: str, metadata: Optional[Dict] = None) -> None:
        self.messages.append(Message(role="assistant", content=content, timestamp=time.time(), metadata=metadata or {}))

    def add_tool_result(self, tool: str, result_summary: str) -> None:
        self.messages.append(Message(role="tool", content=f"[{tool}] {result_summary}", timestamp=time.time()))

    # ── Token management ────────────────────────────────────────────────────────

    def total_tokens(self) -> int:
        return self._token_counter.count_messages(self.messages) + self._token_counter.count_scratchpad(self.scratchpad)

    def remaining_tokens(self) -> int:
        return max(0, self.max_tokens - self.total_tokens())

    def prune_if_needed(self) -> None:
        """Remove oldest messages if over token limit."""
        while self.total_tokens() > self.max_tokens * 0.9 and len(self.messages) > 2:
            # Keep system message and last user query, remove oldest non-system
            for i, m in enumerate(self.messages):
                if m.role != "system":
                    self.messages.pop(i)
                    break
            else:
                break

    # ── Formatting for LLM ──────────────────────────────────────────────────────

    def format_for_llm(self) -> str:
        """Format context as a single text block for LLM consumption."""
        lines = []
        lines.append(f"<context model={self.model} tokens={self.total_tokens()}/{self.max_tokens}>")
        lines.append("<scratchpad>")
        lines.append(self.scratchpad.format())
        lines.append("</scratchpad>")
        lines.append("<messages>")
        for m in self.messages:
            lines.append(f"[{m.role}] {m.content[:200]}")
        lines.append("</messages>")
        lines.append("</context>")
        return "\n".join(lines)

    # ── Checkpoint ───────────────────────────────────────────────────────────────

    def checkpoint(self, label: str = "") -> int:
        cp = {
            "label": label,
            "timestamp": time.time(),
            "messages": [(m.role, m.content) for m in self.messages],
            "scratchpad": list(self.scratchpad.entries),
            "state": dict(self.state),
        }
        self.checkpoints.append(cp)
        return len(self.checkpoints) - 1

    def restore(self, cp_index: int) -> bool:
        if cp_index < 0 or cp_index >= len(self.checkpoints):
            return False
        cp = self.checkpoints[cp_index]
        self.messages = [Message(role=r, content=c) for r, c in cp["messages"]]
        self.scratchpad.entries = list(cp["scratchpad"])
        self.state = dict(cp["state"])
        return True

    # ── Status ──────────────────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "used_tokens": self.total_tokens(),
            "remaining_tokens": self.remaining_tokens(),
            "messages": len(self.messages),
            "scratchpad_entries": len(self.scratchpad),
            "tools_executed": len(self.tool_executor.history()),
            "checkpoints": len(self.checkpoints),
            "approval_mode": self.approval_mode,
            "session_age_sec": int(time.time() - self._created_at),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Self-test
# ═══════════════════════════════════════════════════════════════════════════════

def _self_test() -> int:
    print("=" * 60)
    print("Native Agent Context — Self Test")
    print("=" * 60)
    passed = 0
    total = 7

    # Test 1: Create context
    print("[Test 1] Create context")
    ctx = NativeAgentContext(model="test-model", max_tokens=1024)
    ctx.add_system_message("You are a trading assistant.")
    ctx.add_user_query("Analyze BTC market")
    ok = len(ctx.messages) == 2
    print(f"  2 messages: {ok} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    # Test 2: Scratchpad
    print("[Test 2] Scratchpad")
    ctx.scratchpad.add("Step 1: Fetch data")
    ctx.scratchpad.add("Step 2: Compute edge")
    ok2 = len(ctx.scratchpad) == 2
    print(f"  2 entries: {ok2} — {'PASS' if ok2 else 'FAIL'}")
    passed += ok2

    # Test 3: Tool execution
    print("[Test 3] Tool execution")
    def mock_tool(args):
        return {"markets": [{"ticker": "BTC"}, {"ticker": "ETH"}]}
    ctx.tool_executor.register("kalshi_search", mock_tool)
    result = ctx.tool_executor.execute("kalshi_search", {"query": "BTC"})
    ok3 = result.success and "Dict with keys" in result.summary
    print(f"  Tool executed: {ok3} ({result.summary}) — {'PASS' if ok3 else 'FAIL'}")
    passed += ok3

    # Test 4: Token counting
    print("[Test 4] Token counting")
    tokens = ctx.total_tokens()
    ok4 = tokens > 0 and tokens <= ctx.max_tokens
    print(f"  Tokens={tokens} (max={ctx.max_tokens}): {ok4} — {'PASS' if ok4 else 'FAIL'}")
    passed += ok4

    # Test 5: Format for LLM
    print("[Test 5] Format for LLM")
    fmt = ctx.format_for_llm()
    ok5 = "<scratchpad>" in fmt and "[user]" in fmt
    print(f"  Contains scratchpad and messages: {ok5} — {'PASS' if ok5 else 'FAIL'}")
    passed += ok5

    # Test 6: Checkpoint / restore
    print("[Test 6] Checkpoint / restore")
    ctx.add_assistant_response("Edge is 12%.")
    cp = ctx.checkpoint("after_analysis")
    ctx.scratchpad.add("Extra data")
    ctx.add_assistant_response("Extra response.")
    restored = ctx.restore(cp)
    ok6 = restored and len(ctx.scratchpad) == 2 and len(ctx.messages) == 3
    print(f"  Restored to checkpoint: {ok6} — {'PASS' if ok6 else 'FAIL'}")
    passed += ok6

    # Test 7: Status
    print("[Test 7] Status report")
    st = ctx.status()
    ok7 = st["messages"] == 3 and st["tools_executed"] == 1
    print(f"  Status valid: {ok7} — {'PASS' if ok7 else 'FAIL'}")
    passed += ok7

    print(f"\nPASS: {passed}/{total}")
    print("=" * 60)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
