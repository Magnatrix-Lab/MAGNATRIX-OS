#!/usr/bin/env python3
"""Spam Detector for MAGNATRIX-OS."""
from __future__ import annotations
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

class SpamDetector:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.spam_words = {"free", "win", "winner", "cash", "prize", "urgent", "limited", "click", "buy", "order"}
        self.url_pattern = re.compile(r"http[s]?://")
        self.exclamation_pattern = re.compile(r"!{2,}")
        self.caps_pattern = re.compile(r"[A-Z]{4,}")
    def predict(self, text: str) -> Dict[str, Any]:
        words = text.lower().split()
        spam_score = sum(1 for w in words if w in self.spam_words)
        spam_score += len(self.url_pattern.findall(text)) * 2
        spam_score += len(self.exclamation_pattern.findall(text)) * 1.5
        spam_score += len(self.caps_pattern.findall(text)) * 1
        total_words = len(words) if words else 1
        probability = min(spam_score / total_words, 1.0)
        return {"is_spam": probability > 0.5, "probability": round(probability, 2), "score": spam_score}
    def to_dict(self): return {"spam_words": len(self.spam_words)}
