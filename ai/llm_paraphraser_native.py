"""Paraphraser - Simple paraphrase generation for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict
import random
import re

@dataclass
class Paraphraser:
    synonyms: Dict[str, List[str]] = field(default_factory=dict)
    
    def add_synonyms(self, word: str, synonyms: List[str]) -> None:
        self.synonyms[word] = synonyms
    
    def paraphrase(self, text: str, num_variants: int = 1) -> List[str]:
        tokens = re.findall(r"[a-zA-Z0-9]+|[.,;!?]", text)
        variants = []
        for _ in range(num_variants):
            result = []
            for token in tokens:
                if token.lower() in self.synonyms and random.random() < 0.3:
                    result.append(random.choice(self.synonyms[token.lower()]))
                else:
                    result.append(token)
            variants.append(" ".join(result))
        return variants
    
    def stats(self, text: str) -> dict:
        tokens = re.findall(r"[a-zA-Z]+", text.lower())
        replaceable = sum(1 for t in tokens if t in self.synonyms)
        return {"tokens": len(tokens), "replaceable": replaceable, "synonyms": len(self.synonyms)}

def run():
    p = Paraphraser()
    p.add_synonyms("good", ["great", "excellent", "fine"])
    p.add_synonyms("fast", ["quick", "rapid", "swift"])
    text = "The fast car is good"
    print("Paraphrases:", p.paraphrase(text, 3))
    print("Stats:", p.stats(text))

if __name__ == "__main__": run()
