"""
agent_skills_library_native.py
MAGNATRIX-OS — Agent Skills Library

Inspired by Ponytail skills/rules: Reusable agent skills for IDE plugins (Claude, Cursor, Codex, Devin). Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class AgentSkill:
    skill_id: str
    name: str
    description: str
    rules: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    target_ide: str = "generic"
    usage_count: int = 0
    rating: float = 0.0
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class AgentSkillsLibrary:
    """Reusable agent skills for IDE plugins and AI agents."""

    BUILT_IN_SKILLS = {
        "yagni": {
            "name": "YAGNI Code", "description": "Write only what you need",
            "rules": ["No premature abstractions", "Defer features not needed now", "One-liner over module"],
            "tags": ["minimalism", "yagni"], "target_ide": "generic",
        },
        "comprehension_first": {
            "name": "Comprehension First", "description": "Understand before modifying",
            "rules": ["Read the full file before editing", "Check tests before changes", "Explain the why"],
            "tags": ["safety", "comprehension"], "target_ide": "generic",
        },
        "reuse_rung": {
            "name": "Reuse Rung", "description": "Check existing code before writing new",
            "rules": ["Search codebase for similar patterns", "Extend existing functions", "DRY principle"],
            "tags": ["reuse", "dry"], "target_ide": "generic",
        },
        "lazy_senior": {
            "name": "Lazy Senior Dev", "description": "The laziest correct solution is the best",
            "rules": ["Prefer stdlib over dependency", "Copy-paste over re-implement", "Minimal LOC"],
            "tags": ["lazy", "minimalism"], "target_ide": "generic",
        },
        "claude_specific": {
            "name": "Claude Plugin Rules", "description": "Rules for Claude Code plugin",
            "rules": ["Use @-mentions for context", "Follow .claude-plugin manifest", "Batch operations"],
            "tags": ["claude", "plugin"], "target_ide": "claude",
        },
        "cursor_specific": {
            "name": "Cursor Rules", "description": "Rules for Cursor IDE",
            "rules": ["Follow .cursor/rules", "Use @ symbol for references", "Comprehension-first edits"],
            "tags": ["cursor", "rules"], "target_ide": "cursor",
        },
        "codex_specific": {
            "name": "Codex Plugin", "description": "Rules for OpenAI Codex",
            "rules": ["Follow .codex-plugin manifest", "Use tool calls correctly", "Guard against loops"],
            "tags": ["codex", "plugin"], "target_ide": "codex",
        },
        "devin_specific": {
            "name": "Devin CLI", "description": "Rules for Devin agent",
            "rules": ["Follow .devin-plugin manifest", "Plan before execution", "Report progress"],
            "tags": ["devin", "cli"], "target_ide": "devin",
        },
    }

    def __init__(self, cache_dir: str = "./agent_skills"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.skills: Dict[str, AgentSkill] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "skills.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for sid, sd in data.items():
                        self.skills[sid] = AgentSkill(**sd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "skills.json", "w", encoding="utf-8") as f:
            json.dump({sid: asdict(s) for sid, s in self.skills.items()}, f, indent=2)

    def add_from_library(self, skill_id: str, new_id: Optional[str] = None) -> Optional[AgentSkill]:
        if skill_id not in self.BUILT_IN_SKILLS:
            return None
        info = self.BUILT_IN_SKILLS[skill_id]
        sid = new_id or skill_id
        skill = AgentSkill(
            skill_id=sid, name=info["name"], description=info["description"],
            rules=info.get("rules", []), tags=info.get("tags", []), target_ide=info.get("target_ide", "generic"),
        )
        self.skills[sid] = skill
        self._save()
        return skill

    def add_custom(self, skill_id: str, name: str, description: str, rules: List[str],
                   tags: Optional[List[str]] = None, target_ide: str = "generic") -> AgentSkill:
        skill = AgentSkill(
            skill_id=skill_id, name=name, description=description,
            rules=rules, tags=tags or [], target_ide=target_ide,
        )
        self.skills[skill_id] = skill
        self._save()
        return skill

    def use_skill(self, skill_id: str) -> Optional[List[str]]:
        skill = self.skills.get(skill_id)
        if not skill:
            return None
        skill.usage_count += 1
        self._save()
        return skill.rules

    def rate_skill(self, skill_id: str, rating: float) -> bool:
        skill = self.skills.get(skill_id)
        if not skill or not (0 <= rating <= 5):
            return False
        total = skill.rating * skill.usage_count + rating
        skill.usage_count += 1
        skill.rating = total / skill.usage_count
        self._save()
        return True

    def get_skills_for_ide(self, ide: str) -> List[AgentSkill]:
        return [s for s in self.skills.values() if s.target_ide == ide or s.target_ide == "generic"]

    def get_stats(self) -> Dict[str, Any]:
        return {"total_skills": len(self.skills), "library_size": len(self.BUILT_IN_SKILLS)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["AgentSkillsLibrary", "AgentSkill"]