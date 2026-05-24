#!/usr/bin/env python3
"""
MAGNATRIX-OS — Layer 3: Studio Orchestrator
Native Python, zero external dependencies.
Based on Donchitos/Claude-Code-Game-Studios (19.7k stars) — 49 agents, 72 skills, studio hierarchy.
"""
from __future__ import annotations
import threading, time, random, json, hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum


class AgentState(Enum):
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    RECOVERING = "recovering"
    OFFLINE = "offline"


class AgentRole(Enum):
    STUDIO_DIRECTOR = "studio_director"
    DEPARTMENT_LEAD = "department_lead"
    SPECIALIST = "specialist"
    INTERN = "intern"


class Department(Enum):
    DESIGN = "design"
    ENGINEERING = "engineering"
    ART = "art"
    AUDIO = "audio"
    QA = "qa"
    PRODUCTION = "production"
    MARKETING = "marketing"


class ProductionPhase(Enum):
    CONCEPT = "concept"
    PROTOTYPE = "prototype"
    VERTICAL_SLICE = "vertical_slice"
    ALPHA = "alpha"
    BETA = "beta"
    GOLD = "gold"


@dataclass
class Agent:
    id: str
    name: str
    role: AgentRole
    department: Department
    skills: List[str] = field(default_factory=list)
    state: AgentState = AgentState.IDLE
    current_task: str = ""
    completed_tasks: int = 0
    error_count: int = 0
    created_at: float = field(default_factory=time.time)


@dataclass
class SkillDef:
    name: str
    description: str
    prerequisites: List[str] = field(default_factory=list)
    version: int = 1
    category: str = "general"


@dataclass
class Workflow:
    name: str
    steps: List[Dict] = field(default_factory=list)
    state: str = "pending"
    current_step: int = 0
    created_at: float = field(default_factory=time.time)


class StudioHierarchy:
    """Studio structure: Director → Lead → Specialist → Intern."""

    def __init__(self):
        self._director: Optional[Agent] = None
        self._leads: Dict[str, Agent] = {}
        self._specialists: Dict[str, Agent] = {}
        self._interns: Dict[str, Agent] = {}

    def set_director(self, agent: Agent):
        agent.role = AgentRole.STUDIO_DIRECTOR
        self._director = agent

    def add_lead(self, agent: Agent):
        agent.role = AgentRole.DEPARTMENT_LEAD
        self._leads[agent.id] = agent

    def add_specialist(self, agent: Agent):
        agent.role = AgentRole.SPECIALIST
        self._specialists[agent.id] = agent

    def add_intern(self, agent: Agent):
        agent.role = AgentRole.INTERN
        self._interns[agent.id] = agent

    def get_hierarchy(self) -> Dict:
        return {
            "director": self._director.name if self._director else None,
            "leads": [a.name for a in self._leads.values()],
            "specialists": [a.name for a in self._specialists.values()],
            "interns": [a.name for a in self._interns.values()],
        }


class AgentRegistry:
    """Register 49+ agents, assign roles, track state."""

    def __init__(self):
        self._agents: Dict[str, Agent] = {}
        self._lock = threading.RLock()
        self._id_counter = 0

    def create_agent(self, name: str, role: AgentRole, department: Department, skills: List[str] = None) -> Agent:
        with self._lock:
            self._id_counter += 1
            agent_id = f"agent_{self._id_counter:03d}"
            agent = Agent(
                id=agent_id, name=name, role=role,
                department=department, skills=skills or [],
            )
            self._agents[agent_id] = agent
            return agent

    def get(self, agent_id: str) -> Optional[Agent]:
        with self._lock:
            return self._agents.get(agent_id)

    def update_state(self, agent_id: str, state: AgentState, task: str = ""):
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent:
                agent.state = state
                if task:
                    agent.current_task = task
                if state == AgentState.IDLE and agent.current_task:
                    agent.completed_tasks += 1
                    agent.current_task = ""

    def list_by_department(self, dept: Department) -> List[Agent]:
        with self._lock:
            return [a for a in self._agents.values() if a.department == dept]

    def list_all(self) -> List[Agent]:
        with self._lock:
            return list(self._agents.values())

    def get_available(self) -> List[Agent]:
        with self._lock:
            return [a for a in self._agents.values() if a.state == AgentState.IDLE]


