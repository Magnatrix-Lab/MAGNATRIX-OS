"""LLM PII Masker — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class PIIType(Enum):
    EMAIL = auto()
    PHONE = auto()
    SSN = auto()
    CREDIT_CARD = auto()
    NAME = auto()
    ADDRESS = auto()

@dataclass
class PIIFinding:
    pii_type: PIIType
    text: str
    position: int
    masked: str

class PIIMasker:
    def __init__(self) -> None:
        self._patterns: Dict[PIIType, str] = {
            PIIType.EMAIL: r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            PIIType.PHONE: r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
            PIIType.SSN: r"\b\d{3}-\d{2}-\d{4}\b",
            PIIType.CREDIT_CARD: r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
        }
        self._mask_char = "*"

    def detect(self, text: str) -> List[PIIFinding]:
        findings = []
        for pii_type, pattern in self._patterns.items():
            for match in re.finditer(pattern, text):
                findings.append(PIIFinding(pii_type, match.group(), match.start(), self._mask(match.group())))
        return findings

    def _mask(self, text: str) -> str:
        if len(text) <= 4:
            return self._mask_char * len(text)
        return text[:2] + self._mask_char * (len(text) - 4) + text[-2:]

    def mask(self, text: str) -> str:
        findings = self.detect(text)
        result = text
        for finding in findings:
            result = result.replace(finding.text, finding.masked)
        return result

    def get_stats(self, findings: List[PIIFinding]) -> Dict[str, Any]:
        counts = {}
        for f in findings:
            counts[f.pii_type.name] = counts.get(f.pii_type.name, 0) + 1
        return {"total": len(findings), "by_type": counts}

def run() -> None:
    print("PII Masker test")
    e = PIIMasker()
    text = "Contact alice@example.com or call 555-123-4567. SSN: 123-45-6789. Card: 1234-5678-9012-3456."
    findings = e.detect(text)
    for f in findings:
        print("  " + f.pii_type.name + ": '" + f.text + "' -> '" + f.masked + "'")
    print("  Masked text: " + e.mask(text))
    print("  Stats: " + str(e.get_stats(findings)))
    print("PII Masker test complete.")

if __name__ == "__main__":
    run()
