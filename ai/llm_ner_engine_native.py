"""LLM NER Engine — Native Python (stdlib only)."""
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
    TIME = auto()
    MONEY = auto()
    PERCENT = auto()
    EMAIL = auto()
    URL = auto()
    PHONE = auto()
    HASHTAG = auto()
    MENTION = auto()

@dataclass
class NamedEntity:
    text: str
    entity_type: EntityType
    start: int
    end: int
    confidence: float = 1.0

class NEREngine:
    def __init__(self) -> None:
        self._patterns: List[tuple] = [
            (EntityType.EMAIL, re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')),
            (EntityType.URL, re.compile(r'https?://\S+')),
            (EntityType.PHONE, re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')),
            (EntityType.MONEY, re.compile(r'\$\d+(?:,\d{3})*(?:\.\d{2})?')),
            (EntityType.PERCENT, re.compile(r'\d+(?:\.\d+)?%')),
            (EntityType.DATE, re.compile(r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b')),
            (EntityType.TIME, re.compile(r'\b(?:\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?)\b')),
            (EntityType.HASHTAG, re.compile(r'#[A-Za-z]\w+')),
            (EntityType.MENTION, re.compile(r'@[A-Za-z]\w+')),
        ]
        self._known_names: Dict[str, EntityType] = {
            "alice": EntityType.PERSON, "bob": EntityType.PERSON, "charlie": EntityType.PERSON,
            "paris": EntityType.LOCATION, "london": EntityType.LOCATION, "tokyo": EntityType.LOCATION,
            "google": EntityType.ORGANIZATION, "microsoft": EntityType.ORGANIZATION, "apple": EntityType.ORGANIZATION,
            "amazon": EntityType.ORGANIZATION, "meta": EntityType.ORGANIZATION, "openai": EntityType.ORGANIZATION,
            "usa": EntityType.LOCATION, "indonesia": EntityType.LOCATION, "japan": EntityType.LOCATION,
        }

    def extract(self, text: str) -> List[NamedEntity]:
        entities = []
        for entity_type, pattern in self._patterns:
            for match in pattern.finditer(text):
                entities.append(NamedEntity(match.group(), entity_type, match.start(), match.end()))
        words = re.findall(r'\b\w+\b', text)
        for word in words:
            lower = word.lower()
            if lower in self._known_names:
                start = text.find(word)
                if start >= 0:
                    entities.append(NamedEntity(word, self._known_names[lower], start, start + len(word)))
        entities.sort(key=lambda e: e.start)
        deduped = []
        for e in entities:
            if not any(e.start >= ex.start and e.end <= ex.end for ex in deduped):
                deduped.append(e)
        return deduped

    def get_by_type(self, entities: List[NamedEntity], entity_type: EntityType) -> List[NamedEntity]:
        return [e for e in entities if e.entity_type == entity_type]

    def get_stats(self, entities: List[NamedEntity]) -> Dict[str, Any]:
        counts = {}
        for e in entities:
            counts[e.entity_type.name] = counts.get(e.entity_type.name, 0) + 1
        return {"total": len(entities), "by_type": counts}

def run() -> None:
    print("NER Engine test")
    e = NEREngine()
    text = "Alice from Google met Bob in Tokyo on 2024-01-15 at 3:00 PM. $500 budget, 25% increase. Contact test@email.com or visit https://example.com #AI @user"
    entities = e.extract(text)
    for ent in entities:
        print("  " + ent.entity_type.name + ": '" + ent.text + "' at " + str(ent.start))
    print("  People: " + str([e.text for e in e.get_by_type(entities, EntityType.PERSON)]))
    print("  Stats: " + str(e.get_stats(entities)))
    print("NER Engine test complete.")

if __name__ == "__main__":
    run()
