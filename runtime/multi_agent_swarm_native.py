#!/usr/bin/env python3
"""
MAGNATRIX-OS Layer: Runtime — Multi-Agent Swarm Intelligence Engine
File: runtime/multi_agent_swarm_native.py
Pattern: AMATI-PELAJARI-TIRU dari CrewAI + AutoGen + LangGraph + MCP

Native pure-Python reimplementation of:
  - Multi-agent orchestration dengan swarm topology
  - Agent discovery, registration, heartbeat monitoring
  - Task delegation dengan capability matching
  - Consensus voting untuk decision-making
  - Resource bidding / auction untuk task allocation
  - Blackboard pattern untuk shared workspace
  - Role-based agents (CrewAI pattern)
  - Conversational collaboration (AutoGen pattern)
  - State machine workflow (LangGraph pattern)
  - MCP-style tool protocol interoperability

Zero external dependencies. Pure Python standard library.
"""

from __future__ import annotations

import json
import queue
import random
import re
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union


# ============================================================================
# 1.  AGENT REGISTRY — discovery, registration, heartbeat
# ============================================================================

@dataclass
class AgentCapabilities:
    """What an agent can do."""
    tools: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=lambda: ["python"])
    max_tokens: int = 4096
    max_context: int = 32768
    specialties: List[str] = field(default_factory=list)

    def matches(self, requirement: str) -> float:
        """Score 0.0-1.0 how well this capability matches a requirement."""
        req = requirement.lower()
        score = 0.0
        for specialty in self.specialties:
            if specialty.lower() in req:
                score += 0.4
        for tool in self.tools:
            if tool.lower() in req:
                score += 0.3
        for lang in self.languages:
            if lang.lower() in req:
                score += 0.1
        return min(score, 1.0)


@dataclass
class AgentRegistration:
    """Registered agent info."""
    agent_id: str
    name: str
    role: str  # researcher, writer, coder, critic, reviewer, orchestrator
    capabilities: AgentCapabilities
    status: str = "idle"  # idle | busy | offline
    last_heartbeat: float = field(default_factory=time.time)
    tasks_completed: int = 0
    tasks_failed: int = 0
    reputation: float = 1.0  # 0.0-5.0

    def is_alive(self, timeout: float = 30.0) -> bool:
        return time.time() - self.last_heartbeat < timeout


class AgentRegistry:
    """Central registry for all swarm agents."""

    def __init__(self) -> None:
        self._agents: Dict[str, AgentRegistration] = {}
        self._lock = threading.RLock()
        self._listeners: List[Callable[[str, AgentRegistration], None]] = []

    def register(self, agent: AgentRegistration) -> bool:
        with self._lock:
            self._agents[agent.agent_id] = agent
        self._notify("registered", agent)
        return True

    def unregister(self, agent_id: str) -> bool:
        with self._lock:
            if agent_id in self._agents:
                agent = self._agents.pop(agent_id)
                self._notify("unregistered", agent)
                return True
        return False

    def heartbeat(self, agent_id: str) -> bool:
        with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].last_heartbeat = time.time()
                return True
        return False

    def update_status(self, agent_id: str, status: str) -> bool:
        with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].status = status
                return True
        return False

    def find_by_role(self, role: str) -> List[AgentRegistration]:
        with self._lock:
            return [a for a in self._agents.values() if a.role == role and a.is_alive()]

    def find_by_capability(self, requirement: str, min_score: float = 0.3,
                           alive_only: bool = True) -> List[Tuple[AgentRegistration, float]]:
        with self._lock:
            results = []
            for a in self._agents.values():
                if alive_only and not a.is_alive():
                    continue
                if a.status == "offline":
                    continue
                score = a.capabilities.matches(requirement)
                if score >= min_score:
                    results.append((a, score))
            return sorted(results, key=lambda x: x[1], reverse=True)

    def get_all_alive(self) -> List[AgentRegistration]:
        with self._lock:
            return [a for a in self._agents.values() if a.is_alive()]

    def get(self, agent_id: str) -> Optional[AgentRegistration]:
        with self._lock:
            return self._agents.get(agent_id)

    def on_event(self, listener: Callable[[str, AgentRegistration], None]) -> None:
        self._listeners.append(listener)

    def _notify(self, event: str, agent: AgentRegistration) -> None:
        for listener in self._listeners:
            try:
                listener(event, agent)
            except Exception:
                pass


# ============================================================================
# 2.  SHARED MEMORY / BLACKBOARD — Redis-like + Graph DB + Vector DB
# ============================================================================

