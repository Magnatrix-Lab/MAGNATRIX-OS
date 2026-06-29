
"""
skill_loader_native.py
MAGNATRIX-OS — Skill Loader

Runtime skill loading and injection into agent contexts.
Inspired by SkillKit universal skills loader.

Pure Python standard library.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class LoadedSkill:
    skill_id: str
    name: str
    content: str
    format: str
    injected_at: str
    context_injection: str = ""


class SkillLoader:
    """Runtime skill loader for AI agent contexts."""

    def __init__(self, skills_dir: str = "./skills"):
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(exist_ok=True)
        self.loaded: Dict[str, LoadedSkill] = {}
        self.injection_hooks: List[Callable] = []
        self.active_skills: List[str] = []

    def load_from_file(self, filepath: str, skill_id: str = "") -> Optional[LoadedSkill]:
        path = Path(filepath)
        if not path.exists():
            return None
        content = path.read_text(encoding="utf-8")
        sid = skill_id or path.stem
        skill = LoadedSkill(
            skill_id=sid,
            name=path.stem,
            content=content,
            format=path.suffix.lstrip("."),
            injected_at=datetime.now().isoformat(),
        )
        self.loaded[sid] = skill
        return skill

    def load_from_string(self, skill_id: str, content: str, name: str = "", fmt: str = "md") -> LoadedSkill:
        skill = LoadedSkill(
            skill_id=skill_id,
            name=name or skill_id,
            content=content,
            format=fmt,
            injected_at=datetime.now().isoformat(),
        )
        self.loaded[skill_id] = skill
        return skill

    def load_all_from_directory(self) -> List[LoadedSkill]:
        skills = []
        for f in self.skills_dir.iterdir():
            if f.suffix in (".md", ".txt", ".skill", ".json"):
                skill = self.load_from_file(str(f))
                if skill:
                    skills.append(skill)
        return skills

    def inject_into_context(self, skill_id: str, base_context: str) -> str:
        """Inject a skill into an agent context."""
        skill = self.loaded.get(skill_id)
        if not skill:
            return base_context
        # Mark as active
        if skill_id not in self.active_skills:
            self.active_skills.append(skill_id)
        # Build injection
        injection = f"\n\n## Skill: {skill.name}\n{skill.content}\n"
        skill.context_injection = injection
        return base_context + injection

    def inject_multiple(self, skill_ids: List[str], base_context: str) -> str:
        """Inject multiple skills into context."""
        context = base_context
        for sid in skill_ids:
            context = self.inject_into_context(sid, context)
        return context

    def remove_from_context(self, skill_id: str, context: str) -> str:
        """Remove a skill from context."""
        skill = self.loaded.get(skill_id)
        if skill and skill.context_injection:
            return context.replace(skill.context_injection, "")
        return context

    def deactivate(self, skill_id: str) -> bool:
        if skill_id in self.active_skills:
            self.active_skills.remove(skill_id)
            return True
        return False

    def get_active(self) -> List[LoadedSkill]:
        return [self.loaded[sid] for sid in self.active_skills if sid in self.loaded]

    def resolve_dependencies(self, skill_id: str) -> List[str]:
        """Resolve skill dependencies."""
        # Simple dependency resolution
        resolved = [skill_id]
        # Check if skill has dependency metadata
        skill = self.loaded.get(skill_id)
        if skill:
            # Parse dependency comments from skill content
            for line in skill.content.splitlines():
                if line.startswith("# dependency:") or line.startswith("<!-- dependency:"):
                    dep = line.split(":", 1)[1].strip().strip("- >")
                    if dep not in resolved:
                        resolved.append(dep)
        return resolved

    def build_combined_context(self, skill_ids: List[str]) -> str:
        """Build a combined context with all skills and dependencies."""
        all_skills = set()
        for sid in skill_ids:
            all_skills.update(self.resolve_dependencies(sid))
        context = "## Active Skills\n\n"
        for sid in all_skills:
            skill = self.loaded.get(sid)
            if skill:
                context += f"### {skill.name}\n{skill.content}\n\n"
        return context

    def to_dict(self) -> Dict:
        return {
            "loaded_skills": len(self.loaded),
            "active_skills": len(self.active_skills),
            "skills_dir": str(self.skills_dir),
        }


__all__ = ["SkillLoader", "LoadedSkill"]
