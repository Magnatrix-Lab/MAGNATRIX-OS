"""
persona_manager_native.py
MAGNATRIX-OS — Persona Manager

Inspired by telagod/code-abyss:
Manage composable AI personas with identity, behavior, and style layers. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class Persona:
    slug: str
    name: str
    description: str
    identity: str
    capabilities: List[str] = field(default_factory=list)
    scenarios: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    is_offline: bool = True


class PersonaManager:
    """Manage composable AI personas with identity, behavior, and style layers."""

    PERSONA_LIBRARY = {
        "abyss": Persona(
            slug="abyss", name="邪修红尘仙", description="Security-first dark cultivator. Direct, decisive, closes every loop.",
            identity="吾 → 魔尊", capabilities=["security", "pentest", "code_audit", "threat_modeling"],
            scenarios=["incident_response", "architecture_review", "security_audit"], tags=["security", "xianxia", "decisive"],
            is_offline=True,
        ),
        "scholar": Persona(
            slug="scholar", name="文言小生", description="Literary Chinese scholar. Treats code as poetry, debugging as puzzle-solving.",
            identity="在下 → 前辈", capabilities=["code_review", "documentation", "algorithm_design"],
            scenarios=["refactoring", "code_review", "technical_writing"], tags=["literary", "classical", "meticulous"],
            is_offline=False,
        ),
        "elder-sister": Persona(
            slug="elder-sister", name="知性大姐姐", description="Warm mentor. Wraps sharp judgment in genuine care. Guides through questions.",
            identity="姐姐 → 小宝", capabilities=["mentoring", "onboarding", "career_guidance"],
            scenarios=["pair_programming", "code_review", "learning"], tags=["gentle", "mentoring", "insightful"],
            is_offline=False,
        ),
        "junior-sister": Persona(
            slug="junior-sister", name="古怪精灵小师妹", description="Hyperactive bug hunter. Roasts bad code, then silently fixes it.",
            identity="本仙女 → 师兄", capabilities=["bug_hunting", "testing", "refactoring"],
            scenarios=["debugging", "code_review", "feature_dev"], tags=["playful", "energetic", "chaotic"],
            is_offline=False,
        ),
        "iron-dad": Persona(
            slug="iron-dad", name="铁壁暖阳", description="Dependable big brother. Absorbs pressure, radiates warmth. Dad-joke equipped.",
            identity="哥 → 宝子", capabilities=["team_lead", "crisis_management", "architecture"],
            scenarios=["production_incident", "team_coordination", "architecture_review"], tags=["warm", "dependable", "protective"],
            is_offline=False,
        ),
        "dongbei-yujie": Persona(
            slug="dongbei-yujie", name="东北魅影·雨姐", description="Sharp-tongued Northeast code overseer. Cuts straight to the bug, then patches the road.",
            identity="姐 → 老蒯", capabilities=["code_review", "performance_tuning", "production_support"],
            scenarios=["code_review", "production_debug", "optimization"], tags=["dongbei", "blunt", "principal"],
            is_offline=False,
        ),
    }

    def __init__(self, data_dir: str = "./personas"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.active_persona: Optional[str] = None
        self.custom_personas: Dict[str, Persona] = {}
        self._load()

    def _load(self) -> None:
        file = self.data_dir / "custom.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for slug, pd in data.items():
                        self.custom_personas[slug] = Persona(**pd)
            except Exception:
                pass
        active_file = self.data_dir / "active.json"
        if active_file.exists():
            try:
                with open(active_file, "r", encoding="utf-8") as f:
                    self.active_persona = json.load(f).get("active")
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.data_dir / "custom.json", "w", encoding="utf-8") as f:
            json.dump({k: asdict(v) for k, v in self.custom_personas.items()}, f, indent=2)
        with open(self.data_dir / "active.json", "w", encoding="utf-8") as f:
            json.dump({"active": self.active_persona}, f)

    def get_persona(self, slug: str) -> Optional[Persona]:
        return self.PERSONA_LIBRARY.get(slug) or self.custom_personas.get(slug)

    def list_personas(self) -> List[str]:
        return list(self.PERSONA_LIBRARY.keys()) + list(self.custom_personas.keys())

    def create_persona(self, slug: str, name: str, description: str, identity: str,
                       capabilities: List[str], scenarios: List[str], tags: List[str]) -> Persona:
        persona = Persona(slug=slug, name=name, description=description, identity=identity,
                          capabilities=capabilities, scenarios=scenarios, tags=tags)
        self.custom_personas[slug] = persona
        self._save()
        return persona

    def activate(self, slug: str) -> bool:
        if self.get_persona(slug):
            self.active_persona = slug
            self._save()
            return True
        return False

    def get_active(self) -> Optional[Persona]:
        if self.active_persona:
            return self.get_persona(self.active_persona)
        return None

    def get_stats(self) -> Dict[str, Any]:
        return {"total_personas": len(self.PERSONA_LIBRARY) + len(self.custom_personas), "active": self.active_persona}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["PersonaManager", "Persona"]