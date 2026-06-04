"""Relation Extractor - Pattern-based relation extraction for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import re

class RelationType(Enum):
    WORKS_AT = auto(); LOCATED_IN = auto(); FOUNDED_BY = auto()

@dataclass
class RelationExtractor:
    patterns: Dict[RelationType, List[str]] = field(default_factory=dict)

    def __post_init__(self):
        if not self.patterns:
            self.patterns = {
                RelationType.WORKS_AT: ["works at", "employed by", "works for"],
                RelationType.LOCATED_IN: ["located in", "based in", "headquartered in"],
                RelationType.FOUNDED_BY: ["founded by", "created by", "started by"]
            }

    def extract(self, text: str) -> List[Tuple[str, str, str]]:
        relations = []
        for rtype, patterns in self.patterns.items():
            for pattern in patterns:
                m = re.search(rf"([A-Z][a-zA-Z]+)\s+{pattern}\s+([A-Z][a-zA-Z]+)", text)
                if m:
                    relations.append((m.group(1), rtype.name, m.group(2)))
        return relations

    def stats(self, text: str) -> dict:
        relations = self.extract(text)
        return {"relations": len(relations), "types": list(set(r[1] for r in relations))}

def run():
    re = RelationExtractor()
    text = "Alice works at Google. Google is located in California."
    print("Relations:", re.extract(text))
    print("Stats:", re.stats(text))

if __name__ == "__main__": run()
