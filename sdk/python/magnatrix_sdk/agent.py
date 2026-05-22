#!/usr/bin/env python3
"""
agent.py — MAGNATRIX SDK Agent Builder
Builder pattern untuk define dan spawn custom agents dalam swarm.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable


@dataclass
class Agent:
    """Builder untuk custom MAGNATRIX agent."""
    name: str
    role: str = "generic"  # scout, analyst, executor, guardian, researcher, writer, ops, architect
    description: str = ""
    personality: str = ""
    skills: List[str] = field(default_factory=list)
    schedule: str = "*/15 * * * *"
    can_veto: bool = False
    max_parallel_tasks: int = 3
    config: Dict[str, Any] = field(default_factory=dict)

    def with_skill(self, skill_name: str) -> "Agent":
        """Add skill ke agent."""
        if skill_name not in self.skills:
            self.skills.append(skill_name)
        return self

    def with_skills(self, skill_names: List[str]) -> "Agent":
        """Add multiple skills."""
        for s in skill_names:
            self.with_skill(s)
        return self

    def with_schedule(self, cron: str) -> "Agent":
        """Set cron schedule."""
        self.schedule = cron
        return self

    def with_veto(self, enabled: bool = True) -> "Agent":
        """Set veto power."""
        self.can_veto = enabled
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Export ke dict untuk API submission."""
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "personality": self.personality,
            "skills": self.skills,
            "schedule": self.schedule,
            "can_veto": self.can_veto,
            "max_parallel_tasks": self.max_parallel_tasks,
            "config": self.config,
        }

    @classmethod
    def from_template(cls, template_name: str, name: Optional[str] = None) -> "Agent":
        """Create agent dari template built-in."""
        templates = {
            "scout": {"role": "scout", "skills": ["scan-tokens", "web-monitor"]},
            "analyst": {"role": "analyst", "skills": ["analyze-signal", "forecast-model"]},
            "executor": {"role": "executor", "skills": ["execute-trade", "deploy-node"]},
            "guardian": {"role": "guardian", "skills": ["check-risk", "veto-trigger"], "can_veto": True},
            "researcher": {"role": "researcher", "skills": ["arxiv-scan", "protocol-deep-dive"]},
            "writer": {"role": "writer", "skills": ["daily-digest", "report-generate"]},
            "ops": {"role": "ops", "skills": ["repo-health", "gh-fix-ci"]},
            "architect": {"role": "architect", "skills": ["code-mutate", "mcp-builder"]},
        }
        t = templates.get(template_name, {})
        return cls(
            name=name or template_name,
            role=t.get("role", "generic"),
            skills=list(t.get("skills", [])),
            can_veto=t.get("can_veto", False),
        )
