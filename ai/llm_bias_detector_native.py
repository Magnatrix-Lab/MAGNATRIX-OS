"""LLM Bias Detector — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class BiasType(Enum):
    GENDER = auto()
    RACE = auto()
    AGE = auto()
    RELIGION = auto()
    ABILITY = auto()

@dataclass
class BiasFinding:
    bias_type: BiasType
    text: str
    position: int
    severity: float
    metadata: Dict[str, Any] = field(default_factory=dict)

class BiasDetector:
    def __init__(self) -> None:
        self._patterns: Dict[BiasType, List[str]] = {}

    def register_patterns(self, bias_type: BiasType, patterns: List[str]) -> None:
        self._patterns[bias_type] = patterns

    def detect(self, text: str) -> List[BiasFinding]:
        findings = []
        for bias_type, patterns in self._patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    findings.append(BiasFinding(bias_type, match.group(), match.start(), 0.7))
        return findings

    def get_stats(self, findings: List[BiasFinding]) -> Dict[str, Any]:
        counts = {}
        for f in findings:
            counts[f.bias_type.name] = counts.get(f.bias_type.name, 0) + 1
        return {"total": len(findings), "by_type": counts, "severity_avg": sum(f.severity for f in findings) / len(findings) if findings else 0.0}

def run() -> None:
    print("Bias Detector test")
    e = BiasDetector()
    e.register_patterns(BiasType.GENDER, [r"\b(he|him|his)\b", r"\b(she|her|hers)\b"])
    e.register_patterns(BiasType.RACE, [r"\b(white|black|asian)\b"])
    text = "He went to the store. She bought apples. The black community is strong."
    findings = e.detect(text)
    for f in findings:
        print("  " + f.bias_type.name + " at pos " + str(f.position) + ": '" + f.text + "'")
    print("  Stats: " + str(e.get_stats(findings)))
    print("Bias Detector test complete.")

if __name__ == "__main__":
    run()
