"""LLM Pattern Matcher — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum, auto

class PatternType(Enum):
    EXACT = auto()
    REGEX = auto()
    WILDCARD = auto()
    FUZZY = auto()
    SEQUENCE = auto()

class PatternMatcher:
    def __init__(self) -> None:
        self._patterns: List[tuple] = []

    def add_pattern(self, pattern_id: str, pattern: str, pattern_type: PatternType, metadata: Optional[Dict[str, Any]] = None) -> None:
        self._patterns.append((pattern_id, pattern, pattern_type, metadata or {}))

    def match(self, text: str) -> List[tuple]:
        results = []
        for pid, pattern, ptype, meta in self._patterns:
            if ptype == PatternType.EXACT:
                if pattern in text:
                    results.append((pid, pattern, ptype, text.index(pattern)))
            elif ptype == PatternType.REGEX:
                for match in re.finditer(pattern, text):
                    results.append((pid, match.group(), ptype, match.start()))
            elif ptype == PatternType.WILDCARD:
                regex_pattern = pattern.replace("*", ".*").replace("?", ".")
                for match in re.finditer(regex_pattern, text):
                    results.append((pid, match.group(), ptype, match.start()))
            elif ptype == PatternType.SEQUENCE:
                parts = pattern.split()
                if all(p in text for p in parts):
                    results.append((pid, pattern, ptype, text.find(parts[0])))
        return results

    def match_exact(self, text: str, pattern: str) -> bool:
        return pattern in text

    def match_regex(self, text: str, pattern: str) -> List[Tuple[str, int]]:
        return [(m.group(), m.start()) for m in re.finditer(pattern, text)]

    def get_stats(self, results: List[tuple]) -> Dict[str, Any]:
        counts = {}
        for r in results:
            counts[r[2].name] = counts.get(r[2].name, 0) + 1
        return {"matches": len(results), "by_type": counts}

def run() -> None:
    print("Pattern Matcher test")
    e = PatternMatcher()
    e.add_pattern("p1", "hello", PatternType.EXACT)
    e.add_pattern("p2", r"\b\d+\b", PatternType.REGEX)
    e.add_pattern("p3", "h*o", PatternType.WILDCARD)
    e.add_pattern("p4", "quick brown", PatternType.SEQUENCE)
    text = "hello world, 123 quick brown fox"
    results = e.match(text)
    for r in results:
        print("  Match: " + r[0] + " -> '" + r[1] + "' at " + str(r[3]))
    print("  Stats: " + str(e.get_stats(results)))
    print("Pattern Matcher test complete.")

if __name__ == "__main__":
    run()
