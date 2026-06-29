
"""
prompt_factory_native.py
MAGNATRIX-OS Prompt Factory

Modular prompt generation for LLM calls. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, field


@dataclass
class PromptTemplate:
    template_id: str
    name: str
    description: str
    system_prompt: str
    user_prompt_template: str
    variables: List[str] = field(default_factory=list)
    output_format: str = "json"


class PromptFactory:
    """Modular prompt generation for LLM calls."""

    BUILT_IN = {
        "triple_extraction": {
            "name": "Triple Extraction", "description": "Extract SPO triples",
            "system_prompt": "Extract Subject-Predicate-Object triples. Return JSON.",
            "user_prompt_template": "Extract triples from:\n\n{text}\n\nReturn JSON array.",
            "variables": ["text"], "output_format": "json",
        },
        "entity_standardization": {
            "name": "Entity Standardization", "description": "Standardize entity names",
            "system_prompt": "Group entities by canonical form.",
            "user_prompt_template": "Standardize these entities: {entities}\n\nReturn JSON.",
            "variables": ["entities"], "output_format": "json",
        },
        "relationship_inference": {
            "name": "Relationship Inference", "description": "Infer new relationships",
            "system_prompt": "Infer additional relationships from given entities.",
            "user_prompt_template": "Entities: {entities}\nRelations: {relations}\n\nInfer new relationships.",
            "variables": ["entities", "relations"], "output_format": "json",
        },
    }

    def __init__(self, cache_dir: str = "./prompt_factory"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.templates: Dict[str, PromptTemplate] = {}
        self._load()
        self._init_builtin()

    def _init_builtin(self) -> None:
        for tid, info in self.BUILT_IN.items():
            if tid not in self.templates:
                self.templates[tid] = PromptTemplate(template_id=tid, **info)

    def _load(self) -> None:
        f = self.cache_dir / "templates.json"
        if f.exists():
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                    for tid, td in data.items():
                        self.templates[tid] = PromptTemplate(**td)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "templates.json", "w", encoding="utf-8") as f:
            json.dump({tid: {"template_id": t.template_id, "name": t.name, "description": t.description, "system_prompt": t.system_prompt, "user_prompt_template": t.user_prompt_template, "variables": t.variables, "output_format": t.output_format} for tid, t in self.templates.items()}, f, indent=2)

    def create(self, template_id: str, name: str, description: str, system_prompt: str, user_prompt_template: str, variables: List[str], output_format: str = "json") -> PromptTemplate:
        t = PromptTemplate(template_id=template_id, name=name, description=description, system_prompt=system_prompt, user_prompt_template=user_prompt_template, variables=variables, output_format=output_format)
        self.templates[template_id] = t
        self._save()
        return t

    def render(self, template_id: str, **kwargs) -> Dict[str, str]:
        t = self.templates.get(template_id)
        if not t:
            return {"error": f"Template {template_id} not found"}
        user = t.user_prompt_template
        for key, value in kwargs.items():
            user = user.replace("{" + key + "}", str(value))
        return {"system": t.system_prompt, "user": user, "format": t.output_format}

    def get_stats(self) -> Dict[str, Any]:
        return {"total_templates": len(self.templates), "built_in": len(self.BUILT_IN)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["PromptFactory", "PromptTemplate"]
