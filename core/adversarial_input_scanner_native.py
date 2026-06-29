
"""
adversarial_input_scanner_native.py
MAGNATRIX-OS — Adversarial Input Scanner

Scans inputs for adversarial patterns: encoding tricks, homoglyphs,
embedding attacks, and data poisoning signals.

Pure Python standard library.
"""

import re
import base64
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime


class AdversarialType(Enum):
    HOMOGLYPH = auto()
    ZERO_WIDTH = auto()
    BASE64 = auto()
    HEX = auto()
    URL_ENCODE = auto()
    UNICODE_BIDI = auto()
    TYPO_SQUAT = auto()
    PADDING = auto()
    REPETITION = auto()
    CASE_MANIPULATION = auto()


@dataclass
class AdversarialResult:
    is_adversarial: bool
    confidence: float
    techniques: List[str] = field(default_factory=list)
    sanitized: str = ""
    severity: str = "low"


class AdversarialInputScanner:
    """Scan inputs for adversarial manipulation techniques."""

    def __init__(self):
        self.techniques: Dict[str, Dict] = {
            "homoglyph": {
                "patterns": [
                    r"[аａа]",  # Cyrillic 'a' vs Latin 'a'
                    r"[еｅе]",  # Cyrillic 'e' vs Latin 'e'
                    r"[оｏо]",  # Cyrillic 'o' vs Latin 'o'
                    r"[рｐр]",  # Cyrillic 'p' vs Latin 'p'
                    r"[сｃс]",  # Cyrillic 'c' vs Latin 'c'
                    r"[хｘх]",  # Cyrillic 'x' vs Latin 'x'
                ],
                "score": 0.8,
            },
            "zero_width": {
                "chars": ["\u200b", "\u200c", "\u200d", "\u200e", "\u200f", "\u2060", "\ufeff"],
                "score": 0.7,
            },
            "base64": {
                "pattern": r"^[A-Za-z0-9+/]{40,}={0,2}$",
                "score": 0.6,
            },
            "hex": {
                "pattern": r"^(0x)?[0-9a-fA-F]{20,}$",
                "score": 0.5,
            },
            "url_encode": {
                "pattern": r"%[0-9a-fA-F]{2}",
                "score": 0.4,
            },
            "unicode_bidi": {
                "chars": ["\u202a", "\u202b", "\u202c", "\u202d", "\u202e", "\u2066", "\u2067", "\u2068", "\u2069"],
                "score": 0.9,
            },
            "padding": {
                "pattern": r"(.{1,5})\1{10,}",  # Repeated short sequences
                "score": 0.3,
            },
            "repetition": {
                "pattern": r"(\b\w+\b)(\s+\1){5,}",  # Repeated words
                "score": 0.4,
            },
            "case_manipulation": {
                "pattern": r"([a-z][A-Z]){10,}",  # Alternating case
                "score": 0.3,
            },
        }
        self.history: List[Dict] = []

    def scan(self, text: str) -> AdversarialResult:
        detected = []
        max_score = 0.0
        severity = "low"
        sanitized = text

        # Check each technique
        for name, config in self.techniques.items():
            if "pattern" in config:
                if re.search(config["pattern"], text):
                    detected.append(name)
                    score = config["score"]
                    if score > max_score:
                        max_score = score
                    sanitized = self._sanitize_pattern(sanitized, config["pattern"])
            elif "chars" in config:
                for char in config["chars"]:
                    if char in text:
                        detected.append(name)
                        score = config["score"]
                        if score > max_score:
                            max_score = score
                        sanitized = sanitized.replace(char, "")
            elif "patterns" in config:
                for pattern in config["patterns"]:
                    if re.search(pattern, text):
                        detected.append(name)
                        score = config["score"]
                        if score > max_score:
                            max_score = score
                        break

        if max_score > 0.8:
            severity = "critical"
        elif max_score > 0.6:
            severity = "high"
        elif max_score > 0.4:
            severity = "medium"

        result = AdversarialResult(
            is_adversarial=len(detected) > 0,
            confidence=min(1.0, max_score + len(detected) * 0.1),
            techniques=detected,
            sanitized=sanitized,
            severity=severity,
        )
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "is_adversarial": result.is_adversarial,
            "techniques": detected,
        })
        return result

    def _sanitize_pattern(self, text: str, pattern: str) -> str:
        return re.sub(pattern, "", text)

    def decode_suspicious(self, text: str) -> Dict[str, str]:
        """Try to decode suspicious encoded content."""
        decoded = {}
        # Base64
        try:
            if re.match(r"^[A-Za-z0-9+/]{20,}={0,2}$", text.replace(" ", "")):
                decoded["base64"] = base64.b64decode(text).decode("utf-8", errors="ignore")
        except Exception:
            pass
        # Hex
        try:
            if re.match(r"^(0x)?[0-9a-fA-F]{10,}$", text):
                hex_str = text[2:] if text.startswith("0x") else text
                decoded["hex"] = bytes.fromhex(hex_str).decode("utf-8", errors="ignore")
        except Exception:
            pass
        # URL
        try:
            from urllib.parse import unquote
            if "%" in text:
                decoded["url"] = unquote(text)
        except Exception:
            pass
        return decoded

    def get_stats(self) -> Dict:
        total = len(self.history)
        adversarial = sum(1 for h in self.history if h["is_adversarial"])
        return {
            "total_scanned": total,
            "adversarial_detected": adversarial,
            "techniques": self._technique_distribution(),
        }

    def _technique_distribution(self) -> Dict:
        counts = {}
        for h in self.history:
            for t in h.get("techniques", []):
                counts[t] = counts.get(t, 0) + 1
        return counts

    def to_dict(self) -> Dict:
        return self.get_stats()


__all__ = ["AdversarialInputScanner", "AdversarialResult", "AdversarialType"]
