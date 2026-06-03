"""LLM Hallucination Detector — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class HallucinationType(Enum):
    FACTUAL = auto()
    CONTRADICTORY = auto()
    UNSUPPORTED = auto()
    FABRICATED = auto()

@dataclass
class HallucinationFinding:
    htype: HallucinationType
    text: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)

class HallucinationDetector:
    def __init__(self) -> None:
        self._indicators = ["I think", "probably", "maybe", "likely", "it seems", "possibly", "as far as I know", "I believe"]

    def detect(self, text: str, context: Optional[str] = None) -> List[HallucinationFinding]:
        findings = []
        for indicator in self._indicators:
            if indicator.lower() in text.lower():
                findings.append(HallucinationFinding(HallucinationType.UNSUPPORTED, indicator, 0.5))
        if context and not self._has_overlap(text, context):
            findings.append(HallucinationFinding(HallucinationType.FABRICATED, "No context overlap", 0.8))
        return findings

    def _has_overlap(self, text: str, context: str) -> bool:
        text_words = set(text.lower().split())
        ctx_words = set(context.lower().split())
        return len(text_words & ctx_words) > 2

    def get_stats(self, findings: List[HallucinationFinding]) -> Dict[str, Any]:
        counts = {}
        for f in findings:
            counts[f.htype.name] = counts.get(f.htype.name, 0) + 1
        return {"total": len(findings), "by_type": counts, "confidence_avg": sum(f.confidence for f in findings) / len(findings) if findings else 0.0}

def run() -> None:
    print("Hallucination Detector test")
    e = HallucinationDetector()
    text = "I think Paris is the capital of Germany. It seems that water boils at 90 degrees."
    findings = e.detect(text, "Paris is the capital of France. Water boils at 100 degrees at sea level.")
    for f in findings:
        print("  " + f.htype.name + ": '" + f.text + "' (conf=" + str(f.confidence) + ")")
    print("  Stats: " + str(e.get_stats(findings)))
    print("Hallucination Detector test complete.")

if __name__ == "__main__":
    run()
