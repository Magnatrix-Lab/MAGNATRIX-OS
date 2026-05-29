#!/usr/bin/env python3
"""
MAGNATRIX-OS | Layer 5 — Agent Orchestrator
Native multi-agent orchestrator with planning, consensus, and role assignment.
- Hierarchical task decomposition (HTN-like)
- Agent role registry (specialist, worker, critic)
- Consensus voting for critical decisions
- Dynamic agent pool scaling
"""
import json, time, threading, random, os, sys, hashlib
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum


class AgentRole(Enum):
    SPECIALIST = "specialist"
    WORKER = "worker"
    CRITIC = "critic"
    ORCHESTRATOR = "orchestrator"
    MONITOR = "monitor"


@dataclass
class Agent:
    id: str
    role: str
    capabilities: List[str] = field(default_factory=list)
    load: float = 0.0
    last_heartbeat: float = 0.0
    healthy: bool = True

    def __post_init__(self):
        if self.last_heartbeat == 0.0:
            self.last_heartbeat = time.time()


@dataclass
class SubTask:
    id: str
    description: str
    required_caps: List[str] = field(default_factory=list)
    assigned_to: str = ""
    status: str = "pending"
    result: Any = None


class RoleRegistry:
    """Register agents by role and capabilities."""

    def __init__(self):
        self._agents: Dict[str, Agent] = {}
        self._by_role: Dict[str, List[str]] = defaultdict(list)
        self._by_cap: Dict[str, List[str]] = defaultdict(list)
        self._lock = threading.Lock()

    def register(self, agent: Agent):
        with self._lock:
            self._agents[agent.id] = agent
            self._by_role[agent.role].append(agent.id)
            for cap in agent.capabilities:
                self._by_cap[cap].append(agent.id)

    def deregister(self, agent_id: str):
        with self._lock:
            if agent_id not in self._agents:
                return
            agent = self._agents[agent_id]
            self._by_role[agent.role] = [a for a in self._by_role[agent.role] if a != agent_id]
            for cap in agent.capabilities:
                self._by_cap[cap] = [a for a in self._by_cap[cap] if a != agent_id]
            del self._agents[agent_id]

    def find_by_capability(self, caps: List[str], max_load: float = 0.8) -> Optional[str]:
        with self._lock:
            candidates = set(self._by_cap.get(caps[0], []))
            for cap in caps[1:]:
                candidates &= set(self._by_cap.get(cap, []))
            valid = [a for a in candidates if self._agents[a].load < max_load and self._agents[a].healthy]
            if not valid:
                return None
            return min(valid, key=lambda a: self._agents[a].load)

    def update_load(self, agent_id: str, delta: float):
        with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].load = max(0.0, min(1.0, self._agents[agent_id].load + delta))

    def heartbeat(self, agent_id: str):
        with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].last_heartbeat = time.time()

    def prune_stale(self, max_age: float = 10.0):
        now = time.time()
        with self._lock:
            stale = [aid for aid, a in self._agents.items() if now - a.last_heartbeat > max_age]
            for aid in stale:
                self._agents[aid].healthy = False


class TaskDecomposer:
    """Hierarchical Task Network (HTN) decomposition."""

    def __init__(self):
        self._methods: Dict[str, List[List[str]]] = defaultdict(list)
        self._primitives: Set[str] = set()

    def add_method(self, task: str, subtasks: List[str]):
        self._methods[task].append(subtasks)

    def add_primitive(self, task: str):
        self._primitives.add(task)

    def decompose(self, task: str, depth: int = 0) -> List[str]:
        if depth > 10:
            return [task]
        if task in self._primitives:
            return [task]
        methods = self._methods.get(task, [])
        if not methods:
            return [task]
        # Choose first method
        chosen = methods[0]
        result = []
        for sub in chosen:
            result.extend(self.decompose(sub, depth + 1))
        return result

    def build_plan(self, high_level_task: str) -> List[SubTask]:
        steps = self.decompose(high_level_task)
        return [SubTask(id=f"{high_level_task}-{i}", description=s, required_caps=[s]) for i, s in enumerate(steps)]


class ConsensusVoter:
    """Byzantine-fault-tolerant consensus voting (simplified)."""

    def __init__(self, threshold: float = 0.66):
        self.threshold = threshold
        self._votes: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._lock = threading.Lock()

    def vote(self, proposal_id: str, agent_id: str, vote: Any):
        with self._lock:
            self._votes[proposal_id][agent_id] = vote

    def tally(self, proposal_id: str) -> Tuple[bool, Any]:
        with self._lock:
            votes = self._votes.get(proposal_id, {})
        if not votes:
            return False, None
        # Count by value
        counts = defaultdict(int)
        for v in votes.values():
            counts[str(v)] += 1
        total = len(votes)
        winner, count = max(counts.items(), key=lambda x: x[1])
        if count / total >= self.threshold:
            return True, winner
        return False, None

    def reset(self, proposal_id: str):
        with self._lock:
            if proposal_id in self._votes:
                del self._votes[proposal_id]