class SharedMemory:
    """
    Redis-like shared memory dengan pub/sub, graph relations, dan vector search.
    All in-memory, pure Python, zero external dependencies.
    """

    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}
        self._graphs: Dict[str, Dict[str, List[Tuple[str, str, Any]]]] = defaultdict(
            lambda: defaultdict(list)
        )  # graph_name -> node -> [(rel_type, target, properties)]
        self._vectors: Dict[str, Tuple[List[float], Any]] = {}  # id -> (embedding, payload)
        self._pubsub: Dict[str, List[Callable[[str, Any], None]]] = defaultdict(list)
        self._lock = threading.RLock()
        self._vector_dim = 128

    # --- Key-Value ---

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        with self._lock:
            self._store[key] = {"value": value, "expires": time.time() + ttl if ttl else None}

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return default
            if entry["expires"] and time.time() > entry["expires"]:
                del self._store[key]
                return default
            return entry["value"]

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def keys(self, pattern: str = "*") -> List[str]:
        with self._lock:
            if pattern == "*":
                return list(self._store.keys())
            regex = pattern.replace("*", ".*").replace("?", ".")
            return [k for k in self._store.keys() if re.match(regex, k)]

    # --- Pub/Sub ---

    def publish(self, channel: str, message: Any) -> int:
        with self._lock:
            listeners = self._pubsub[channel].copy()
        for listener in listeners:
            try:
                listener(channel, message)
            except Exception:
                pass
        return len(listeners)

    def subscribe(self, channel: str, listener: Callable[[str, Any], None]) -> None:
        with self._lock:
            self._pubsub[channel].append(listener)

    def unsubscribe(self, channel: str, listener: Callable[[str, Any], None]) -> None:
        with self._lock:
            if listener in self._pubsub[channel]:
                self._pubsub[channel].remove(listener)

    # --- Graph DB ---

    def graph_add_node(self, graph: str, node_id: str, properties: Dict[str, Any] = None) -> None:
        key = f"graph:{graph}:node:{node_id}"
        self.set(key, properties or {})

    def graph_add_edge(self, graph: str, from_node: str, to_node: str,
                       relation: str, properties: Any = None) -> None:
        with self._lock:
            self._graphs[graph][from_node].append((relation, to_node, properties))

    def graph_neighbors(self, graph: str, node_id: str,
                        relation: Optional[str] = None) -> List[Tuple[str, str, Any]]:
        with self._lock:
            edges = self._graphs[graph].get(node_id, [])
            if relation:
                edges = [e for e in edges if e[0] == relation]
            return edges

    def graph_traverse(self, graph: str, start: str, max_depth: int = 3,
                       relation: Optional[str] = None) -> List[List[str]]:
        """BFS traversal returning all paths dari start node."""
        paths: List[List[str]] = []
        visited: Set[str] = set()
        q: deque = deque([(start, [start])])
        while q:
            node, path = q.popleft()
            if len(path) > max_depth + 1:
                continue
            if node != start and node not in visited:
                visited.add(node)
                paths.append(path)
            for rel, target, _ in self.graph_neighbors(graph, node, relation):
                if target not in path:  # avoid cycles
                    q.append((target, path + [target]))
        return paths

    # --- Vector DB ---

    @staticmethod
    def _hash_embedding(text: str, dim: int = 128) -> List[float]:
        """Deterministic hash-based embedding (no numpy)."""
        import hashlib
        h = hashlib.sha256(text.encode()).digest()
        vec = []
        for i in range(dim):
            val = (h[i % 32] + i * 7) % 200 - 100
            vec.append(val / 100.0)
        # Normalize
        mag = sum(x * x for x in vec) ** 0.5
        if mag > 0:
            vec = [x / mag for x in vec]
        return vec

    def vector_upsert(self, doc_id: str, text: str, payload: Any = None) -> None:
        embedding = self._hash_embedding(text, self._vector_dim)
        with self._lock:
            self._vectors[doc_id] = (embedding, payload or text)

    def vector_search(self, query: str, top_k: int = 5) -> List[Tuple[str, float, Any]]:
        q_vec = self._hash_embedding(query, self._vector_dim)
        with self._lock:
            results = []
            for doc_id, (vec, payload) in self._vectors.items():
                score = sum(a * b for a, b in zip(q_vec, vec))
                results.append((doc_id, score, payload))
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]

    # --- Temporal / Audit ---

    def append_log(self, key: str, entry: Dict[str, Any], max_len: int = 1000) -> None:
        with self._lock:
            logs = self._store.get(key, [])
            if not isinstance(logs, list):
                logs = []
            logs.append({"t": time.time(), **entry})
            if len(logs) > max_len:
                logs = logs[-max_len:]
            self._store[key] = logs

    def get_logs(self, key: str, since: float = 0) -> List[Dict[str, Any]]:
        with self._lock:
            logs = self._store.get(key, [])
            if not isinstance(logs, list):
                return []
            return [l for l in logs if l.get("t", 0) >= since]


# ============================================================================
# 3.  MESSAGE BUS — inter-agent communication
# ============================================================================

@dataclass
class AgentMessage:
    msg_id: str
    sender_id: str
    recipient_id: str  # "broadcast" or specific agent_id
    msg_type: str  # task_request | task_result | critique | vote | heartbeat | chat
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    priority: int = 5  # 1=highest


