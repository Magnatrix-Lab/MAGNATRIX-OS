"""
skill_execution_engine_native.py
MAGNATRIX-OS — Skill Execution Engine

Inspired by Deer-Flow (ByteDance): Skills system with templates and execution.
Define, parameterize, and execute agent skills with input/output validation. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class SkillTemplate:
    skill_id: str
    name: str
    description: str
    template: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    category: str = "general"
    usage_count: int = 0
    avg_latency_ms: float = 0.0


class SkillExecutionEngine:
    """Define, parameterize, and execute agent skills."""

    BUILT_IN_SKILLS = {
        "research_topic": {
            "name": "Research Topic", "description": "Deep research on a topic",
            "template": "Research the topic: {topic}. Find {num_sources} sources and summarize key findings.",
            "parameters": {"topic": "string", "num_sources": "integer"}, "category": "research",
        },
        "code_review": {
            "name": "Code Review", "description": "Review code for quality",
            "template": "Review the following {language} code for bugs, style, and performance issues:\\n{code}",
            "parameters": {"language": "string", "code": "string"}, "category": "development",
        },
        "generate_tests": {
            "name": "Generate Tests", "description": "Generate unit tests for code",
            "template": "Generate {framework} tests for the following function:\\n{code}",
            "parameters": {"framework": "string", "code": "string"}, "category": "development",
        },
        "summarize_document": {
            "name": "Summarize Document", "description": "Summarize a long document",
            "template": "Summarize the following document in {max_words} words:\\n{document}",
            "parameters": {"document": "string", "max_words": "integer"}, "category": "nlp",
        },
        "extract_entities": {
            "name": "Extract Entities", "description": "Extract named entities from text",
            "template": "Extract all {entity_types} from the following text:\\n{text}",
            "parameters": {"text": "string", "entity_types": "list"}, "category": "nlp",
        },
        "create_outline": {
            "name": "Create Outline", "description": "Create a structured outline",
            "template": "Create a {depth}-level outline for: {topic}",
            "parameters": {"topic": "string", "depth": "integer"}, "category": "writing",
        },
        "compare_options": {
            "name": "Compare Options", "description": "Compare multiple options",
            "template": "Compare the following options based on {criteria}:\\n{options}",
            "parameters": {"options": "list", "criteria": "list"}, "category": "analysis",
        },
        "debug_error": {
            "name": "Debug Error", "description": "Debug an error with context",
            "template": "Debug the following error in {language}:\\nError: {error}\\nContext: {context}",
            "parameters": {"error": "string", "context": "string", "language": "string"}, "category": "development",
        },
    }

    def __init__(self, skills_dir: str = "./skills"):
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(exist_ok=True)
        self.skills: Dict[str, SkillTemplate] = {}
        self._load()

    def _load(self) -> None:
        file = self.skills_dir / "skills.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for sid, sd in data.items():
                        self.skills[sid] = SkillTemplate(**sd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.skills_dir / "skills.json", "w", encoding="utf-8") as f:
            json.dump({sid: asdict(s) for sid, s in self.skills.items()}, f, indent=2)

    def register(self, skill_id: str, name: str, description: str, template: str,
                 parameters: Dict[str, Any], category: str = "general") -> SkillTemplate:
        skill = SkillTemplate(
            skill_id=skill_id, name=name, description=description,
            template=template, parameters=parameters, category=category,
        )
        self.skills[skill_id] = skill
        self._save()
        return skill

    def register_builtin(self, skill_id: str) -> Optional[SkillTemplate]:
        if skill_id not in self.BUILT_IN_SKILLS:
            return None
        info = self.BUILT_IN_SKILLS[skill_id]
        return self.register(
            skill_id=skill_id, name=info["name"], description=info["description"],
            template=info["template"], parameters=info["parameters"], category=info["category"],
        )

    def execute(self, skill_id: str, params: Dict[str, Any]) -> Optional[str]:
        """Execute a skill by filling in the template."""
        skill = self.skills.get(skill_id)
        if not skill:
            return None
        try:
            result = skill.template.format(**params)
            skill.usage_count += 1
            self._save()
            return result
        except KeyError:
            return None

    def validate(self, skill_id: str, params: Dict[str, Any]) -> bool:
        skill = self.skills.get(skill_id)
        if not skill:
            return False
        for key in skill.parameters:
            if key not in params:
                return False
        return True

    def get_skill(self, skill_id: str) -> Optional[SkillTemplate]:
        return self.skills.get(skill_id)

    def list_skills(self, category: Optional[str] = None) -> List[SkillTemplate]:
        if category:
            return [s for s in self.skills.values() if s.category == category]
        return list(self.skills.values())

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.skills)
        total_usage = sum(s.usage_count for s in self.skills.values())
        return {"total_skills": total, "builtin_skills": len(self.BUILT_IN_SKILLS), "total_usage": total_usage}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["SkillExecutionEngine", "SkillTemplate"]