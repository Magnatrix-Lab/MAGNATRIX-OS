"""
stoa_native_swarm.py
======================
MAGNATRIX Native Swarm Intelligence Engine
Layer 0.5: COLLECTIVE BRAIN (extends agent_roles.py)

Pola AMATI-PELAJARI-TIRU dari stoaaadev/stoa:
- Amati:  8-role swarm system, mesh broadcast, consensus mechanism,
          guardian veto, HALT mechanism, task decomposition
- Pelajari: Core pattern: (1) AgentRole = persona + capabilities + memory,
            (2) SwarmEngine = coordinator + consensus + veto,
            (3) MeshBroadcaster = priority messaging dengan TTL,
            (4) TaskDecomposer = recursive splitting + role assignment,
            (5) ConsensusVoter = reputation-weighted voting
- Tiru:   Native Python asyncio, MAGNATRIX mesh integration,
          guardian-superAI safety layer, resource-aware task allocation
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable, Any, Set
from enum import Enum
from collections import defaultdict
import heapq


class AgentRoleType(Enum):
    SCOUT = "scout"
    ANALYST = "analyst"
    EXECUTOR = "executor"
    GUARDIAN = "guardian"
    RESEARCHER = "researcher"
    WRITER = "writer"
    OPS = "ops"
    ARCHITECT = "architect"


class MessagePriority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class SwarmState(Enum):
    ACTIVE = "active"
    HALTED = "halted"
    DEGRADED = "degraded"
    RECOVERING = "recovering"


@dataclass
class AgentRole:
    """Swarm agent role definition"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    role_type: AgentRoleType = AgentRoleType.EXECUTOR
    name: str = ""
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    system_prompt: str = ""
    # Runtime
    active: bool = True
    reputation: float = 1.0  # 0.0 - 2.0
    tasks_completed: int = 0
    tasks_failed: int = 0
    last_active: float = field(default_factory=time.time)
    # Memory
    short_term_memory: List[Dict] = field(default_factory=list)
    # Safety
    can_veto: bool = False  # Only guardian
    can_halt: bool = False  # Only guardian
    # MAGNATRIX
    mesh_channel: str = "swarm.agents"

    def get_effectiveness(self) -> float:
        total = self.tasks_completed + self.tasks_failed
        if total == 0:
            return self.reputation
        success_rate = self.tasks_completed / total
        return (success_rate + self.reputation) / 2

    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            "role_type": self.role_type.value,
            "effectiveness": self.get_effectiveness()
        }


@dataclass
class SwarmMessage:
    """Priority mesh message"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    priority: MessagePriority = MessagePriority.NORMAL
    sender_id: str = ""
    target_id: Optional[str] = ""
    message_type: str = ""  # SIGNAL, ANALYSIS, EXECUTE, HALT, etc.
    payload: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    ttl: int = 300  # seconds
    requires_ack: bool = False

    def is_expired(self) -> bool:
        return (time.time() - self.timestamp) > self.ttl

    def __lt__(self, other):
        return self.priority.value < other.priority.value


@dataclass
class SwarmTask:
    """Decomposed swarm task"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    parent_id: Optional[str] = None
    title: str = ""
    description: str = ""
    required_capabilities: List[str] = field(default_factory=list)
    assigned_agent_id: Optional[str] = None
    status: str = "pending"  # pending, assigned, in_progress, completed, failed
    result: Optional[Dict] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    subtasks: List['SwarmTask'] = field(default_factory=list)
    # Voting
    votes: Dict[str, str] = field(default_factory=dict)  # agent_id -> vote
    consensus_threshold: float = 0.6

    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            "subtasks": [s.to_dict() for s in self.subtasks]
        }


class MeshBroadcaster:
    """Priority-based mesh messaging system"""

    def __init__(self):
        self._queue: List[SwarmMessage] = []
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._delivered: Set[str] = set()

    def subscribe(self, message_type: str, handler: Callable):
        self._handlers[message_type].append(handler)

    def broadcast(self, message: SwarmMessage):
        heapq.heappush(self._queue, message)

    async def process_loop(self, max_per_cycle: int = 10):
        """Process messages by priority"""
        processed = 0
        while self._queue and processed < max_per_cycle:
            message = heapq.heappop(self._queue)
            if message.is_expired() or message.id in self._delivered:
                continue
            self._delivered.add(message.id)
            processed += 1

            # Deliver to handlers
            handlers = self._handlers.get(message.message_type, [])
            for handler in handlers:
                try:
                    await handler(message)
                except Exception:
                    pass

    def get_queue_depth(self) -> int:
        return len(self._queue)


