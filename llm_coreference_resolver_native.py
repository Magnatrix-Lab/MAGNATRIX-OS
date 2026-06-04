"""Coreference Resolver — pronoun resolution, entity chains, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum, auto
import re

@dataclass
class Mention:
    text: str
    start: int
    end: int
    mention_type: str  # pronoun, name, noun_phrase

@dataclass
class CorefChain:
    chain_id: str
    mentions: List[Mention]
    representative: str

class CoreferenceResolver:
    def __init__(self):
        self.pronouns = {"he", "she", "it", "they", "him", "her", "them", "his", "their", "its", "this", "that", "these", "those"}
        self.gender_map = {"he": "M", "she": "F", "him": "M", "her": "F", "his": "M", "her_poss": "F"}

    def extract_mentions(self, text: str) -> List[Mention]:
        mentions = []
        # Simple noun phrase extraction
        words = text.split()
        pos = 0
        for i, word in enumerate(words):
            clean = re.sub(r"[^\w]", "", word).lower()
            if clean in self.pronouns:
                mentions.append(Mention(word, pos, pos + len(word), "pronoun"))
            elif word[0].isupper() and i > 0:
                mentions.append(Mention(word, pos, pos + len(word), "name"))
            pos += len(word) + 1
        return mentions

    def resolve(self, text: str) -> List[CorefChain]:
        mentions = self.extract_mentions(text)
        chains: List[CorefChain] = []
        for m in mentions:
            if m.mention_type == "pronoun":
                # Find closest preceding antecedent
                for prev in reversed(mentions[:mentions.index(m)]):
                    if prev.mention_type in ("name", "noun_phrase"):
                        chain = next((c for c in chains if c.representative == prev.text), None)
                        if chain:
                            chain.mentions.append(m)
                        else:
                            chains.append(CorefChain(str(len(chains)), [prev, m], prev.text))
                        break
        return chains

    def stats(self) -> Dict:
        return {"pronouns": len(self.pronouns)}

def run():
    resolver = CoreferenceResolver()
    text = "Alice went to the store. She bought some milk. Bob saw her there."
    chains = resolver.resolve(text)
    for c in chains:
        print(f"Chain: {c.representative} -> {[m.text for m in c.mentions]}")
    print(resolver.stats())

if __name__ == "__main__":
    run()
