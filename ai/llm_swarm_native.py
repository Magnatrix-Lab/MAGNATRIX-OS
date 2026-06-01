#!/usr/bin/env python3
"""
ai/llm_swarm_native.py
MAGNATRIX-OS — Multi-Agent Swarm Engine for the LLM Arena
AMATI pattern: multi-agent collaboration, swarm intelligence, consensus

Pure Python, stdlib only. Simulates multiple agents collaborating on complex tasks.
"""
from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ───────────────────────────────────────────────────────────────
# 0. UTILITIES
# ───────────────────────────────────────────────────────────────

def _now() -> float:
    return time.time()


# ───────────────────────────────────────────────────────────────
# 1. SWARM AGENT
# ───────────────────────────────────────────────────────────────

@dataclass
class SwarmAgent:
    agent_id: str
    role: str  # planner, executor, critic, researcher, synthesizer
    capability: float  # 0-1
    memory: List[str] = field(default_factory=list)
    success_count: int = 0
    total_tasks: int = 0

    def success_rate(self) -> float:
        return self.success_count / max(self.total_tasks, 1)

    def record(self, task: str, success: bool) -> None:
        self.memory.append(task)
        self.total_tasks += 1
        if success:
            self.success_count += 1

    def score(self) -> float:
        return (self.capability * 0.6) + (self.success_rate() * 0.4)


# ───────────────────────────────────────────────────────────────
# 2. ROLE ROUTER
# ───────────────────────────────────────────────────────────────

class RoleRouter:
    """Assign tasks to agents based on role and capability."""

    def __init__(self, agents: List[SwarmAgent]) -> None:
        self.agents = agents

    def route(self, task_type: str) -> SwarmAgent:
        role_map = {
            "plan": "planner",
            "execute": "executor",
            "critique": "critic",
            "research": "researcher",
            "synthesize": "synthesizer",
        }
        target_role = role_map.get(task_type, "executor")
        candidates = [a for a in self.agents if a.role == target_role]
        if not candidates:
            candidates = self.agents
        return max(candidates, key=lambda a: a.score())

    def get_stats(self) -> Dict[str, Any]:
        return {a.agent_id: {"role": a.role, "score": round(a.score(), 3)} for a in self.agents}


# ───────────────────────────────────────────────────────────────
# 3. CONSENSUS ENGINE
# ───────────────────────────────────────────────────────────────

class ConsensusEngine:
    """Agents vote on solutions, weighted by capability."""

    def vote(self, proposals: Dict[str, str], agents: List[SwarmAgent]) -> Tuple[str, float]:
        votes: Dict[str, float] = {}
        for agent in agents:
            # Simulate voting for a proposal based on agent preference
            preferred = random.choice(list(proposals.keys()))
            votes[preferred] = votes.get(preferred, 0) + agent.score()
        winner = max(votes, key=votes.get)
        total = sum(votes.values())
        confidence = votes[winner] / total if total > 0 else 0.0
        return proposals[winner], confidence


# ───────────────────────────────────────────────────────────────
# 4. COLLABORATION LOOP
# ───────────────────────────────────────────────────────────────

class CollaborationLoop:
    """Agents take turns, pass context, build on each other's work."""

    def __init__(self, agents: List[SwarmAgent], max_rounds: int = 5) -> None:
        self.agents = agents
        self.max_rounds = max_rounds

    def collaborate(self, task: str) -> Dict[str, Any]:
        context = f"Task: {task}"
        contributions = []
        for round_num in range(self.max_rounds):
            agent = self.agents[round_num % len(self.agents)]
            # Simulate contribution
            contribution = f"[{agent.role.upper()}] {agent.agent_id} contributes: analyzing '{task[:40]}'..."
            context += f"\n{contribution}"
            contributions.append({"round": round_num + 1, "agent": agent.agent_id, "contribution": contribution})
            # Check if consensus reached (simulated)
            if round_num >= 2 and random.random() > 0.3:
                break
        return {"context": context, "contributions": contributions, "rounds": len(contributions)}


# ───────────────────────────────────────────────────────────────
# 5. TASK DECOMPOSER
# ───────────────────────────────────────────────────────────────

