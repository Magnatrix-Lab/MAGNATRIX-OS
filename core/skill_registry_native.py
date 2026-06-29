"""
skill_registry_native.py
MAGNATRIX-OS — Skill Registry

Inspired by AgentSkillOS: Extensible registry for skill registration, versioning, and metadata. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class SkillEntry:
    skill_id: str
    name: str
    description: str
    version: str
    author: str
    language: str
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    is_active: bool = True
    stars: int = 0
    downloads: int = 0
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class SkillRegistry:
    """Extensible registry for skill registration, versioning, and metadata."""

    def __init__(self, registry_dir: str = "./skill_registry"):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(exist_ok=True)
        self.skills: Dict[str, SkillEntry] = {}
        self._load()

    def _load(self) -> None:
        file = self.registry_dir / "skills.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for sid, sd in data.items():
                        self.skills[sid] = SkillEntry(**sd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.registry_dir / "skills.json", "w", encoding="utf-8") as f:
            json.dump({sid: asdict(s) for sid, s in self.skills.items()}, f, indent=2)

    def register(self, skill_id: str, name: str, description: str, version: str,
                 author: str, language: str, tags: Optional[List[str]] = None,
                 dependencies: Optional[List[str]] = None) -> SkillEntry:
        entry = SkillEntry(
            skill_id=skill_id, name=name, description=description, version=version,
            author=author, language=language, tags=tags or [], dependencies=dependencies or [],
        )
        self.skills[skill_id] = entry
        self._save()
        return entry

    def update_version(self, skill_id: str, new_version: str) -> Optional[SkillEntry]:
        skill = self.skills.get(skill_id)
        if skill:
            skill.version = new_version
            self._save()
            return skill
        return None

    def activate(self, skill_id: str) -> bool:
        skill = self.skills.get(skill_id)
        if skill:
            skill.is_active = True
            self._save()
            return True
        return False

    def deactivate(self, skill_id: str) -> bool:
        skill = self.skills.get(skill_id)
        if skill:
            skill.is_active = False
            self._save()
            return True
        return False

    def get_skill(self, skill_id: str) -> Optional[SkillEntry]:
        return self.skills.get(skill_id)

    def search(self, query: str) -> List[SkillEntry]:
        q = query.lower()
        return [s for s in self.skills.values() if q in s.name.lower() or q in s.description.lower() or q in s.tags]

    def get_by_language(self, language: str) -> List[SkillEntry]:
        return [s for s in self.skills.values() if s.language == language]

    def get_stats(self) -> Dict[str, Any]:
        active = sum(1 for s in self.skills.values() if s.is_active)
        languages = {}
        for s in self.skills.values():
            languages[s.language] = languages.get(s.language, 0) + 1
        return {"total": len(self.skills), "active": active, "languages": languages}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["SkillRegistry", "SkillEntry"]