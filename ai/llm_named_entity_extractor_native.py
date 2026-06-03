"""Named Entity Extractor - NER for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
import re

class EntityType(Enum):
    PERSON = auto(); ORG = auto(); LOC = auto(); DATE = auto(); MONEY = auto(); PERCENT = auto()

@dataclass
class NamedEntityExtractor:
    patterns: Dict[EntityType, List[str]] = field(default_factory=dict)

    def __post_init__(self):
        self.patterns = {EntityType.PERSON: ["Mr.", "Mrs.", "Dr.", "Prof."], EntityType.ORG: ["Inc.", "Corp.", "Ltd.", "University"], EntityType.LOC: ["Street", "City", "Country", "River"], EntityType.DATE: [r"\d{4}-\d{2}-\d{2}", r"January|February|March"], EntityType.MONEY: [r"\$\d+", r"\d+ dollars"], EntityType.PERCENT: [r"\d+\s*%", r"\d+ percent"]}

    def extract(self, text: str) -> List[tuple]:
        entities = []
        for etype, patterns in self.patterns.items():
            for pattern in patterns:
                if pattern.startswith("\\"):
                    for match in re.finditer(pattern, text):
                        entities.append((match.group(), etype, match.start(), match.end()))
                else:
                    words = re.findall(r"[a-zA-Z0-9.\$]+", text)
                    for word in words:
                        if pattern.lower() in word.lower():
                            idx = text.find(word)
                            if idx >= 0: entities.append((word, etype, idx, idx+len(word)))
        seen = set()
        unique = []
        for e in sorted(entities, key=lambda x: x[2]):
            key = (e[0], e[1], e[2])
            if key not in seen:
                seen.add(key); unique.append(e)
        return unique

    def stats(self, text: str) -> dict:
        entities = self.extract(text)
        counts = {}
        for _, etype, _, _ in entities:
            counts[etype.name] = counts.get(etype.name, 0) + 1
        return {"entities": len(entities), "counts": counts}

def run():
    ner = NamedEntityExtractor()
    text = "Apple Inc. is in Cupertino. $100B in 2023."
    print("Entities:", [(e[0], e[1].name) for e in ner.extract(text)])
    print("Stats:", ner.stats(text))

if __name__ == "__main__":
    run()
