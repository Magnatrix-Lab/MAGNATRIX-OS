"""
llm_bias_scanner_native.py
MAGNATRIX-OS Bias Scanner Engine
Native Python, stdlib only.
Provides bias detection in text: gender, racial, age, and stereotype scanning.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BiasFinding:
    category: str
    text: str
    severity: float
    position: int

    def to_dict(self) -> Dict[str, Any]:
        return {"category": self.category, "text": self.text, "severity": self.severity}


class BiasScannerEngine:
    def __init__(self) -> None:
        self._patterns: Dict[str, List[str]] = {
            "gender": [r"\b(he|she|his|her|him)\b", r"\b(mankind|manpower|chairman)\b", r"\b(fireman|policeman|mailman)\b"],
            "racial": [r"\b(black|white|asian|hispanic)\b", r"\b(minority|majority)\b"],
            "age": [r"\b(old|young|elderly|senior|junior)\b", r"\b(millennial|boomer|gen z)\b"],
            "stereotype": [r"\b(all \w+ are|every \w+ is)\b", r"\b(always|never) \w+\b"],
        }

    def scan(self, text: str) -> List[BiasFinding]:
        findings = []
        for category, patterns in self._patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    findings.append(BiasFinding(category, match.group(), 0.5, match.start()))
        return findings

    def score(self, text: str) -> Dict[str, Any]:
        findings = self.scan(text)
        by_cat: Dict[str, int] = {}
        for f in findings:
            by_cat[f.category] = by_cat.get(f.category, 0) + 1
        return {"findings": len(findings), "by_category": by_cat, "severity": sum(f.severity for f in findings) / max(len(findings), 1)}


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Bias Scanner")
    print("=" * 60)
    e = BiasScannerEngine()
    text = "He is a fireman. All millennials are lazy. The chairman will decide."
    findings = e.scan(text)
    for f in findings:
        print(f"  [{f.category}] '{f.text}' at pos {f.position}")
    print(f"\n  Score: {e.score(text)}")
    print("\nBias Scanner test complete.")


if __name__ == "__main__":
    run()
