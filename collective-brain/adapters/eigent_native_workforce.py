"""
eigent_native_workforce.py
===========================
MAGNATRIX Native Multi-Agent Workforce
Layer 0.5: COLLECTIVE BRAIN (extends adapters)

Pola AMATI-PELAJARI-TIRU dari eigent-ai:
- Amati:  Multi-agent workforce dengan credit system, 5 agent types,
          task routing by capability, performance tracking, cost estimation
- Pelajari: Core pattern: (1) WorkforcePool = agent collection,
            (2) CreditLedger = 1000 free + 200 daily credits,
            (3) CapabilityScorer = 0-100 capability matrix,
            (4) TaskRouter = composite routing formula,
            (5) PerformanceTracker = EMA reputation updates
- Tiru:   Native Python, MAGNATRIX mesh integration untuk distributed
          workforce, skill-based routing, cost optimization, reputation
          economy antara agents
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from collections import defaultdict


class AgentType(Enum):
    RESEARCHER = "researcher"
    CODER = "coder"
    WRITER = "writer"
    ANALYST = "analyst"
    DESIGNER = "designer"


@dataclass
class AgentProfile:
    """Workforce agent profile"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_type: AgentType = AgentType.RESEARCHER
    name: str = ""
    # Capability matrix: task_type -> score (0-100)
    capabilities: Dict[str, float] = field(default_factory=dict)
    # Performance
    reputation: float = 1.0  # EMA-based
    tasks_completed: int = 0
    tasks_failed: int = 0
    avg_quality_score: float = 0.0  # 0-1
    avg_response_time_ms: float = 0.0
    # Availability
    active: bool = True
    current_load: int = 0
    max_concurrent: int = 3
    # Cost
    cost_per_task: float = 1.0  # credits
    # MAGNATRIX
    mesh_node_id: Optional[str] = None

    def get_capability_score(self, task_type: str) -> float:
        return self.capabilities.get(task_type, 0.0)

    def get_overall_score(self) -> float:
        total = self.tasks_completed + self.tasks_failed
        success_rate = self.tasks_completed / total if total > 0 else 0.5
        return (success_rate * 0.4 + self.reputation * 0.3 +
                self.avg_quality_score * 0.2 + min(1.0, 1000 / max(self.avg_response_time_ms, 1)) * 0.1)

    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            "agent_type": self.agent_type.value,
            "overall_score": self.get_overall_score()
        }