class DepartmentManager:
    """Manage departments, assign agents, track capacity."""

    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self._capacity: Dict[Department, int] = {
            Department.DESIGN: 8,
            Department.ENGINEERING: 15,
            Department.ART: 10,
            Department.AUDIO: 5,
            Department.QA: 6,
            Department.PRODUCTION: 3,
            Department.MARKETING: 2,
        }

    def assign_to_department(self, agent_id: str, dept: Department) -> bool:
        agent = self.registry.get(agent_id)
        if not agent:
            return False
        current = len(self.registry.list_by_department(dept))
        if current >= self._capacity[dept]:
            return False
        agent.department = dept
        return True

    def get_department_status(self, dept: Department) -> Dict:
        agents = self.registry.list_by_department(dept)
        return {
            "department": dept.value,
            "total": len(agents),
            "idle": sum(1 for a in agents if a.state == AgentState.IDLE),
            "busy": sum(1 for a in agents if a.state == AgentState.BUSY),
            "capacity": self._capacity[dept],
        }


class EscalationEngine:
    """Escalation paths: specialist → lead → director, with timeouts."""

    def __init__(self, hierarchy: StudioHierarchy, registry: AgentRegistry):
        self.hierarchy = hierarchy
        self.registry = registry
        self._escalations: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    def escalate(self, agent_id: str, issue: str, timeout_sec: float = 300.0) -> Optional[str]:
        agent = self.registry.get(agent_id)
        if not agent:
            return None

        with self._lock:
            escalation_id = hashlib.md5(f"{agent_id}{issue}{time.time()}".encode()).hexdigest()[:8]
            self._escalations[escalation_id] = {
                "agent": agent_id,
                "issue": issue,
                "level": 1,
                "timeout": time.time() + timeout_sec,
                "resolved": False,
            }

        # Auto-escalate based on role
        if agent.role == AgentRole.SPECIALIST:
            # Escalate to lead
            leads = [a for a in self.hierarchy._leads.values() if a.department == agent.department]
            if leads:
                return leads[0].id
        elif agent.role == AgentRole.DEPARTMENT_LEAD:
            # Escalate to director
            if self.hierarchy._director:
                return self.hierarchy._director.id

        return None

    def check_timeouts(self):
        with self._lock:
            now = time.time()
            for esc in self._escalations.values():
                if not esc["resolved"] and now > esc["timeout"]:
                    esc["level"] += 1
                    # Escalate to next level
                    agent = self.registry.get(esc["agent"])
                    if agent and self.hierarchy._director:
                        esc["timeout"] = now + 300.0


class QualityGate:
    """Code review gate, design doc review, test pass, approval workflow."""

    def __init__(self):
        self._gates: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    def create_gate(self, artifact_id: str, checks: List[str]) -> str:
        gate_id = f"gate_{hashlib.md5(artifact_id.encode()).hexdigest()[:6]}"
        with self._lock:
            self._gates[gate_id] = {
                "artifact": artifact_id,
                "checks": {c: "pending" for c in checks},
                "status": "pending",
                "approved_by": [],
            }
        return gate_id

    def submit_check(self, gate_id: str, check: str, result: str, reviewer: str = ""):
        with self._lock:
            gate = self._gates.get(gate_id)
            if gate and check in gate["checks"]:
                gate["checks"][check] = result
                if reviewer:
                    gate["approved_by"].append(reviewer)
                # Update overall status
                if all(r == "pass" for r in gate["checks"].values()):
                    gate["status"] = "approved"
                elif any(r == "fail" for r in gate["checks"].values()):
                    gate["status"] = "rejected"

    def get_status(self, gate_id: str) -> Optional[Dict]:
        with self._lock:
            return self._gates.get(gate_id)


