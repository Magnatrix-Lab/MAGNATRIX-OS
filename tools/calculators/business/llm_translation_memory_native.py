"""Translation Memory — fuzzy matching, segment storage, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import re

@dataclass
class TranslationUnit:
    source: str
    target: str
    source_lang: str
    target_lang: str
    usage_count: int = 0
    last_used: float = 0.0

class TranslationMemory:
    def __init__(self, match_threshold: float = 0.7):
        self.match_threshold = match_threshold
        self.units: List[TranslationUnit] = []
        self.index: Dict[str, List[int]] = {}

    def add(self, source: str, target: str, source_lang: str, target_lang: str):
        tu = TranslationUnit(source, target, source_lang, target_lang)
        self.units.append(tu)
        words = set(re.findall(r'\w+', source.lower()))
        for w in words:
            if w not in self.index:
                self.index[w] = []
            self.index[w].append(len(self.units) - 1)

    def _similarity(self, a: str, b: str) -> float:
        words_a = set(re.findall(r'\w+', a.lower()))
        words_b = set(re.findall(r'\w+', b.lower()))
        if not words_a or not words_b:
            return 0.0
        return len(words_a & words_b) / len(words_a | words_b)

    def search(self, query: str, source_lang: str, target_lang: str) -> Optional[TranslationUnit]:
        words = set(re.findall(r'\w+', query.lower()))
        candidates = set()
        for w in words:
            candidates.update(self.index.get(w, []))
        best = None
        best_score = 0.0
        for idx in candidates:
            tu = self.units[idx]
            if tu.source_lang == source_lang and tu.target_lang == target_lang:
                score = self._similarity(query, tu.source)
                if score > best_score and score >= self.match_threshold:
                    best_score = score
                    best = tu
        return best

    def translate(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        tu = self.search(text, source_lang, target_lang)
        return tu.target if tu else None

    def stats(self) -> Dict:
        return {"units": len(self.units), "index_size": len(self.index), "threshold": self.match_threshold}

def run():
    tm = TranslationMemory(0.6)
    tm.add("Hello world", "Halo dunia", "en", "id")
    tm.add("Good morning", "Selamat pagi", "en", "id")
    tm.add("Hello there", "Halo sana", "en", "id")
    print(tm.translate("Hello world!", "en", "id"))
    print(tm.search("Hello world", "en", "id"))
    print(tm.stats())

if __name__ == "__main__":
    run()
