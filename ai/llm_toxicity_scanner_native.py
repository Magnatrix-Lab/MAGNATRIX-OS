"""LLM Toxicity Scanner — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class ToxicityCategory(Enum):
    HATE = auto()
    HARASSMENT = auto()
    PROFANITY = auto()
    THREAT = auto()
    SELF_HARM = auto()

@dataclass
class ToxicityFinding:
    category: ToxicityCategory
    text: str
    position: int
    severity: float
    metadata: Dict[str, Any] = field(default_factory=dict)

class ToxicityScanner:
    def __init__(self) -> None:
        self._patterns: Dict[ToxicityCategory, List[str]] = {}

    def register_patterns(self, category: ToxicityCategory, patterns: List[str]) -> None:
        self._patterns[category] = patterns

    def scan(self, text: str) -> List[ToxicityFinding]:
        findings = []
        for category, patterns in self._patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    findings.append(ToxicityFinding(category, match.group(), match.start(), 0.8))
        return findings

    def get_stats(self, findings: List[ToxicityFinding]) -> Dict[str, Any]:
        counts = {}
        for f in findings:
            counts[f.category.name] = counts.get(f.category.name, 0) + 1
        return {"total": len(findings), "by_category": counts, "max_severity": max((f.severity for f in findings), default=0.0)}

def run() -> None:
    print("Toxicity Scanner test")
    e = ToxicityScanner()
    e.register_patterns(ToxicityCategory.PROFANITY, [r"\b(darn|heck|stupid)\b"])
    e.register_patterns(ToxicityCategory.HARASSMENT, [r"\b(you are useless|idiot)\b"])
    text = "You are useless and stupid. This is a darn mess."
    findings = e.scan(text)
    for f in findings:
        print("  " + f.category.name + " at pos " + str(f.position) + ": '" + f.text + "'")
    print("  Stats: " + str(e.get_stats(findings)))
    print("Toxicity Scanner test complete.")

if __name__ == "__main__":
    run()
