"""Semantics Extractor — word sense, semantic roles, relations, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
import re

@dataclass
class SemanticsExtractor:
    word_senses: Dict[str, List[str]] = field(default_factory=dict)
    semantic_roles: Dict[str, str] = field(default_factory=dict)

    def add_sense(self, word: str, senses: List[str]):
        self.word_senses[word] = senses

    def disambiguate(self, word: str, context: str) -> str:
        senses = self.word_senses.get(word, [word])
        context_lower = context.lower()
        for sense in senses:
            if sense.lower() in context_lower:
                return sense
        return senses[0] if senses else word

    def extract_entities(self, text: str) -> List[Tuple[str, str]]:
        entities = []
        patterns = [
            ("PERSON", r'[A-Z][a-z]+\s[A-Z][a-z]+'),
            ("DATE", r'\d{1,2}/\d{1,2}/\d{2,4}'),
            ("ORG", r'[A-Z][A-Z]+'),
        ]
        for label, pattern in patterns:
            for m in re.finditer(pattern, text):
                entities.append((label, m.group()))
        return entities

    def semantic_roles(self, text: str) -> Dict[str, str]:
        roles = {}
        words = text.split()
        for i, word in enumerate(words):
            if word.lower() in ["gave", "sent", "told"]:
                if i + 1 < len(words):
                    roles["AGENT"] = words[i-1] if i > 0 else ""
                if i + 2 < len(words):
                    roles["THEME"] = words[i+1]
                if i + 4 < len(words):
                    roles["RECIPIENT"] = words[i+3]
        return roles

    def stats(self) -> Dict:
        return {"senses": len(self.word_senses), "roles": len(self.semantic_roles)}

def run():
    se = SemanticsExtractor()
    se.add_sense("bank", ["financial institution", "river edge"])
    print("Disambiguate:", se.disambiguate("bank", "I sat by the river bank"))
    print("Entities:", se.extract_entities("John Smith visited IBM on 5/12/2024"))
    print("Roles:", se.semantic_roles("Alice gave Bob a book"))
    print(se.stats())

if __name__ == "__main__":
    run()
