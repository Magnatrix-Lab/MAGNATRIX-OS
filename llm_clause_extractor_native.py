"""Clause Extractor — indemnity, liability, force majeure, confidentiality, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
import re

class ClauseType(Enum):
    INDEMNITY = auto()
    LIABILITY = auto()
    FORCE_MAJEURE = auto()
    CONFIDENTIALITY = auto()
    TERMINATION = auto()
    GOVERNING_LAW = auto()

class ClauseExtractor:
    def __init__(self):
        self.patterns = {
            ClauseType.INDEMNITY: [r"indemnif", r"hold harmless", r"defend"],
            ClauseType.LIABILITY: [r"liabilit", r"limitation of liability", r"damages"],
            ClauseType.FORCE_MAJEURE: [r"force majeure", r"act of god", r"beyond.*control"],
            ClauseType.CONFIDENTIALITY: [r"confidential", r"non-disclosure", r"NDA"],
            ClauseType.TERMINATION: [r"terminat", r"cancel", r"breach"],
            ClauseType.GOVERNING_LAW: [r"governed by", r"jurisdiction", r"governing law"],
        }
        self.clauses: List[Dict] = []

    def extract(self, text: str) -> List[Dict]:
        found = []
        for clause_type, patterns in self.patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 150)
                    snippet = text[start:end]
                    found.append({"type": clause_type.name, "snippet": snippet, "position": match.start()})
        self.clauses.extend(found)
        return found

    def has_clause(self, text: str, clause_type: ClauseType) -> bool:
        patterns = self.patterns.get(clause_type, [])
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)

    def missing_clauses(self, text: str) -> List[str]:
        return [ct.name for ct in ClauseType if not self.has_clause(text, ct)]

    def stats(self) -> Dict:
        by_type = {}
        for c in self.clauses:
            t = c["type"]
            by_type[t] = by_type.get(t, 0) + 1
        return {"extracted": len(self.clauses), "by_type": by_type}

def run():
    ce = ClauseExtractor()
    text = "This agreement is governed by California law. The parties agree to confidentiality. In case of force majeure..."
    print(ce.extract(text))
    print("Missing:", ce.missing_clauses(text))
    print(ce.stats())

if __name__ == "__main__":
    run()
