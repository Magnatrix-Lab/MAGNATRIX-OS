#!/usr/bin/env python3
"""
Swarm Intelligence / COLLECTIVE BRAIN for MAGNATRIX-OS
=====================================================
Multi-node federated intelligence, task distribution, P2P mesh,
voting consensus, and emergent swarm behavior. Pure stdlib.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations
import hashlib, json, random, threading, time, urllib.request, urllib.error
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple


class NodeState(Enum):
    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    DEGRADED = "degraded"
    OFFLINE = "offline"


class TaskPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class VoteType(Enum):
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


@dataclass
class SwarmNode:
    """Represents a node in the swarm."""
    node_id: str
    host: str
    port: int
    capabilities: List[str] = field(default_factory=list)
    state: NodeState = NodeState.IDLE
    load: float = 0.0
    last_heartbeat: float = field(default_factory=time.time)
    reputation: float = 1.0
    tasks_completed: int = 0
    tasks_failed: int = 0

    def is_alive(self, timeout: float = 30.0) -> bool:
        return (time.time() - self.last_heartbeat) < timeout

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["state"] = self.state.value
        return d


@dataclass
class SwarmTask:
    """Task distributed to swarm nodes."""
    task_id: str
    task_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    assigned_node: Optional[str] = None
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["priority"] = self.priority.value
        return d


@dataclass
class Vote:
    """A vote in the swarm consensus."""
    voter_id: str
    vote_type: VoteType
    proposal_id: str
    weight: float = 1.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["vote_type"] = self.vote_type.value
        return d


@dataclass
class Proposal:
    """A proposal for swarm voting."""
    proposal_id: str
    proposer: str
    action: str
    target: str
    params: Dict[str, Any] = field(default_factory=dict)
    votes: List[Vote] = field(default_factory=list)
    status: str = "open"
    created_at: float = field(default_factory=time.time)
    threshold: float = 0.66

    def tally(self) -> Dict[str, float]:
        approve = sum(v.weight for v in self.votes if v.vote_type == VoteType.APPROVE)
        reject = sum(v.weight for v in self.votes if v.vote_type == VoteType.REJECT)
        abstain = sum(v.weight for v in self.votes if v.vote_type == VoteType.ABSTAIN)
        total = approve + reject + abstain
        if total == 0:
            return {"approve": 0.0, "reject": 0.0, "abstain": 0.0}
        return {
            "approve": approve / total,
            "reject": reject / total,
            "abstain": abstain / total,
        }

    def is_passed(self) -> bool:
        result = self.tally()
        return result["approve"] >= self.threshold

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["votes"] = [v.to_dict() for v in self.votes]
        return d


class NodeRegistry:
    """Manages all nodes in the swarm."""

    def __init__(self, node_id: str = "") -> None:
        self.my_id = node_id or f"node_{hash(str(time.time()))}"
        self.nodes: Dict[str, SwarmNode] = {}
        self._lock = threading.RLock()
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._running = False

    def register(self, node: SwarmNode) -> None:
        with self._lock:
            self.nodes[node.node_id] = node

    def unregister(self, node_id: str) -> None:
        with self._lock:
            self.nodes.pop(node_id, None)

    def get_node(self, node_id: str) -> Optional[SwarmNode]:
        with self._lock:
            return self.nodes.get(node_id)

    def get_alive_nodes(self) -> List[SwarmNode]:
        with self._lock:
            return [n for n in self.nodes.values() if n.is_alive()]

    def get_nodes_by_capability(self, capability: str) -> List[SwarmNode]:
        with self._lock:
            return [n for n in self.nodes.values() if n.is_alive() and capability in n.capabilities]

    def get_best_node(self, capability: str) -> Optional[SwarmNode]:
        candidates = self.get_nodes_by_capability(capability)
        if not candidates:
            return None
        return min(candidates, key=lambda n: n.load)

    def update_heartbeat(self, node_id: str) -> None:
        with self._lock:
            if node_id in self.nodes:
                self.nodes[node_id].last_heartbeat = time.time()

    def get_topology(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "my_id": self.my_id,
                "total_nodes": len(self.nodes),
                "alive_nodes": len(self.get_alive_nodes()),
                "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            }

    def start_heartbeat(self) -> None:
        self._running = True
        def _loop():
            while self._running:
                self._broadcast_heartbeat()
                time.sleep(10.0)
        self._heartbeat_thread = threading.Thread(target=_loop, daemon=True)
        self._heartbeat_thread.start()

    def stop_heartbeat(self) -> None:
        self._running = False

    def _broadcast_heartbeat(self) -> None:
        pass


class TaskDistributor:
    """Distributes tasks to swarm nodes."""

    def __init__(self, registry: NodeRegistry) -> None:
        self.registry = registry
        self.tasks: Dict[str, SwarmTask] = {}
        self._lock = threading.RLock()
        self._task_counter = 0

    def submit(self, task_type: str, payload: Dict[str, Any], priority: TaskPriority = TaskPriority.NORMAL) -> SwarmTask:
        with self._lock:
            self._task_counter += 1
            task_id = f"task_{self.registry.my_id}_{self._task_counter}_{int(time.time())}"
            task = SwarmTask(task_id=task_id, task_type=task_type, payload=payload, priority=priority)
            self.tasks[task_id] = task
            return task

    def assign(self, task_id: str) -> Optional[SwarmTask]:
        with self._lock:
            task = self.tasks.get(task_id)
            if not task or task.assigned_node:
                return task
            node = self.registry.get_best_node(task.task_type)
            if node:
                task.assigned_node = node.node_id
                task.status = "assigned"
                node.state = NodeState.BUSY
            return task

    def complete(self, task_id: str, result: Dict[str, Any]) -> Optional[SwarmTask]:
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return None
            task.status = "completed"
            task.completed_at = time.time()
            task.result = result
            if task.assigned_node:
                node = self.registry.get_node(task.assigned_node)
                if node:
                    node.state = NodeState.IDLE
                    node.tasks_completed += 1
                    node.load = max(0.0, node.load - 1.0)
            return task

    def fail(self, task_id: str, error: str) -> Optional[SwarmTask]:
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return None
            task.retry_count += 1
            if task.retry_count >= task.max_retries:
                task.status = "failed"
                if task.assigned_node:
                    node = self.registry.get_node(task.assigned_node)
                    if node:
                        node.tasks_failed += 1
                        node.reputation = max(0.0, node.reputation - 0.1)
            else:
                task.assigned_node = None
                task.status = "pending"
            return task

    def get_pending(self) -> List[SwarmTask]:
        with self._lock:
            return [t for t in self.tasks.values() if t.status == "pending"]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self.tasks)
            completed = sum(1 for t in self.tasks.values() if t.status == "completed")
            failed = sum(1 for t in self.tasks.values() if t.status == "failed")
            pending = sum(1 for t in self.tasks.values() if t.status == "pending")
            return {
                "total": total,
                "completed": completed,
                "failed": failed,
                "pending": pending,
                "success_rate": completed / total if total > 0 else 0.0,
            }


class ConsensusEngine:
    """Swarm consensus via weighted voting."""

    def __init__(self, registry: NodeRegistry) -> None:
        self.registry = registry
        self.proposals: Dict[str, Proposal] = {}
        self._lock = threading.RLock()
        self._proposal_counter = 0

    def propose(self, proposer: str, action: str, target: str, params: Optional[Dict[str, Any]] = None, threshold: float = 0.66) -> Proposal:
        with self._lock:
            self._proposal_counter += 1
            pid = f"prop_{proposer}_{self._proposal_counter}_{int(time.time())}"
            proposal = Proposal(
                proposal_id=pid, proposer=proposer, action=action,
                target=target, params=params or {}, threshold=threshold,
            )
            self.proposals[pid] = proposal
            return proposal

    def vote(self, proposal_id: str, voter_id: str, vote_type: VoteType, weight: Optional[float] = None) -> bool:
        with self._lock:
            proposal = self.proposals.get(proposal_id)
            if not proposal or proposal.status != "open":
                return False
            node = self.registry.get_node(voter_id)
            if not node:
                return False
            w = weight if weight is not None else node.reputation
            proposal.votes.append(Vote(voter_id=voter_id, vote_type=vote_type, proposal_id=proposal_id, weight=w))
            return True

    def close_proposal(self, proposal_id: str) -> Optional[Proposal]:
        with self._lock:
            proposal = self.proposals.get(proposal_id)
            if not proposal:
                return None
            proposal.status = "passed" if proposal.is_passed() else "rejected"
            return proposal

    def get_proposals(self, status: Optional[str] = None) -> List[Proposal]:
        with self._lock:
            if status is None:
                return list(self.proposals.values())
            return [p for p in self.proposals.values() if p.status == status]

    def get_consensus_rate(self) -> float:
        with self._lock:
            if not self.proposals:
                return 0.0
            passed = sum(1 for p in self.proposals.values() if p.status == "passed")
            return passed / len(self.proposals)


class EmergentBehaviorDetector:
    """Detects emergent patterns in swarm behavior."""

    def __init__(self, window_size: int = 100) -> None:
        self.window_size = window_size
        self.behavior_log: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def record(self, event_type: str, data: Dict[str, Any]) -> None:
        with self._lock:
            self.behavior_log.append({"type": event_type, "data": data, "timestamp": time.time()})
            if len(self.behavior_log) > self.window_size:
                self.behavior_log = self.behavior_log[-self.window_size:]

    def detect_patterns(self) -> List[Dict[str, Any]]:
        with self._lock:
            if len(self.behavior_log) < 10:
                return []
            patterns = []
            # Detect load imbalance
            loads = {}
            for entry in self.behavior_log:
                if entry["type"] == "node_load":
                    node_id = entry["data"].get("node_id")
                    if node_id:
                        loads[node_id] = entry["data"].get("load", 0.0)
            if loads:
                avg_load = sum(loads.values()) / len(loads)
                overloaded = [n for n, l in loads.items() if l > avg_load * 2]
                underutilized = [n for n, l in loads.items() if l < avg_load * 0.5]
                if overloaded or underutilized:
                    patterns.append({
                        "pattern": "load_imbalance",
                        "overloaded": overloaded,
                        "underutilized": underutilized,
                        "avg_load": avg_load,
                    })
            # Detect consensus failure
            consensus_events = [e for e in self.behavior_log if e["type"] == "consensus"]
            if len(consensus_events) >= 3:
                failures = sum(1 for e in consensus_events if e["data"].get("status") == "rejected")
                if failures / len(consensus_events) > 0.5:
                    patterns.append({
                        "pattern": "consensus_failure",
                        "failure_rate": failures / len(consensus_events),
                        "recent_events": len(consensus_events),
                    })
            # Detect emergent cooperation
            task_events = [e for e in self.behavior_log if e["type"] == "task_complete"]
            if len(task_events) >= 5:
                cooperative = sum(1 for e in task_events if e["data"].get("nodes_involved", 1) > 1)
                if cooperative / len(task_events) > 0.5:
                    patterns.append({
                        "pattern": "emergent_cooperation",
                        "cooperation_rate": cooperative / len(task_events),
                    })
            return patterns

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_events": len(self.behavior_log),
                "patterns_detected": len(self.detect_patterns()),
                "window_size": self.window_size,
            }


class SwarmIntelligence:
    """Top-level COLLECTIVE BRAIN orchestrator."""

    def __init__(self, node_id: str = "") -> None:
        self.registry = NodeRegistry(node_id)
        self.distributor = TaskDistributor(self.registry)
        self.consensus = ConsensusEngine(self.registry)
        self.emergent = EmergentBehaviorDetector()
        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None

    def join(self, node: SwarmNode) -> None:
        self.registry.register(node)

    def leave(self, node_id: str) -> None:
        self.registry.unregister(node_id)

    def submit_task(self, task_type: str, payload: Dict[str, Any], priority: TaskPriority = TaskPriority.NORMAL) -> str:
        task = self.distributor.submit(task_type, payload, priority)
        self.distributor.assign(task.task_id)
        return task.task_id

    def propose(self, action: str, target: str, params: Optional[Dict[str, Any]] = None) -> str:
        proposal = self.consensus.propose(self.registry.my_id, action, target, params)
        return proposal.proposal_id

    def vote(self, proposal_id: str, vote_type: VoteType) -> bool:
        return self.consensus.vote(proposal_id, self.registry.my_id, vote_type)

    def start(self) -> None:
        self._running = True
        self.registry.start_heartbeat()
        def _scheduler():
            while self._running:
                for task in self.distributor.get_pending():
                    self.distributor.assign(task.task_id)
                time.sleep(1.0)
        self._scheduler_thread = threading.Thread(target=_scheduler, daemon=True)
        self._scheduler_thread.start()

    def stop(self) -> None:
        self._running = False
        self.registry.stop_heartbeat()

    def status(self) -> Dict[str, Any]:
        return {
            "my_id": self.registry.my_id,
            "running": self._running,
            "nodes": self.registry.get_topology(),
            "tasks": self.distributor.get_stats(),
            "consensus_rate": self.consensus.get_consensus_rate(),
            "emergent_patterns": self.emergent.detect_patterns(),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.status()
