"""NER Extractor — named entity recognition, types, spans, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum, auto
import re

class EntityCategory(Enum):
    PERSON = auto()
    ORG = auto()
    LOC = auto()
    DATE = auto()
    MONEY = auto()
    PRODUCT = auto()
    EVENT = auto()

@dataclass
class NamedEntity:
    text: str
    start: int
    end: int
    category: EntityCategory
    confidence: float = 1.0

class NERExtractor:
    def __init__(self):
        self.patterns = {
            EntityCategory.PERSON: [r"[A-Z][a-z]+\s[A-Z][a-z]+"],
            EntityCategory.ORG: [r"[A-Z][a-z]*\s?(Inc|Corp|Ltd|LLC|Company|Bank)"],
            EntityCategory.LOC: [r"(New York|London|Paris|Tokyo|Berlin|Beijing|Singapore)"],
            EntityCategory.DATE: [r"\d{1,2}/\d{1,2}/\d{2,4}", r"(January|February|March|April|May|June|July|August|September|October|November|December)\s\d{1,2}"],
            EntityCategory.MONEY: [r"\$\d+(?:,\d{3})*(?:\.\d{2})?"],
        }
        self.gazetteers = {
            EntityCategory.PERSON: {"John", "Alice", "Bob", "Charlie", "David", "Emma"},
            EntityCategory.ORG: {"Google", "Microsoft", "Apple", "Amazon", "Meta"},
            EntityCategory.LOC: {"USA", "UK", "Japan", "Germany", "France", "China"},
        }

    def extract(self, text: str) -> List[NamedEntity]:
        entities = []
        for category, patterns in self.patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text):
                    entities.append(NamedEntity(match.group(), match.start(), match.end(), category))
        # Gazetteer lookup
        words = text.split()
        pos = 0
        for word in words:
            clean = re.sub(r"[^\w]", "", word)
            for category, names in self.gazetteers.items():
                if clean in names:
                    entities.append(NamedEntity(clean, pos, pos + len(word), category))
            pos += len(word) + 1
        # Merge overlapping
        entities.sort(key=lambda e: e.start)
        merged = []
        for e in entities:
            if merged and e.start < merged[-1].end and e.category == merged[-1].category:
                continue
            merged.append(e)
        return merged

    def extract_by_type(self, text: str, category: EntityCategory) -> List[NamedEntity]:
        return [e for e in self.extract(text) if e.category == category]

    def stats(self) -> Dict:
        return {"patterns": sum(len(v) for v in self.patterns.values()), "gazetteers": sum(len(v) for v in self.gazetteers.values())}

def run():
    ner = NERExtractor()
    text = "Alice works at Google in New York. She earned $50000 on January 15."
    entities = ner.extract(text)
    for e in entities:
        print(f"{e.category.name}: {e.text}")
    print(ner.stats())

if __name__ == "__main__":
    run()
