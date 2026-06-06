#!/usr/bin/env python3
"""
Agent Attribution for MAGNATRIX-OS
Multi-agent response tagging, attribution, and formatting.
Prefixes responses with agent identifiers, manages reply chains,
and tracks attribution history. Native stdlib only.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import time
from typing import Any, Dict, List, Optional


@dataclasses.dataclass
class AttributionTag:
    agent_id: str
    agent_name: str
    color: str  # hex color code
    icon: str


@dataclasses.dataclass
class AttributedResponse:
    agent_id: str
    agent_name: str
    content: str
    timestamp: float
    tag_prefix: str
    raw_content: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "content": self.content,
            "tag": self.tag_prefix,
            "timestamp": self.timestamp,
        }


class AgentAttribution:
    """Tags responses with agent identifiers and manages attribution display."""

    COLORS = {
        "agent1": "#6366f1",
        "agent2": "#a855f7",
        "agent3": "#06b6d4",
        "agent4": "#10b981",
        "agent5": "#f59e0b",
        "default": "#94a3b8",
    }

    ICONS = {
        "agent1": "A",
        "agent2": "B",
        "agent3": "C",
        "agent4": "D",
        "agent5": "E",
        "default": "?",
    }

    def __init__(self, tag_format: str = "[{name}] {content}") -> None:
        self.tag_format = tag_format
        self._tags: Dict[str, AttributionTag] = {}
        self._history: List[AttributedResponse] = []
        self._reply_chains: Dict[str, List[str]] = {}  # thread_id -> ordered agent_ids

    def register(self, agent_id: str, agent_name: str, color: Optional[str] = None, icon: Optional[str] = None) -> None:
        self._tags[agent_id] = AttributionTag(
            agent_id=agent_id,
            agent_name=agent_name,
            color=color or self.COLORS.get(agent_id, self.COLORS["default"]),
            icon=icon or self.ICONS.get(agent_id, self.ICONS["default"]),
        )

    def tag(self, agent_id: str, content: str) -> str:
        """Prefix content with agent tag."""
        tag = self._tags.get(agent_id)
        if not tag:
            return f"[?] {content}"
        prefix = self.tag_format.format(name=tag.agent_name, icon=tag.icon, id=agent_id)
        return prefix.replace("{content}", content)

    def add_response(self, agent_id: str, content: str, thread_id: str = "default") -> AttributedResponse:
        """Record an attributed response."""
        tag = self._tags.get(agent_id)
        tagged = self.tag(agent_id, content) if tag else content
        resp = AttributedResponse(
            agent_id=agent_id,
            agent_name=tag.agent_name if tag else agent_id,
            content=tagged,
            timestamp=time.time(),
            tag_prefix=f"[{tag.agent_name}]" if tag else "[?]",
            raw_content=content,
        )
        self._history.append(resp)
        # Track reply chain
        chain = self._reply_chains.setdefault(thread_id, [])
        if not chain or chain[-1] != agent_id:
            chain.append(agent_id)
        return resp

    def format_thread(self, thread_id: str = "default") -> str:
        """Format all responses in a thread with attribution."""
        chain = self._reply_chains.get(thread_id, [])
        if not chain:
            return ""
        parts = []
        for agent_id in chain:
            responses = [r for r in self._history if r.agent_id == agent_id]
            if responses:
                parts.append(responses[-1].content)
        return "\n\n".join(parts)

    def format_collaborative(self, responses: Dict[str, str]) -> str:
        """Format multiple agent responses into a collaborative reply."""
        parts = []
        for agent_id, content in responses.items():
            tag = self._tags.get(agent_id)
            if tag:
                parts.append(f"[{tag.agent_name}] {content}")
            else:
                parts.append(f"[{agent_id}] {content}")
        return "\n---\n".join(parts)

    def format_summary(self, responses: Dict[str, str]) -> str:
        """Format a summary of multiple responses."""
        parts = []
        for agent_id, content in responses.items():
            tag = self._tags.get(agent_id)
            name = tag.agent_name if tag else agent_id
            # Summarize: first sentence only
            summary = content.split(".")[0] + "." if "." in content else content[:100] + "..."
            parts.append(f"{name}: {summary}")
        return "\n".join(parts)

    def get_history(self, agent_id: Optional[str] = None, limit: int = 100) -> List[AttributedResponse]:
        if agent_id:
            return [r for r in self._history if r.agent_id == agent_id][-limit:]
        return self._history[-limit:]

    def get_reply_chain(self, thread_id: str = "default") -> List[str]:
        return self._reply_chains.get(thread_id, [])

    def stats(self) -> Dict[str, Any]:
        by_agent = {}
        for r in self._history:
            by_agent[r.agent_id] = by_agent.get(r.agent_id, 0) + 1
        return {
            "total_responses": len(self._history),
            "threads": len(self._reply_chains),
            "agents": len(self._tags),
            "by_agent": by_agent,
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    attr = AgentAttribution()
    print("=== Agent Attribution Demo ===\n")
    # Register agents
    attr.register("agent1", "Hermes", "#6366f1", "H")
    attr.register("agent2", "OpenClaw", "#a855f7", "C")
    attr.register("agent3", "OpenCode", "#06b6d4", "O")
    # Add responses
    r1 = attr.add_response("agent1", "Hello! I can help with general questions.", "thread1")
    r2 = attr.add_response("agent2", "I specialize in code analysis.", "thread1")
    r3 = attr.add_response("agent3", "I can write creative code with vibes.", "thread1")
    print("Tagged responses:")
    print(f"  {r1.content}")
    print(f"  {r2.content}")
    print(f"  {r3.content}")
    # Collaborative format
    print(f"\nCollaborative format:")
    collab = attr.format_collaborative({
        "agent1": "Use Python for this task.",
        "agent2": "Add type hints for better code.",
        "agent3": "Make it async with vibes!",
    })
    print(collab)
    # Summary
    print(f"\nSummary:")
    summary = attr.format_summary({
        "agent1": "Python is the best choice here. Use functions and classes.",
        "agent2": "Add proper error handling and type hints.",
    })
    print(summary)
    # Stats
    print(f"\nStats: {attr.stats()}")


if __name__ == "__main__":
    _demo()
