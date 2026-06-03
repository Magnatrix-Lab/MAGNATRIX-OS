"""LLM Entity Tracker — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class EntityType(Enum):
    PERSON = auto()
    ORGANIZATION = auto()
    LOCATION = auto()
    DATE = auto()
    NUMBER = auto()

@dataclass
class Entity:
    id: str
    text: str
    entity_type: EntityType
    position: int
    metadata: Dict[str, Any] = field(default_factory=dict)

class EntityTracker:
    def __init__(self) -> None:
        self._entities: List[Entity] = []
        self._patterns: Dict[EntityType, List[str]] = {}

    def register_pattern(self, entity_type: EntityType, patterns: List[str]) -> None:
        self._patterns[entity_type] = patterns

    def extract(self, text: str) -> List[Entity]:
        entities = []
        for etype, patterns in self._patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text):
                    entities.append(Entity(
                        id=etype.name + "_" + str(match.start()),
                        text=match.group(),
                        entity_type=etype,
                        position=match.start()
                    ))
        return entities

    def track(self, text: str) -> Dict[str, List[Entity]]:
        entities = self.extract(text)
        by_type = {}
        for e in entities:
            if e.entity_type.name not in by_type:
                by_type[e.entity_type.name] = []
            by_type[e.entity_type.name].append(e)
        return by_type

    def get_stats(self, entities: List[Entity]) -> Dict[str, Any]:
        counts = {}
        for e in entities:
            counts[e.entity_type.name] = counts.get(e.entity_type.name, 0) + 1
        return {"total": len(entities), "by_type": counts}

def run() -> None:
    print("Entity Tracker test")
    e = EntityTracker()
    e.register_pattern(EntityType.PERSON, [r"\b[A-Z][a-z]+\b"])
    e.register_pattern(EntityType.LOCATION, [r"\b(?:Paris|London|Tokyo|New York)\b"])
    e.register_pattern(EntityType.NUMBER, [r"\b\d+\b"])
    text = "Alice went to Paris on March 15. She met Bob at the Eiffel Tower."
    entities = e.extract(text)
    for en in entities:
        print("  " + en.entity_type.name + " '" + en.text + "' at pos " + str(en.position))
    print("  Stats: " + str(e.get_stats(entities)))
    print("Entity Tracker test complete.")

if __name__ == "__main__":
    run()
