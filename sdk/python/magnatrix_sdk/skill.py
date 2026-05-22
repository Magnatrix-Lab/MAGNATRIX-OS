#!/usr/bin/env python3
"""
skill.py — MAGNATRIX SDK Skill Loader
Load dan invoke skills dari SkillRegistry.
"""

from pathlib import Path
from typing import Dict, Optional, Any


class Skill:
    """Wrapper untuk MAGNATRIX skill."""

    def __init__(self, name: str, skills_dir: str = "skills"):
        self.name = name
        self.skills_dir = Path(skills_dir)
        self._content: Optional[str] = None

    def load(self) -> Optional[str]:
        """Load SKILL.md content."""
        skill_file = self.skills_dir / self.name / "SKILL.md"
        if skill_file.exists():
            self._content = skill_file.read_text(encoding="utf-8")
            return self._content
        return None

    def exists(self) -> bool:
        """Check apakah skill file exists."""
        return (self.skills_dir / self.name / "SKILL.md").exists()

    def to_prompt(self, context: Optional[Dict[str, Any]] = None) -> str:
        """Render skill sebagai LLM prompt."""
        content = self._content or self.load()
        if not content:
            return ""
        if context:
            import json
            return content + f"\n\n## Context\n```json\n{json.dumps(context, indent=2, default=str)}\n```"
        return content

    @classmethod
    def list_all(cls, skills_dir: str = "skills") -> list:
        """List semua available skills."""
        d = Path(skills_dir)
        if not d.exists():
            return []
        return [p.name for p in d.iterdir() if p.is_dir() and (p / "SKILL.md").exists()]