class ConsensusVoter:
    """Reputation-weighted voting system"""

    def __init__(self, agents: Dict[str, AgentRole]):
        self.agents = agents

    def vote(self, task: SwarmTask, agent_id: str, vote: str) -> bool:
        """Cast vote, return True if consensus reached"""
        task.votes[agent_id] = vote
        return self._check_consensus(task)

    def _check_consensus(self, task: SwarmTask) -> bool:
        if not task.votes:
            return False

        # Weight by reputation
        total_weight = sum(self.agents[a].reputation for a in task.votes if a in self.agents)
        if total_weight == 0:
            return False

        # Count weighted votes
        vote_weights: Dict[str, float] = defaultdict(float)
        for agent_id, vote in task.votes.items():
            weight = self.agents.get(agent_id, AgentRole()).reputation
            vote_weights[vote] += weight

        # Check if any option reaches threshold
        for vote, weight in vote_weights.items():
            if weight / total_weight >= task.consensus_threshold:
                return True
        return False

    def get_consensus_result(self, task: SwarmTask) -> Optional[str]:
        """Get winning vote if consensus exists"""
        if not self._check_consensus(task):
            return None

        vote_weights: Dict[str, float] = defaultdict(float)
        for agent_id, vote in task.votes.items():
            weight = self.agents.get(agent_id, AgentRole()).reputation
            vote_weights[vote] += weight

        return max(vote_weights, key=vote_weights.get) if vote_weights else None


class TaskDecomposer:
    """Recursive task decomposition dengan role assignment"""

    def __init__(self, agents: Dict[str, AgentRole]):
        self.agents = agents

    async def decompose(self, task: SwarmTask, max_depth: int = 3) -> SwarmTask:
        """Decompose task into subtasks"""
        if max_depth <= 0:
            return task

        # Simple heuristic decomposition based on capabilities
        if "research" in task.required_capabilities:
            task.subtasks.append(SwarmTask(
                parent_id=task.id,
                title=f"Research: {task.title}",
                description="Gather information and sources",
                required_capabilities=["research", "analysis"]
            ))

        if "code" in task.required_capabilities or "implementation" in task.required_capabilities:
            task.subtasks.append(SwarmTask(
                parent_id=task.id,
                title=f"Implement: {task.title}",
                description="Write and test code",
                required_capabilities=["coding", "execution"]
            ))

        if "review" in task.required_capabilities:
            task.subtasks.append(SwarmTask(
                parent_id=task.id,
                title=f"Review: {task.title}",
                description="Review and validate",
                required_capabilities=["review", "guardian"]
            ))

        # Assign subtasks to best agents
        for subtask in task.subtasks:
            best_agent = self._find_best_agent(subtask)
            if best_agent:
                subtask.assigned_agent_id = best_agent

        return task

    def _find_best_agent(self, task: SwarmTask) -> Optional[str]:
        """Find best agent by capability overlap"""
        best_agent = None
        best_score = -1

        for agent_id, agent in self.agents.items():
            if not agent.active:
                continue
            score = self._capability_overlap(agent.capabilities, task.required_capabilities)
            score *= agent.get_effectiveness()
            if score > best_score:
                best_score = score
                best_agent = agent_id

        return best_agent

    def _capability_overlap(self, agent_caps: List[str], task_caps: List[str]) -> float:
        if not task_caps:
            return 1.0
        matches = sum(1 for c in task_caps if c in agent_caps)
        return matches / len(task_caps)


