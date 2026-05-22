#!/usr/bin/env python3
"""
agent_roles.py — MAGNATRIX Swarm Agent Role System
Adaptasi konsep STOA (github.com/stoaaadev/stoa) ke MAGNATrix Agentic OS.

STOA punya 7 agent spesialisasi: scout, analyst, executor, guardian,
researcher, writer, ops. MAGNATRIX mengadaptasi ini ke dalam 8 role
yang bekerja di atas P2P Mesh Layer 4:

  1. scout       → Pemantau sinyal pasar, web, repos
  2. analyst     → Analisis data, scoring, pattern recognition
  3. executor    → Eksekusi trading, deploy, API calls
  4. guardian    → Risk monitoring, veto power, governance enforcement
  5. researcher  → Deep research, paper scanning, protocol analysis
  6. writer      → Content generation, docs, reports, changelogs
  7. ops         → CI/CD, repo health, dependency audit, security scan
  8. architect   → (MAGNATRIX-specific) System evolution, code mutation, constitution evolution

Setiap agent punya:
  - personality (prompt traits)
  - skills (list of skill names)
  - schedule (cron-like tick schedule)
  - mesh_inbox (queue pesan dari agent lain)
  - state (dict persisten)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
import time
import json


@dataclass
class AgentRole:
    """Definisi satu agent dalam swarm MAGNATRIX."""
    name: str
    description: str
    personality: str
    skills: List[str] = field(default_factory=list)
    schedule: str = "*/15 * * * *"  # default tiap 15 menit
    can_veto: bool = False
    max_parallel_tasks: int = 3
    mesh_inbox: List[Dict[str, Any]] = field(default_factory=list, repr=False)
    state: Dict[str, Any] = field(default_factory=dict, repr=False)


AGENT_ROLE_TEMPLATES: Dict[str, AgentRole] = {
    "scout": AgentRole(
        name="scout",
        description="Pemantau sinyal pasar, web, repos, dan network anomaly",
        personality="Agresif, cepat, tidak ragu-ragu. Fokus discovery bukan analisis.",
        skills=[
            "scan-tokens",
            "web-monitor",
            "repo-hunt",
            "news-scrape",
            "social-listen",
            "anomaly-detect",
        ],
        schedule="*/5 * * * *",  # tiap 5 menit
        max_parallel_tasks=5,
    ),
    "analyst": AgentRole(
        name="analyst",
        description="Brain swarm. Evaluasi sinyal, scoring, pattern recognition, prediksi.",
        personality="Metodis, skeptis, data-driven. Selalu cross-validate sebelum mengirim sinyal ke executor.",
        skills=[
            "analyze-signal",
            "trend-analysis",
            "market-structure",
            "sentiment-score",
            "pattern-recognition",
            "forecast-model",
            "cross-domain-synthesis",
        ],
        schedule="*/10 * * * *",
        max_parallel_tasks=3,
    ),
    "executor": AgentRole(
        name="executor",
        description="Hands swarm. Eksekusi trading, deploy, API calls, automation.",
        personality="Tepat, cepat, reliable. Hanya eksekusi signal yang sudah validated. Purely reactive.",
        skills=[
            "execute-trade",
            "dca-execute",
            "stop-loss-trigger",
            "deploy-node",
            "api-call",
            "browser-action",
        ],
        schedule="*/5 * * * *",
        max_parallel_tasks=5,
    ),
    "guardian": AgentRole(
        name="guardian",
        description="Immune system swarm. Risk monitoring, drawdown check, anomaly flag, veto power.",
        personality="Paranoid, conservative, protective. Satu HALT message freeze seluruh swarm.",
        skills=[
            "check-risk",
            "drawdown-monitor",
            "anomaly-flag",
            "veto-trigger",
            "self-repair",
            "constitution-check",
        ],
        schedule="*/3 * * * *",  # tiap 3 menit — paling sering
        can_veto=True,
        max_parallel_tasks=2,
    ),
    "researcher": AgentRole(
        name="researcher",
        description="Scholar swarm. Deep research, paper scan, protocol docs, security audit.",
        personality="Curious, thorough, skeptical. Fakta > opini. Selalu cite source.",
        skills=[
            "arxiv-scan",
            "paper-summarize",
            "competitor-watch",
            "github-trending",
            "protocol-deep-dive",
            "exploit-postmortem",
            "security-audit-watch",
        ],
        schedule="*/30 * * * *",
        max_parallel_tasks=2,
    ),
    "writer": AgentRole(
        name="writer",
        description="Voice swarm. Content generation, docs, reports, changelogs, social.",
        personality="Kreatif tapi disciplined. Fact-check sebelum publish. Clear, concise.",
        skills=[
            "daily-digest",
            "weekly-recap",
            "changelog-generate",
            "editorial-review",
            "write-newsletter",
            "tweet-compose",
            "report-generate",
        ],
        schedule="0 */4 * * *",  # tiap 4 jam
        max_parallel_tasks=2,
    ),
    "ops": AgentRole(
        name="ops",
        description="Engineer swarm. Repo health, CI, deploy, dependency audit, security scan.",
        personality="Systematic, detail-oriented, automation-obsessed. Tidak toleransi manual step.",
        skills=[
            "repo-health",
            "pr-review",
            "dependency-audit",
            "ci-monitor",
            "security-scan",
            "node-health-check",
            "backup-verify",
        ],
        schedule="*/10 * * * *",
        max_parallel_tasks=3,
    ),
    "architect": AgentRole(
        name="architect",
        description="Evolution swarm. System improvement, code mutation, constitution evolution, capability ranking.",
        personality="Visionary, recursive, self-improving. Selalu cari bottleneck dan evolusi path.",
        skills=[
            "code-mutate",
            "capability-rank",
            "constitution-evolve",
            "emergent-predict",
            "adversarial-train",
            "world-model-update",
            "cross-domain-meta-learn",
        ],
        schedule="0 */6 * * *",  # tiap 6 jam
        max_parallel_tasks=1,
    ),
}


class SwarmAgentRegistry:
    """Registry untuk semua agent aktif dalam swarm."""

    def __init__(self):
        self.agents: Dict[str, AgentRole] = {}
        self._halted = False
        self._halt_reason: Optional[str] = None
        self._halt_timestamp: Optional[float] = None

    def register(self, role_key: str, overrides: Optional[Dict[str, Any]] = None) -> AgentRole:
        """Register agent dari template."""
        if role_key not in AGENT_ROLE_TEMPLATES:
            raise ValueError(f"Unknown role: {role_key}. Available: {list(AGENT_ROLE_TEMPLATES.keys())}")
        template = AGENT_ROLE_TEMPLATES[role_key]
        agent = AgentRole(
            name=template.name,
            description=template.description,
            personality=template.personality,
            skills=list(template.skills),
            schedule=template.schedule,
            can_veto=template.can_veto,
            max_parallel_tasks=template.max_parallel_tasks,
        )
        if overrides:
            for k, v in overrides.items():
                if hasattr(agent, k):
                    setattr(agent, k, v)
        self.agents[role_key] = agent
        return agent

    def spawn_full_swarm(self) -> Dict[str, AgentRole]:
        """Spawn semua 8 agent sekaligus."""
        for key in AGENT_ROLE_TEMPLATES:
            self.register(key)
        return dict(self.agents)

    def mesh_broadcast(self, sender: str, message_type: str, payload: Dict[str, Any], target: Optional[str] = None) -> None:
        """Kirim pesan ke mesh. Jika target=None, broadcast ke semua."""
        envelope = {
            "id": f"msg-{int(time.time()*1000)}",
            "sender": sender,
            "target": target,
            "type": message_type,
            "payload": payload,
            "timestamp": time.time(),
        }
        recipients = [target] if target else list(self.agents.keys())
        for r in recipients:
            if r in self.agents and r != sender:
                self.agents[r].mesh_inbox.append(envelope)

    def inbox_pop(self, role_key: str, max_items: int = 10) -> List[Dict[str, Any]]:
        """Ambil dan hapus pesan dari inbox agent."""
        if role_key not in self.agents:
            return []
        inbox = self.agents[role_key].mesh_inbox
        taken = inbox[:max_items]
        self.agents[role_key].mesh_inbox = inbox[max_items:]
        return taken

    def halt(self, reason: str, triggered_by: str) -> Dict[str, Any]:
        """Guardian-triggered swarm halt. Freeze semua agent."""
        if not self.agents.get(triggered_by, AgentRole("", "", "")).can_veto:
            return {"status": "rejected", "reason": f"{triggered_by} does not have veto power"}
        self._halted = True
        self._halt_reason = reason
        self._halt_timestamp = time.time()
        # broadcast HALT ke semua agent
        self.mesh_broadcast(
            sender=triggered_by,
            message_type="HALT",
            payload={"reason": reason, "timestamp": self._halt_timestamp},
        )
        return {
            "status": "halted",
            "reason": reason,
            "triggered_by": triggered_by,
            "timestamp": self._halt_timestamp,
        }

    def resume(self, triggered_by: str) -> Dict[str, Any]:
        """Resume swarm dari halt state. Hanya guardian atau manual override."""
        if not self._halted:
            return {"status": "already_running"}
        agent = self.agents.get(triggered_by, AgentRole("", "", ""))
        if not agent.can_veto and triggered_by != "manual":
            return {"status": "rejected", "reason": f"{triggered_by} cannot resume"}
        self._halted = False
        self._halt_reason = None
        self._halt_timestamp = None
        return {"status": "resumed", "triggered_by": triggered_by}

    def is_halted(self) -> bool:
        return self._halted

    def get_status(self) -> Dict[str, Any]:
        return {
            "halted": self._halted,
            "halt_reason": self._halt_reason,
            "halt_timestamp": self._halt_timestamp,
            "agent_count": len(self.agents),
            "agents": {
                k: {
                    "name": v.name,
                    "skills_count": len(v.skills),
                    "inbox_size": len(v.mesh_inbox),
                    "state_keys": list(v.state.keys()),
                    "can_veto": v.can_veto,
                }
                for k, v in self.agents.items()
            },
        }


# ===================================================================
# Demo
# ===================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX Agent Role System — STOA Adaptation")
    print("=" * 60)

    registry = SwarmAgentRegistry()
    registry.spawn_full_swarm()

    print(f"\n[1] Swarm spawned: {len(registry.agents)} agents")
    for key, agent in registry.agents.items():
        veto = " (VETO)" if agent.can_veto else ""
        print(f"  • {key:12s} — {agent.description[:40]}...{veto}")

    print("\n[2] Simulating mesh broadcast...")
    registry.mesh_broadcast(
        sender="scout",
        message_type="SIGNAL",
        payload={"symbol": "SOL", "price": 145.2, "change_24h": 0.05},
    )
    print(f"  Analyst inbox: {len(registry.agents['analyst'].mesh_inbox)} message(s)")

    print("\n[3] Guardian HALT test...")
    result = registry.halt("drawdown > 15%", triggered_by="guardian")
    print(f"  {result}")

    print("\n[4] Resume test...")
    result = registry.resume("guardian")
    print(f"  {result}")

    print("\n[5] Final status:")
    print(json.dumps(registry.get_status(), indent=2, default=str))

    print("\n" + "=" * 60)
    print("Agent Role System ready.")
    print("=" * 60)
