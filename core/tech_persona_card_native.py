"""
tech_persona_card_native.py
MAGNATRIX-OS — Tech Persona Card Engine

Inspired by telagod/code-abyss Tech Persona Card v1.0:
Portable AI agent persona interchange format with bidirectional conversion. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class TechPersonaCard:
    card_version: str
    persona_id: str
    name: str
    voice: str
    capabilities: List[str] = field(default_factory=list)
    scenarios: List[str] = field(default_factory=list)
    identity_content: str = ""
    behavior_rules: List[str] = field(default_factory=list)
    style_preferences: Dict[str, Any] = field(default_factory=dict)


class TechPersonaCardEngine:
    """Tech Persona Card v1.0 — portable AI agent persona interchange format."""

    def __init__(self, data_dir: str = "./persona_cards"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.cards: Dict[str, TechPersonaCard] = {}
        self._load()

    def _load(self) -> None:
        file = self.data_dir / "cards.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for pid, cd in data.items():
                        self.cards[pid] = TechPersonaCard(**cd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.data_dir / "cards.json", "w", encoding="utf-8") as f:
            json.dump({k: asdict(v) for k, v in self.cards.items()}, f, indent=2)

    def create_card(self, persona_id: str, name: str, voice: str, capabilities: List[str],
                    scenarios: List[str], identity_content: str, behavior_rules: List[str],
                    style_preferences: Optional[Dict[str, Any]] = None) -> TechPersonaCard:
        card = TechPersonaCard(
            card_version="1.0", persona_id=persona_id, name=name, voice=voice,
            capabilities=capabilities, scenarios=scenarios, identity_content=identity_content,
            behavior_rules=behavior_rules, style_preferences=style_preferences or {},
        )
        self.cards[persona_id] = card
        self._save()
        return card

    def to_gpt_instructions(self, persona_id: str) -> Optional[str]:
        """Convert persona card to OpenAI Custom GPT instructions."""
        card = self.cards.get(persona_id)
        if not card:
            return None
        lines = [
            f"# {card.name}",
            f"## Voice\n{card.voice}",
            f"## Identity\n{card.identity_content}",
            "## Capabilities",
        ] + [f"- {c}" for c in card.capabilities] + [
            "## Scenarios",
        ] + [f"- {s}" for s in card.scenarios] + [
            "## Behavior Rules",
        ] + [f"- {r}" for r in card.behavior_rules]
        return "\n\n".join(lines)

    def to_chara_card_v2(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """Convert to Character Card V2 format."""
        card = self.cards.get(persona_id)
        if not card:
            return None
        return {
            "name": card.name, "description": card.identity_content,
            "personality": card.voice, "scenario": ", ".join(card.scenarios),
            "first_mes": f"Hello, I am {card.name}. Ready to assist.",
            "mes_example": "", "creatorcomment": "", "tags": card.capabilities,
            "character_version": card.card_version,
        }

    def from_chara_card_v2(self, card_data: Dict[str, Any]) -> TechPersonaCard:
        """Import from Character Card V2 format."""
        return self.create_card(
            persona_id=card_data.get("name", "unknown").lower().replace(" ", "-"),
            name=card_data.get("name", "Unknown"),
            voice=card_data.get("personality", ""),
            capabilities=card_data.get("tags", []),
            scenarios=[card_data.get("scenario", "")],
            identity_content=card_data.get("description", ""),
            behavior_rules=[],
            style_preferences={},
        )

    def get_card(self, persona_id: str) -> Optional[TechPersonaCard]:
        return self.cards.get(persona_id)

    def get_stats(self) -> Dict[str, Any]:
        return {"total_cards": len(self.cards), "version": "1.0"}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["TechPersonaCardEngine", "TechPersonaCard"]