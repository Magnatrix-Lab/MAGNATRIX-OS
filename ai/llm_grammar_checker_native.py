"""Grammar Checker - Context-free grammar validator for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set
from enum import Enum, auto

@dataclass
class GrammarChecker:
    rules: Dict[str, List[List[str]]] = field(default_factory=dict)
    start: str = "S"

    def add_rule(self, lhs: str, rhs: List[str]) -> None:
        if lhs not in self.rules: self.rules[lhs] = []
        self.rules[lhs].append(rhs)

    def validate(self, tokens: List[str]) -> bool:
        return self._derive(self.start, tokens, 0) == len(tokens)

    def _derive(self, symbol: str, tokens: List[str], pos: int) -> int:
        if pos >= len(tokens): return -1
        if symbol not in self.rules:
            return pos + 1 if pos < len(tokens) and symbol == tokens[pos] else -1
        for rhs in self.rules[symbol]:
            new_pos = pos
            valid = True
            for s in rhs:
                new_pos = self._derive(s, tokens, new_pos)
                if new_pos < 0: valid = False; break
            if valid: return new_pos
        return -1

    def stats(self) -> dict:
        return {"rules": len(self.rules), "start": self.start}

def run():
    gc = GrammarChecker()
    gc.add_rule("S", ["NP", "VP"]); gc.add_rule("NP", ["DET", "N"]); gc.add_rule("VP", ["V", "NP"])
    gc.add_rule("DET", ["the"]); gc.add_rule("N", ["cat"]); gc.add_rule("N", ["dog"]); gc.add_rule("V", ["sees"])
    tokens = ["the", "cat", "sees", "the", "dog"]
    print("Valid:", gc.validate(tokens))
    print("Stats:", gc.stats())

if __name__ == "__main__": run()
