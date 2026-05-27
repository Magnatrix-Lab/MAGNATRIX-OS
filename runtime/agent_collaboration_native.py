#!/usr/bin/env python3
"""
MAGNATRIX-OS Layer: Runtime — Agent Collaboration Patterns
File: runtime/agent_collaboration_native.py
Pattern: AMATI-PELAJARI-TIRU dari CrewAI + AutoGen + LangGraph + MCP

Concrete multi-agent collaboration scenarios demonstrating:
  1. CrewAI Pattern — Role-based sequential execution
     Researcher → Writer → Critic → Reviewer
  2. AutoGen Pattern — Conversational group chat
     Agents chat back-and-forth until consensus
  3. LangGraph Pattern — State machine workflow
     Nodes and edges dengan conditional branching
  4. MCP Pattern — Tool interoperability across agents
     One agent's tool callable by another via protocol
  5. Hierarchical Pattern — Manager delegates to workers
     Top-down task decomposition and result aggregation

All patterns use runtime/multi_agent_swarm_native.py as foundation.
Zero external dependencies. Pure Python standard library.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

# Import swarm engine
from runtime.multi_agent_swarm_native import (
    AgentCapabilities, AgentRegistration, AgentRegistry,
    AgentMessage, CollaborativeAgent, ConsensusEngine,
    MCPToolProtocol, MessageBus, SharedMemory, SwarmOrchestrator,
    Task, TaskDelegator,
)


# ============================================================================
# 1.  CREWAI PATTERN — Role-based Sequential Execution
# ============================================================================

class CrewAIExecutor:
    """
    CrewAI-style: agents with specific roles execute tasks sequentially.
    Researcher researches → Writer writes → Critic critiques → Reviewer approves.
    """

    ROLES = ["researcher", "writer", "critic", "reviewer"]

    def __init__(self, orchestrator: SwarmOrchestrator) -> None:
        self.orch = orchestrator
        self.results: Dict[str, Any] = {}

    def execute(self, goal: str) -> Dict[str, Any]:
        """Execute a goal through the full crew pipeline."""
        pipeline = [
            ("researcher", f"Research: {goal}", "research"),
            ("writer", f"Write draft based on research for: {goal}", "write"),
            ("critic", f"Critique the draft for: {goal}", "review"),
            ("reviewer", f"Final review and approve: {goal}", "verify"),
        ]

        for role, desc, cap in pipeline:
            agents = self.orch.registry.find_by_role(role)
            if not agents:
                # Fallback: use any available agent
                agents = self.orch.registry.get_all_alive()
            if not agents:
                self.results[role] = f"[ERROR] No {role} agent available"
                continue

            agent = agents[0]
            task = self.orch.delegator.create_task(desc, cap)
            self.orch.delegator.assign(task, "best_match")
            # Simulate execution
            result = f"[{agent.name}] {role.upper()}: Completed {desc[:40]}..."
            self.orch.delegator.report_result(task.task_id, result, success=True)
            self.results[role] = result

        return self.results


# ============================================================================
# 2.  AUTOGEN PATTERN — Conversational Group Chat
# ============================================================================

class AutoGenChat:
    """
    AutoGen-style: agents chat in a group until they reach consensus.
    Each agent can speak, reply, and reference previous messages.
    """

    def __init__(self, orchestrator: SwarmOrchestrator, participants: List[str]) -> None:
        self.orch = orchestrator
        self.participants = participants
        self.chat_log: List[Dict[str, Any]] = []
        self.rounds = 0
        self.max_rounds = 6

    def start(self, topic: str) -> List[Dict[str, Any]]:
        """Start a group chat about a topic."""
        # Initial message dari orchestrator
        self._broadcast("orchestrator", f"Let's discuss: {topic}. Each of you share your perspective.")

        for _round in range(self.max_rounds):
            self.rounds += 1
            for participant_id in self.participants:
                agent = self.orch.registry.get(participant_id)
                if not agent or agent.status == "offline":
                    continue

                # Agent "reads" recent chat history dan formulates response
                context = self._get_context(3)
                response = self._generate_response(agent, topic, context)
                self._broadcast(participant_id, response)

            # Check for convergence (simplified: all said something similar)
            if self._check_consensus():
                break

        return self.chat_log

    def _broadcast(self, sender_id: str, text: str) -> None:
        msg = {
            "round": self.rounds,
            "sender": sender_id,
            "sender_name": self.orch.registry.get(sender_id).name if self.orch.registry.get(sender_id) else sender_id,
            "text": text,
            "time": time.time(),
        }
        self.chat_log.append(msg)

    def _get_context(self, n: int) -> str:
        recent = self.chat_log[-n:]
        return " | ".join(f"{m['sender_name']}: {m['text'][:30]}" for m in recent)

    def _generate_response(self, agent: AgentRegistration, topic: str, context: str) -> str:
        role = agent.role
        if role == "researcher":
            return f"From my research on {topic[:20]}, I found key insights about data patterns."
        elif role == "writer":
            return f"I can draft a compelling narrative on {topic[:20]} incorporating those insights."
        elif role == "critic":
            return f"But have we considered the edge cases in {topic[:20]}?"
        elif role == "reviewer":
            return f"The approach looks solid. I approve with minor revisions."
        else:
            return f"Interesting point. I agree with the direction on {topic[:20]}."

    def _check_consensus(self) -> bool:
        if len(self.chat_log) < 4:
            return False
        # Simplified: if last 3 messages contain "agree" or "approve"
        last = [m["text"].lower() for m in self.chat_log[-3:]]
        return any("agree" in t or "approve" in t for t in last)


# ============================================================================
# 3.  LANGGRAPH PATTERN — State Machine Workflow
# ============================================================================

@dataclass
class GraphState:
    """Mutable state bag untuk LangGraph-style workflows."""
    data: Dict[str, Any] = field(default_factory=dict)
    current_node: str = "start"
    history: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def update(self, key: str, value: Any) -> None:
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)


class LangGraphWorkflow:
    """
    LangGraph-style: define nodes (functions) dan edges (transitions).
    Conditional edges based on state.
    """

    def __init__(self) -> None:
        self.nodes: Dict[str, Callable[[GraphState], GraphState]] = {}
        self.edges: Dict[str, List[Tuple[str, Optional[Callable[[GraphState], bool]]]]] = defaultdict(list)
        self.entry_point: str = "start"

    def add_node(self, name: str, fn: Callable[[GraphState], GraphState]) -> None:
        self.nodes[name] = fn

    def add_edge(self, from_node: str, to_node: str,
                 condition: Optional[Callable[[GraphState], bool]] = None) -> None:
        self.edges[from_node].append((to_node, condition))

    def set_entry(self, node: str) -> None:
        self.entry_point = node

    def run(self, initial_state: Optional[GraphState] = None,
            max_steps: int = 20) -> GraphState:
        state = initial_state or GraphState()
        state.current_node = self.entry_point
        steps = 0

        while steps < max_steps:
            steps += 1
            node_name = state.current_node
            state.history.append(node_name)

            if node_name == "__end__":
                break

            if node_name not in self.nodes:
                state.errors.append(f"Node '{node_name}' not found")
                break

            # Execute node
            state = self.nodes[node_name](state)

            # Determine next node
            transitions = self.edges.get(node_name, [])
            next_node = None
            for to_node, condition in transitions:
                if condition is None or condition(state):
                    next_node = to_node
                    break

            if next_node is None:
                # No valid transition — try unconditional
                for to_node, condition in transitions:
                    if condition is None:
                        next_node = to_node
                        break

            if next_node is None:
                state.errors.append(f"Dead end at '{node_name}'")
                break

            state.current_node = next_node

        return state


# ============================================================================
# 4.  MCP PATTERN — Cross-Agent Tool Interoperability
# ============================================================================

class MCPCollaboration:
    """
    MCP-style: agents expose tools via schema. Other agents call them.
    """

    def __init__(self, orchestrator: SwarmOrchestrator) -> None:
        self.orch = orchestrator
        self.mcp = MCPToolProtocol(orchestrator.bus)
        self._setup_tools()

    def _setup_tools(self) -> None:
        # Researcher exposes search tool
        self.mcp.register_tool(
            "researcher", "web_search",
            {"query": "string", "max_results": "integer"},
            lambda args: f"Search results for '{args.get('query')}': [r1, r2, r3]"
        )
        # Writer exposes draft tool
        self.mcp.register_tool(
            "writer", "draft_document",
            {"topic": "string", "sections": "integer"},
            lambda args: f"Draft: {args.get('topic')} ({args.get('sections', 3)} sections)"
        )
        # Coder exposes code tool
        self.mcp.register_tool(
            "coder", "generate_code",
            {"language": "string", "spec": "string"},
            lambda args: f"```{args.get('language')}\n# Code for: {args.get('spec')}\n```"
        )

    def call_cross_agent_tool(self, caller: str, tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
        return self.mcp.call_tool(caller, tool, args)

    def list_all_tools(self) -> List[Dict[str, Any]]:
        return self.mcp.list_tools()


# ============================================================================
# 5.  HIERARCHICAL PATTERN — Manager + Workers
# ============================================================================

class HierarchicalSwarm:
    """
    Hierarchical: Manager agent breaks tasks, assigns to workers, aggregates results.
    """

    def __init__(self, orchestrator: SwarmOrchestrator) -> None:
        self.orch = orchestrator

    def execute(self, goal: str, worker_ids: List[str]) -> Dict[str, Any]:
        # Manager decomposes
        subtasks = self._decompose(goal)
        results = {}

        # Assign to workers round-robin
        for i, subtask in enumerate(subtasks):
            worker_id = worker_ids[i % len(worker_ids)]
            worker = self.orch.registry.get(worker_id)
            if not worker:
                continue

            task = self.orch.delegator.create_task(subtask, "general")
            self.orch.delegator.assign(task, "round_robin")
            # Simulate
            result = f"[{worker.name}] Done: {subtask[:40]}"
            self.orch.delegator.report_result(task.task_id, result)
            results[worker_id] = result

        # Manager synthesizes
        synthesis = f"[Manager] Synthesized {len(results)} worker outputs for: {goal[:40]}"
        return {"sub_results": results, "synthesis": synthesis}

    def _decompose(self, goal: str) -> List[str]:
        g = goal.lower()
        subtasks = []
        if "build" in g or "create" in g:
            subtasks.append(f"Design architecture for: {goal}")
            subtasks.append(f"Implement core logic for: {goal}")
            subtasks.append(f"Add tests for: {goal}")
        if "research" in g or "analyze" in g:
            subtasks.append(f"Gather data for: {goal}")
            subtasks.append(f"Analyze findings for: {goal}")
            subtasks.append(f"Summarize results for: {goal}")
        if not subtasks:
            subtasks = [f"Step 1: {goal}", f"Step 2: Verify {goal}", f"Step 3: Finalize {goal}"]
        return subtasks


# ============================================================================
# 6.  TEST SUITE & DEMO
# ============================================================================

def _setup_orchestrator() -> SwarmOrchestrator:
    orch = SwarmOrchestrator()
    agents_config = [
        ("r1", "Alice-Researcher", "researcher", AgentCapabilities(tools=["search", "analyze"], specialties=["research", "data"])),
        ("w1", "Bob-Writer", "writer", AgentCapabilities(tools=["write", "summarize"], specialties=["write", "content"])),
        ("c1", "Carol-Critic", "critic", AgentCapabilities(tools=["review", "compare"], specialties=["review", "critique"])),
        ("rv1", "Dave-Reviewer", "reviewer", AgentCapabilities(tools=["verify", "check"], specialties=["verify", "qa"])),
        ("cd1", "Eve-Coder", "coder", AgentCapabilities(tools=["code", "test"], specialties=["code", "debug"])),
        ("m1", "Frank-Manager", "manager", AgentCapabilities(tools=["plan", "delegate"], specialties=["plan", "manage"])),
    ]
    for agent_id, name, role, caps in agents_config:
        orch.register_agent(agent_id, name, role, caps)
    return orch


def _test_crewai() -> None:
    orch = _setup_orchestrator()
    crew = CrewAIExecutor(orch)
    results = crew.execute("Build a Python async web scraper")
    assert "researcher" in results
    assert "writer" in results
    assert "critic" in results
    assert "reviewer" in results
    orch.stop()
    print("  [OK] CrewAI Pattern — 4-role sequential pipeline")


def _test_autogen_chat() -> None:
    orch = _setup_orchestrator()
    chat = AutoGenChat(orch, ["r1", "w1", "c1", "rv1"])
    log = chat.start("Should we use asyncio or threading for I/O bound tasks?")
    assert len(log) > 4
    assert chat.rounds >= 1
    orch.stop()
    print(f"  [OK] AutoGen Pattern — {len(log)} messages, {chat.rounds} rounds")


def _test_langgraph() -> None:
    workflow = LangGraphWorkflow()

    def start_node(state: GraphState) -> GraphState:
        state.update("step", "started")
        return state

    def research_node(state: GraphState) -> GraphState:
        state.update("research", "completed")
        state.update("data_found", True)
        return state

    def write_node(state: GraphState) -> GraphState:
        state.update("draft", "completed")
        return state

    def review_node(state: GraphState) -> GraphState:
        state.update("review", "approved")
        return state

    def end_node(state: GraphState) -> GraphState:
        state.update("final", "done")
        return state

    workflow.add_node("start", start_node)
    workflow.add_node("research", research_node)
    workflow.add_node("write", write_node)
    workflow.add_node("review", review_node)
    workflow.add_node("end", end_node)

    workflow.set_entry("start")
    workflow.add_edge("start", "research")
    workflow.add_edge("research", "write", condition=lambda s: s.get("data_found", False))
    workflow.add_edge("research", "end", condition=lambda s: not s.get("data_found", False))
    workflow.add_edge("write", "review")
    workflow.add_edge("review", "end")

    state = workflow.run()
    assert state.get("final") == "done"
    assert "research" in state.history
    assert "write" in state.history
    print("  [OK] LangGraph Pattern — state machine workflow")


def _test_mcp_collaboration() -> None:
    orch = _setup_orchestrator()
    mcp = MCPCollaboration(orch)
    tools = mcp.list_all_tools()
    assert len(tools) == 3

    r1 = mcp.call_cross_agent_tool("caller1", "web_search", {"query": "asyncio", "max_results": 5})
    assert "asyncio" in str(r1)

    r2 = mcp.call_cross_agent_tool("caller2", "generate_code", {"language": "python", "spec": "hello world"})
    assert "python" in str(r2)
    orch.stop()
    print(f"  [OK] MCP Pattern — {len(tools)} cross-agent tools")


def _test_hierarchical() -> None:
    orch = _setup_orchestrator()
    hier = HierarchicalSwarm(orch)
    result = hier.execute("Build a trading bot", ["cd1", "r1", "w1"])
    assert "sub_results" in result
    assert "synthesis" in result
    assert len(result["sub_results"]) >= 3
    orch.stop()
    print(f"  [OK] Hierarchical Pattern — {len(result['sub_results'])} subtasks managed")


def _demo() -> None:
    print("=" * 60)
    print("MAGNATRIX Agent Collaboration Patterns — Native Demo")
    print("Patterns: CrewAI + AutoGen + LangGraph + MCP + Hierarchical")
    print("=" * 60)

    print("\n[Unit Tests]")
    _test_crewai()
    _test_autogen_chat()
    _test_langgraph()
    _test_mcp_collaboration()
    _test_hierarchical()

    print("\n[Integration Demo — Full Pipeline]")
    orch = _setup_orchestrator()

    # 1. CrewAI: sequential role pipeline
    print("\n  [1] CrewAI Pipeline:")
    crew = CrewAIExecutor(orch)
    crew_results = crew.execute("Design a secure messaging protocol")
    for role, result in crew_results.items():
        print(f"      {role:12s} → {result[:50]}...")

    # 2. AutoGen: group chat
    print("\n  [2] AutoGen Group Chat:")
    chat = AutoGenChat(orch, ["r1", "w1", "c1", "rv1"])
    chat_log = chat.start("What is the best architecture for agentic AI?")
    for msg in chat_log[:6]:
        print(f"      [{msg['sender_name']:15s}] {msg['text'][:50]}...")

    # 3. LangGraph: state workflow
    print("\n  [3] LangGraph Workflow:")
    workflow = LangGraphWorkflow()
    workflow.add_node("start", lambda s: s.update("phase", "start") or s)
    workflow.add_node("gather", lambda s: s.update("data", "collected") or s)
    workflow.add_node("process", lambda s: s.update("processed", True) or s)
    workflow.add_node("end", lambda s: s.update("done", True) or s)
    workflow.set_entry("start")
    workflow.add_edge("start", "gather")
    workflow.add_edge("gather", "process")
    workflow.add_edge("process", "end")
    state = workflow.run()
    print(f"      Path: {' → '.join(state.history)}")
    print(f"      Data: {state.get('data')}, Processed: {state.get('processed')}")

    # 4. MCP: tool calls
    print("\n  [4] MCP Cross-Agent Tools:")
    mcp = MCPCollaboration(orch)
    for tool in mcp.list_all_tools():
        print(f"      • {tool['name']} (by {tool['agent_id']})")
    result = mcp.call_cross_agent_tool("orchestrator", "draft_document", {"topic": "Swarm Intelligence", "sections": 5})
    print(f"      Result: {result.get('result')}")

    # 5. Hierarchical: manager + workers
    print("\n  [5] Hierarchical Swarm:")
    hier = HierarchicalSwarm(orch)
    hier_result = hier.execute("Build a real-time data pipeline", ["cd1", "r1", "w1", "rv1"])
    print(f"      Manager: {hier_result['synthesis'][:60]}...")
    for wid, res in hier_result["sub_results"].items():
        agent = orch.registry.get(wid)
        name = agent.name if agent else wid
        print(f"      {name:15s} → {res[:50]}...")

    orch.stop()

    print("\n" + "=" * 60)
    print("All collaboration patterns tested. Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    _demo()
