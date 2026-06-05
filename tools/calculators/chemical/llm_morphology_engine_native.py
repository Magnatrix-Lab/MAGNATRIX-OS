"""Morphology Engine — stemming, lemmatization, affixes, conjugation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
import re

@dataclass
class MorphologyEngine:
    suffixes: List[str] = field(default_factory=lambda: ["ing", "ed", "s", "es", "ly", "tion", "ness", "ment"])
    prefixes: List[str] = field(default_factory=lambda: ["un", "re", "pre", "dis", "over", "under"])

    def remove_suffix(self, word: str) -> str:
        for suffix in sorted(self.suffixes, key=len, reverse=True):
            if word.endswith(suffix):
                return word[:-len(suffix)]
        return word

    def remove_prefix(self, word: str) -> str:
        for prefix in sorted(self.prefixes, key=len, reverse=True):
            if word.startswith(prefix):
                return word[len(prefix):]
        return word

    def stem(self, word: str) -> str:
        w = word.lower()
        w = self.remove_suffix(w)
        w = self.remove_prefix(w)
        return w

    def apply_suffix(self, root: str, suffix: str) -> str:
        if suffix in ["s", "es"] and root.endswith(("s", "x", "z", "ch", "sh")):
            return root + "es"
        if suffix == "ed" and root.endswith("e"):
            return root + "d"
        return root + suffix

    def apply_prefix(self, root: str, prefix: str) -> str:
        if root[0] == prefix[-1]:
            return prefix + root[1:]
        return prefix + root

    def stats(self) -> Dict:
        return {"suffixes": len(self.suffixes), "prefixes": len(self.prefixes)}

def run():
    me = MorphologyEngine()
    print("Stem running:", me.stem("running"))
    print("Stem unhappiness:", me.stem("unhappiness"))
    print("Apply suffix:", me.apply_suffix("walk", "ed"))
    print(me.stats())

if __name__ == "__main__":
    run()