class TaskDecomposer:
    """Break complex tasks into subtasks with dependencies."""

    def decompose(self, task: str) -> List[Dict[str, Any]]:
        # Simulate decomposition based on task keywords
        subtasks = []
        if "research" in task.lower():
            subtasks.append({"id": "t1", "type": "research", "description": "Gather information", "deps": []})
        if "analyze" in task.lower() or "compare" in task.lower():
            subtasks.append({"id": "t2", "type": "plan", "description": "Create analysis plan", "deps": ["t1"] if subtasks else []})
        if "write" in task.lower() or "create" in task.lower():
            subtasks.append({"id": "t3", "type": "execute", "description": "Produce deliverable", "deps": ["t2"] if len(subtasks) > 1 else []})
        if not subtasks:
            subtasks = [
                {"id": "t1", "type": "plan", "description": "Plan approach", "deps": []},
                {"id": "t2", "type": "execute", "description": "Execute plan", "deps": ["t1"]},
            ]
        return subtasks


# ───────────────────────────────────────────────────────────────
# 6. RESULT MERGER
# ───────────────────────────────────────────────────────────────

class ResultMerger:
    """Merge outputs from multiple agents into coherent response."""

    def merge(self, contributions: List[Dict[str, Any]]) -> str:
        parts = ["[SWARM RESULT]"]
        for c in contributions:
            parts.append(f"Round {c['round']} — {c['agent']}: {c['contribution']}")
        return "\n".join(parts)


# ───────────────────────────────────────────────────────────────
# 7. SWARM ORCHESTRATOR
# ───────────────────────────────────────────────────────────────

class SwarmOrchestrator:
    """Main orchestrator: decompose -> assign -> collaborate -> consensus -> merge."""

    def __init__(self, agents: List[SwarmAgent]) -> None:
        self.agents = agents
        self.router = RoleRouter(agents)
        self.consensus = ConsensusEngine()
        self.collaborator = CollaborationLoop(agents)
        self.decomposer = TaskDecomposer()
        self.merger = ResultMerger()

    def solve(self, task: str) -> Dict[str, Any]:
        # Decompose
        subtasks = self.decomposer.decompose(task)

        # Assign and execute subtasks
        subtask_results = []
        for st in subtasks:
            agent = self.router.route(st["type"])
            result = f"[{agent.agent_id}] Completed: {st['description']}"
            agent.record(st["description"], success=True)
            subtask_results.append({"subtask": st, "agent": agent.agent_id, "result": result})

        # Collaborate on synthesis
        collab = self.collaborator.collaborate(task)

        # Consensus on final answer
        proposals = {a.agent_id: f"Answer from {a.role} {a.agent_id}" for a in self.agents}
        answer, confidence = self.consensus.vote(proposals, self.agents)

        # Merge
        merged = self.merger.merge(collab["contributions"])

        return {
            "task": task,
            "subtasks": subtask_results,
            "collaboration": collab,
            "consensus_answer": answer,
            "consensus_confidence": round(confidence, 3),
            "merged_output": merged,
            "agent_stats": self.router.get_stats(),
        }

    def stats(self) -> Dict[str, Any]:
        return {"agents": len(self.agents), "roles": list(set(a.role for a in self.agents))}


# ───────────────────────────────────────────────────────────────
# 8. DEMO
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Multi-Agent Swarm Demo")
    print("=" * 60)

    agents = [
        SwarmAgent("planner_1", "planner", 0.92),
        SwarmAgent("executor_1", "executor", 0.88),
        SwarmAgent("critic_1", "critic", 0.85),
        SwarmAgent("researcher_1", "researcher", 0.90),
        SwarmAgent("synthesizer_1", "synthesizer", 0.87),
    ]

    swarm = SwarmOrchestrator(agents)

    task = "Research and compare the pros and cons of Python vs Rust for systems programming, then write a recommendation."
    print(f"\n[TASK] {task[:70]}...")
    result = swarm.solve(task)

    print(f"\n[SUBTASKS] {len(result['subtasks'])}")
    for st in result["subtasks"]:
        print(f"  {st['subtask']['id']} ({st['subtask']['type']}) -> {st['agent']}")

    print(f"\n[COLLABORATION] {result['collaboration']['rounds']} rounds")
    for c in result["collaboration"]["contributions"][:3]:
        print(f"  Round {c['round']}: {c['agent']}")

    print(f"\n[CONSENSUS] confidence={result['consensus_confidence']:.3f}")
    print(f"  Answer: {result['consensus_answer'][:80]}...")

    print(f"\n[STATS] {json.dumps(result['agent_stats'], indent=2)}")

    print("\n" + "=" * 60)
    print("Demo complete. Swarm Engine ready for LLM Arena.")
    print("=" * 60)
