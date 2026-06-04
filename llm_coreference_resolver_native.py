"""Coreference Resolver — mention pairs, chains, entity linking, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
import re

@dataclass
class Mention:
    text: str
    start: int
    end: int
    sentence: int

@dataclass
class CoreferenceResolver:
    mentions: List[Mention] = field(default_factory=list)
    chains: List[List[int]] = field(default_factory=list)
    """indices into mentions"""

    def add_mention(self, text: str, start: int, end: int, sentence: int):
        self.mentions.append(Mention(text, start, end, sentence))

    def resolve(self) -> List[List[int]]:
        self.chains = []
        used = set()
        for i, m1 in enumerate(self.mentions):
            if i in used:
                continue
            chain = [i]
            used.add(i)
            for j, m2 in enumerate(self.mentions):
                if j in used or i == j:
                    continue
                if self._match(m1, m2):
                    chain.append(j)
                    used.add(j)
            self.chains.append(chain)
        return self.chains

    def _match(self, m1: Mention, m2: Mention) -> bool:
        if m1.text.lower() == m2.text.lower():
            return True
        if m1.text.lower() in {"he", "she", "it", "they"} and m2.text[0].isupper() and m1.sentence > m2.sentence:
            return True
        if m2.text.lower() in {"he", "she", "it", "they"} and m1.text[0].isupper() and m2.sentence > m1.sentence:
            return True
        return False

    def entity_chains(self) -> Dict[str, List[str]]:
        chains = self.resolve()
        return {f"chain_{i}": [self.mentions[idx].text for idx in chain] for i, chain in enumerate(chains)}

    def stats(self) -> Dict:
        return {"mentions": len(self.mentions), "chains": len(self.chains)}

def run():
    cr = CoreferenceResolver()
    cr.add_mention("Alice", 0, 5, 0)
    cr.add_mention("she", 20, 23, 1)
    cr.add_mention("Bob", 30, 33, 0)
    cr.add_mention("he", 45, 47, 1)
    print("Chains:", cr.entity_chains())
    print(cr.stats())

if __name__ == "__main__":
    run()