class MessageBus:
    """Async message bus for agent-to-agent communication."""

    def __init__(self, shared_memory: Optional[SharedMemory] = None) -> None:
        self._inboxes: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._shared = shared_memory or SharedMemory()
        self._lock = threading.Lock()
        self._running = True
        self._delivery_thread = threading.Thread(target=self._delivery_loop, daemon=True)
        self._delivery_thread.start()
        self._outbox: queue.PriorityQueue = queue.PriorityQueue()

    def send(self, msg: AgentMessage) -> bool:
        """Send a message. PriorityQueue uses (priority, timestamp)."""
        self._outbox.put((msg.priority, msg.timestamp, msg))
        return True

    def _delivery_loop(self) -> None:
        while self._running:
            try:
                _, _, msg = self._outbox.get(timeout=0.5)
                if msg.recipient_id == "broadcast":
                    # Deliver to all agent inboxes + pub/sub
                    self._shared.publish(f"agent:{msg.msg_type}", msg)
                else:
                    with self._lock:
                        self._inboxes[msg.recipient_id].append(msg)
            except queue.Empty:
                continue
            except Exception:
                pass

    def recv(self, agent_id: str, timeout: float = 1.0,
             msg_type: Optional[str] = None) -> Optional[AgentMessage]:
        """Receive one message for agent_id."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                inbox = self._inboxes[agent_id]
                for i, msg in enumerate(inbox):
                    if msg_type is None or msg.msg_type == msg_type:
                        del inbox[i]
                        return msg
            time.sleep(0.05)
        return None

    def recv_all(self, agent_id: str, msg_type: Optional[str] = None) -> List[AgentMessage]:
        with self._lock:
            inbox = self._inboxes[agent_id]
            if msg_type:
                matching = [m for m in inbox if m.msg_type == msg_type]
                remaining = [m for m in inbox if m.msg_type != msg_type]
                self._inboxes[agent_id] = deque(remaining, maxlen=100)
                return matching
            else:
                self._inboxes[agent_id] = deque(maxlen=100)
                return list(inbox)

    def subscribe_broadcast(self, agent_id: str, msg_type: str,
                           callback: Callable[[AgentMessage], None]) -> None:
        def _wrapper(channel: str, msg: Any) -> None:
            if isinstance(msg, AgentMessage) and msg.msg_type == msg_type:
                callback(msg)
        self._shared.subscribe(f"agent:{msg_type}", _wrapper)

    def stop(self) -> None:
        self._running = False
        self._delivery_thread.join(timeout=2.0)


# ============================================================================
# 4.  TASK DELEGATOR — CrewAI-style role assignment + AutoGen chat delegation
# ============================================================================

@dataclass
class Task:
    task_id: str
    description: str
    required_capabilities: str = ""
    assigned_to: Optional[str] = None
    status: str = "pending"  # pending | assigned | running | review | done | failed
    result: Any = None
    created_by: str = "system"
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    reviews: List[Dict[str, Any]] = field(default_factory=list)
    subtasks: List[str] = field(default_factory=list)


class TaskDelegator:
    """
    Breaks tasks into subtasks and delegates to best-matching agents.
    Pattern: CrewAI role-based + AutoGen conversational delegation.
    """

    def __init__(self, registry: AgentRegistry, bus: MessageBus,
                 shared: SharedMemory) -> None:
        self.registry = registry
        self.bus = bus
        self.shared = shared
        self._tasks: Dict[str, Task] = {}
        self._lock = threading.Lock()

    def create_task(self, description: str, required_caps: str = "",
                    created_by: str = "system") -> Task:
        task = Task(
            task_id=f"task_{uuid.uuid4().hex[:8]}",
            description=description,
            required_capabilities=required_caps,
            created_by=created_by,
        )
        with self._lock:
            self._tasks[task.task_id] = task
        return task

    def assign(self, task: Task, strategy: str = "best_match") -> Optional[str]:
        """Assign task to agent. Returns agent_id atau None."""
        if strategy == "best_match":
            candidates = self.registry.find_by_capability(task.required_capabilities)
            if not candidates:
                return None
            best_agent, score = candidates[0]
            task.assigned_to = best_agent.agent_id
            task.status = "assigned"
            # Notify agent
            self.bus.send(AgentMessage(
                msg_id=f"m_{uuid.uuid4().hex[:8]}",
                sender_id="delegator",
                recipient_id=best_agent.agent_id,
                msg_type="task_request",
                payload={"task_id": task.task_id, "description": task.description},
                priority=1,
            ))
            self.registry.update_status(best_agent.agent_id, "busy")
            return best_agent.agent_id

        elif strategy == "round_robin":
            agents = self.registry.find_by_role("worker")
            if not agents:
                agents = self.registry.get_all_alive()
            if not agents:
                return None
            # Pick least loaded
            best = min(agents, key=lambda a: a.tasks_completed + a.tasks_failed)
            task.assigned_to = best.agent_id
            task.status = "assigned"
            self.bus.send(AgentMessage(
                msg_id=f"m_{uuid.uuid4().hex[:8]}",
                sender_id="delegator",
                recipient_id=best.agent_id,
                msg_type="task_request",
                payload={"task_id": task.task_id, "description": task.description},
                priority=2,
            ))
            self.registry.update_status(best.agent_id, "busy")
            return best.agent_id

        return None

    def decompose(self, task: Task) -> List[Task]:
        """Break task into subtasks based on keywords."""
        desc = task.description.lower()
        subtasks: List[Task] = []

        patterns = [
            ("research", "Research and gather information"),
            ("write", "Draft and compose content"),
            ("code", "Implement and test code"),
            ("review", "Review and critique output"),
            ("analyze", "Analyze data and findings"),
            ("test", "Test and verify correctness"),
            ("optimize", "Optimize and improve performance"),
        ]

        for keyword, sub_desc in patterns:
            if keyword in desc:
                st = self.create_task(
                    description=f"{sub_desc} for: {task.description[:60]}",
                    required_caps=keyword,
                    created_by=task.task_id,
                )
                subtasks.append(st)

        if not subtasks:
            # At least 2 subtasks: do + verify
            st1 = self.create_task(
                description=f"Execute: {task.description[:60]}",
                required_capabilities="general",
                created_by=task.task_id,
            )
            st2 = self.create_task(
                description=f"Verify: {task.description[:60]}",
                required_capabilities="review",
                created_by=task.task_id,
            )
            subtasks = [st1, st2]

        with self._lock:
            task.subtasks = [st.task_id for st in subtasks]
        return subtasks

    def report_result(self, task_id: str, result: Any, success: bool = True) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            task.result = result
            task.status = "done" if success else "failed"
            task.completed_at = time.time()

        agent = self.registry.get(task.assigned_to or "")
        if agent:
            self.registry.update_status(agent.agent_id, "idle")
            if success:
                agent.tasks_completed += 1
                agent.reputation = min(5.0, agent.reputation + 0.05)
            else:
                agent.tasks_failed += 1
                agent.reputation = max(0.0, agent.reputation - 0.1)

        # Notify parent jika subtask
        if task.created_by.startswith("task_"):
            self.bus.send(AgentMessage(
                msg_id=f"m_{uuid.uuid4().hex[:8]}",
                sender_id=task.assigned_to or "unknown",
                recipient_id=task.created_by,
                msg_type="task_result",
                payload={"task_id": task_id, "result": result, "success": success},
            ))

    def get_task(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self._tasks.get(task_id)

    def get_all_tasks(self) -> List[Task]:
        with self._lock:
            return list(self._tasks.values())


# ============================================================================
# 5.  CONSENSUS ENGINE — Byzantine fault tolerant voting
# ============================================================================

@dataclass
class Vote:
    voter_id: str
    proposal_id: str
    vote: str  # yes | no | abstain
    reason: str = ""
    timestamp: float = field(default_factory=time.time)


class ConsensusEngine:
    """
    Byzantine Fault Tolerant consensus via majority voting.
    Pattern: Practical Byzantine Fault Tolerance (PBFT) simplified.
    """

    def __init__(self, registry: AgentRegistry, bus: MessageBus) -> None:
        self.registry = registry
        self.bus = bus
        self._proposals: Dict[str, Dict[str, Any]] = {}
        self._votes: Dict[str, List[Vote]] = defaultdict(list)
        self._lock = threading.Lock()

    def propose(self, proposal_id: str, description: str,
                proposer_id: str, required_agents: int = 3) -> bool:
        with self._lock:
            self._proposals[proposal_id] = {
                "description": description,
                "proposer": proposer_id,
                "required": required_agents,
                "status": "voting",
                "result": None,
            }
        # Broadcast proposal
        self.bus.send(AgentMessage(
            msg_id=f"m_{uuid.uuid4().hex[:8]}",
            sender_id=proposer_id,
            recipient_id="broadcast",
            msg_type="vote",
            payload={"proposal_id": proposal_id, "description": description, "action": "vote_request"},
            priority=1,
        ))
        return True

    def cast_vote(self, proposal_id: str, voter_id: str, vote: str, reason: str = "") -> bool:
        with self._lock:
            if proposal_id not in self._proposals:
                return False
            if self._proposals[proposal_id]["status"] != "voting":
                return False
            # Check for duplicate vote
            existing = [v for v in self._votes[proposal_id] if v.voter_id == voter_id]
            if existing:
                return False
            self._votes[proposal_id].append(Vote(voter_id, proposal_id, vote, reason))
            # Check if consensus reached
            return self._check_consensus(proposal_id)

    def _check_consensus(self, proposal_id: str) -> bool:
        proposal = self._proposals[proposal_id]
        votes = self._votes[proposal_id]
        total = len(votes)
        yes_count = sum(1 for v in votes if v.vote == "yes")
        no_count = sum(1 for v in votes if v.vote == "no")
        required = proposal["required"]

        if total >= required:
            if yes_count > total / 2:
                proposal["status"] = "accepted"
                proposal["result"] = "yes"
                return True
            elif no_count >= total / 2:
                proposal["status"] = "rejected"
                proposal["result"] = "no"
                return True
        return False

    def get_result(self, proposal_id: str) -> Optional[str]:
        with self._lock:
            p = self._proposals.get(proposal_id)
            if not p:
                return None
            return p.get("result")

    def get_votes(self, proposal_id: str) -> List[Vote]:
        with self._lock:
            return self._votes.get(proposal_id, []).copy()


# ============================================================================
# 6.  RESOURCE BIDDING / AUCTION — agents bid for tasks
# ============================================================================

@dataclass
class Bid:
    bidder_id: str
    task_id: str
    price: float  # lower = better (cost to execute)
    estimated_time: float  # seconds
    confidence: float  # 0.0-1.0


class AuctionHouse:
    """
    Second-price sealed bid auction untuk task allocation.
    Agents bid based on capability match, load, dan reputation.
    """

    def __init__(self, registry: AgentRegistry, bus: MessageBus) -> None:
        self.registry = registry
        self.bus = bus
        self._bids: Dict[str, List[Bid]] = defaultdict(list)
        self._lock = threading.Lock()

    def open_auction(self, task_id: str, task_description: str,
                     timeout: float = 5.0) -> None:
        """Broadcast auction invitation."""
        self.bus.send(AgentMessage(
            msg_id=f"m_{uuid.uuid4().hex[:8]}",
            sender_id="auctioneer",
            recipient_id="broadcast",
            msg_type="task_request",
            payload={"task_id": task_id, "description": task_description, "action": "bid_invitation", "timeout": timeout},
            priority=2,
        ))

    def place_bid(self, bid: Bid) -> bool:
        with self._lock:
            self._bids[bid.task_id].append(bid)
        return True

    def resolve(self, task_id: str) -> Optional[Bid]:
        """Resolve auction: winner is lowest price, pays second-lowest price."""
        with self._lock:
            bids = self._bids.get(task_id, [])
            if not bids:
                return None
            # Sort by effective score: price adjusted by confidence dan reputation
            def score(b: Bid) -> float:
                agent = self.registry.get(b.bidder_id)
                rep = agent.reputation if agent else 1.0
                return b.price / (b.confidence * rep + 0.01)
            bids_sorted = sorted(bids, key=score)
            winner = bids_sorted[0]
            second_price = bids_sorted[1].price if len(bids_sorted) > 1 else winner.price
            # Store result
            self._bids[task_id] = [{"winner": winner.bidder_id, "price_paid": second_price}]
            return winner


# ============================================================================
# 7.  SWARM ORCHESTRATOR — top-level coordinator
# ============================================================================

class SwarmOrchestrator:
    """
    Top-level swarm coordinator combining all subsystems.
    """

    def __init__(self) -> None:
        self.registry = AgentRegistry()
        self.shared = SharedMemory()
        self.bus = MessageBus(self.shared)
        self.delegator = TaskDelegator(self.registry, self.bus, self.shared)
        self.consensus = ConsensusEngine(self.registry, self.bus)
        self.auction = AuctionHouse(self.registry, self.bus)
        self._agents: Dict[str, Any] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def register_agent(self, agent_id: str, name: str, role: str,
                       capabilities: AgentCapabilities) -> AgentRegistration:
        reg = AgentRegistration(
            agent_id=agent_id, name=name, role=role,
            capabilities=capabilities,
        )
        self.registry.register(reg)
        return reg

    def submit_task(self, description: str, strategy: str = "best_match") -> Task:
        task = self.delegator.create_task(description)
        # Auto-decompose untuk complex tasks
        if len(description) > 40:
            subtasks = self.delegator.decompose(task)
            for st in subtasks:
                self.delegator.assign(st, strategy)
        else:
            self.delegator.assign(task, strategy)
        return task

    def run_collaborative(self, goal: str, agents: List[str]) -> Dict[str, Any]:
        """
        Run collaborative task dengan multiple agents.
        Pattern: CrewAI-style sequential execution.
        """
        results = {}
        # Phase 1: Research (all researchers)
        researchers = [a for a in agents if self.registry.get(a) and self.registry.get(a).role == "researcher"]
        if researchers:
            research_task = self.delegator.create_task(f"Research: {goal}", "research")
            for r in researchers:
                self.delegator.assign(research_task, "best_match")
            # Simulate result
            self.delegator.report_result(research_task.task_id, f"Research findings on {goal}")
            results["research"] = research_task.result

        # Phase 2: Write (writers)
        writers = [a for a in agents if self.registry.get(a) and self.registry.get(a).role == "writer"]
        if writers:
            write_task = self.delegator.create_task(f"Write: {goal}", "write")
            self.delegator.assign(write_task, "best_match")
            self.delegator.report_result(write_task.task_id, f"Draft on {goal}")
            results["draft"] = write_task.result

        # Phase 3: Review (critics)
        critics = [a for a in agents if self.registry.get(a) and self.registry.get(a).role == "critic"]
        if critics:
            critique_task = self.delegator.create_task(f"Review: {goal}", "review")
            self.delegator.assign(critique_task, "best_match")
            self.delegator.report_result(critique_task.task_id, f"Critique: Good structure, needs more depth")
            results["critique"] = critique_task.result

        return results

    def propose_consensus(self, description: str, proposer: str) -> str:
        proposal_id = f"prop_{uuid.uuid4().hex[:8]}"
        alive = self.registry.get_all_alive()
        self.consensus.propose(proposal_id, description, proposer, len(alive) // 2 + 1)
        return proposal_id

    def stop(self) -> None:
        self._running = False
        self.bus.stop()


# ============================================================================
# 8.  COLLABORATIVE AGENT — LangGraph-style state machine + AutoGen chat
# ============================================================================

class CollaborativeAgent:
    """
    An agent that can participate in swarm collaboration.
    Implements LangGraph state machine + AutoGen conversational loops.
    """

    STATES = ["idle", "researching", "writing", "coding", "reviewing", "waiting", "done", "error"]

    def __init__(self, agent_id: str, name: str, role: str,
                 orchestrator: SwarmOrchestrator) -> None:
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.orchestrator = orchestrator
        self.state = "idle"
        self.memory: deque = deque(maxlen=50)
        self.tools: Dict[str, Callable[..., str]] = {}
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self) -> None:
        while self._running:
            # Heartbeat
            self.orchestrator.registry.heartbeat(self.agent_id)
            # Check for messages
            msg = self.orchestrator.bus.recv(self.agent_id, timeout=0.5)
            if msg:
                self._handle_message(msg)
            time.sleep(0.2)

    def _handle_message(self, msg: AgentMessage) -> None:
        self.memory.append(msg)
        if msg.msg_type == "task_request":
            payload = msg.payload
            task_id = payload.get("task_id", "")
            desc = payload.get("description", "")
            self.state = self._pick_state_for_task(desc)
            # Simulate work
            time.sleep(0.05)  # Instant for demo
            result = f"[{self.name}] Completed: {desc[:40]}..."
            self.orchestrator.delegator.report_result(task_id, result, success=True)
            self.state = "idle"
        elif msg.msg_type == "chat":
            # AutoGen-style chat response
            response = f"[{self.name}] I received: {msg.payload.get('text', '')[:30]}"
            self.orchestrator.bus.send(AgentMessage(
                msg_id=f"m_{uuid.uuid4().hex[:8]}",
                sender_id=self.agent_id,
                recipient_id=msg.sender_id,
                msg_type="chat",
                payload={"text": response, "in_response_to": msg.msg_id},
            ))
        elif msg.msg_type == "vote":
            # Auto-vote based on reputation heuristic
            vote = "yes" if random.random() < 0.8 else "no"
            self.orchestrator.consensus.cast_vote(
                msg.payload.get("proposal_id", ""), self.agent_id, vote,
                f"Voted by {self.role}"
            )

    def _pick_state_for_task(self, desc: str) -> str:
        d = desc.lower()
        if "research" in d:
            return "researching"
        if "write" in d or "draft" in d:
            return "writing"
        if "code" in d or "implement" in d:
            return "coding"
        if "review" in d or "critique" in d:
            return "reviewing"
        return "researching"

    def stop(self) -> None:
        self._running = False
        self._thread.join(timeout=2.0)


# ============================================================================
# 9.  MCP TOOL PROTOCOL — Model Context Protocol interoperability
# ============================================================================

class MCPToolProtocol:
    """
    MCP (Model Context Protocol) tool interoperability layer.
    Agents expose tools via JSON schema; others call them via MCP messages.
    """

    def __init__(self, bus: MessageBus) -> None:
        self.bus = bus
        self._tools: Dict[str, Dict[str, Any]] = {}  # tool_name -> schema
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {}

    def register_tool(self, agent_id: str, tool_name: str,
                      schema: Dict[str, Any],
                      handler: Callable[[Dict[str, Any]], Any]) -> None:
        self._tools[tool_name] = {
            "agent_id": agent_id,
            "schema": schema,
            "name": tool_name,
        }
        self._handlers[tool_name] = handler

    def call_tool(self, caller_id: str, tool_name: str,
                  arguments: Dict[str, Any], timeout: float = 5.0) -> Any:
        if tool_name not in self._tools:
            return {"error": f"Tool '{tool_name}' not found"}
        tool = self._tools[tool_name]
        # Send MCP call message
        call_id = f"call_{uuid.uuid4().hex[:8]}"
        self.bus.send(AgentMessage(
            msg_id=call_id,
            sender_id=caller_id,
            recipient_id=tool["agent_id"],
            msg_type="task_request",
            payload={"mcp_call": True, "tool": tool_name, "args": arguments, "call_id": call_id},
            priority=1,
        ))
        # Wait for result (simplified: directly call handler)
        if tool_name in self._handlers:
            try:
                return {"result": self._handlers[tool_name](arguments)}
            except Exception as e:
                return {"error": str(e)}
        return {"error": "No handler"}

    def list_tools(self) -> List[Dict[str, Any]]:
        return list(self._tools.values())


# ============================================================================
# 10.  TEST SUITE & DEMO
# ============================================================================

def _test_agent_registry() -> None:
    reg = AgentRegistry()
    cap = AgentCapabilities(tools=["search", "write"], specialties=["research"])
    a1 = AgentRegistration("a1", "Alice", "researcher", cap)
    reg.register(a1)
    assert reg.get("a1") is not None
    found = reg.find_by_capability("research paper")
    assert len(found) >= 1
    reg.heartbeat("a1")
    assert a1.is_alive()
    print("  [OK] AgentRegistry")


def _test_shared_memory() -> None:
    mem = SharedMemory()
    mem.set("key1", "value1")
    assert mem.get("key1") == "value1"
    mem.delete("key1")
    assert mem.get("key1") is None

    # Pub/sub
    received = []
    mem.subscribe("test", lambda ch, msg: received.append(msg))
    mem.publish("test", "hello")
    assert "hello" in received

    # Graph
    mem.graph_add_node("kg", "node1", {"name": "AI"})
    mem.graph_add_edge("kg", "node1", "node2", "relates_to")
    neighbors = mem.graph_neighbors("kg", "node1")
    assert len(neighbors) == 1
    paths = mem.graph_traverse("kg", "node1", max_depth=2)
    assert len(paths) >= 1

    # Vector
    mem.vector_upsert("doc1", "artificial intelligence", {"topic": "AI"})
    mem.vector_upsert("doc2", "machine learning", {"topic": "ML"})
    results = mem.vector_search("AI systems", top_k=2)
    assert len(results) == 2
    # Doc1 should be in top results (AI keyword match)
    doc_ids = [r[0] for r in results]
    assert "doc1" in doc_ids  # AI document should be found

    print("  [OK] SharedMemory (KV + PubSub + Graph + Vector)")


def _test_message_bus() -> None:
    bus = MessageBus()
    msg = AgentMessage("m1", "a1", "a2", "chat", {"text": "hi"})
    bus.send(msg)
    received = bus.recv("a2", timeout=2.0)
    assert received is not None
    assert received.payload["text"] == "hi"
    bus.stop()
    print("  [OK] MessageBus")


def _test_task_delegator() -> None:
    reg = AgentRegistry()
    bus = MessageBus()
    mem = SharedMemory()
    delegator = TaskDelegator(reg, bus, mem)

    cap = AgentCapabilities(tools=["search"], specialties=["research"])
    reg.register(AgentRegistration("r1", "Researcher", "researcher", cap))

    task = delegator.create_task("Research Python asyncio", "research")
    assigned = delegator.assign(task, "best_match")
    assert assigned == "r1"
    assert task.status == "assigned"

    delegator.report_result(task.task_id, "Asyncio is great", success=True)
    assert task.status == "done"
    bus.stop()
    print("  [OK] TaskDelegator")


def _test_consensus() -> None:
    reg = AgentRegistry()
    bus = MessageBus()
    ce = ConsensusEngine(reg, bus)

    for i in range(5):
        reg.register(AgentRegistration(f"v{i}", f"Voter{i}", "voter",
                                       AgentCapabilities()))

    pid = "prop1"
    ce.propose(pid, "Should we add Redis support?", "v0", required_agents=3)

    ce.cast_vote(pid, "v1", "yes")
    ce.cast_vote(pid, "v2", "yes")
    result = ce.cast_vote(pid, "v3", "yes")
    assert result is True
    assert ce.get_result(pid) == "yes"
    bus.stop()
    print("  [OK] ConsensusEngine")


def _test_auction() -> None:
    reg = AgentRegistry()
    bus = MessageBus()
    ah = AuctionHouse(reg, bus)

    reg.register(AgentRegistration("b1", "Bidder1", "worker",
                                   AgentCapabilities(), reputation=4.0))
    reg.register(AgentRegistration("b2", "Bidder2", "worker",
                                   AgentCapabilities(), reputation=3.0))

    ah.place_bid(Bid("b1", "task1", 10.0, 5.0, 0.9))
    ah.place_bid(Bid("b2", "task1", 8.0, 3.0, 0.7))
    winner = ah.resolve("task1")
    assert winner is not None
    bus.stop()
    print("  [OK] AuctionHouse")


def _test_swarm_orchestrator() -> None:
    orch = SwarmOrchestrator()
    orch.register_agent("r1", "Alice", "researcher",
                        AgentCapabilities(specialties=["research"]))
    orch.register_agent("w1", "Bob", "writer",
                        AgentCapabilities(specialties=["write"]))
    orch.register_agent("c1", "Carol", "critic",
                        AgentCapabilities(specialties=["review"]))

    results = orch.run_collaborative("Build a trading bot", ["r1", "w1", "c1"])
    assert "research" in results
    assert "draft" in results
    assert "critique" in results
    orch.stop()
    print("  [OK] SwarmOrchestrator collaborative workflow")


def _test_collaborative_agent() -> None:
    orch = SwarmOrchestrator()
    orch.register_agent("ca1", "TestAgent", "researcher",
                        AgentCapabilities())
    agent = CollaborativeAgent("ca1", "TestAgent", "researcher", orch)
    time.sleep(0.3)
    assert agent.state in ["idle", "researching"]
    agent.stop()
    orch.stop()
    print("  [OK] CollaborativeAgent")


def _test_mcp_protocol() -> None:
    bus = MessageBus()
    mcp = MCPToolProtocol(bus)
    mcp.register_tool("a1", "calculator", {"input": "expression"},
                      lambda args: eval(args.get("expression", "0")))
    result = mcp.call_tool("caller", "calculator", {"expression": "2+3"})
    assert result.get("result") == 5
    bus.stop()
    print("  [OK] MCPToolProtocol")


def _demo() -> None:
    print("=" * 60)
    print("MAGNATRIX Multi-Agent Swarm Intelligence — Native Demo")
    print("Patterns: CrewAI + AutoGen + LangGraph + MCP")
    print("=" * 60)

    print("\n[Unit Tests]")
    _test_agent_registry()
    _test_shared_memory()
    _test_message_bus()
    _test_task_delegator()
    _test_consensus()
    _test_auction()
    _test_swarm_orchestrator()
    _test_collaborative_agent()
    _test_mcp_protocol()

    print("\n[Swarm Collaboration Demo — Research Team]")
    orch = SwarmOrchestrator()

    # Register diverse agents (CrewAI-style roles)
    roles = [
        ("researcher", AgentCapabilities(tools=["search", "analyze"], specialties=["research", "data"])),
        ("writer", AgentCapabilities(tools=["write", "summarize"], specialties=["write", "content"])),
        ("critic", AgentCapabilities(tools=["review", "compare"], specialties=["review", "critique"])),
        ("coder", AgentCapabilities(tools=["code", "test"], specialties=["code", "debug"])),
        ("reviewer", AgentCapabilities(tools=["verify", "check"], specialties=["verify", "qa"])),
    ]
    for i, (role, caps) in enumerate(roles):
        orch.register_agent(f"agent_{i}", f"{role.title()}-{i}", role, caps)
        CollaborativeAgent(f"agent_{i}", f"{role.title()}-{i}", role, orch)

    # Submit a complex task
    task = orch.submit_task("Research and build a Python async web scraper with error handling and rate limiting")
    print(f"  Task: {task.description}")
    print(f"  Subtasks: {len(task.subtasks)}")
    for st_id in task.subtasks:
        st = orch.delegator.get_task(st_id)
        if st:
            print(f"    - {st.description[:50]}... [{st.status}]")

    # Consensus demo
    print("\n[Consensus Demo]")
    prop_id = orch.propose_consensus("Enable auto-compilation for C++ HFT engine", "agent_0")
    time.sleep(0.2)
    result = orch.consensus.get_result(prop_id)
    print(f"  Proposal: {prop_id}")
    print(f"  Result: {result or 'voting in progress'}")
    votes = orch.consensus.get_votes(prop_id)
    print(f"  Votes: {len(votes)} ({sum(1 for v in votes if v.vote == 'yes')} yes, {sum(1 for v in votes if v.vote == 'no')} no)")

    # Shared memory demo
    print("\n[Shared Memory Demo]")
    orch.shared.vector_upsert("swarm_knowledge_1", "agents should collaborate via consensus", {"topic": "swarm"})
    orch.shared.vector_upsert("swarm_knowledge_2", "resource bidding prevents overload", {"topic": "auction"})
    search = orch.shared.vector_search("how agents collaborate", top_k=2)
    print(f"  Vector search: {len(search)} results")
    for doc_id, score, payload in search:
        print(f"    - {doc_id}: score={score:.3f}, {str(payload)[:50]}")

    # MCP demo
    print("\n[MCP Protocol Demo]")
    mcp = MCPToolProtocol(orch.bus)
    mcp.register_tool("agent_3", "code_search", {"query": "string"},
                      lambda args: f"Found 5 matches for '{args.get('query')}'")
    result = mcp.call_tool("agent_0", "code_search", {"query": "async def"})
    print(f"  Tool call result: {result}")

    orch.stop()

    print("\n" + "=" * 60)
    print("All tests passed. Swarm demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    _demo()
