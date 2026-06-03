"""LLM Spell Checker — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from enum import Enum, auto

class SpellChecker:
    def __init__(self) -> None:
        self._dictionary: Set[str] = set()
        self._word_freq: Dict[str, int] = {}

    def add_word(self, word: str) -> None:
        lower = word.lower()
        self._dictionary.add(lower)
        self._word_freq[lower] = self._word_freq.get(lower, 0) + 1

    def add_corpus(self, words: List[str]) -> None:
        for word in words:
            self.add_word(word)

    def is_valid(self, word: str) -> bool:
        return word.lower() in self._dictionary

    def _edit_distance(self, s1: str, s2: str) -> int:
        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                cost = 0 if s1[i-1] == s2[j-1] else 1
                dp[i][j] = min(dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + cost)
        return dp[m][n]

    def suggest(self, word: str, top_k: int = 3) -> List[tuple]:
        lower = word.lower()
        if lower in self._dictionary:
            return [(lower, 0)]
        candidates = []
        for dict_word in self._dictionary:
            if abs(len(dict_word) - len(lower)) <= 2:
                dist = self._edit_distance(lower, dict_word)
                if dist <= 3:
                    candidates.append((dist, self._word_freq.get(dict_word, 0), dict_word))
        candidates.sort(key=lambda x: (x[0], -x[1]))
        return [(w, d) for d, _, w in candidates[:top_k]]

    def check_text(self, text: str) -> List[Dict[str, Any]]:
        words = text.split()
        errors = []
        for word in words:
            clean = "".join(c for c in word if c.isalpha()).lower()
            if clean and not self.is_valid(clean):
                suggestions = self.suggest(clean, 3)
                errors.append({"word": word, "suggestions": [s[0] for s in suggestions]})
        return errors

    def get_stats(self) -> Dict[str, Any]:
        return {"dictionary_size": len(self._dictionary), "total_words": sum(self._word_freq.values())}

def run() -> None:
    print("Spell Checker test")
    e = SpellChecker()
    e.add_corpus(["apple", "apples", "application", "apply", "app", "banana", "band", "bandana", "cat", "car", "card", "care", "careful"])
    print("  'aple' -> " + str(e.suggest("aple", 3)))
    print("  'bananna' -> " + str(e.suggest("bananna", 3)))
    print("  'carr' -> " + str(e.suggest("carr", 3)))
    print("  Check text: " + str(e.check_text("I like aple and bananna")))
    print("  Stats: " + str(e.get_stats()))
    print("Spell Checker test complete.")

if __name__ == "__main__":
    run()