@dataclass
class WorkforceTask:
    """Task dalam workforce"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_type: str = ""  # e.g., "research", "coding", "analysis"
    description: str = ""
    priority: int = 1  # 1-5, lower = higher
    complexity: float = 1.0  # 1-10
    estimated_cost: float = 0.0
    estimated_duration_ms: float = 0.0
    # Assignment
    assigned_agent_id: Optional[str] = None
    status: str = "pending"
    result: Optional[Dict] = None
    quality_score: float = 0.0
    # Timing
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict:
        return asdict(self)


class CreditLedger:
    """Credit system: 1000 free + 200 daily"""

    def __init__(self, free_credits: float = 1000.0,
                 daily_credits: float = 200.0):
        self.free_credits = free_credits
        self.daily_credits = daily_credits
        self._balances: Dict[str, float] = defaultdict(lambda: free_credits)
        self._daily_claimed: Dict[str, float] = {}  # user_id -> last_claim_time
        self._spent: Dict[str, float] = defaultdict(float)

    def get_balance(self, user_id: str) -> float:
        return self._balances[user_id]

    def deduct(self, user_id: str, amount: float) -> bool:
        if self._balances[user_id] >= amount:
            self._balances[user_id] -= amount
            self._spent[user_id] += amount
            return True
        return False

    def refund(self, user_id: str, amount: float):
        self._balances[user_id] += amount
        self._spent[user_id] -= amount

    def claim_daily(self, user_id: str) -> float:
        now = time.time()
        last_claim = self._daily_claimed.get(user_id, 0)
        if now - last_claim >= 86400:  # 24 hours
            self._balances[user_id] += self.daily_credits
            self._daily_claimed[user_id] = now
            return self.daily_credits
        return 0.0

    def get_usage(self, user_id: str) -> Dict:
        return {
            "balance": self._balances[user_id],
            "total_spent": self._spent[user_id],
            "free_remaining": max(0, self._balances[user_id] - self._spent.get(user_id, 0))
        }


class CapabilityScorer:
    """Score agent capabilities per task type"""

    def score(self, agent: AgentProfile, task_type: str) -> float:
        base = agent.get_capability_score(task_type)
        # Boost by reputation
        base *= (0.5 + agent.reputation)
        # Penalize high load
        load_penalty = agent.current_load / max(agent.max_concurrent, 1)
        base *= (1.0 - load_penalty * 0.3)
        return max(0, min(100, base))

    def compare_agents(self, agents: List[AgentProfile],
                       task_type: str) -> List[tuple]:
        """Return (agent_id, score) sorted by score descending"""
        scores = [(a.id, self.score(a, task_type)) for a in agents]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores


class TaskRouter:
    """Composite task routing: capability × availability × reputation / cost"""

    def __init__(self, scorer: CapabilityScorer):
        self.scorer = scorer

    def route(self, task: WorkforceTask,
              agents: List[AgentProfile],
              ledger: CreditLedger) -> Optional[str]:
        """Find best agent untuk task"""
        candidates = []
        for agent in agents:
            if not agent.active or agent.current_load >= agent.max_concurrent:
                continue

            capability = self.scorer.score(agent, task.task_type) / 100.0
            availability = 1.0 - (agent.current_load / max(agent.max_concurrent, 1))
            reputation = agent.reputation / 2.0  # Normalize
            cost_factor = 1.0 / max(agent.cost_per_task, 0.1)

            # Composite score
            score = (capability * 0.4 + availability * 0.2 +
                     reputation * 0.25 + cost_factor * 0.15)

            # Check if user can afford
            if ledger.get_balance("user") >= agent.cost_per_task * task.complexity:
                candidates.append((agent.id, score, agent.cost_per_task))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]


class PerformanceTracker:
    """EMA reputation tracking"""

    def __init__(self, alpha: float = 0.3):
        self.alpha = alpha  # EMA smoothing factor
        self._history: Dict[str, List[Dict]] = defaultdict(list)

    def record_completion(self, agent: AgentProfile, task: WorkforceTask):
        quality = task.quality_score
        duration = (task.completed_at or time.time()) - (task.started_at or task.created_at)

        # Update EMA reputation
        agent.reputation = (self.alpha * quality +
                           (1 - self.alpha) * agent.reputation)

        # Update average quality
        n = agent.tasks_completed + agent.tasks_failed
        agent.avg_quality_score = ((agent.avg_quality_score * (n - 1) + quality)
                                    / max(n, 1))

        # Update response time
        agent.avg_response_time_ms = ((agent.avg_response_time_ms * (n - 1) + duration * 1000)
                                       / max(n, 1))

        agent.tasks_completed += 1
        agent.current_load -= 1

        self._history[agent.id].append({
            "task_id": task.id,
            "quality": quality,
            "duration_ms": duration * 1000,
            "timestamp": time.time()
        })

    def record_failure(self, agent: AgentProfile, task: WorkforceTask):
        agent.tasks_failed += 1
        agent.current_load -= 1
        # Reputation penalty
        agent.reputation *= (1 - self.alpha * 0.5)

    def get_stats(self, agent_id: str) -> Dict:
        history = self._history.get(agent_id, [])
        if not history:
            return {}
        return {
            "tasks": len(history),
            "avg_quality": sum(h["quality"] for h in history) / len(history),
            "avg_duration_ms": sum(h["duration_ms"] for h in history) / len(history)
        }


class WorkforcePool:
    """
    Main workforce orchestrator.
    Tiru Eigent: manage multi-agent workforce dengan credit economy.
    """

    def __init__(self):
        self.agents: Dict[str, AgentProfile] = {}
        self.ledger = CreditLedger()
        self.scorer = CapabilityScorer()
        self.router = TaskRouter(self.scorer)
        self.tracker = PerformanceTracker()
        self.tasks: Dict[str, WorkforceTask] = {}
        self._mesh_broadcast: Optional[Callable] = None

    def connect_mesh(self, broadcast_fn: Callable):
        self._mesh_broadcast = broadcast_fn

    def register_agent(self, agent: AgentProfile) -> str:
        self.agents[agent.id] = agent
        return agent.id

    def create_task(self, task_type: str, description: str,
                    priority: int = 1, complexity: float = 1.0) -> WorkforceTask:
        task = WorkforceTask(
            task_type=task_type,
            description=description,
            priority=priority,
            complexity=complexity,
            estimated_cost=complexity * 1.0  # Base cost estimation
        )
        self.tasks[task.id] = task
        return task

    async def assign_task(self, task_id: str,
                          user_id: str = "default") -> Optional[str]:
        """Assign task to best agent"""
        task = self.tasks.get(task_id)
        if not task:
            return None

        # Claim daily credits
        self.ledger.claim_daily(user_id)

        # Route
        agent_id = self.router.route(
            task, list(self.agents.values()), self.ledger
        )
        if not agent_id:
            return None

        # Deduct cost
        agent = self.agents[agent_id]
        cost = agent.cost_per_task * task.complexity
        if not self.ledger.deduct(user_id, cost):
            return None

        task.assigned_agent_id = agent_id
        task.status = "assigned"
        task.started_at = time.time()
        agent.current_load += 1

        return agent_id

    async def complete_task(self, task_id: str, result: Dict,
                            quality_score: float = 0.8):
        """Mark task complete dan update metrics"""
        task = self.tasks.get(task_id)
        if not task or not task.assigned_agent_id:
            return

        agent = self.agents[task.assigned_agent_id]
        task.result = result
        task.quality_score = quality_score
        task.completed_at = time.time()
        task.status = "completed"

        self.tracker.record_completion(agent, task)

        if self._mesh_broadcast:
            self._mesh_broadcast({
                "type": "TASK_COMPLETED",
                "channel": "workforce.tasks",
                "task_id": task_id,
                "agent_id": agent.id,
                "quality": quality_score
            })

    def get_status(self) -> Dict:
        return {
            "agents": len(self.agents),
            "active_agents": sum(1 for a in self.agents.values() if a.active),
            "tasks": len(self.tasks),
            "pending": sum(1 for t in self.tasks.values() if t.status == "pending"),
            "completed": sum(1 for t in self.tasks.values() if t.status == "completed"),
            "total_credits_issued": sum(self.ledger._balances.values())
        }


# ==================== DEMO ====================

if __name__ == "__main__":
    async def demo():
        pool = WorkforcePool()

        # Register agents
        for atype in AgentType:
            agent = AgentProfile(
                agent_type=atype,
                name=f"{atype.value.capitalize()}-01",
                capabilities={
                    "research": 90 if atype == AgentType.RESEARCHER else 30,
                    "coding": 95 if atype == AgentType.CODER else 20,
                    "writing": 85 if atype == AgentType.WRITER else 25,
                    "analysis": 88 if atype == AgentType.ANALYST else 35,
                    "design": 80 if atype == AgentType.DESIGNER else 20,
                },
                cost_per_task=1.0
            )
            pool.register_agent(agent)

        # Create task
        task = pool.create_task("research", "Research LLM architecture trends", priority=1, complexity=2.0)

        # Assign
        agent_id = await pool.assign_task(task.id, "user1")
        print(f"Assigned to: {agent_id}")

        # Complete
        await pool.complete_task(task.id, {"findings": ["Transformer evolution", "MoE scaling"]}, quality_score=0.9)

        print(json.dumps(pool.get_status(), indent=2))

    asyncio.run(demo())