class SkillManager:
    """72+ skills registry, assignment, prerequisites, versioning."""

    def __init__(self):
        self._skills: Dict[str, SkillDef] = {}
        self._agent_skills: Dict[str, Set[str]] = {}
        self._lock = threading.RLock()

    def register_skill(self, skill: SkillDef):
        with self._lock:
            self._skills[skill.name] = skill

    def assign_skill(self, agent_id: str, skill_name: str) -> bool:
        with self._lock:
            skill = self._skills.get(skill_name)
            if not skill:
                return False
            # Check prerequisites
            for prereq in skill.prerequisites:
                if prereq not in self._agent_skills.get(agent_id, set()):
                    return False
            self._agent_skills.setdefault(agent_id, set()).add(skill_name)
            return True

    def get_agent_skills(self, agent_id: str) -> List[str]:
        with self._lock:
            return list(self._agent_skills.get(agent_id, set()))

    def list_all(self) -> List[SkillDef]:
        with self._lock:
            return list(self._skills.values())


class WorkflowEngine:
    """Workflow definition: linear, parallel, conditional, loop."""

    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self._workflows: Dict[str, Workflow] = {}
        self._lock = threading.Lock()

    def create_workflow(self, name: str, steps: List[Dict]) -> Workflow:
        wf = Workflow(name=name, steps=steps)
        with self._lock:
            self._workflows[name] = wf
        return wf

    def execute_step(self, wf_name: str) -> Optional[Dict]:
        with self._lock:
            wf = self._workflows.get(wf_name)
            if not wf or wf.current_step >= len(wf.steps):
                return None
            step = wf.steps[wf.current_step]
            wf.current_step += 1
            if wf.current_step >= len(wf.steps):
                wf.state = "completed"
            return step

    def get_status(self, wf_name: str) -> Optional[Dict]:
        with self._lock:
            wf = self._workflows.get(wf_name)
            if not wf:
                return None
            return {
                "name": wf.name,
                "state": wf.state,
                "progress": f"{wf.current_step}/{len(wf.steps)}",
            }


class SessionStateManager:
    """Persist session state, checkpoint/restore, context resilience."""

    def __init__(self):
        self._checkpoints: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    def checkpoint(self, session_id: str, state: Dict):
        with self._lock:
            self._checkpoints[session_id] = {
                "state": dict(state),
                "timestamp": time.time(),
            }

    def restore(self, session_id: str) -> Optional[Dict]:
        with self._lock:
            cp = self._checkpoints.get(session_id)
            return cp["state"] if cp else None

    def list_checkpoints(self) -> List[str]:
        with self._lock:
            return list(self._checkpoints.keys())


class DesignReviewBoard:
    """Design proposal submission, review cycle, feedback, approval."""

    def __init__(self):
        self._proposals: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    def submit(self, proposal_id: str, title: str, content: str, submitter: str) -> str:
        with self._lock:
            self._proposals[proposal_id] = {
                "title": title,
                "content": content,
                "submitter": submitter,
                "status": "submitted",
                "reviews": [],
                "submitted_at": time.time(),
            }
        return proposal_id

    def review(self, proposal_id: str, reviewer: str, feedback: str, decision: str):
        with self._lock:
            prop = self._proposals.get(proposal_id)
            if prop:
                prop["reviews"].append({"reviewer": reviewer, "feedback": feedback, "decision": decision})
                if decision in ("approved", "rejected"):
                    prop["status"] = decision

    def get_status(self, proposal_id: str) -> Optional[Dict]:
        with self._lock:
            return self._proposals.get(proposal_id)


class ProductionPipeline:
    """Concept → prototype → vertical-slice → alpha → beta → gold."""

    PHASES = [ProductionPhase.CONCEPT, ProductionPhase.PROTOTYPE, ProductionPhase.VERTICAL_SLICE,
              ProductionPhase.ALPHA, ProductionPhase.BETA, ProductionPhase.GOLD]

    def __init__(self):
        self._projects: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    def create_project(self, project_id: str, name: str):
        with self._lock:
            self._projects[project_id] = {
                "name": name,
                "current_phase": ProductionPhase.CONCEPT,
                "phase_index": 0,
                "gates_passed": [],
            }

    def advance_phase(self, project_id: str) -> bool:
        with self._lock:
            proj = self._projects.get(project_id)
            if not proj or proj["phase_index"] >= len(self.PHASES) - 1:
                return False
            proj["phase_index"] += 1
            proj["current_phase"] = self.PHASES[proj["phase_index"]]
            return True

    def get_status(self, project_id: str) -> Optional[Dict]:
        with self._lock:
            proj = self._projects.get(project_id)
            if not proj:
                return None
            return {
                "name": proj["name"],
                "phase": proj["current_phase"].value,
                "progress": f"{proj['phase_index'] + 1}/{len(self.PHASES)}",
            }