class DynamicPool:
    """Dynamic scaling of agent pool based on queue depth."""

    def __init__(self, min_agents: int = 2, max_agents: int = 20):
        self.min_agents = min_agents
        self.max_agents = max_agents
        self._queue_depth = 0
        self._active = 0
        self._lock = threading.Lock()

    def desired_count(self, queue_depth: int) -> int:
        with self._lock:
            self._queue_depth = queue_depth
            desired = self.min_agents + queue_depth // 5
            return max(self.min_agents, min(self.max_agents, desired))

    def scale(self, current: int, queue_depth: int) -> int:
        desired = self.desired_count(queue_depth)
        if desired > current:
            return min(desired - current, self.max_agents - current)
        return 0


class AgentOrchestrator:
    """Full orchestrator combining all subsystems."""

    def __init__(self):
        self.registry = RoleRegistry()
        self.decomposer = TaskDecomposer()
        self.consensus = ConsensusVoter()
        self.pool = DynamicPool()
        self._results: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def add_agent(self, agent: Agent):
        self.registry.register(agent)

    def plan(self, task: str) -> List[SubTask]:
        return self.decomposer.build_plan(task)

    def assign(self, subtasks: List[SubTask]) -> Dict[str, str]:
        assignments = {}
        for st in subtasks:
            agent_id = self.registry.find_by_capability(st.required_caps)
            if agent_id:
                st.assigned_to = agent_id
                self.registry.update_load(agent_id, 0.1)
                assignments[st.id] = agent_id
        return assignments

    def execute_plan(self, task: str, handlers: Dict[str, Callable]) -> Dict[str, Any]:
        subtasks = self.plan(task)
        self.assign(subtasks)
        results = {}
        for st in subtasks:
            if not st.assigned_to:
                st.status = "failed"
                continue
            handler = handlers.get(st.description)
            if handler:
                try:
                    st.result = handler()
                    st.status = "done"
                    results[st.id] = st.result
                except Exception as e:
                    st.status = "failed"
                    st.result = str(e)
            else:
                st.status = "skipped"
        return results

    def propose(self, proposal_id: str, agent_id: str, vote: Any) -> Tuple[bool, Any]:
        self.consensus.vote(proposal_id, agent_id, vote)
        return self.consensus.tally(proposal_id)

    def stats(self) -> Dict:
        return {
            "agents": len(self.registry._agents),
            "healthy": sum(1 for a in self.registry._agents.values() if a.healthy),
            "methods": len(self.decomposer._methods),
            "proposals": len(self.consensus._votes),
        }


# ─── SELF TESTS ───
if __name__ == "__main__":
    tests = []
    def _t(name, fn):
        tests.append((name, fn))

    _t("registry_find", lambda: (r := RoleRegistry(), r.register(Agent("a1", "worker", ["code"])), r.find_by_capability(["code"]) == "a1")[2])
    _t("registry_load", lambda: (r := RoleRegistry(), r.register(Agent("a1", "worker", ["code"], load=0.9)), r.find_by_capability(["code"], max_load=0.8) is None)[2])
    _t("decompose", lambda: (d := TaskDecomposer(), d.add_method("deploy", ["build", "test", "push"]), d.add_primitive("build"), d.decompose("deploy") == ["build", "test", "push"])[3])
    _t("consensus_pass", lambda: (c := ConsensusVoter(threshold=0.6), c.vote("p1", "a1", "yes"), c.vote("p1", "a2", "yes"), c.tally("p1")[0])[3])
    _t("consensus_fail", lambda: (c := ConsensusVoter(threshold=0.9), c.vote("p1", "a1", "yes"), c.vote("p1", "a2", "no"), not c.tally("p1")[0])[3])
    _t("pool_scale", lambda: DynamicPool(min_agents=2, max_agents=10).desired_count(30) == 8)
    _t("pool_max", lambda: DynamicPool(min_agents=2, max_agents=5).desired_count(100) == 5)
    _t("orchestrator_plan", lambda: (o := AgentOrchestrator(), o.decomposer.add_method("scan", ["nmap", "analyze"]), o.decomposer.add_primitive("nmap"), len(o.plan("scan")) == 2)[3])
    _t("orchestrator_assign", lambda: (o := AgentOrchestrator(), o.add_agent(Agent("a1", "worker", ["code"])), o.assign([SubTask("t1", "code", ["code"])])["t1"] == "a1")[2])
    _t("stats", lambda: "agents" in AgentOrchestrator().stats())

    passed = 0
    for name, fn in tests:
        try:
            ok = fn()
            print(f"  {'PASS' if ok else 'FAIL'} {name}")
            if ok:
                passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
    print(f"\nAgent Orchestrator: {passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)
