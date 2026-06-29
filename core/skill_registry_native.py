
"""
skill_registry_native.py
MAGNATRIX-OS — Skill Registry

Inspired by SkillKit (rohitg00/skillkit):
Central skill registry with portable skill definitions, versioning,
metadata, and cross-platform compatibility tracking.

Pure Python standard library.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto


class SkillFormat(Enum):
    CLAUDE = "claude"           # Claude Code / Claude Desktop
    CURSOR = "cursor"           # Cursor IDE
    CODEX = "codex"             # OpenAI Codex
    COPILOT = "copilot"         # GitHub Copilot
    WINDSURF = "windsurf"       # Windsurf/Codium
    HERMES = "hermes"           # Hermes Agent
    AIDER = "aider"             # Aider
    OPENCODE = "opencode"       # OpenCode
    GENERIC = "generic"         # Generic/markdown


@dataclass
class SkillDefinition:
    skill_id: str
    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    tags: List[str] = field(default_factory=list)
    formats: Dict[str, str] = field(default_factory=dict)  # format -> content
    metadata: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    usage_count: int = 0
    rating: float = 0.0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at

    def fingerprint(self) -> str:
        content = json.dumps({"name": self.name, "version": self.version, "tags": sorted(self.tags)}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class SkillRegistry:
    """Central registry for portable AI agent skills."""

    def __init__(self, registry_file: str = "skill_registry.json"):
        self.registry_file = Path(registry_file)
        self.skills: Dict[str, SkillDefinition] = {}
        self.tags_index: Dict[str, Set[str]] = {}
        self.author_index: Dict[str, Set[str]] = {}
        self._load()

    def _load(self) -> None:
        if self.registry_file.exists():
            with open(self.registry_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for sid, sd in data.items():
                    self.skills[sid] = SkillDefinition(**sd)
                self._rebuild_indexes()

    def _save(self) -> None:
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump({sid: asdict(s) for sid, s in self.skills.items()}, f, indent=2)

    def _rebuild_indexes(self) -> None:
        self.tags_index = {}
        self.author_index = {}
        for sid, skill in self.skills.items():
            for tag in skill.tags:
                self.tags_index.setdefault(tag, set()).add(sid)
            if skill.author:
                self.author_index.setdefault(skill.author, set()).add(sid)

    def register(self, skill: SkillDefinition) -> bool:
        self.skills[skill.skill_id] = skill
        self._rebuild_indexes()
        self._save()
        return True

    def unregister(self, skill_id: str) -> bool:
        if skill_id in self.skills:
            del self.skills[skill_id]
            self._rebuild_indexes()
            self._save()
            return True
        return False

    def get(self, skill_id: str) -> Optional[SkillDefinition]:
        return self.skills.get(skill_id)

    def get_format(self, skill_id: str, format: SkillFormat) -> Optional[str]:
        skill = self.skills.get(skill_id)
        if skill:
            return skill.formats.get(format.value) or skill.formats.get(SkillFormat.GENERIC.value)
        return None

    def search(self, query: str) -> List[SkillDefinition]:
        """Search skills by name, description, tags."""
        q = query.lower()
        results = []
        for skill in self.skills.values():
            if q in skill.name.lower() or q in skill.description.lower() or q in " ".join(skill.tags).lower():
                results.append(skill)
        return results

    def search_by_tag(self, tag: str) -> List[SkillDefinition]:
        sids = self.tags_index.get(tag, set())
        return [self.skills[sid] for sid in sids if sid in self.skills]

    def list_by_author(self, author: str) -> List[SkillDefinition]:
        sids = self.author_index.get(author, set())
        return [self.skills[sid] for sid in sids if sid in self.skills]

    def get_all_formats(self, skill_id: str) -> Dict[str, str]:
        skill = self.skills.get(skill_id)
        return skill.formats if skill else {}

    def increment_usage(self, skill_id: str) -> None:
        if skill_id in self.skills:
            self.skills[skill_id].usage_count += 1
            self._save()

    def rate(self, skill_id: str, rating: float) -> None:
        if skill_id in self.skills:
            s = self.skills[skill_id]
            # EMA rating update
            s.rating = 0.7 * s.rating + 0.3 * rating if s.rating > 0 else rating
            self._save()

    def to_dict(self) -> Dict:
        return {
            "total_skills": len(self.skills),
            "total_tags": len(self.tags_index),
            "total_authors": len(self.author_index),
        }


__all__ = ["SkillRegistry", "SkillDefinition", "SkillFormat"]
