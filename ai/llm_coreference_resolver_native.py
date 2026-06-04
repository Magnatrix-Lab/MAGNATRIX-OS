"""Coreference Resolver - Simple pronoun resolution for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import re

@dataclass
class CoreferenceResolver:
    mentions: List[str] = field(default_factory=list)

    def resolve(self, text: str) -> Dict[str, str]:
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
        entities = []
        for s in sentences:
            words = re.findall(r"[A-Z][a-zA-Z]+", s)
            entities.extend(words)
        pronouns = {"he": "male", "she": "female", "it": "neutral", "they": "plural"}
        resolved = {}
        for s in sentences:
            words = s.lower().split()
            for i, w in enumerate(words):
                if w in pronouns:
                    # Find nearest preceding entity
                    for j in range(len(entities) - 1, -1, -1):
                        if entities[j].lower() != w:
                            resolved[w] = entities[j]
                            break
        return resolved

    def stats(self, text: str) -> dict:
        resolved = self.resolve(text)
        return {"pronouns": len(resolved), "entities": len(re.findall(r"[A-Z][a-zA-Z]+", text))}

def run():
    cr = CoreferenceResolver()
    text = "Alice went to the store. She bought some apples. Bob saw her."
    print("Resolved:", cr.resolve(text))
    print("Stats:", cr.stats(text))

if __name__ == "__main__": run()
