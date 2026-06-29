
"""
skill_composer_native.py
MAGNATRIX-OS — Skill Composer

Compose multiple skills into complex agent workflows.
Chain skills, conditionally activate, and create skill pipelines.
Inspired by SkillKit composability.

Pure Python standard library.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto


class CompositionType(Enum):
    SEQUENTIAL = auto()
    PARALLEL = auto()
    CONDITIONAL = auto()
    LOOP = auto()
    MERGE = auto()


@dataclass
class SkillStep:
    step_id: str
    skill_id: str
    condition: Optional[str] = None
    outputs: Dict[str, str] = field(default_factory=dict)
    retry_count: int = 0


@dataclass
class Composition:
    composition_id: str
    name: str
    composition_type: CompositionType
    steps: List[SkillStep] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class SkillComposer:
    """Compose skills into complex workflows."""

    def __init__(self, registry=None):
        self.registry = registry
        self.compositions: Dict[str, Composition] = {}
        self.composition_file = Path("skill_compositions.json")
        self._load()

    def _load(self) -> None:
        if self.composition_file.exists():
            with open(self.composition_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for cid, cd in data.items():
                    self.compositions[cid] = Composition(**cd)

    def _save(self) -> None:
        with open(self.composition_file, "w", encoding="utf-8") as f:
            json.dump({cid: asdict(c) for cid, c in self.compositions.items()}, f, indent=2)

    def create_composition(self, name: str, comp_type: CompositionType) -> Composition:
        comp = Composition(
            composition_id=f"comp_{int(datetime.now().timestamp())}",
            name=name,
            composition_type=comp_type,
        )
        self.compositions[comp.composition_id] = comp
        self._save()
        return comp

    def add_step(self, comp_id: str, skill_id: str, condition: Optional[str] = None) -> bool:
        comp = self.compositions.get(comp_id)
        if not comp:
            return False
        step = SkillStep(
            step_id=f"step_{len(comp.steps)}_{int(datetime.now().timestamp())}",
            skill_id=skill_id,
            condition=condition,
        )
        comp.steps.append(step)
        self._save()
        return True

    def execute(self, comp_id: str, initial_context: str = "") -> Dict:
        """Execute a composition."""
        comp = self.compositions.get(comp_id)
        if not comp:
            return {"error": "Composition not found"}
        results = {"composition_id": comp_id, "steps": [], "final_context": initial_context}
        context = initial_context
        if comp.composition_type == CompositionType.SEQUENTIAL:
            for step in comp.steps:
                context = self._execute_step(step, context)
                results["steps"].append({"step_id": step.step_id, "skill_id": step.skill_id, "context_length": len(context)})
        elif comp.composition_type == CompositionType.PARALLEL:
            # For parallel, collect all skill contents and merge
            contents = []
            for step in comp.steps:
                content = self._get_skill_content(step.skill_id)
                if content:
                    contents.append(content)
            context = initial_context + "\n\n".join(contents)
            results["steps"] = [{"step_id": s.step_id, "skill_id": s.skill_id} for s in comp.steps]
        elif comp.composition_type == CompositionType.CONDITIONAL:
            for step in comp.steps:
                if step.condition and self._evaluate_condition(step.condition, comp.variables):
                    context = self._execute_step(step, context)
                    results["steps"].append({"step_id": step.step_id, "executed": True})
                else:
                    results["steps"].append({"step_id": step.step_id, "executed": False, "reason": "condition_not_met"})
        elif comp.composition_type == CompositionType.MERGE:
            # Merge all skill contexts
            merged = [context]
            for step in comp.steps:
                content = self._get_skill_content(step.skill_id)
                if content:
                    merged.append(content)
            context = "\n\n---\n\n".join(merged)
            results["steps"] = [{"step_id": s.step_id, "skill_id": s.skill_id} for s in comp.steps]
        results["final_context"] = context
        return results

    def _execute_step(self, step: SkillStep, context: str) -> str:
        content = self._get_skill_content(step.skill_id)
        if content:
            return context + f"\n\n## Applied Skill: {step.skill_id}\n{content}"
        return context

    def _get_skill_content(self, skill_id: str) -> Optional[str]:
        if self.registry:
            skill = self.registry.get(skill_id)
            if skill:
                # Return generic format content
                return skill.formats.get("generic", "") or skill.description
        return None

    def _evaluate_condition(self, condition: str, variables: Dict) -> bool:
        try:
            # Simple condition evaluation
            for key, value in variables.items():
                condition = condition.replace(f"${{{key}}}", str(value))
            return eval(condition, {"__builtins__": {}}, {})  # Safe eval with no builtins
        except Exception:
            return False

    def delete_composition(self, comp_id: str) -> bool:
        if comp_id in self.compositions:
            del self.compositions[comp_id]
            self._save()
            return True
        return False

    def list_compositions(self) -> List[Dict]:
        return [asdict(c) for c in self.compositions.values()]

    def to_dict(self) -> Dict:
        return {
            "total_compositions": len(self.compositions),
            "composition_types": [t.name for t in CompositionType],
        }


__all__ = ["SkillComposer", "Composition", "SkillStep", "CompositionType"]
