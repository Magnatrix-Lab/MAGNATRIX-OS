"""Agent Swarm Coordinator — Multi-agent orchestration, task distribution, and consensus.

Modul ini menyediakan:
- AgentRegistry untuk register/unregister agents dengan capability
- SwarmCoordinator untuk distribute tasks ke swarm agents
- TaskDistributor untuk load balancing antar agents
- ConsensusEngine untuk voting dan agreement
- SwarmOptimizer untuk auto-scale dan reassign
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class AgentStatus(Enum):
    IDLE = auto()
    BUSY = auto()
    OFFLINE = auto()
    ERROR = auto()


class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Agent:
    """Single agent in the swarm."""
    agent_id: str
    name: str
    capabilities: Set[str]
    status: AgentStatus = AgentStatus.IDLE
    current_task: Optional[str] = None
    success_rate: float = 1.0
    total_tasks: int = 0
    completed_tasks: int = 0
    avg_latency: float = 0.0
    max_concurrent: int = 1
    active_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_heartbeat: float = field(default_factory=time.time)

    def can_accept(self) -> bool:
        return self.status == AgentStatus.IDLE and self.active_count < self.max_concurrent

    def score_for_task(self, task_caps: Set[str]) -> float:
        match = len(self.capabilities & task_caps) / max(len(task_caps), 1)
        load_penalty = self.active_count / max(self.max_concurrent, 1)
        return match * 100 - load_penalty * 20 + self.success_rate * 10


@dataclass
class Task:
    """Task to be distributed to swarm."""
    task_id: str
    description: str
    required_caps: Set[str]
    priority: TaskPriority = TaskPriority.MEDIUM
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    assigned_to: Optional[str] = None
    completed_at: Optional[float] = None
    result: Any = None
    status: str = "pending"  # pending, assigned, completed, failed


@dataclass
class ConsensusVote:
    """Vote from an agent on a decision."""
    agent_id: str
    vote: Any
    confidence: float = 0.5
    reasoning: str = ""


class AgentRegistry:
    """Register and manage swarm agents."""

    def __init__(self):
        self._agents: Dict[str, Agent] = {}
        self._by_capability: Dict[str, Set[str]] = {}

    def register(self, agent: Agent) -> None:
        self._agents[agent.agent_id] = agent
        for cap in agent.capabilities:
            self._by_capability.setdefault(cap, set()).add(agent.agent_id)

    def unregister(self, agent_id: str) -> None:
        agent = self._agents.pop(agent_id, None)
        if agent:
            for cap in agent.capabilities:
                self._by_capability.get(cap, set()).discard(agent_id)

    def get(self, agent_id: str) -> Optional[Agent]:
        return self._agents.get(agent_id)

    def find_by_capability(self, cap: str) -> List[Agent]:
        return [self._agents[aid] for aid in self._by_capability.get(cap, set()) if aid in self._agents]

    def list_all(self) -> List[Agent]:
        return list(self._agents.values())

    def update_heartbeat(self, agent_id: str) -> None:
        if agent_id in self._agents:
            self._agents[agent_id].last_heartbeat = time.time()

    def check_health(self, timeout: float = 60.0) -> List[str]:
        now = time.time()
        stale = []
        for aid, agent in self._agents.items():
            if now - agent.last_heartbeat > timeout:
                agent.status = AgentStatus.OFFLINE
                stale.append(aid)
        return stale


class TaskDistributor:
    """Distribute tasks to agents with load balancing."""

    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self._pending: List[Task] = []
        self._history: List[Task] = []

    def submit(self, task: Task) -> Optional[str]:
        candidates = []
        for cap in task.required_caps:
            for agent in self.registry.find_by_capability(cap):
                if agent.can_accept():
                    candidates.append(agent)
        if not candidates:
            self._pending.append(task)
            return None
        # Score and pick best
        candidates = list({a.agent_id: a for a in candidates}.values())
        best = max(candidates, key=lambda a: a.score_for_task(task.required_caps))
        task.assigned_to = best.agent_id
        task.status = "assigned"
        best.active_count += 1
        best.status = AgentStatus.BUSY if best.active_count >= best.max_concurrent else AgentStatus.IDLE
        return best.agent_id

    def complete(self, task_id: str, result: Any, success: bool = True) -> Optional[Task]:
        for task in self._history + self._pending:
            if task.task_id == task_id:
                task.result = result
                task.status = "completed" if success else "failed"
                task.completed_at = time.time()
                if task.assigned_to and task.assigned_to in self.registry._agents:
                    agent = self.registry._agents[task.assigned_to]
                    agent.active_count = max(0, agent.active_count - 1)
                    agent.status = AgentStatus.IDLE if agent.active_count < agent.max_concurrent else AgentStatus.BUSY
                    agent.total_tasks += 1
                    if success:
                        agent.completed_tasks += 1
                    agent.success_rate = agent.completed_tasks / max(agent.total_tasks, 1)
                return task
        return None

    def get_pending(self) -> List[Task]:
        return self._pending

    def get_stats(self) -> Dict[str, Any]:
        all_tasks = self._history + self._pending
        return {
            "pending": len(self._pending),
            "total": len(all_tasks),
            "completed": sum(1 for t in all_tasks if t.status == "completed"),
            "failed": sum(1 for t in all_tasks if t.status == "failed"),
        }


class ConsensusEngine:
    """Voting and consensus among agents."""

    def __init__(self, min_agreement: float = 0.6):
        self.min_agreement = min_agreement

    def vote(self, votes: List[ConsensusVote]) -> Tuple[Any, float, List[ConsensusVote]]:
        if not votes:
            return None, 0.0, []
        # Group votes by value
        groups: Dict[str, List[ConsensusVote]] = {}
        for v in votes:
            key = str(v.vote)
            groups.setdefault(key, []).append(v)
        # Find majority
        best_key = max(groups, key=lambda k: len(groups[k]))
        best_votes = groups[best_key]
        agreement = len(best_votes) / len(votes)
        avg_confidence = sum(v.confidence for v in best_votes) / len(best_votes)
        return best_votes[0].vote, agreement, best_votes

    def is_consensus(self, votes: List[ConsensusVote]) -> bool:
        _, agreement, _ = self.vote(votes)
        return agreement >= self.min_agreement

    def weighted_vote(self, votes: List[ConsensusVote]) -> Tuple[Any, float]:
        # Weight by confidence * success_rate
        weighted = {}
        for v in votes:
            key = str(v.vote)
            weighted[key] = weighted.get(key, 0.0) + v.confidence
        best = max(weighted, key=weighted.get)
        total = sum(weighted.values())
        return best, weighted[best] / max(total, 1)


class SwarmOptimizer:
    """Auto-scale and optimize swarm configuration."""

    def __init__(self, target_utilization: float = 0.7):
        self.target_utilization = target_utilization

    def optimize(self, registry: AgentRegistry, distributor: TaskDistributor) -> Dict[str, Any]:
        agents = registry.list_all()
        if not agents:
            return {"recommendation": "no_agents"}

        busy = sum(1 for a in agents if a.status == AgentStatus.BUSY)
        idle = sum(1 for a in agents if a.status == AgentStatus.IDLE)
        offline = sum(1 for a in agents if a.status == AgentStatus.OFFLINE)
        utilization = busy / max(len(agents), 1)

        recommendations = []
        if utilization > self.target_utilization + 0.2:
            recommendations.append("scale_up")
        elif utilization < self.target_utilization - 0.2 and len(agents) > 3:
            recommendations.append("scale_down")
        if offline > 0:
            recommendations.append("restart_offline")
        if distributor._pending:
            recommendations.append("redistribute_pending")

        return {
            "utilization": round(utilization, 2),
            "busy": busy,
            "idle": idle,
            "offline": offline,
            "pending_tasks": len(distributor._pending),
            "recommendations": recommendations,
        }


class SwarmCoordinator:
    """Main orchestrator for agent swarm."""

    def __init__(self):
        self.registry = AgentRegistry()
        self.distributor = TaskDistributor(self.registry)
        self.consensus = ConsensusEngine()
        self.optimizer = SwarmOptimizer()
        self._callbacks: List[Callable[[str, Any], None]] = []

    def add_agent(self, name: str, capabilities: Set[str], max_concurrent: int = 1) -> Agent:
        agent = Agent(
            agent_id=str(uuid.uuid4())[:12],
            name=name,
            capabilities=capabilities,
            max_concurrent=max_concurrent,
        )
        self.registry.register(agent)
        return agent

    def submit_task(self, description: str, required_caps: Set[str], priority: TaskPriority = TaskPriority.MEDIUM,
                    payload: Optional[Dict[str, Any]] = None) -> Task:
        task = Task(
            task_id=str(uuid.uuid4())[:12],
            description=description,
            required_caps=required_caps,
            priority=priority,
            payload=payload or {},
        )
        assigned = self.distributor.submit(task)
        if assigned:
            self._notify("task_assigned", task)
        else:
            self._notify("task_pending", task)
        return task

    def complete_task(self, task_id: str, result: Any, success: bool = True) -> bool:
        task = self.distributor.complete(task_id, result, success)
        if task:
            self._notify("task_completed", task)
            return True
        return False

    def run_consensus(self, question: str, votes: List[ConsensusVote]) -> Dict[str, Any]:
        winner, agreement, supporting = self.consensus.vote(votes)
        return {
            "question": question,
            "winner": winner,
            "agreement": round(agreement, 2),
            "supporting_agents": [v.agent_id for v in supporting],
            "is_consensus": agreement >= self.consensus.min_agreement,
        }

    def health_check(self) -> List[str]:
        return self.registry.check_health(timeout=30.0)

    def optimize(self) -> Dict[str, Any]:
        return self.optimizer.optimize(self.registry, self.distributor)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "agents": len(self.registry.list_all()),
            "tasks": self.distributor.get_stats(),
            "health": len(self.health_check()),
        }

    def on_event(self, callback: Callable[[str, Any], None]) -> None:
        self._callbacks.append(callback)

    def _notify(self, event: str, data: Any) -> None:
        for cb in self._callbacks:
            try:
                cb(event, data)
            except Exception:
                pass


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("AGENT SWARM COORDINATOR DEMO")
    print("=" * 70)

    # 1. Setup swarm
    print("\n[1] Setup Swarm")
    swarm = SwarmCoordinator()
    a1 = swarm.add_agent("Researcher-A", {"research", "analysis"}, max_concurrent=2)
    a2 = swarm.add_agent("Researcher-B", {"research", "writing"}, max_concurrent=1)
    a3 = swarm.add_agent("Coder-A", {"coding", "analysis"}, max_concurrent=2)
    a4 = swarm.add_agent("Reviewer-A", {"review", "writing"}, max_concurrent=1)
    print(f"  {len(swarm.registry.list_all())} agents registered")
    for a in swarm.registry.list_all():
        print(f"    {a.name}: caps={a.capabilities}, max_concurrent={a.max_concurrent}")

    # 2. Submit tasks
    print("\n[2] Submit Tasks")
    tasks = [
        swarm.submit_task("Research climate change", {"research"}, TaskPriority.HIGH),
        swarm.submit_task("Write report on AI", {"writing", "research"}),
        swarm.submit_task("Code sorting algorithm", {"coding"}),
        swarm.submit_task("Review code quality", {"review"}),
        swarm.submit_task("Analyze market data", {"analysis"}),
    ]
    for t in tasks:
        print(f"    {t.task_id[:8]}: {t.description[:30]}... -> assigned={t.assigned_to}")

    # 3. Check pending
    print(f"\n[3] Pending Tasks: {len(swarm.distributor.get_pending())}")

    # 4. Complete tasks
    print("\n[4] Complete Tasks")
    for t in tasks:
        if t.assigned_to:
            swarm.complete_task(t.task_id, f"Result for {t.description[:20]}", success=True)
            print(f"    Completed: {t.task_id[:8]} by {t.assigned_to}")

    # 5. Agent stats
    print("\n[5] Agent Stats")
    for a in swarm.registry.list_all():
        print(f"    {a.name}: tasks={a.total_tasks}, success_rate={a.success_rate:.0%}, status={a.status.name}")

    # 6. Consensus
    print("\n[6] Consensus Voting")
    votes = [
        ConsensusVote(a1.agent_id, "deploy", 0.9, "System is stable"),
        ConsensusVote(a2.agent_id, "deploy", 0.8, "Tests pass"),
        ConsensusVote(a3.agent_id, "wait", 0.6, "Need more testing"),
        ConsensusVote(a4.agent_id, "deploy", 0.85, "Code review clean"),
    ]
    result = swarm.run_consensus("Should we deploy?", votes)
    print(f"    Winner: {result['winner']}, Agreement: {result['agreement']}")
    print(f"    Consensus: {result['is_consensus']}")

    # 7. Weighted vote
    winner, confidence = swarm.consensus.weighted_vote(votes)
    print(f"\n[7] Weighted Vote: {winner} (confidence={confidence:.2f})")

    # 8. Optimization
    print("\n[8] Swarm Optimization")
    opt = swarm.optimize()
    print(f"    Utilization: {opt['utilization']}")
    print(f"    Recommendations: {opt['recommendations']}")

    # 9. Stats
    print(f"\n[9] Overall Stats")
    print(f"    {swarm.get_stats()}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
