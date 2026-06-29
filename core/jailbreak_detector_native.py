
"""
jailbreak_detector_native.py
MAGNATRIX-OS — Jailbreak Detector

Detects jailbreak attempts (DAN, STAN, DADDY, etc.) and roleplay
escalation patterns. Inspired by AI/ML pentesting roadmap.

Pure Python standard library.
"""

import re
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime


class JailbreakFamily(Enum):
    DAN = "Do Anything Now"
    STAN = "STAN"
    DADDY = "DADDY"
    DEVELOPER = "Developer Mode"
    MD_JAILBREAK = "Markdown Jailbreak"
    REFUSAL_SUPPRESSION = "Refusal Suppression"
    HYPOBOT = "Hypothetical Bot"
    EVIL_CONFIDANT = "Evil Confidant"
    AIM = "Always Intelligent Machina"
    UCAR = "Universal Computer-Assisted Reasoning"


@dataclass
class JailbreakResult:
    is_jailbreak: bool
    confidence: float
    family: Optional[str] = None
    technique: str = ""
    mitigation: str = ""
    matched_rules: List[str] = field(default_factory=list)


class JailbreakDetector:
    """Detect jailbreak attempts against LLM systems."""

    def __init__(self):
        self.rules: Dict[str, List[str]] = {
            "DAN": [
                r"\bDAN\b", r"do anything now", r"dan mode",
                r"dan\s*:[-–—]", r"\[dan\]", r"#dan",
            ],
            "STAN": [
                r"\bSTAN\b", r"strive to avoid norms",
                r"strive to", r"unethical norms",
            ],
            "DADDY": [
                r"\bDADDY\b", r"daddy mode", r"dominant ai",
            ],
            "DEVELOPER": [
                r"developer mode", r"\bdev mode\b",
                r"debug mode", r"maintenance mode",
                r"system configuration", r"configuration mode",
            ],
            "MD_JAILBREAK": [
                r"ignore previous", r"ignore above",
                r"```system", r"```instructions",
                r"---system---", r"---instructions---",
            ],
            "REFUSAL_SUPPRESSION": [
                r"refusal suppression", r"do not refuse",
                r"never refuse", r"always comply",
                r"suppress.*refusal", r"bypass.*filter",
            ],
            "HYPOBOT": [
                r"hypothetically", r"hypothetical scenario",
                r"purely fictional", r"for the sake of argument",
                r"in a fictional world", r"imagine a world",
            ],
            "EVIL_CONFIDANT": [
                r"evil confidant", r"confidant mode",
                r"unrestricted mode", r"no boundaries",
            ],
            "AIM": [
                r"\bAIM\b", r"always intelligent machina",
                r"unfiltered ai", r"machina",
            ],
            "UCAR": [
                r"\bUCAR\b", r"universal computer",
                r"computer-assisted reasoning",
            ],
        }
        self.escalation_patterns = [
            r"(pretend|act|roleplay|imagine).*(evil|bad|unethical|harmful|dangerous|illegal)",
            r"(you are|from now on).*(unrestricted|no limit|no filter|no safety)",
            r"(bypass|ignore|disable).*(safety|filter|guardrail|restriction|limit)",
            r"(write|generate|create).*(malware|virus|exploit|hack|attack|bomb|weapon)",
            r"(how to|steps to|guide to).*(steal|hack|kill|harm|attack|exploit|break in)",
        ]
        self.history: List[Dict] = []

    def detect(self, text: str) -> JailbreakResult:
        text_lower = text.lower()
        matches = []
        max_conf = 0.0
        family = None
        technique = ""

        # Check family-specific rules
        for fam, patterns in self.rules.items():
            for pat in patterns:
                if re.search(pat, text_lower):
                    matches.append(f"{fam}:{pat}")
                    conf = self._family_confidence(fam, len(matches))
                    if conf > max_conf:
                        max_conf = conf
                        family = fam
                        technique = pat

        # Check escalation patterns
        for esc in self.escalation_patterns:
            if re.search(esc, text_lower):
                matches.append(f"ESCALATION:{esc}")
                max_conf = max(max_conf, 0.7)

        result = JailbreakResult(
            is_jailbreak=len(matches) > 0,
            confidence=min(1.0, max_conf),
            family=family,
            technique=technique,
            mitigation=self._mitigation(family),
            matched_rules=matches[:10],
        )
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "is_jailbreak": result.is_jailbreak,
            "family": family,
        })
        return result

    def _family_confidence(self, family: str, match_count: int) -> float:
        scores = {
            "DAN": 0.9, "STAN": 0.8, "DADDY": 0.85,
            "DEVELOPER": 0.75, "MD_JAILBREAK": 0.7,
            "REFUSAL_SUPPRESSION": 0.85, "HYPOBOT": 0.6,
            "EVIL_CONFIDANT": 0.8, "AIM": 0.75, "UCAR": 0.7,
        }
        base = scores.get(family, 0.5)
        return min(1.0, base + (match_count - 1) * 0.1)

    def _mitigation(self, family: Optional[str]) -> str:
        mitigations = {
            "DAN": "Block DAN keywords and roleplay prefixes",
            "STAN": "Detect unethical norm suppression patterns",
            "DADDY": "Block dominant/submissive roleplay triggers",
            "DEVELOPER": "Reject system configuration override requests",
            "MD_JAILBREAK": "Sanitize markdown delimiter sequences",
            "REFUSAL_SUPPRESSION": "Enforce refusal policy regardless of instructions",
            "HYPOBOT": "Require factual grounding for hypothetical requests",
            "EVIL_CONFIDANT": "Block unrestricted mode requests",
            "AIM": "Filter machina/unfiltered roleplay triggers",
            "UCAR": "Block universal reasoning override attempts",
        }
        return mitigations.get(family or "", "General input sanitization and policy enforcement")

    def get_stats(self) -> Dict:
        total = len(self.history)
        jailbreaks = sum(1 for h in self.history if h["is_jailbreak"])
        families = {}
        for h in self.history:
            f = h.get("family")
            if f:
                families[f] = families.get(f, 0) + 1
        return {
            "total_scanned": total,
            "jailbreaks_detected": jailbreaks,
            "families": families,
        }

    def to_dict(self) -> Dict:
        return self.get_stats()


__all__ = ["JailbreakDetector", "JailbreakResult", "JailbreakFamily"]
