#!/usr/bin/env python3
"""
MAGNATRIX-OS — Multi-Agent Swarm Engine
ai/llm_multi_agent_swarm_native.py

Features:
- Swarm formation (dynamic agent grouping)
- Task decomposition (break tasks into subtasks for swarm)
- Consensus voting (swarm decision aggregation)
- Load balancing (distribute subtasks across agents)
- Result aggregation (combine swarm outputs)

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("swarm")


class AgentState(enum.Enum):
    IDLE = "idle"
    WORKING = "working"
    DONE = "done"
    FAILED = "failed"


@dataclass
class SwarmAgent:
    id: str
    capabilities: List[str]
    state: AgentState = AgentState.IDLE
    current_task: Optional[str] = None
    results: List[Any] = field(default_factory=list)
    load: int = 0


@dataclass
class Subtask:
    id: str
    description: str
    required_caps: List[str]
    assigned_to: Optional[str] = None
    status: str = "pending"
    result: Optional[Any] = None


@dataclass
class SwarmResult:
    task_id: str
    subtask_results: Dict[str, Any]
    consensus: Optional[Any] = None
    aggregate: Optional[Any] = None


class SwarmEngine:
    """Multi-agent swarm coordination."""

    def __init__(self, agents: List[SwarmAgent]):
        self.agents = {a.id: a for a in agents}
        self._task_counter = 0

    def form_swarm(self, task: str, required_caps: List[str], size: int = 5) -> List[SwarmAgent]:
        """Form a swarm of agents matching required capabilities."""
        scored = []
        for agent in self.agents.values():
            score = sum(1 for cap in required_caps if cap in agent.capabilities)
            scored.append((score, agent))
        scored.sort(key=lambda x: x[0], reverse=True)
        selected = [a for _, a in scored[:size] if a.state == AgentState.IDLE]
        return selected

    def decompose(self, task: str, subtask_specs: List[Tuple[str, List[str]]]) -> List[Subtask]:
        """Decompose task into subtasks."""
        subtasks = []
        for i, (desc, caps) in enumerate(subtask_specs):
            subtasks.append(Subtask(id=f"ST-{i}", description=desc, required_caps=caps))
        return subtasks

    def assign(self, subtasks: List[Subtask]) -> None:
        """Assign subtasks to agents by capability match and load."""
        for subtask in subtasks:
            candidates = []
            for agent in self.agents.values():
                if agent.state == AgentState.IDLE and all(cap in agent.capabilities for cap in subtask.required_caps):
                    candidates.append((agent.load, agent.id))
            if candidates:
                candidates.sort()
                chosen_id = candidates[0][1]
                subtask.assigned_to = chosen_id
                agent = self.agents[chosen_id]
                agent.state = AgentState.WORKING
                agent.current_task = subtask.id
                agent.load += 1

    def execute(self, subtasks: List[Subtask], executor: Callable[[Subtask], Any]) -> List[Subtask]:
        """Execute subtasks via provided executor."""
        for subtask in subtasks:
            if subtask.assigned_to:
                try:
                    subtask.result = executor(subtask)
                    subtask.status = "done"
                    agent = self.agents[subtask.assigned_to]
                    agent.state = AgentState.DONE
                    agent.results.append(subtask.result)
                except Exception as e:
                    subtask.status = "failed"
                    subtask.result = str(e)
                    agent = self.agents[subtask.assigned_to]
                    agent.state = AgentState.FAILED
        return subtasks

    def vote(self, results: List[Any]) -> Any:
        """Simple majority voting on results."""
        from collections import Counter
        counts = Counter(str(r) for r in results if r is not None)
        if counts:
            return counts.most_common(1)[0][0]
        return None

    def aggregate(self, subtasks: List[Subtask]) -> SwarmResult:
        """Aggregate subtask results into final output."""
        results = {st.id: st.result for st in subtasks}
        all_results = [r for r in results.values() if r is not None]
        consensus = self.vote(all_results) if all_results else None
        return SwarmResult(
            task_id=f"task-{self._task_counter}",
            subtask_results=results,
            consensus=consensus,
            aggregate=" | ".join(str(r) for r in all_results[:3]),
        )

    def reset(self) -> None:
        for agent in self.agents.values():
            agent.state = AgentState.IDLE
            agent.current_task = None
            agent.results = []

    def get_stats(self) -> Dict[str, Any]:
        states = defaultdict(int)
        for a in self.agents.values():
            states[a.state.value] += 1
        return {
            "agents": len(self.agents),
            "state_distribution": dict(states),
            "total_load": sum(a.load for a in self.agents.values()),
        }


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Multi-Agent Swarm Engine")
    print("ai/llm_multi_agent_swarm_native.py")
    print("=" * 60)

    agents = [
        SwarmAgent("A1", ["code", "review"]),
        SwarmAgent("A2", ["code", "test"]),
        SwarmAgent("A3", ["design", "review"]),
        SwarmAgent("A4", ["code", "deploy"]),
        SwarmAgent("A5", ["test", "monitor"]),
        SwarmAgent("A6", ["code", "design", "test"]),
    ]

    engine = SwarmEngine(agents)

    # 1. Form swarm
    print("\n[1] Form Swarm for Coding Task")
    swarm = engine.form_swarm("Build API", ["code", "test"], size=4)
    print(f"  Selected: {[a.id for a in swarm]}")

    # 2. Decompose
    print("\n[2] Decompose Task")
    subtasks = engine.decompose("Build API", [
        ("Implement endpoints", ["code"]),
        ("Write tests", ["test"]),
        ("Review code", ["review"]),
        ("Deploy", ["deploy"]),
    ])
    print(f"  Subtasks: {len(subtasks)}")

    # 3. Assign
    print("\n[3] Assign Subtasks")
    engine.assign(subtasks)
    for st in subtasks:
        print(f"  {st.id} → {st.assigned_to}: {st.description}")

    # 4. Execute
    print("\n[4] Execute")
    def mock_executor(st: Subtask) -> str:
        return f"Done: {st.description}"
    engine.execute(subtasks, mock_executor)

    # 5. Aggregate
    print("\n[5] Aggregate Results")
    result = engine.aggregate(subtasks)
    print(f"  Consensus: {result.consensus}")
    print(f"  Aggregate: {result.aggregate}")

    # 6. Stats
    print("\n[6] Swarm Stats")
    stats = engine.get_stats()
    print(f"  {stats}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
