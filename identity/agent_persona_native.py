#!/usr/bin/env python3
"""
================================================================================
MAGNATRIX-OS — Agent Persona Registry (Layer 2 Extension)
Inspired by: itseffi/agentic-os AGENTS.md / CLAUDE.md / CODEX.md / OPENCLAW.md
Multi-agent orchestration with persona definitions, capability matching,
role-based routing, and cross-agent messaging.
================================================================================
Zero-dependency persona registry for distributed agent coordination.
================================================================================
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple


# =============================================================================
# Constants
# =============================================================================
PERSONA_DIR = "/tmp/magnatrix_personas"


# =============================================================================
# Data Types
# =============================================================================
class AgentRole(Enum):
    ORCHESTRATOR = "orchestrator"
    CODER = "coder"
    RESEARCHER = "researcher"
    TRADER = "trader"
    SECURITY = "security"
    DEVOPS = "devops"
    DESIGNER = "designer"
    ANALYST = "analyst"
    GENERAL = "general"


@dataclass
class AgentCapability:
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0  # 0-1


@dataclass
class AgentPersona:
    persona_id: str
    name: str
    role: AgentRole
    description: str
    instructions: str = ""
    capabilities: List[AgentCapability] = field(default_factory=list)
    model_preferences: Dict[str, Any] = field(default_factory=dict)
    context_window: int = 8192
    temperature: float = 0.7
    max_tokens: int = 2048
    tools_allowed: Set[str] = field(default_factory=set)
    tools_denied: Set[str] = field(default_factory=set)
    fallback_persona: str = ""  # Escalate to this persona if blocked
    created_at: float = field(default_factory=time.time)
    version: str = "1.0.0"
    active: bool = True

    @property
    def capability_names(self) -> Set[str]:
        return {c.name for c in self.capabilities}


@dataclass
class AgentMessage:
    msg_id: str
    from_persona: str
    to_persona: str
    content: str
    msg_type: str = "text"  # text, command, query, result, error
    timestamp: float = field(default_factory=time.time)
    priority: int = 0
    thread_id: str = ""


# =============================================================================
# Persona Parser
# =============================================================================
class PersonaParser:
    """Parse persona definitions from markdown files (like AGENTS.md)."""

    SECTION_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
    KV_RE = re.compile(r"^-\s+([A-Z_]+):\s*(.+)$", re.MULTILINE)

    def parse_file(self, path: str) -> Optional[AgentPersona]:
        text = Path(path).read_text(encoding="utf-8")
        return self.parse_text(text, Path(path).stem)

    def parse_text(self, text: str, name_hint: str = "") -> Optional[AgentPersona]:
        # Extract title from first # header
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        title = title_match.group(1) if title_match else name_hint
        pid = hashlib.sha256(text.encode()).hexdigest()[:12]
        # Extract role
        role = AgentRole.GENERAL
        for r in AgentRole:
            if r.value.lower() in text.lower():
                role = r
                break
        # Extract capabilities from ## Capabilities section
        caps: List[AgentCapability] = []
        cap_section = re.search(r"##\s+Capabilities\s*\n(.*?)(?=##|$)", text, re.DOTALL | re.IGNORECASE)
        if cap_section:
            for line in cap_section.group(1).strip().split("\n"):
                m = re.match(r"^-\s+(.+)$", line.strip())
                if m:
                    caps.append(AgentCapability(name=m.group(1).strip(), description=""))
        # Extract instructions from ## Instructions section
        instructions = ""
        instr_section = re.search(r"##\s+Instructions\s*\n(.*?)(?=##|$)", text, re.DOTALL | re.IGNORECASE)
        if instr_section:
            instructions = instr_section.group(1).strip()
        # Extract model preferences
        model_prefs: Dict[str, Any] = {}
        temp_match = re.search(r"temperature[:\s]+(\d+\.?\d*)", text, re.IGNORECASE)
        if temp_match:
            model_prefs["temperature"] = float(temp_match.group(1))
        ctx_match = re.search(r"context[:\s]+(\d+)", text, re.IGNORECASE)
        if ctx_match:
            model_prefs["context_window"] = int(ctx_match.group(1))
        return AgentPersona(
            persona_id=pid,
            name=title,
            role=role,
            description=text[:200],
            instructions=instructions,
            capabilities=caps,
            model_preferences=model_prefs,
        )

    def to_markdown(self, persona: AgentPersona) -> str:
        lines = [
            f"# {persona.name}",
            "",
            f"**Role:** {persona.role.value}",
            f"**Version:** {persona.version}",
            f"**ID:** `{persona.persona_id}`",
            "",
            "## Description",
            persona.description,
            "",
            "## Instructions",
            persona.instructions or "(none)",
            "",
            "## Capabilities",
        ]
        for c in persona.capabilities:
            lines.append(f"- {c.name}: {c.description}")
        lines.extend([
            "",
            "## Model Preferences",
            f"- Temperature: {persona.temperature}",
            f"- Context Window: {persona.context_window}",
            f"- Max Tokens: {persona.max_tokens}",
            "",
            "## Tools",
            f"- Allowed: {', '.join(persona.tools_allowed) or '(all)'}",
            f"- Denied: {', '.join(persona.tools_denied) or '(none)'}",
            f"- Fallback: {persona.fallback_persona or '(none)'}",
        ])
        return "\n".join(lines)


# =============================================================================
# Persona Registry
# =============================================================================
class PersonaRegistry:
    """Store, search, and match agent personas."""

    def __init__(self, persona_dir: str = PERSONA_DIR) -> None:
        self.persona_dir = Path(persona_dir)
        self.persona_dir.mkdir(parents=True, exist_ok=True)
        self._parser = PersonaParser()
        self._personas: Dict[str, AgentPersona] = {}
        self._lock = threading.Lock()
        self._load_all()

    def _load_all(self) -> None:
        for p in self.persona_dir.glob("*.md"):
            per = self._parser.parse_file(str(p))
            if per:
                self._personas[per.persona_id] = per

    def _save(self, persona: AgentPersona) -> None:
        safe_name = re.sub(r"[^\w-]", "_", persona.name.lower())[:40]
        path = self.persona_dir / f"{safe_name}.md"
        path.write_text(self._parser.to_markdown(persona), encoding="utf-8")

    def register(self, persona: AgentPersona) -> bool:
        with self._lock:
            if persona.persona_id in self._personas:
                return False
            self._personas[persona.persona_id] = persona
            self._save(persona)
            return True

    def update(self, persona: AgentPersona) -> bool:
        with self._lock:
            if persona.persona_id not in self._personas:
                return False
            self._personas[persona.persona_id] = persona
            self._save(persona)
            return True

    def get(self, persona_id: str) -> Optional[AgentPersona]:
        return self._personas.get(persona_id)

    def get_by_name(self, name: str) -> Optional[AgentPersona]:
        for p in self._personas.values():
            if p.name.lower() == name.lower():
                return p
        return None

    def list_all(self, role: Optional[AgentRole] = None, active_only: bool = True) -> List[AgentPersona]:
        result = list(self._personas.values())
        if role:
            result = [p for p in result if p.role == role]
        if active_only:
            result = [p for p in result if p.active]
        return result

    def find_for_task(self, required_capabilities: List[str]) -> List[Tuple[AgentPersona, float]]:
        """Score personas by capability match."""
        scored: List[Tuple[AgentPersona, float]] = []
        for p in self._personas.values():
            if not p.active:
                continue
            caps = p.capability_names
            matched = sum(1 for c in required_capabilities if c in caps)
            score = matched / len(required_capabilities) if required_capabilities else 0.0
            scored.append((p, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def match_role(self, task_description: str) -> List[Tuple[AgentRole, float]]:
        """Simple keyword-based role matching."""
        text = task_description.lower()
        scores: Dict[AgentRole, float] = {}
        keywords = {
            AgentRole.CODER: ["code", "program", "function", "class", "script", "debug", "refactor"],
            AgentRole.RESEARCHER: ["research", "analyze", "study", "investigate", "survey"],
            AgentRole.TRADER: ["trade", "signal", "market", "price", "profit", "buy", "sell"],
            AgentRole.SECURITY: ["security", "audit", "scan", "vulnerability", "exploit", "penetration"],
            AgentRole.DEVOPS: ["deploy", "infra", "docker", "kubernetes", "ci/cd", "pipeline"],
            AgentRole.DESIGNER: ["design", "ui", "ux", "layout", "visual", "css", "frontend"],
            AgentRole.ANALYST: ["data", "metric", "report", "dashboard", "kpi", "analysis"],
            AgentRole.ORCHESTRATOR: ["coordinate", "manage", "schedule", "orchestrate", "route"],
        }
        for role, kw_list in keywords.items():
            score = sum(1 for k in kw_list if k in text) / len(kw_list)
            scores[role] = score
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    def deactivate(self, persona_id: str) -> bool:
        p = self._personas.get(persona_id)
        if p:
            p.active = False
            self._save(p)
            return True
        return False

    def activate(self, persona_id: str) -> bool:
        p = self._personas.get(persona_id)
        if p:
            p.active = True
            self._save(p)
            return True
        return False


# =============================================================================
# Agent Router
# =============================================================================
class AgentRouter:
    """Route tasks and messages to appropriate personas."""

    def __init__(self, registry: PersonaRegistry) -> None:
        self.registry = registry
        self._routes: Dict[str, str] = {}  # task_pattern -> persona_id
        self._default = ""
        self._history: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def set_default(self, persona_id: str) -> None:
        self._default = persona_id

    def add_route(self, pattern: str, persona_id: str) -> None:
        self._routes[pattern] = persona_id

    def route_task(self, task_description: str, required_caps: Optional[List[str]] = None) -> Optional[AgentPersona]:
        # Exact route match
        for pattern, pid in self._routes.items():
            if pattern.lower() in task_description.lower():
                return self.registry.get(pid)
        # Capability match
        if required_caps:
            scored = self.registry.find_for_task(required_caps)
            if scored and scored[0][1] > 0:
                return scored[0][0]
        # Role match
        role_scores = self.registry.match_role(task_description)
        if role_scores and role_scores[0][1] > 0:
            candidates = self.registry.list_all(role=role_scores[0][0])
            if candidates:
                return candidates[0]
        # Default
        if self._default:
            return self.registry.get(self._default)
        return None

    def record(self, task: str, persona: AgentPersona) -> None:
        with self._lock:
            self._history.append({
                "task": task,
                "persona_id": persona.persona_id,
                "timestamp": time.time(),
            })


# =============================================================================
# Cross-Agent Messaging
# =============================================================================
class AgentMailbox:
    """Message queue between personas."""

    def __init__(self) -> None:
        self._queues: Dict[str, List[AgentMessage]] = {}
        self._lock = threading.Lock()
        self._handlers: Dict[str, List[Callable[[AgentMessage], None]]] = {}

    def send(self, msg: AgentMessage) -> None:
        with self._lock:
            self._queues.setdefault(msg.to_persona, []).append(msg)
        for h in self._handlers.get(msg.to_persona, []):
            h(msg)
        for h in self._handlers.get("*", []):
            h(msg)

    def receive(self, persona_id: str, limit: int = 10) -> List[AgentMessage]:
        with self._lock:
            q = self._queues.get(persona_id, [])
            result = q[:limit]
            self._queues[persona_id] = q[limit:]
            return result

    def peek(self, persona_id: str) -> List[AgentMessage]:
        with self._lock:
            return list(self._queues.get(persona_id, []))

    def on_message(self, persona_id: str, handler: Callable[[AgentMessage], None]) -> None:
        self._handlers.setdefault(persona_id, []).append(handler)

    def broadcast(self, from_persona: str, content: str, msg_type: str = "text") -> None:
        msg = AgentMessage(
            msg_id=hashlib.sha256(str(time.time()).encode()).hexdigest()[:12],
            from_persona=from_persona,
            to_persona="*",
            content=content,
            msg_type=msg_type,
        )
        self.send(msg)


# =============================================================================
# Persona Kernel Bridge
# =============================================================================
class PersonaKernelBridge:
    def __init__(self, registry: PersonaRegistry, router: AgentRouter, mailbox: AgentMailbox, event_bus: Any = None) -> None:
        self.registry = registry
        self.router = router
        self.mailbox = mailbox
        self.bus = event_bus

    def dispatch(self, task: str, caps: Optional[List[str]] = None) -> Optional[AgentPersona]:
        p = self.router.route_task(task, caps)
        if p and self.bus:
            self.bus.publish("persona.assigned", {"task": task, "persona": p.name, "id": p.persona_id})
        return p

    def escalate(self, from_persona_id: str, to_persona_id: str, reason: str) -> bool:
        msg = AgentMessage(
            msg_id=hashlib.sha256(str(time.time()).encode()).hexdigest()[:12],
            from_persona=from_persona_id,
            to_persona=to_persona_id,
            content=reason,
            msg_type="escalation",
        )
        self.mailbox.send(msg)
        if self.bus:
            self.bus.publish("persona.escalated", {"from": from_persona_id, "to": to_persona_id, "reason": reason})
        return True


# =============================================================================
# Demo
# =============================================================================
def run_demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Agent Persona Registry Demo")
    print("=" * 60)
    reg = PersonaRegistry("/tmp/magnatrix_demo_personas")
    p1 = AgentPersona(
        persona_id="claude-coder",
        name="Claude Coder",
        role=AgentRole.CODER,
        description="Expert in Python, TypeScript, and system design",
        instructions="Write clean, documented code. Follow SOLID principles.",
        capabilities=[
            AgentCapability("code_review", "Review code for bugs and style"),
            AgentCapability("refactor", "Refactor legacy code"),
            AgentCapability("debug", "Debug complex issues"),
        ],
    )
    p2 = AgentPersona(
        persona_id="quant-trader",
        name="Quant Trader",
        role=AgentRole.TRADER,
        description="Algorithmic trading specialist",
        instructions="Always backtest before deploying strategies.",
        capabilities=[
            AgentCapability("signal_generation", "Generate alpha signals"),
            AgentCapability("backtest", "Run historical backtests"),
        ],
    )
    reg.register(p1)
    reg.register(p2)
    print(f"Registered {len(reg.list_all())} personas")

    router = AgentRouter(reg)
    router.set_default("claude-coder")
    match = router.route_task("Refactor the order execution engine for lower latency", ["refactor"])
    print(f"Routed to: {match.name if match else 'none'}")

    mailbox = AgentMailbox()
    mailbox.on_message("quant-trader", lambda m: print(f"  [MAIL] {m.from_persona} -> {m.to_persona}: {m.content[:50]}"))
    mailbox.send(AgentMessage(
        msg_id="m1",
        from_persona="claude-coder",
        to_persona="quant-trader",
        content="The backtesting module is ready for integration.",
    ))
    msgs = mailbox.receive("quant-trader")
    print(f"Received {len(msgs)} messages")
    print("Demo complete.")


if __name__ == "__main__":
    run_demo()
