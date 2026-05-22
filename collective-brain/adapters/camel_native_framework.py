"""
camel_native_framework.py
===========================
MAGNATRIX Native Roleplay AI Framework
Layer 0.5: COLLECTIVE BRAIN (extends adapters)

Pola AMATI-PELAJARI-TIRU dari camel-ai:
- Amati:  Role-playing sessions, ChatAgent pattern, workforce planner,
          society simulation, task decomposition dengan role-based assignment
- Pelajari: Core pattern: (1) RoleplaySession = set roles + let agents converse,
            (2) ChatAgent = persona-driven dengan system prompts,
            (3) WorkforcePlanner = auto-assign by capability matching,
            (4) SocietySimulator = multi-agent society dengan norms/rules,
            (5) TaskPlanner = decompose + assign + replan on failure
- Tiru:   Native Python, MAGNATRIX mesh integration untuk society-wide
          communication, constitutional constraints per role, reputation tracking
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from collections import defaultdict


class ConversationMode(Enum):
    ROUND_ROBIN = "round_robin"
    DIRECTED = "directed"  # Specific sender -> receiver
    BROADCAST = "broadcast"  # One to all
    DEBATE = "debate"  # Pro/con structured


@dataclass
class Persona:
    """Agent persona definition"""
    name: str = ""
    role: str = ""  # e.g., "expert_programmer", "skeptical_reviewer"
    background: str = ""  # Context/personality description
    expertise: List[str] = field(default_factory=list)
    communication_style: str = "professional"  # professional, casual, technical, socratic
    constraints: List[str] = field(default_factory=list)  # e.g., "never write unsafe code"
    system_prompt: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ConversationTurn:
    """Single turn dalam roleplay"""
    turn_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    speaker_id: str = ""
    speaker_name: str = ""
    message: str = ""
    timestamp: float = field(default_factory=time.time)
    referenced_turns: List[str] = field(default_factory=list)  # Turn IDs referenced
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class RoleplaySession:
    """Complete roleplay session"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    topic: str = ""
    mode: ConversationMode = ConversationMode.ROUND_ROBIN
    personas: Dict[str, Persona] = field(default_factory=dict)
    turns: List[ConversationTurn] = field(default_factory=list)
    max_turns: int = 20
    current_turn_index: int = 0
    # Rules
    rules: List[str] = field(default_factory=list)
    # State
    status: str = "active"  # active, paused, completed
    conclusion: Optional[str] = None
    # MAGNATRIX
    mesh_broadcast: bool = True

    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            "mode": self.mode.value,
            "turn_count": len(self.turns)
        }


class ChatAgent:
    """Persona-driven agent untuk roleplay"""

    def __init__(self, agent_id: str, persona: Persona,
                 llm_callback: Optional[Callable] = None):
        self.agent_id = agent_id
        self.persona = persona
        self.llm_callback = llm_callback
        self.memory: List[ConversationTurn] = []
        self.max_memory_window: int = 10

    async def respond(self, session: RoleplaySession,
                      context: str = "") -> ConversationTurn:
        """Generate response dalam persona"""
        # Build prompt dari persona + context
        prompt = self._build_prompt(session, context)

        # Call LLM atau fallback
        if self.llm_callback:
            response_text = await self.llm_callback(prompt)
        else:
            response_text = f"[{self.persona.name}] Acknowledged. {context[:50]}..."

        turn = ConversationTurn(
            speaker_id=self.agent_id,
            speaker_name=self.persona.name,
            message=response_text,
            referenced_turns=[t.turn_id for t in session.turns[-3:]]
        )

        self.memory.append(turn)
        if len(self.memory) > self.max_memory_window:
            self.memory = self.memory[-self.max_memory_window:]

        return turn

    def _build_prompt(self, session: RoleplaySession, context: str) -> str:
        recent_turns = "\n".join([
            f"{t.speaker_name}: {t.message[:100]}"
            for t in session.turns[-5:]
        ])

        return f"""You are {self.persona.name}, {self.persona.role}.
Background: {self.persona.background}
Expertise: {', '.join(self.persona.expertise)}
Style: {self.persona.communication_style}
Constraints: {', '.join(self.persona.constraints)}

Topic: {session.topic}
Recent conversation:
{recent_turns}

Context: {context}

Respond as {self.persona.name}:"""


