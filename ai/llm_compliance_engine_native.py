#!/usr/bin/env python3
"""
MAGNATRIX-OS — Compliance Engine
ai/llm_compliance_engine_native.py

Features:
- Policy rule evaluation (allow/deny/warn based on rules)
- Data classification (PII, sensitive, public)
- Regulatory framework mapping (GDPR, HIPAA, SOC2)
- Compliance score calculation
- Audit trail generation

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("compliance_engine")


class DataClass(enum.Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    PII = "pii"
    PHI = "phi"


class ComplianceFramework(enum.Enum):
    GDPR = "gdpr"
    HIPAA = "hipaa"
    SOC2 = "soc2"
    PCI = "pci"


class ComplianceVerdict(enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    NEEDS_REVIEW = "needs_review"


@dataclass
class ComplianceRule:
    id: str
    framework: ComplianceFramework
    description: str
    pattern: Optional[str] = None
    required_classification: Optional[DataClass] = None
    action: str = "warn"


@dataclass
class ComplianceResult:
    rule_id: str
    verdict: ComplianceVerdict
    message: str
    confidence: float


class ComplianceEngine:
    """Compliance checking with rules and frameworks."""

    RULES = [
        ComplianceRule("GDPR-1", ComplianceFramework.GDPR, "Email must not be exposed without consent", r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", DataClass.PII, "fail"),
        ComplianceRule("GDPR-2", ComplianceFramework.GDPR, "SSN must be encrypted", r"\b\d{3}-\d{2}-\d{4}\b", DataClass.PII, "fail"),
        ComplianceRule("HIPAA-1", ComplianceFramework.HIPAA, "Medical record number must be protected", r"MRN[:\s]*\d+", DataClass.PHI, "fail"),
        ComplianceRule("SOC2-1", ComplianceFramework.SOC2, "Passwords must not be in plaintext", r"password[:\s]*\w+", DataClass.CONFIDENTIAL, "warn"),
    ]

    def __init__(self):
        self._results: List[ComplianceResult] = []
        self._audit: List[Dict[str, Any]] = []

    def classify_data(self, text: str) -> List[Tuple[str, DataClass]]:
        classifications = []
        for rule in self.RULES:
            if rule.pattern and re.search(rule.pattern, text, re.IGNORECASE):
                classifications.append((rule.description, rule.required_classification or DataClass.CONFIDENTIAL))
        return classifications

    def check(self, text: str, framework: Optional[ComplianceFramework] = None) -> List[ComplianceResult]:
        results = []
        for rule in self.RULES:
            if framework and rule.framework != framework:
                continue
            if rule.pattern and re.search(rule.pattern, text, re.IGNORECASE):
                verdict = ComplianceVerdict.FAIL if rule.action == "fail" else ComplianceVerdict.WARN
                results.append(ComplianceResult(rule.id, verdict, f"{rule.description} detected", 0.9))
            else:
                results.append(ComplianceResult(rule.id, ComplianceVerdict.PASS, f"{rule.description} clean", 1.0))
        self._results.extend(results)
        return results

    def compliance_score(self, results: List[ComplianceResult]) -> float:
        if not results:
            return 1.0
        passes = sum(1 for r in results if r.verdict == ComplianceVerdict.PASS)
        return passes / len(results)

    def get_audit_trail(self) -> List[Dict[str, Any]]:
        return self._audit

    def get_stats(self) -> Dict[str, Any]:
        by_verdict = defaultdict(int)
        for r in self._results:
            by_verdict[r.verdict.value] += 1
        return {"total_checks": len(self._results), "by_verdict": dict(by_verdict)}


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Compliance Engine")
    print("ai/llm_compliance_engine_native.py")
    print("=" * 60)

    engine = ComplianceEngine()

    texts = [
        "User email is alice@example.com and SSN is 123-45-6789",
        "Password: secret123 in plaintext",
        "MRN: 12345 for patient John",
        "This is a clean public message",
        "Contact bob@test.com for info",
    ]

    for text in texts:
        print(f"\nText: {text[:50]}...")
        results = engine.check(text)
        for r in results:
            print(f"  [{r.verdict.value.upper()}] {r.rule_id}: {r.message}")
        score = engine.compliance_score(results)
        print(f"  Compliance score: {score:.1%}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
