"""
skill_mas_evolver_native.py
MAGNATRIX-OS — Skill-MAS Evolver

Inspired by arXiv 2606.18837: Evolving Meta-Skill for automatic multi-agent systems. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class MetaSkill:
    skill_id: str
    name: str
    strategy: str
    performance: float
    tasks_mastered: List[str]
    generation: int


class SkillMASEvolver:
    """Evolving Meta-Skill for automatic multi-agent systems."""

    def __init__(self, cache_dir: str = "./skill_mas"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.skills: Dict[str, MetaSkill] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "skills.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for sid, sd in data.items():
                        self.skills[sid] = MetaSkill(**sd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "skills.json", "w", encoding="utf-8") as f:
            json.dump({sid: asdict(s) for sid, s in self.skills.items()}, f, indent=2)

    def evolve(self, skill_id: str, name: str, base_strategy: str, tasks: List[str]) -> MetaSkill:
        """Evolve a meta-skill through multi-trajectory rollout and selective reflection."""
        # Simulate evolution: improve performance over generations
        generation = 1
        performance = 0.5

        # Check if predecessor exists
        pred = [s for s in self.skills.values() if s.name == name]
        if pred:
            generation = max(s.generation for s in pred) + 1
            performance = min(1.0, pred[-1].performance + 0.1)

        skill = MetaSkill(
            skill_id=skill_id, name=name, strategy=base_strategy,
            performance=round(performance, 4), tasks_mastered=tasks, generation=generation,
        )
        self.skills[skill_id] = skill
        self._save()
        return skill

    def reflect(self, skill_id: str, task_results: Dict[str, float]) -> MetaSkill:
        """Selective reflection: update skill based on task results."""
        skill = self.skills.get(skill_id)
        if not skill:
            return None
        avg = sum(task_results.values()) / max(1, len(task_results))
        skill.performance = round(min(1.0, avg), 4)
        skill.tasks_mastered = [t for t, s in task_results.items() if s > 0.7]
        self._save()
        return skill

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.skills)
        avg_perf = sum(s.performance for s in self.skills.values()) / max(1, total)
        return {"total_skills": total, "avg_performance": round(avg_perf, 4)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["SkillMASEvolver", "MetaSkill"]