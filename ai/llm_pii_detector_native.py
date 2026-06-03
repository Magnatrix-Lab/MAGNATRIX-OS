"""
llm_pii_detector_native.py
MAGNATRIX-OS PII Detector Engine
Native Python, stdlib only.
Provides PII detection: emails, phone numbers, SSNs, credit cards, and redaction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PIIFinding:
    type: str
    value: str
    position: int
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, "value": self.value[:10] + "...", "position": self.position}


class PIIDetectorEngine:
    def __init__(self) -> None:
        self._patterns: Dict[str, str] = {
            "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
            "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
            "credit_card": r"\b(?:\d{4}[- ]?){3}\d{4}\b",
            "ip_address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
        }

    def detect(self, text: str) -> List[PIIFinding]:
        findings = []
        for pii_type, pattern in self._patterns.items():
            for match in re.finditer(pattern, text):
                findings.append(PIIFinding(pii_type, match.group(), match.start()))
        return findings

    def redact(self, text: str, replacement: str = "[REDACTED]") -> str:
        for pii_type, pattern in self._patterns.items():
            text = re.sub(pattern, replacement, text)
        return text

    def mask(self, text: str, mask_char: str = "*") -> str:
        for finding in self.detect(text):
            masked = mask_char * len(finding.value)
            text = text[:finding.position] + masked + text[finding.position + len(finding.value):]
        return text

    def get_stats(self, text: str) -> Dict[str, Any]:
        findings = self.detect(text)
        by_type: Dict[str, int] = {}
        for f in findings:
            by_type[f.type] = by_type.get(f.type, 0) + 1
        return {"findings": len(findings), "by_type": by_type}


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS PII Detector")
    print("=" * 60)
    e = PIIDetectorEngine()
    text = "Contact me at john@example.com or call 555-123-4567. My SSN is 123-45-6789."
    print(f"  Findings: {[f.to_dict() for f in e.detect(text)]}")
    print(f"  Redacted: {e.redact(text)}")
    print(f"  Stats: {e.get_stats(text)}")
    print("\nPII Detector test complete.")


if __name__ == "__main__":
    run()
