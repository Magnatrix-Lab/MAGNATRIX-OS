"""Entity Linker — mention to entity disambiguation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import re

class EntityType(Enum):
    PERSON = auto()
    ORGANIZATION = auto()
    LOCATION = auto()
    PRODUCT = auto()
    EVENT = auto()

@dataclass
class Entity:
    entity_id: str
    label: str
    entity_type: EntityType
    aliases: List[str] = field(default_factory=list)
    popularity: float = 1.0

@dataclass
class Mention:
    text: str
    start: int
    end: int
    candidates: List[Tuple[str, float]] = field(default_factory=list)
    linked_entity: Optional[str] = None
    confidence: float = 0.0

class EntityLinker:
    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.alias_map: Dict[str, List[str]] = {}

    def add_entity(self, entity: Entity):
        self.entities[entity.entity_id] = entity
        for alias in [entity.label] + entity.aliases:
            alias_lower = alias.lower()
            if alias_lower not in self.alias_map:
                self.alias_map[alias_lower] = []
            self.alias_map[alias_lower].append(entity.entity_id)

    def find_mentions(self, text: str) -> List[Mention]:
        mentions = []
        # Simple token-based matching
        words = text.split()
        for i in range(len(words)):
            for j in range(i + 1, min(i + 4, len(words) + 1)):
                phrase = " ".join(words[i:j]).lower().strip(".,!?")
                if phrase in self.alias_map:
                    start = sum(len(w) + 1 for w in words[:i])
                    end = start + len(" ".join(words[i:j]))
                    mention = Mention(" ".join(words[i:j]), start, end)
                    mention.candidates = [(eid, self.entities[eid].popularity) for eid in self.alias_map[phrase]]
                    mention.candidates.sort(key=lambda x: x[1], reverse=True)
                    if mention.candidates:
                        mention.linked_entity = mention.candidates[0][0]
                        mention.confidence = mention.candidates[0][1] / sum(c[1] for c in mention.candidates) if sum(c[1] for c in mention.candidates) > 0 else 0
                    mentions.append(mention)
        return mentions

    def disambiguate(self, mention: Mention, context: str) -> str:
        # Simple context overlap scoring
        if not mention.candidates:
            return None
        context_words = set(context.lower().split())
        best_score = -1
        best = None
        for eid, pop in mention.candidates:
            entity = self.entities[eid]
            entity_words = set((entity.label + " " + " ".join(entity.aliases)).lower().split())
            overlap = len(context_words & entity_words)
            score = overlap + pop
            if score > best_score:
                best_score = score
                best = eid
        return best

    def link(self, text: str) -> List[Mention]:
        mentions = self.find_mentions(text)
        for m in mentions:
            if len(m.candidates) > 1:
                m.linked_entity = self.disambiguate(m, text)
        return mentions

    def stats(self) -> Dict:
        return {"entities": len(self.entities), "aliases": len(self.alias_map), "types": len(set(e.entity_type for e in self.entities.values()))}

def run():
    linker = EntityLinker()
    linker.add_entity(Entity("e1", "Apple", EntityType.ORGANIZATION, ["Apple Inc"], 10.0))
    linker.add_entity(Entity("e2", "Apple", EntityType.PRODUCT, ["fruit"], 5.0))
    linker.add_entity(Entity("e3", "Steve Jobs", EntityType.PERSON, ["Jobs"], 8.0))
    text = "Apple was founded by Steve Jobs. Apple is a tasty fruit."
    mentions = linker.link(text)
    for m in mentions:
        print(f"'{m.text}' -> {m.linked_entity} (conf={m.confidence:.2f})")
    print(linker.stats())

if __name__ == "__main__":
    run()
