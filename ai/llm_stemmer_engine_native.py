"""LLM Stemmer Engine — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class StemmerEngine:
    def __init__(self) -> None:
        self._rules: List[tuple] = [
            (r'ies$', 'y'), (r'es$', ''), (r's$', ''), (r'ing$', ''),
            (r'ed$', ''), (r'er$', ''), (r'est$', ''), (r'ly$', ''),
            (r'ness$', ''), (r'ful$', ''), (r'less$', ''), (r'able$', ''),
            (r'ible$', ''), (r'ion$', ''), (r'tion$', ''), (r'ation$', ''),
            (r'ity$', ''), (r'ive$', ''), (r'ize$', ''), (r'ise$', ''),
            (r'ify$', ''), (r'ify$', ''), (r'al$', ''), (r'ical$', ''),
        ]
        self._exceptions: Dict[str, str] = {
            'children': 'child', 'women': 'woman', 'men': 'man',
            'feet': 'foot', 'teeth': 'tooth', 'mice': 'mouse',
            'geese': 'goose', 'oxen': 'ox', 'deer': 'deer',
        }

    def stem(self, word: str) -> str:
        lower = word.lower()
        if lower in self._exceptions:
            return self._exceptions[lower]
        for pattern, replacement in self._rules:
            if re.search(pattern, lower):
                stem = re.sub(pattern, replacement, lower)
                if len(stem) >= 2:
                    return stem
        return lower

    def stem_list(self, words: List[str]) -> List[str]:
        return [self.stem(w) for w in words]

    def get_stems_with_counts(self, words: List[str]) -> Dict[str, int]:
        stems = self.stem_list(words)
        counts = {}
        for s in stems:
            counts[s] = counts.get(s, 0) + 1
        return counts

    def get_stats(self, words: List[str]) -> Dict[str, Any]:
        stems = self.stem_list(words)
        return {"words": len(words), "unique_stems": len(set(stems)), "reduction": len(words) - len(set(stems))}

def run() -> None:
    print("Stemmer Engine test")
    e = StemmerEngine()
    words = ["running", "runs", "runner", "children", "happiness", "beautiful", "organization", "mice"]
    for w in words:
        print("  " + w + " -> " + e.stem(w))
    print("  Stats: " + str(e.get_stats(words)))
    print("Stemmer Engine test complete.")

if __name__ == "__main__":
    run()