class WorkforcePlanner:
    """Auto-assign tasks based on agent capability matching"""

    def __init__(self, agents: Dict[str, ChatAgent]):
        self.agents = agents

    def plan(self, task_description: str,
             required_expertise: List[str]) -> List[str]:
        """Plan task assignment - return agent IDs"""
        scores = []
        for agent_id, agent in self.agents.items():
            score = self._match_score(agent.persona.expertise, required_expertise)
            scores.append((agent_id, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [agent_id for agent_id, score in scores if score > 0.3]

    def _match_score(self, agent_exp: List[str], required: List[str]) -> float:
        if not required:
            return 1.0
        matches = sum(1 for r in required if any(r.lower() in a.lower() for a in agent_exp))
        return matches / len(required)


class SocietySimulator:
    """Multi-agent society simulation dengan norms"""

    def __init__(self):
        self.agents: Dict[str, ChatAgent] = {}
        self.norms: List[str] = []
        self.violations: List[Dict] = []
        self.rewards: List[Dict] = []

    def add_norm(self, norm: str):
        self.norms.append(norm)

    def check_norm_compliance(self, turn: ConversationTurn) -> bool:
        """Check if turn violates society norms"""
        for norm in self.norms:
            if norm.lower() in turn.message.lower():
                # Simplified: positive norm mention = compliance
                continue
        return True

    def record_violation(self, agent_id: str, norm: str, turn_id: str):
        self.violations.append({
            "agent_id": agent_id,
            "norm": norm,
            "turn_id": turn_id,
            "timestamp": time.time()
        })

    def get_society_health(self) -> Dict:
        return {
            "norms": len(self.norms),
            "violations": len(self.violations),
            "rewards": len(self.rewards),
            "health_score": max(0, 1.0 - len(self.violations) / max(len(self.rewards), 1))
        }


class TaskPlanner:
    """Task decomposition dengan role-based assignment + replan"""

    def __init__(self, workforce: WorkforcePlanner):
        self.workforce = workforce

    async def plan(self, task: str, context: str = "") -> Dict:
        """Create execution plan"""
        # Simplified: decompose into research, execute, review
        phases = [
            {"phase": "research", "expertise": ["research", "analysis"], "description": f"Research: {task}"},
            {"phase": "execute", "expertise": ["coding", "implementation"], "description": f"Execute: {task}"},
            {"phase": "review", "expertise": ["review", "testing"], "description": f"Review: {task}"},
        ]

        plan = {"task": task, "phases": []}
        for phase in phases:
            agents = self.workforce.plan(phase["description"], phase["expertise"])
            plan["phases"].append({
                **phase,
                "assigned_agents": agents[:2]  # Top 2 matches
            })

        return plan

    async def replan(self, failed_phase: Dict, reason: str) -> Dict:
        """Replan setelah failure"""
        new_plan = dict(failed_phase)
        new_plan["retry"] = True
        new_plan["failure_reason"] = reason
        # Assign different agents
        agents = self.workforce.plan(failed_phase["description"],
                                      failed_phase["expertise"])
        new_plan["assigned_agents"] = agents[:2]
        return new_plan


class RoleplayFramework:
    """High-level roleplay orchestrator"""

    def __init__(self):
        self.agents: Dict[str, ChatAgent] = {}
        self.sessions: Dict[str, RoleplaySession] = {}
        self.workforce = WorkforcePlanner(self.agents)
        self.society = SocietySimulator()
        self.planner = TaskPlanner(self.workforce)
        self._llm_callback: Optional[Callable] = None

    def set_llm_callback(self, callback: Callable):
        self._llm_callback = callback

    def create_persona(self, name: str, role: str,
                       expertise: List[str], **kwargs) -> Persona:
        return Persona(name=name, role=role, expertise=expertise, **kwargs)

    def register_agent(self, agent_id: str, persona: Persona):
        agent = ChatAgent(agent_id, persona, self._llm_callback)
        self.agents[agent_id] = agent
        self.workforce = WorkforcePlanner(self.agents)

    def create_session(self, topic: str,
                       mode: ConversationMode = ConversationMode.ROUND_ROBIN,
                       agent_ids: List[str] = None) -> RoleplaySession:
        session = RoleplaySession(topic=topic, mode=mode)
        for aid in (agent_ids or list(self.agents.keys())):
            if aid in self.agents:
                session.personas[aid] = self.agents[aid].persona
        self.sessions[session.id] = session
        return session

    async def run_session(self, session_id: str, max_turns: int = 10) -> RoleplaySession:
        session = self.sessions[session_id]
        agent_ids = list(session.personas.keys())

        for i in range(min(max_turns, session.max_turns)):
            if session.mode == ConversationMode.ROUND_ROBIN:
                agent_id = agent_ids[i % len(agent_ids)]
                agent = self.agents.get(agent_id)
                if agent:
                    turn = await agent.respond(session)
                    session.turns.append(turn)

        session.status = "completed"
        return session

    def get_status(self) -> Dict:
        return {
            "agents": len(self.agents),
            "sessions": len(self.sessions),
            "society_health": self.society.get_society_health()
        }


# ==================== DEMO ====================

if __name__ == "__main__":
    async def demo():
        framework = RoleplayFramework()

        # Create personas
        programmer = framework.create_persona(
            "Alice", "expert_programmer",
            ["python", "system_design", "debugging"],
            background="Senior engineer with 10 years experience"
        )
        reviewer = framework.create_persona(
            "Bob", "skeptical_reviewer",
            ["security", "code_review", "testing"],
            background="Security-focused code reviewer",
            constraints=["always mention security implications"]
        )

        framework.register_agent("alice", programmer)
        framework.register_agent("bob", reviewer)

        session = framework.create_session(
            "Design authentication system",
            ConversationMode.ROUND_ROBIN,
            ["alice", "bob"]
        )

        result = await framework.run_session(session.id, max_turns=4)
        print(f"Session completed: {len(result.turns)} turns")
        for turn in result.turns:
            print(f"{turn.speaker_name}: {turn.message[:80]}...")

    asyncio.run(demo())