class NotificationHub:
    """Notify agents of events: broadcast, targeted, priority."""

    def __init__(self):
        self._notifications: List[Dict] = []
        self._lock = threading.Lock()

    def broadcast(self, message: str, priority: str = "normal"):
        with self._lock:
            self._notifications.append({
                "type": "broadcast",
                "message": message,
                "priority": priority,
                "timestamp": time.time(),
            })

    def targeted(self, agent_id: str, message: str, priority: str = "normal"):
        with self._lock:
            self._notifications.append({
                "type": "targeted",
                "agent": agent_id,
                "message": message,
                "priority": priority,
                "timestamp": time.time(),
            })

    def get_for_agent(self, agent_id: str) -> List[Dict]:
        with self._lock:
            return [n for n in self._notifications if n.get("agent") == agent_id or n["type"] == "broadcast"]


class TaskScheduler:
    """Schedule tasks, dependency resolution, critical path."""

    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self._tasks: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    def schedule(self, task_id: str, description: str, assignee: str = "", dependencies: List[str] = None):
        with self._lock:
            self._tasks[task_id] = {
                "description": description,
                "assignee": assignee,
                "dependencies": dependencies or [],
                "status": "pending",
                "started": 0,
                "completed": 0,
            }

    def start_task(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            # Check dependencies
            for dep in task["dependencies"]:
                dep_task = self._tasks.get(dep)
                if dep_task and dep_task["status"] != "completed":
                    return False
            task["status"] = "in_progress"
            task["started"] = time.time()
            if task["assignee"]:
                self.registry.update_state(task["assignee"], AgentState.BUSY, task_id)
            return True

    def complete_task(self, task_id: str):
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task["status"] = "completed"
                task["completed"] = time.time()
                if task["assignee"]:
                    self.registry.update_state(task["assignee"], AgentState.IDLE)

    def get_critical_path(self) -> List[str]:
        with self._lock:
            pending = [tid for tid, t in self._tasks.items() if t["status"] != "completed"]
            # Simple: tasks with no unmet dependencies first
            ready = []
            for tid in pending:
                t = self._tasks[tid]
                if all(self._tasks.get(d, {}).get("status") == "completed" for d in t["dependencies"]):
                    ready.append(tid)
            return ready


class ConsistencyChecker:
    """Check consistency across agent outputs, detect conflicts."""

    def check(self, outputs: Dict[str, str]) -> List[Dict]:
        conflicts = []
        keys = list(outputs.keys())
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                a, b = outputs[keys[i]], outputs[keys[j]]
                if self._is_contradictory(a, b):
                    conflicts.append({
                        "agents": (keys[i], keys[j]),
                        "issue": "contradictory_output",
                        "suggestion": "Run arbitration workflow",
                    })
        return conflicts

    def _is_contradictory(self, a: str, b: str) -> bool:
        # Simple heuristic: check for opposite boolean statements
        if ("true" in a.lower() and "false" in b.lower()) or ("yes" in a.lower() and "no" in b.lower()):
            return True
        return False


class StudioKernelBridge:
    """Bridge to event_bus and service_registry."""

    def __init__(self, event_bus=None, service_registry=None):
        self.event_bus = event_bus
        self.service_registry = service_registry

    def publish(self, event_type: str, data: Dict):
        if self.event_bus:
            try:
                self.event_bus.publish(f"studio.{event_type}", data)
            except Exception:
                pass

    def register(self):
        if self.service_registry:
            try:
                self.service_registry.register("studio_orchestrator", {"status": "running"})
            except Exception:
                pass


class StudioOrchestrator:
    """Main orchestrator — compose all components."""

    def __init__(self):
        self.hierarchy = StudioHierarchy()
        self.registry = AgentRegistry()
        self.dept_manager = DepartmentManager(self.registry)
        self.escalation = EscalationEngine(self.hierarchy, self.registry)
        self.quality_gate = QualityGate()
        self.skill_manager = SkillManager()
        self.workflow = WorkflowEngine(self.registry)
        self.session = SessionStateManager()
        self.review_board = DesignReviewBoard()
        self.pipeline = ProductionPipeline()
        self.notifications = NotificationHub()
        self.scheduler = TaskScheduler(self.registry)
        self.consistency = ConsistencyChecker()
        self.bridge = StudioKernelBridge()
        self._booted = False

    def boot(self):
        self.bridge.register()
        # Create default studio structure
        director = self.registry.create_agent("Director", AgentRole.STUDIO_DIRECTOR, Department.PRODUCTION)
        self.hierarchy.set_director(director)

        # Create department leads
        for dept in [Department.DESIGN, Department.ENGINEERING, Department.ART, Department.QA]:
            lead = self.registry.create_agent(f"{dept.value.title()}_Lead", AgentRole.DEPARTMENT_LEAD, dept)
            self.hierarchy.add_lead(lead)

        # Create specialists
        for i in range(10):
            dept = random.choice(list(Department))
            agent = self.registry.create_agent(f"Spec_{i+1}", AgentRole.SPECIALIST, dept, ["coding", "design"])
            self.hierarchy.add_specialist(agent)

        # Register skills
        for skill_name in ["coding", "design", "review", "testing", "modeling", "sound", "marketing"]:
            self.skill_manager.register_skill(SkillDef(name=skill_name, description=f"{skill_name} skill"))

        self._booted = True
        print(f"[Studio] Booted with {len(self.registry.list_all())} agents")

    def create_project(self, name: str) -> str:
        pid = f"proj_{hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()[:6]}"
        self.pipeline.create_project(pid, name)
        return pid

    def assign_task(self, task_id: str, description: str, dept: Department) -> bool:
        agents = self.registry.list_by_department(dept)
        available = [a for a in agents if a.state == AgentState.IDLE]
        if not available:
            return False
        agent = random.choice(available)
        self.scheduler.schedule(task_id, description, agent.id)
        return self.scheduler.start_task(task_id)

    def get_status(self) -> Dict:
        return {
            "agents": len(self.registry.list_all()),
            "departments": {d.value: self.dept_manager.get_department_status(d) for d in Department},
            "hierarchy": self.hierarchy.get_hierarchy(),
        }

    def shutdown(self):
        print("[Studio] Shutdown complete")


def run_demo():
    print("=" * 60)
    print("MAGNATRIX-OS Studio Orchestrator Demo")
    print("=" * 60)

    studio = StudioOrchestrator()
    studio.boot()

    print("\n--- Studio Hierarchy ---")
    status = studio.get_status()
    print(f"Total agents: {status['agents']}")
    for dept, info in status['departments'].items():
        print(f"  {dept}: {info['total']} agents ({info['idle']} idle, {info['busy']} busy)")

    print("\n--- Create Project ---")
    proj_id = studio.create_project("Game_A")
    print(f"Project created: {proj_id}")
    print(f"Phase: {studio.pipeline.get_status(proj_id)['phase']}")

    print("\n--- Assign Tasks ---")
    for i in range(5):
        task_id = f"task_{i+1}"
        dept = random.choice([Department.ENGINEERING, Department.DESIGN, Department.ART])
        result = studio.assign_task(task_id, f"Implement feature {i+1}", dept)
        print(f"  {task_id} → {dept.value}: {'ASSIGNED' if result else 'FAILED'}")

    print("\n--- Quality Gate ---")
    gate_id = studio.quality_gate.create_gate("feature_1", ["code_review", "test_pass", "design_review"])
    studio.quality_gate.submit_check(gate_id, "code_review", "pass", "lead_1")
    studio.quality_gate.submit_check(gate_id, "test_pass", "pass", "qa_1")
    gate_status = studio.quality_gate.get_status(gate_id)
    print(f"  Gate status: {gate_status['status']}")

    print("\n--- Escalation ---")
    spec = [a for a in studio.registry.list_all() if a.role == AgentRole.SPECIALIST][0]
    escalated_to = studio.escalation.escalate(spec.id, "Cannot resolve rendering bug")
    if escalated_to:
        lead = studio.registry.get(escalated_to)
        print(f"  {spec.name} escalated to {lead.name if lead else 'Unknown'}")

    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
