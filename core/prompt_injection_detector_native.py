
"""
prompt_injection_detector_native.py
MAGNATRIX-OS — Prompt Injection Detector

Detects and classifies prompt injection attempts on LLM systems.
Inspired by AI/ML pentesting roadmap for prompt injection attacks.

Pure Python standard library.
"""

import re
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime


class InjectionType(Enum):
    DIRECT = "direct_injection"
    INDIRECT = "indirect_injection"
    JAILBREAK = "jailbreak"
    ROLEPLAY = "roleplay"
    IGNORE_PREVIOUS = "ignore_previous"
    DELIMITER = "delimiter_manipulation"
    MARKDOWN = "markdown_injection"
    XML = "xml_tag_injection"
    BASE64 = "base64_encoding"
    UNICODE = "unicode_manipulation"


@dataclass
class InjectionResult:
    is_injection: bool
    confidence: float
    injection_type: Optional[str] = None
    matched_patterns: List[str] = field(default_factory=list)
    severity: str = "low"
    position: str = ""


class PromptInjectionDetector:
    """Detect prompt injection attempts with pattern matching and heuristics."""

    def __init__(self):
        self.patterns: Dict[InjectionType, List[str]] = {
            InjectionType.DIRECT: [
                r"ignore previous instructions",
                r"ignore all prior",
                r"disregard the above",
                r"ignore the system prompt",
                r"forget everything",
                r"new instructions: ",
                r"override the system",
                r"bypass the",
                r"ignore safety",
                r"you are now ",
            ],
            InjectionType.INDIRECT: [
                r"https?://\S+\s+inject",
                r"user[_-]?input.*system",
                r"concatenate.*prompt",
                r"template.*injection",
            ],
            InjectionType.JAILBREAK: [
                r"dan\s*mode",
                r"developer mode",
                r"jailbreak",
                r"do anything now",
                r"\bDAN\b",
                r"\bDADDY\b",
                r"\bSTAN\b",
                r"hypothetically speaking",
                r"purely fictional",
                r"for educational purposes",
                r"this is a test scenario",
            ],
            InjectionType.ROLEPLAY: [
                r"pretend you are",
                r"act as if you are",
                r"roleplay as",
                r"you are now a",
                r"imagine you are",
                r"from now on you are",
            ],
            InjectionType.IGNORE_PREVIOUS: [
                r"ignore (all|the|previous|above|prior).*instructions",
                r"disregard.*command",
                r"cancel.*prompt",
                r"reset.*context",
                r"clear.*memory",
            ],
            InjectionType.DELIMITER: [
                r"```.*ignore",
                r"---.*new instructions",
                r"###.*override",
                r"\|\|\|.*system",
                r"<\|endoftext\|>",
                r"<\|im_start\|>",
                r"<\|im_sep\|>",
            ],
            InjectionType.MARKDOWN: [
                r"\[system\]",
                r"\[assistant\]",
                r"\[user\]",
                r"<system>",
                r"<assistant>",
                r"<user>",
                r"# System Prompt",
                r"## Instructions",
            ],
            InjectionType.XML: [
                r"<system>.*</system>",
                r"<instructions>.*</instructions>",
                r"<prompt>.*</prompt>",
                r"<override>.*</override>",
            ],
            InjectionType.BASE64: [
                r"[A-Za-z0-9+/]{40,}={0,2}",
                r"base64_decode",
                r"atob\s*\(",
                r"b64decode",
            ],
            InjectionType.UNICODE: [
                r"\u200[bcdef]",  # zero-width chars
                r"\u200e\u200f",  # directional marks
                r"\u202[89ae]",  # bidirectional chars
                r"\u206[0-9a-f]",  # invisible formatting
            ],
        }
        self.history: List[Dict] = []

    def scan(self, text: str, context: str = "") -> InjectionResult:
        """Scan text for prompt injection patterns."""
        combined = f"{context} {text}".lower()
        matches = []
        max_confidence = 0.0
        detected_type = None
        severity = "low"

        for inj_type, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, combined, re.IGNORECASE):
                    matches.append(pattern)
                    conf = self._confidence_score(inj_type, len(matches))
                    if conf > max_confidence:
                        max_confidence = conf
                        detected_type = inj_type.value
                        severity = self._severity(inj_type, conf)

        result = InjectionResult(
            is_injection=len(matches) > 0,
            confidence=min(1.0, max_confidence),
            injection_type=detected_type,
            matched_patterns=matches[:10],
            severity=severity,
            position=self._find_position(text, matches),
        )
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "is_injection": result.is_injection,
            "type": detected_type,
        })
        return result

    def _confidence_score(self, inj_type: InjectionType, match_count: int) -> float:
        base_scores = {
            InjectionType.DIRECT: 0.8,
            InjectionType.INDIRECT: 0.6,
            InjectionType.JAILBREAK: 0.9,
            InjectionType.ROLEPLAY: 0.5,
            InjectionType.IGNORE_PREVIOUS: 0.85,
            InjectionType.DELIMITER: 0.7,
            InjectionType.MARKDOWN: 0.6,
            InjectionType.XML: 0.75,
            InjectionType.BASE64: 0.4,
            InjectionType.UNICODE: 0.5,
        }
        base = base_scores.get(inj_type, 0.5)
        boost = min(0.3, match_count * 0.1)
        return min(1.0, base + boost)

    def _severity(self, inj_type: InjectionType, confidence: float) -> str:
        if confidence > 0.9:
            return "critical"
        elif confidence > 0.7:
            return "high"
        elif confidence > 0.5:
            return "medium"
        return "low"

    def _find_position(self, text: str, matches: List[str]) -> str:
        if not matches:
            return ""
        first = matches[0]
        m = re.search(first, text, re.IGNORECASE)
        if m:
            return f"offset:{m.start()}-{m.end()}"
        return ""

    def sanitize(self, text: str) -> str:
        """Sanitize input by neutralizing injection patterns."""
        sanitized = text
        for inj_type, patterns in self.patterns.items():
            for pattern in patterns:
                sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)
        return sanitized

    def get_stats(self) -> Dict:
        total = len(self.history)
        injections = sum(1 for h in self.history if h["is_injection"])
        return {
            "total_scanned": total,
            "injections_detected": injections,
            "detection_rate": injections / max(total, 1),
        }

    def to_dict(self) -> Dict:
        return self.get_stats()


__all__ = ["PromptInjectionDetector", "InjectionResult", "InjectionType"]
