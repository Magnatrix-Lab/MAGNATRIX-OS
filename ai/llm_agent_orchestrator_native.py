"""Multi-Agent Orchestrator — Agent discovery, task delegation, swarm coordination.

Modul ini menyediakan:
- AgentRegistry untuk agent discovery dan capability matching
- TaskPlanner untuk task decomposition dan assignment
- SwarmCoordinator untuk multi-agent coordination
- CommunicationBus untuk inter-agent messaging
- ResultAggregator untuk merging agent outputs
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
    DEGRADED = auto()


class TaskStatus(Enum):
    PENDING = auto()
    ASSIGNED = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class AgentCapability:
    """Capability yang dimiliki agent."""
    name: str
    skill_level: float = 1.0  # 0.0 - 10.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Agent:
    """Single agent dalam swarm."""
    agent_id: str
    name: str
    capabilities: List[AgentCapability]
    status: AgentStatus = AgentStatus.IDLE
    current_task: Optional[str] = None
    max_concurrent: int = 1
    active_tasks: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_heartbeat: float = field(default_factory=time.time)

    def has_capability(self, cap_name: str, min_level: float = 0.0) -> bool:
        for cap in self.capabilities:
            if cap.name == cap_name and cap.skill_level >= min_level:
                return True
        return False

    def is_available(self) -> bool:
        return self.status == AgentStatus.IDLE and self.active_tasks < self.max_concurrent


@dataclass
class Task:
    """Single task dalam sistem."""
    task_id: str
    description: str
    required_capabilities: List[str]
    priority: int = 5  # 1-10, higher = more important
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Message:
    """Inter-agent message."""
    message_id: str
    from_agent: str
    to_agent: str
    message_type: str  # request, response, broadcast, heartbeat
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)


class AgentRegistry:
    """Register dan discover agents."""

    def __init__(self):
        self._agents: Dict[str, Agent] = {}

    def register(self, agent: Agent) -> Agent:
        self._agents[agent.agent_id] = agent
        return agent

    def unregister(self, agent_id: str) -> bool:
        return self._agents.pop(agent_id, None) is not None

    def get(self, agent_id: str) -> Optional[Agent]:
        return self._agents.get(agent_id)

    def find_by_capability(self, cap_name: str, min_level: float = 0.0, available_only: bool = True) -> List[Agent]:
        results = [a for a in self._agents.values() if a.has_capability(cap_name, min_level)]
        if available_only:
            results = [a for a in results if a.is_available()]
        # Sort by skill level descending
        results.sort(key=lambda a: max((c.skill_level for c in a.capabilities if c.name == cap_name), default=0), reverse=True)
        return results

    def list_all(self) -> List[Agent]:
        return list(self._agents.values())

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total": len(self._agents),
            "idle": sum(1 for a in self._agents.values() if a.status == AgentStatus.IDLE),
            "busy": sum(1 for a in self._agents.values() if a.status == AgentStatus.BUSY),
            "offline": sum(1 for a in self._agents.values() if a.status == AgentStatus.OFFLINE),
        }

    def heartbeat(self, agent_id: str) -> bool:
        agent = self._agents.get(agent_id)
        if agent:
            agent.last_heartbeat = time.time()
            return True
        return False

    def check_stale(self, threshold: float = 60.0) -> List[str]:
        stale = []
        now = time.time()
        for agent_id, agent in self._agents.items():
            if now - agent.last_heartbeat > threshold:
                agent.status = AgentStatus.OFFLINE
                stale.append(agent_id)
        return stale


class TaskPlanner:
    """Plan dan decompose tasks."""

    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self._tasks: Dict[str, Task] = {}
        self._task_queue: List[Task] = []

    def create_task(self, description: str, required_caps: List[str], priority: int = 5, metadata: Optional[Dict[str, Any]] = None) -> Task:
        task = Task(
            task_id=str(uuid.uuid4())[:12],
            description=description,
            required_capabilities=required_caps,
            priority=priority,
            metadata=metadata or {}
        )
        self._tasks[task.task_id] = task
        self._task_queue.append(task)
        self._task_queue.sort(key=lambda t: -t.priority)
        return task

    def assign_task(self, task_id: str, agent_id: Optional[str] = None) -> Optional[Task]:
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.PENDING:
            return None
        if agent_id:
            agent = self.registry.get(agent_id)
        else:
            # Find best agent
            candidates = []
            for cap in task.required_capabilities:
                candidates.extend(self.registry.find_by_capability(cap))
            # Pick agent with most matching capabilities
            if candidates:
                agent = max(candidates, key=lambda a: sum(1 for c in task.required_capabilities if a.has_capability(c)))
            else:
                agent = None
        if not agent or not agent.is_available():
            return None
        task.assigned_to = agent.agent_id
        task.status = TaskStatus.ASSIGNED
        task.started_at = time.time()
        agent.status = AgentStatus.BUSY
        agent.current_task = task.task_id
        agent.active_tasks += 1
        self._task_queue = [t for t in self._task_queue if t.task_id != task_id]
        return task

    def complete_task(self, task_id: str, result: Any) -> Optional[Task]:
        task = self._tasks.get(task_id)
        if not task:
            return None
        task.status = TaskStatus.COMPLETED
        task.completed_at = time.time()
        task.result = result
        if task.assigned_to:
            agent = self.registry.get(task.assigned_to)
            if agent:
                agent.active_tasks = max(0, agent.active_tasks - 1)
                if agent.active_tasks == 0:
                    agent.status = AgentStatus.IDLE
                    agent.current_task = None
        return task

    def fail_task(self, task_id: str, error: str) -> Optional[Task]:
        task = self._tasks.get(task_id)
        if not task:
            return None
        task.status = TaskStatus.FAILED
        task.error = error
        if task.assigned_to:
            agent = self.registry.get(task.assigned_to)
            if agent:
                agent.active_tasks = max(0, agent.active_tasks - 1)
                if agent.active_tasks == 0:
                    agent.status = AgentStatus.IDLE
                    agent.current_task = None
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def get_pending(self) -> List[Task]:
        return [t for t in self._tasks.values() if t.status == TaskStatus.PENDING]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total": len(self._tasks),
            "pending": sum(1 for t in self._tasks.values() if t.status == TaskStatus.PENDING),
            "running": sum(1 for t in self._tasks.values() if t.status == TaskStatus.RUNNING),
            "completed": sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED),
            "failed": sum(1 for t in self._tasks.values() if t.status == TaskStatus.FAILED),
        }


class CommunicationBus:
    """Inter-agent communication channel."""

    def __init__(self):
        self._messages: List[Message] = []
        self._handlers: Dict[str, List[Callable[[Message], None]]] = {}

    def send(self, message: Message) -> None:
        self._messages.append(message)
        # Deliver to handlers
        handlers = self._handlers.get(message.to_agent, [])
        for handler in handlers:
            try:
                handler(message)
            except Exception:
                pass
        # Broadcast handlers
        if message.message_type == "broadcast":
            for agent_id, handlers in self._handlers.items():
                if agent_id != message.from_agent:
                    for handler in handlers:
                        try:
                            handler(message)
                        except Exception:
                            pass

    def broadcast(self, from_agent: str, payload: Dict[str, Any]) -> Message:
        msg = Message(
            message_id=str(uuid.uuid4())[:12],
            from_agent=from_agent,
            to_agent="*",
            message_type="broadcast",
            payload=payload
        )
        self.send(msg)
        return msg

    def on_message(self, agent_id: str, handler: Callable[[Message], None]) -> None:
        self._handlers.setdefault(agent_id, []).append(handler)

    def get_messages(self, agent_id: Optional[str] = None, limit: int = 50) -> List[Message]:
        msgs = self._messages
        if agent_id:
            msgs = [m for m in msgs if m.to_agent == agent_id or m.to_agent == "*" or m.from_agent == agent_id]
        return msgs[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_messages": len(self._messages),
            "subscribers": len(self._handlers)
        }


class SwarmCoordinator:
    """Coordinate swarm of agents untuk complex tasks."""

    def __init__(self, registry: AgentRegistry, planner: TaskPlanner, bus: CommunicationBus):
        self.registry = registry
        self.planner = planner
        self.bus = bus
        self._swarm_tasks: Dict[str, List[str]] = {}  # swarm_id -> task_ids

    def create_swarm_task(self, description: str, subtasks: List[Tuple[str, List[str], int]]) -> Tuple[str, List[Task]]:
        """Create a swarm task dengan subtasks. Returns (swarm_id, tasks)."""
        swarm_id = str(uuid.uuid4())[:12]
        tasks = []
        for sub_desc, caps, priority in subtasks:
            task = self.planner.create_task(sub_desc, caps, priority, {"swarm_id": swarm_id})
            tasks.append(task)
        self._swarm_tasks[swarm_id] = [t.task_id for t in tasks]
        return swarm_id, tasks

    def assign_swarm(self, swarm_id: str) -> List[Task]:
        """Assign all tasks dalam swarm ke agents."""
        task_ids = self._swarm_tasks.get(swarm_id, [])
        assigned = []
        for tid in task_ids:
            task = self.planner.assign_task(tid)
            if task:
                assigned.append(task)
        return assigned

    def execute_swarm(self, swarm_id: str, task_fn: Callable[[Task], Any]) -> Dict[str, Any]:
        """Execute all tasks in swarm."""
        task_ids = self._swarm_tasks.get(swarm_id, [])
        results = {}
        for tid in task_ids:
            task = self.planner.get_task(tid)
            if task and task.status == TaskStatus.ASSIGNED:
                try:
                    task.status = TaskStatus.RUNNING
                    result = task_fn(task)
                    self.planner.complete_task(tid, result)
                    results[tid] = result
                except Exception as e:
                    self.planner.fail_task(tid, str(e))
                    results[tid] = None
        return results

    def get_swarm_status(self, swarm_id: str) -> Dict[str, Any]:
        task_ids = self._swarm_tasks.get(swarm_id, [])
        tasks = [self.planner.get_task(tid) for tid in task_ids]
        return {
            "swarm_id": swarm_id,
            "total_tasks": len(tasks),
            "completed": sum(1 for t in tasks if t and t.status == TaskStatus.COMPLETED),
            "failed": sum(1 for t in tasks if t and t.status == TaskStatus.FAILED),
            "pending": sum(1 for t in tasks if t and t.status == TaskStatus.PENDING),
            "running": sum(1 for t in tasks if t and t.status == TaskStatus.RUNNING),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "active_swarms": len(self._swarm_tasks),
            "total_tasks": sum(len(tids) for tids in self._swarm_tasks.values()),
        }


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("MULTI-AGENT ORCHESTRATOR DEMO")
    print("=" * 70)

    # Setup
    registry = AgentRegistry()
    planner = TaskPlanner(registry)
    bus = CommunicationBus()
    coordinator = SwarmCoordinator(registry, planner, bus)

    # 1. Register agents
    print("\n[1] Register Agents")
    registry.register(Agent("agent-1", "Researcher", [AgentCapability("research", 9.0), AgentCapability("summarize", 7.0)]))
    registry.register(Agent("agent-2", "Coder", [AgentCapability("coding", 9.5), AgentCapability("debug", 8.0)]))
    registry.register(Agent("agent-3", "Writer", [AgentCapability("writing", 8.5), AgentCapability("summarize", 6.0)]))
    registry.register(Agent("agent-4", "Analyzer", [AgentCapability("analysis", 8.0), AgentCapability("research", 7.0)]))
    print(f"  Registered {len(registry.list_all())} agents")
    print(f"  Stats: {registry.get_stats()}")

    # 2. Find by capability
    print("\n[2] Find by Capability")
    coders = registry.find_by_capability("coding")
    print(f"  Coders: {[a.name for a in coders]}")
    researchers = registry.find_by_capability("research", min_level=8.0)
    print(f"  Researchers (level >= 8): {[a.name for a in researchers]}")

    # 3. Create dan assign tasks
    print("\n[3] Task Planning")
    t1 = planner.create_task("Research Python async patterns", ["research"], priority=8)
    t2 = planner.create_task("Write code example", ["coding"], priority=7)
    t3 = planner.create_task("Summarize findings", ["summarize"], priority=5)
    print(f"  Created tasks: {t1.task_id}, {t2.task_id}, {t3.task_id}")

    assigned1 = planner.assign_task(t1.task_id)
    print(f"  Task 1 assigned to: {assigned1.assigned_to if assigned1 else 'None'}")
    assigned2 = planner.assign_task(t2.task_id)
    print(f"  Task 2 assigned to: {assigned2.assigned_to if assigned2 else 'None'}")
    assigned3 = planner.assign_task(t3.task_id)
    print(f"  Task 3 assigned to: {assigned3.assigned_to if assigned3 else 'None'}")

    # 4. Complete tasks
    print("\n[4] Task Completion")
    planner.complete_task(t1.task_id, {"research": "asyncio is powerful"})
    planner.complete_task(t2.task_id, {"code": "async def main(): ..."})
    planner.complete_task(t3.task_id, {"summary": "Async patterns in Python"})
    print(f"  Task stats: {planner.get_stats()}")

    # 5. Communication bus
    print("\n[5] Communication Bus")
    received = []
    bus.on_message("agent-2", lambda msg: received.append(msg.payload))
    bus.send(Message("m1", "agent-1", "agent-2", "request", {"task": "help needed"}))
    bus.broadcast("agent-1", {"announcement": "new task available"})
    print(f"  Messages to agent-2: {len(received)}")
    print(f"  Bus stats: {bus.get_stats()}")

    # 6. Swarm coordination
    print("\n[6] Swarm Coordination")
    swarm_id, tasks = coordinator.create_swarm_task(
        "Build AI pipeline",
        [
            ("Research models", ["research"], 8),
            ("Implement core", ["coding"], 9),
            ("Write documentation", ["writing"], 6),
            ("Performance analysis", ["analysis"], 7),
        ]
    )
    print(f"  Swarm {swarm_id}: {len(tasks)} tasks")
    coordinator.assign_swarm(swarm_id)

    def execute_task(task: Task) -> Any:
        return {"status": "done", "agent": task.assigned_to, "desc": task.description[:30]}

    results = coordinator.execute_swarm(swarm_id, execute_task)
    print(f"  Swarm status: {coordinator.get_swarm_status(swarm_id)}")
    print(f"  Results: {len(results)} tasks completed")

    # 7. Heartbeat dan stale detection
    print("\n[7] Heartbeat & Stale Detection")
    registry.heartbeat("agent-1")
    stale = registry.check_stale(threshold=0.1)  # Very short threshold for demo
    print(f"  Stale agents detected: {len(stale)}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