class SwarmEngine:
    """
    Main swarm orchestrator.
    Tiru STOA: swarm coordination dengan safety layers.
    """

    def __init__(self):
        self.agents: Dict[str, AgentRole] = {}
        self.mesh = MeshBroadcaster()
        self.consensus = ConsensusVoter(self.agents)
        self.decomposer = TaskDecomposer(self.agents)
        self.tasks: Dict[str, SwarmTask] = {}
        self.state = SwarmState.ACTIVE
        self._halt_reason: Optional[str] = None
        self._mesh_broadcast: Optional[Callable] = None

    def connect_mesh(self, broadcast_fn: Callable):
        self._mesh_broadcast = broadcast_fn

    def register_agent(self, agent: AgentRole) -> str:
        self.agents[agent.id] = agent
        self.consensus = ConsensusVoter(self.agents)
        self.decomposer = TaskDecomposer(self.agents)
        return agent.id

    def create_task(self, title: str, description: str,
                    capabilities: List[str] = None) -> SwarmTask:
        task = SwarmTask(
            title=title,
            description=description,
            required_capabilities=capabilities or []
        )
        self.tasks[task.id] = task
        return task

    async def execute_task(self, task: SwarmTask) -> SwarmTask:
        """Execute task dengan swarm coordination"""
        if self.state == SwarmState.HALTED:
            task.status = "halted"
            return task

        # Decompose
        task = await self.decomposer.decompose(task)

        # Execute subtasks
        for subtask in task.subtasks:
            if subtask.assigned_agent_id:
                await self._execute_subtask(subtask)

        # Guardian review jika ada
        guardian_votes = self._get_guardian_votes(task)
        if "reject" in guardian_votes:
            task.status = "rejected"
            return task

        task.status = "completed"
        task.completed_at = time.time()
        return task

    async def _execute_subtask(self, subtask: SwarmTask):
        """Execute single subtask"""
        subtask.status = "in_progress"
        subtask.started_at = time.time()

        # Simulate execution
        await asyncio.sleep(0.1)

        agent = self.agents.get(subtask.assigned_agent_id)
        if agent:
            agent.tasks_completed += 1
            agent.last_active = time.time()

        subtask.status = "completed"
        subtask.completed_at = time.time()
        subtask.result = {"status": "success", "agent": subtask.assigned_agent_id}

    def _get_guardian_votes(self, task: SwarmTask) -> List[str]:
        guardians = [a for a in self.agents.values() if a.role_type == AgentRoleType.GUARDIAN]
        return [task.votes.get(g.id, "approve") for g in guardians]

    def halt(self, reason: str = "emergency", agent_id: str = "") -> bool:
        """HALT swarm - hanya guardian atau conductor"""
        agent = self.agents.get(agent_id)
        if agent and not agent.can_halt:
            return False

        self.state = SwarmState.HALTED
        self._halt_reason = reason

        # Broadcast HALT
        self.mesh.broadcast(SwarmMessage(
            priority=MessagePriority.CRITICAL,
            message_type="HALT",
            sender_id=agent_id,
            payload={"reason": reason, "timestamp": time.time()}
        ))

        if self._mesh_broadcast:
            self._mesh_broadcast({
                "type": "SWARM_HALT",
                "channel": "swarm.control",
                "reason": reason,
                "agent_id": agent_id
            })

        return True

    def resume(self, agent_id: str = "") -> bool:
        agent = self.agents.get(agent_id)
        if agent and not agent.can_halt:
            return False

        self.state = SwarmState.ACTIVE
        self._halt_reason = None
        return True

    def get_status(self) -> Dict:
        return {
            "state": self.state.value,
            "agents": len(self.agents),
            "active_agents": sum(1 for a in self.agents.values() if a.active),
            "tasks": len(self.tasks),
            "pending_tasks": sum(1 for t in self.tasks.values() if t.status == "pending"),
            "completed_tasks": sum(1 for t in self.tasks.values() if t.status == "completed"),
            "mesh_queue_depth": self.mesh.get_queue_depth(),
            "halt_reason": self._halt_reason
        }


# ==================== DEMO ====================

if __name__ == "__main__":
    async def demo():
        engine = SwarmEngine()

        # Register agents
        for role in AgentRoleType:
            agent = AgentRole(
                role_type=role,
                name=f"{role.value.capitalize()}-01",
                capabilities=[role.value, "communication"],
                can_veto=(role == AgentRoleType.GUARDIAN),
                can_halt=(role == AgentRoleType.GUARDIAN)
            )
            engine.register_agent(agent)

        # Create task
        task = engine.create_task(
            "Build API endpoint",
            "Create REST API for user management",
            capabilities=["research", "coding", "review"]
        )

        result = await engine.execute_task(task)
        print(json.dumps(engine.get_status(), indent=2))
        print(f"Task completed: {result.status}")
        print(f"Subtasks: {len(result.subtasks)}")

    asyncio.run(demo())
