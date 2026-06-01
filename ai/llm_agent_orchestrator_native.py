"""Multi-Agent Orchestrator — Task delegation, agent coordination, and planning.

Modul ini menyediakan:
- AgentRegistry untuk manajemen agent dan capabilities
- TaskPlanner untuk dekomposisi task dan assignment
- AgentCoordinator untuk parallel execution dan result aggregation
- CommunicationBus untuk inter-agent messaging
- ConflictResolver untuk handling overlapping claims

Arsitektur: Orchestrator → Planner → Agents → Bus → Results
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


class TaskPriority(Enum):
    CRITICAL = 4
    HIGH = 3
    MEDIUM = 2
    LOW = 1
    BACKGROUND = 0


class TaskStatus(Enum):
    PENDING = auto()
    ASSIGNED = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class AgentCapability:
    """Capability that an agent can perform."""
    name: str
    description: str = ""
    score: float = 1.0  # proficiency 0-1
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Agent:
    """Registered agent in the orchestrator."""
    agent_id: str
    name: str
    capabilities: List[AgentCapability]
    status: AgentStatus = AgentStatus.IDLE
    max_concurrent: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    current_tasks: int = 0
    total_completed: int = 0
    total_failed: int = 0

    def can_handle(self, capability: str) -> bool:
        return any(c.name == capability for c in self.capabilities)

    def proficiency(self, capability: str) -> float:
        for c in self.capabilities:
            if c.name == capability:
                return c.score
        return 0.0


@dataclass
class SubTask:
    """Decomposed sub-task from a parent task."""
    subtask_id: str
    parent_id: str
    description: str
    required_capability: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: Optional[str] = None
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    dependencies: List[str] = field(default_factory=list)


@dataclass
class Task:
    """Top-level task submitted to the orchestrator."""
    task_id: str
    description: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    subtasks: List[SubTask] = field(default_factory=list)
    result: Any = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Message:
    """Inter-agent message."""
    msg_id: str
    from_agent: str
    to_agent: str
    msg_type: str  # request, response, broadcast, alert
    payload: Any
    timestamp: float = field(default_factory=time.time)


class AgentRegistry:
    """Register and discover agents with their capabilities."""

    def __init__(self):
        self._agents: Dict[str, Agent] = {}

    def register(self, agent: Agent) -> None:
        self._agents[agent.agent_id] = agent

    def unregister(self, agent_id: str) -> bool:
        return self._agents.pop(agent_id, None) is not None

    def get(self, agent_id: str) -> Optional[Agent]:
        return self._agents.get(agent_id)

    def find_by_capability(self, capability: str, min_proficiency: float = 0.0) -> List[Agent]:
        results = []
        for agent in self._agents.values():
            if agent.status == AgentStatus.OFFLINE:
                continue
            prof = agent.proficiency(capability)
            if prof >= min_proficiency and agent.can_handle(capability):
                results.append((prof, agent))
        results.sort(reverse=True, key=lambda x: x[0])
        return [a for _, a in results]

    def list_agents(self) -> List[Agent]:
        return list(self._agents.values())

    def update_status(self, agent_id: str, status: AgentStatus) -> bool:
        if agent_id in self._agents:
            self._agents[agent_id].status = status
            return True
        return False


class TaskPlanner:
    """Decompose tasks into subtasks and create execution plan."""

    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    def plan(self, task: Task) -> List[SubTask]:
        # Default planning: decompose into capability-based subtasks
        # In real impl, this would use LLM to decompose
        subtasks = []
        for i, cap in enumerate(task.metadata.get("required_capabilities", ["general"])):
            st = SubTask(
                subtask_id=f"{task.task_id}-st{i}",
                parent_id=task.task_id,
                description=f"Execute {cap} for: {task.description}",
                required_capability=cap,
                priority=task.priority,
                dependencies=[] if i == 0 else [f"{task.task_id}-st{i-1}"]
            )
            subtasks.append(st)
        return subtasks

    def assign(self, subtasks: List[SubTask]) -> List[SubTask]:
        for st in subtasks:
            if st.status != TaskStatus.PENDING:
                continue
            candidates = self.registry.find_by_capability(st.required_capability)
            # Pick best available (proficiency + load balanced)
            best = None
            best_score = -1.0
            for agent in candidates:
                if agent.status == AgentStatus.BUSY and agent.current_tasks >= agent.max_concurrent:
                    continue
                score = agent.proficiency(st.required_capability) - (agent.current_tasks * 0.1)
                if score > best_score:
                    best_score = score
                    best = agent
            if best:
                st.assigned_to = best.agent_id
                st.status = TaskStatus.ASSIGNED
                best.current_tasks += 1
        return subtasks


class CommunicationBus:
    """Pub/sub messaging between agents."""

    def __init__(self):
        self._messages: List[Message] = []
        self._handlers: Dict[str, List[Callable[[Message], None]]] = {}

    def send(self, msg: Message) -> None:
        self._messages.append(msg)
        for handler in self._handlers.get(msg.to_agent, []):
            try:
                handler(msg)
            except Exception:
                pass
        # Broadcast handlers
        for handler in self._handlers.get("*", []):
            try:
                handler(msg)
            except Exception:
                pass

    def broadcast(self, from_agent: str, msg_type: str, payload: Any) -> None:
        msg = Message(
            msg_id=str(uuid.uuid4())[:12],
            from_agent=from_agent,
            to_agent="*",
            msg_type=msg_type,
            payload=payload
        )
        self.send(msg)

    def on_message(self, agent_id: str, handler: Callable[[Message], None]) -> None:
        self._handlers.setdefault(agent_id, []).append(handler)

    def get_messages(self, agent_id: str, limit: int = 50) -> List[Message]:
        return [m for m in self._messages if m.to_agent == agent_id or m.to_agent == "*"][-limit:]


class AgentCoordinator:
    """Coordinate execution of subtasks across agents."""

    def __init__(self, registry: AgentRegistry, bus: CommunicationBus):
        self.registry = registry
        self.bus = bus
        self._tasks: Dict[str, Task] = {}
        self._results: Dict[str, Any] = {}

    def submit(self, task: Task) -> Task:
        planner = TaskPlanner(self.registry)
        task.subtasks = planner.plan(task)
        task.subtasks = planner.assign(task.subtasks)
        task.status = TaskStatus.RUNNING
        self._tasks[task.task_id] = task
        return task

    def execute(self, task_id: str, executor_fn: Optional[Callable[[SubTask], Any]] = None) -> Task:
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        executor_fn = executor_fn or self._default_executor

        # Execute in dependency order (simplified: assume sequential for now)
        completed = set()
        for st in sorted(task.subtasks, key=lambda x: len(x.dependencies)):
            # Wait for dependencies
            if not all(d in completed for d in st.dependencies):
                st.status = TaskStatus.FAILED
                st.error = "Dependencies not met"
                continue

            if st.status == TaskStatus.ASSIGNED and st.assigned_to:
                st.status = TaskStatus.RUNNING
                try:
                    result = executor_fn(st)
                    st.result = result
                    st.status = TaskStatus.COMPLETED
                    st.completed_at = time.time()
                    completed.add(st.subtask_id)
                    agent = self.registry.get(st.assigned_to)
                    if agent:
                        agent.current_tasks -= 1
                        agent.total_completed += 1
                    self.bus.send(Message(
                        msg_id=str(uuid.uuid4())[:12],
                        from_agent=st.assigned_to,
                        to_agent=task_id,
                        msg_type="subtask_complete",
                        payload={"subtask_id": st.subtask_id, "result": result}
                    ))
                except Exception as e:
                    st.status = TaskStatus.FAILED
                    st.error = str(e)
                    agent = self.registry.get(st.assigned_to)
                    if agent:
                        agent.current_tasks -= 1
                        agent.total_failed += 1

        # Aggregate results
        task.result = [st.result for st in task.subtasks if st.status == TaskStatus.COMPLETED]
        task.status = TaskStatus.COMPLETED if all(st.status == TaskStatus.COMPLETED for st in task.subtasks) else TaskStatus.FAILED
        task.completed_at = time.time()
        return task

    def _default_executor(self, subtask: SubTask) -> Any:
        # Simulated execution
        time.sleep(0.01)
        return f"Result of {subtask.description} by {subtask.assigned_to}"

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task and task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
            for st in task.subtasks:
                if st.status in (TaskStatus.PENDING, TaskStatus.ASSIGNED):
                    st.status = TaskStatus.CANCELLED
                    if st.assigned_to:
                        agent = self.registry.get(st.assigned_to)
                        if agent:
                            agent.current_tasks = max(0, agent.current_tasks - 1)
            task.status = TaskStatus.CANCELLED
            return True
        return False


class ConflictResolver:
    """Resolve conflicts between agents claiming the same task."""

    def __init__(self):
        self._rules: List[Callable[[Agent, Agent, SubTask], Optional[Agent]]] = []

    def add_rule(self, rule: Callable[[Agent, Agent, SubTask], Optional[Agent]]) -> None:
        self._rules.append(rule)

    def resolve(self, agent_a: Agent, agent_b: Agent, task: SubTask) -> Optional[Agent]:
        for rule in self._rules:
            winner = rule(agent_a, agent_b, task)
            if winner is not None:
                return winner
        # Default: higher proficiency wins
        return agent_a if agent_a.proficiency(task.required_capability) >= agent_b.proficiency(task.required_capability) else agent_b

    @staticmethod
    def default_rules() -> List[Callable[[Agent, Agent, SubTask], Optional[Agent]]]:
        def higher_proficiency(a: Agent, b: Agent, t: SubTask) -> Optional[Agent]:
            pa = a.proficiency(t.required_capability)
            pb = b.proficiency(t.required_capability)
            if pa > pb + 0.2:
                return a
            if pb > pa + 0.2:
                return b
            return None

        def less_busy(a: Agent, b: Agent, t: SubTask) -> Optional[Agent]:
            if a.current_tasks < b.current_tasks - 1:
                return a
            if b.current_tasks < a.current_tasks - 1:
                return b
            return None

        return [higher_proficiency, less_busy]


class MultiAgentOrchestrator:
    """End-to-end orchestrator combining all components."""

    def __init__(self):
        self.registry = AgentRegistry()
        self.bus = CommunicationBus()
        self.coordinator = AgentCoordinator(self.registry, self.bus)
        self.resolver = ConflictResolver()
        for rule in ConflictResolver.default_rules():
            self.resolver.add_rule(rule)

    def register_agent(self, agent: Agent) -> None:
        self.registry.register(agent)

    def create_task(self, description: str, priority: TaskPriority = TaskPriority.MEDIUM,
                    required_capabilities: Optional[List[str]] = None,
                    metadata: Optional[Dict[str, Any]] = None) -> Task:
        task = Task(
            task_id=str(uuid.uuid4())[:12],
            description=description,
            priority=priority,
            metadata=metadata or {}
        )
        task.metadata["required_capabilities"] = required_capabilities or ["general"]
        return task

    def run(self, task: Task, executor: Optional[Callable[[SubTask], Any]] = None) -> Task:
        self.coordinator.submit(task)
        return self.coordinator.execute(task.task_id, executor)

    def get_status(self) -> Dict[str, Any]:
        return {
            "agents": len(self.registry.list_agents()),
            "tasks": len(self.coordinator._tasks),
            "messages": len(self.bus._messages),
        }

    def export_report(self, path: str) -> None:
        report = {
            "agents": [{
                "id": a.agent_id,
                "name": a.name,
                "status": a.status.name,
                "capabilities": [c.name for c in a.capabilities],
                "completed": a.total_completed,
                "failed": a.total_failed
            } for a in self.registry.list_agents()],
            "tasks": [{
                "id": t.task_id,
                "description": t.description,
                "status": t.status.name,
                "subtasks_completed": sum(1 for st in t.subtasks if st.status == TaskStatus.COMPLETED),
                "subtasks_total": len(t.subtasks)
            } for t in self.coordinator._tasks.values()]
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("MULTI-AGENT ORCHESTRATOR DEMO")
    print("=" * 70)

    orch = MultiAgentOrchestrator()

    # 1. Register agents
    print("\n[1] Register Agents")
    agents = [
        Agent("agent-1", "CodeWriter", [
            AgentCapability("code", "Write Python code", 0.95),
            AgentCapability("review", "Review code", 0.7)
        ], max_concurrent=2),
        Agent("agent-2", "Researcher", [
            AgentCapability("research", "Research topics", 0.9),
            AgentCapability("summarize", "Summarize content", 0.85)
        ], max_concurrent=1),
        Agent("agent-3", "CodeReviewer", [
            AgentCapability("review", "Review code", 0.95),
            AgentCapability("test", "Write tests", 0.8)
        ], max_concurrent=2),
    ]
    for a in agents:
        orch.register_agent(a)
    print(f"  Registered {len(agents)} agents")

    # 2. Create task
    print("\n[2] Create Task")
    task = orch.create_task(
        "Build a Python API with documentation",
        priority=TaskPriority.HIGH,
        required_capabilities=["code", "review", "research"]
    )
    print(f"  Task: {task.task_id}")
    print(f"  Subtasks planned: {len(orch.coordinator.submit(task).subtasks)}")

    # 3. Execute
    print("\n[3] Execute Task")
    result = orch.run(task)
    print(f"  Status: {result.status.name}")
    print(f"  Completed: {sum(1 for st in result.subtasks if st.status == TaskStatus.COMPLETED)}/{len(result.subtasks)}")
    for st in result.subtasks:
        print(f"    [{st.status.name}] {st.subtask_id} -> {st.assigned_to} -> {str(st.result)[:50]}")

    # 4. Conflict resolution
    print("\n[4] Conflict Resolution")
    a1 = orch.registry.get("agent-1")
    a3 = orch.registry.get("agent-3")
    st = SubTask("test-1", "task-1", "Review code", "review")
    winner = orch.resolver.resolve(a1, a3, st)
    print(f"  Conflict between {a1.name} (prof={a1.proficiency('review')}) and {a3.name} (prof={a3.proficiency('review')})")
    print(f"  Winner: {winner.name}")

    # 5. Communication bus
    print("\n[5] Communication Bus")
    received = []
    orch.bus.on_message("agent-2", lambda m: received.append(m))
    orch.bus.broadcast("agent-1", "alert", {"msg": "New task available"})
    print(f"  Messages sent: {len(orch.bus._messages)}")
    print(f"  Agent-2 received: {len(received)}")

    # 6. Status report
    print("\n[6] Status Report")
    print(f"  {orch.get_status()}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
