#!/usr/bin/env python3
"""
Multi-Agent Router for MAGNATRIX-OS
Routes user requests to different AI agents based on command prefixes,
round-robin, or intent classification. Supports /agent switching,
/broadcast mode, and weighted routing.
Native stdlib only — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import json
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class RouteMode(enum.Enum):
    SINGLE = "single"       # Route to one agent
    BROADCAST = "broadcast" # Route to all agents
    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"
    INTENT = "intent"       # Classify intent then route


@dataclasses.dataclass
class AgentEndpoint:
    """A registered AI agent endpoint."""
    agent_id: str
    name: str
    description: str
    handler: Callable[[str, Dict[str, Any]], str]
    weight: float = 1.0
    active: bool = True
    priority: int = 0  # Lower = higher priority
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)
    request_count: int = 0
    error_count: int = 0
    avg_latency_ms: float = 0.0


@dataclasses.dataclass
class RouteResult:
    """Result of a routing decision."""
    query: str
    mode: RouteMode
    targets: List[str]
    responses: Dict[str, str]
    latency_ms: float
    routed_by: str  # "command", "intent", "round_robin", "default"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "mode": self.mode.value,
            "targets": self.targets,
            "responses": self.responses,
            "latency_ms": self.latency_ms,
            "routed_by": self.routed_by,
        }


class MultiAgentRouter:
    """Routes messages to multiple AI agents with command switching."""

    # Command prefixes that trigger routing
    COMMAND_MAP: Dict[str, str] = {
        "/agent1": "agent1",
        "/agent2": "agent2",
        "/agent3": "agent3",
        "/all": "__all__",
        "/broadcast": "__all__",
        "/both": "__all__",
        "/three": "__all__",
    }

    def __init__(self, default_agent: str = "default") -> None:
        self._agents: Dict[str, AgentEndpoint] = {}
        self._default_agent = default_agent
        self._current_route: Dict[str, str] = {}  # session_id -> agent_id
        self._round_robin_index = 0
        self._mode: RouteMode = RouteMode.SINGLE
        self._command_map: Dict[str, str] = dict(self.COMMAND_MAP)
        self._history: List[RouteResult] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, agent: AgentEndpoint) -> None:
        self._agents[agent.agent_id] = agent

    def unregister(self, agent_id: str) -> bool:
        return self._agents.pop(agent_id, None) is not None

    def set_default(self, agent_id: str) -> None:
        self._default_agent = agent_id

    def set_mode(self, mode: RouteMode) -> None:
        self._mode = mode

    def add_command(self, command: str, agent_id: str) -> None:
        self._command_map[command] = agent_id

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def _detect_command(self, query: str) -> Tuple[Optional[str], str]:
        """Detect routing command in query. Returns (agent_id, stripped_query)."""
        parts = query.strip().split(None, 1)
        if not parts:
            return None, query
        cmd = parts[0].lower()
        if cmd in self._command_map:
            agent_id = self._command_map[cmd]
            rest = parts[1] if len(parts) > 1 else ""
            return agent_id, rest
        return None, query

    def _classify_intent(self, query: str) -> str:
        """Simple keyword-based intent classification."""
        lower = query.lower()
        # Map keywords to agent capabilities
        for agent_id, agent in self._agents.items():
            caps = agent.metadata.get("capabilities", [])
            for cap in caps:
                if cap.lower() in lower:
                    return agent_id
        return self._default_agent

    def _round_robin_target(self) -> str:
        active = [a.agent_id for a in self._agents.values() if a.active]
        if not active:
            return self._default_agent
        idx = self._round_robin_index % len(active)
        self._round_robin_index += 1
        return active[idx]

    def _weighted_target(self) -> str:
        active = [(a.agent_id, a.weight) for a in self._agents.values() if a.active]
        if not active:
            return self._default_agent
        total = sum(w for _, w in active)
        import random
        r = random.random() * total
        cum = 0.0
        for aid, w in active:
            cum += w
            if r <= cum:
                return aid
        return active[-1][0]

    def route(self, query: str, session_id: str = "default", context: Optional[Dict[str, Any]] = None) -> RouteResult:
        start = time.perf_counter()
        ctx = context or {}

        # Check for command override
        cmd_target, stripped_query = self._detect_command(query)

        if cmd_target == "__all__":
            targets = [a.agent_id for a in self._agents.values() if a.active]
            mode = RouteMode.BROADCAST
            routed_by = "command"
            query_to_send = stripped_query
        elif cmd_target:
            targets = [cmd_target] if cmd_target in self._agents and self._agents[cmd_target].active else [self._default_agent]
            mode = RouteMode.SINGLE
            routed_by = "command"
            query_to_send = stripped_query
            # Update session route
            self._current_route[session_id] = cmd_target
        else:
            query_to_send = query
            # Determine target based on mode
            if self._mode == RouteMode.BROADCAST:
                targets = [a.agent_id for a in self._agents.values() if a.active]
                routed_by = "mode"
            elif self._mode == RouteMode.ROUND_ROBIN:
                target = self._round_robin_target()
                targets = [target]
                routed_by = "round_robin"
            elif self._mode == RouteMode.WEIGHTED:
                target = self._weighted_target()
                targets = [target]
                routed_by = "weighted"
            elif self._mode == RouteMode.INTENT:
                target = self._classify_intent(query)
                targets = [target]
                routed_by = "intent"
            else:
                # Single mode: use session route or default
                target = self._current_route.get(session_id, self._default_agent)
                if target not in self._agents or not self._agents[target].active:
                    target = self._default_agent
                targets = [target]
                routed_by = "default"

        # Execute
        responses: Dict[str, str] = {}
        for aid in targets:
            agent = self._agents.get(aid)
            if not agent or not agent.active:
                continue
            a_start = time.perf_counter()
            try:
                resp = agent.handler(query_to_send, ctx)
                responses[aid] = resp
                agent.request_count += 1
                agent.avg_latency_ms = (agent.avg_latency_ms * (agent.request_count - 1) + (time.perf_counter() - a_start) * 1000) / agent.request_count
            except Exception as e:
                agent.error_count += 1
                responses[aid] = f"[ERROR: {e}]"

        latency = (time.perf_counter() - start) * 1000
        result = RouteResult(
            query=query_to_send,
            mode=mode,
            targets=targets,
            responses=responses,
            latency_ms=latency,
            routed_by=routed_by,
        )
        self._history.append(result)
        return result

    def get_current_route(self, session_id: str = "default") -> str:
        return self._current_route.get(session_id, self._default_agent)

    def set_session_route(self, session_id: str, agent_id: str) -> None:
        self._current_route[session_id] = agent_id

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def list_agents(self) -> List[AgentEndpoint]:
        return list(self._agents.values())

    def get_agent(self, agent_id: str) -> Optional[AgentEndpoint]:
        return self._agents.get(agent_id)

    def get_history(self, limit: int = 100) -> List[RouteResult]:
        return self._history[-limit:]

    def stats(self) -> Dict[str, Any]:
        by_agent = {}
        for a in self._agents.values():
            by_agent[a.agent_id] = {
                "requests": a.request_count,
                "errors": a.error_count,
                "avg_latency_ms": a.avg_latency_ms,
                "active": a.active,
            }
        return {
            "agents": len(self._agents),
            "mode": self._mode.value,
            "default": self._default_agent,
            "total_routes": len(self._history),
            "by_agent": by_agent,
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    router = MultiAgentRouter(default_agent="default")

    # Register mock agents
    def handler_a(q, ctx):
        return f"[Agent-A] I received: {q}"
    def handler_b(q, ctx):
        return f"[Agent-B] Processing: {q}"
    def handler_c(q, ctx):
        return f"[Agent-C] Analyzing: {q}"

    router.register(AgentEndpoint("agent1", "Hermes", "General purpose", handler_a, weight=2.0, metadata={"capabilities": ["general", "chat"]}))
    router.register(AgentEndpoint("agent2", "OpenClaw", "Code specialist", handler_b, weight=1.0, metadata={"capabilities": ["code", "programming"]}))
    router.register(AgentEndpoint("agent3", "OpenCode", "Vibe coder", handler_c, weight=1.5, metadata={"capabilities": ["vibe", "creative"]}))

    print("=== Multi-Agent Router Demo ===\n")
    # Command routing
    print("Command routing:")
    r = router.route("/agent2 Write a Python function", "session1")
    print(f"  {r.query} -> {r.targets} ({r.routed_by})")
    for aid, resp in r.responses.items():
        print(f"    {aid}: {resp}")
    # Broadcast
    print(f"\nBroadcast mode:")
    r = router.route("/all Hello everyone", "session1")
    print(f"  {r.query} -> {r.targets} ({r.mode.value})")
    for aid, resp in r.responses.items():
        print(f"    {aid}: {resp}")
    # Intent-based
    print(f"\nIntent-based routing:")
    router.set_mode(RouteMode.INTENT)
    r = router.route("How to write a Python function?", "session2")
    print(f"  {r.query} -> {r.targets} ({r.routed_by})")
    # Stats
    print(f"\nStats: {router.stats()}")


if __name__ == "__main__":
    _demo()
