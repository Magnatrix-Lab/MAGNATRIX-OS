
"""
sensitive_tab_redactor_native.py
MAGNATRIX-OS — Sensitive Tab Redactor

Inspired by Hermes Browser Extension v0.1.6 sensitive-tab redaction:
Banking, password, payment, health, and similar tabs are redacted
before prompt assembly so sensitive data does not leak.

Pure Python standard library.
"""

import re
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
import json


class SensitivityLevel(Enum):
    NONE = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


@dataclass
class SensitivityRule:
    name: str
    patterns: List[str]
    keywords: List[str]
    level: SensitivityLevel
    redaction_action: str = "redact"


class SensitiveTabRedactor:
    """Detect and redact sensitive browser tab content."""

    def __init__(self, custom_rules: Optional[List[SensitivityRule]] = None):
        self.rules: List[SensitivityRule] = [
            SensitivityRule(
                name="banking",
                patterns=[r"bank\.", r"online-banking", r"secure\.bank", r"\.bank/"],
                keywords=["login", "account", "balance", "transfer", "routing", "swift"],
                level=SensitivityLevel.CRITICAL,
            ),
            SensitivityRule(
                name="password",
                patterns=[r"password", r"login", r"signin", r"auth", r"sso\.", r"2fa"],
                keywords=["password", "passphrase", "secret", "token", "credential"],
                level=SensitivityLevel.CRITICAL,
            ),
            SensitivityRule(
                name="payment",
                patterns=[r"pay\.", r"checkout", r"billing", r"stripe", r"paypal"],
                keywords=["card", "cvv", "ccn", "payment", "billing", "invoice"],
                level=SensitivityLevel.CRITICAL,
            ),
            SensitivityRule(
                name="health",
                patterns=[r"health", r"medical", r"patient", r"epic", r"mychart"],
                keywords=["diagnosis", "prescription", "medical", "ssn", "dob", "patient"],
                level=SensitivityLevel.HIGH,
            ),
            SensitivityRule(
                name="personal",
                patterns=[r"profile", r"settings/account", r"personal"],
                keywords=["address", "phone", "email", "ssn", "dob", "full name"],
                level=SensitivityLevel.HIGH,
            ),
            SensitivityRule(
                name="government",
                patterns=[r"gov\.", r"tax", r"irs", r"ssa", r"passport"],
                keywords=["tax id", "ein", "ssn", "passport", "citizenship"],
                level=SensitivityLevel.HIGH,
            ),
        ]
        if custom_rules:
            self.rules.extend(custom_rules)
        self.redaction_log: List[Dict] = []

    def analyze(self, title: str, url: str, content: Optional[str] = None) -> SensitivityLevel:
        """Analyze a tab for sensitivity level."""
        max_level = SensitivityLevel.NONE
        for rule in self.rules:
            if self._matches_rule(title, url, content, rule):
                if rule.level.value > max_level.value:
                    max_level = rule.level
        return max_level

    def _matches_rule(self, title: str, url: str, content: Optional[str], rule: SensitivityRule) -> bool:
        combined = f"{title} {url} {content or ''}".lower()
        for pattern in rule.patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                return True
        for keyword in rule.keywords:
            if keyword.lower() in combined:
                return True
        return False

    def redact(self, title: str, url: str, content: Optional[str] = None) -> Dict:
        """Redact sensitive tab information."""
        level = self.analyze(title, url, content)
        if level in (SensitivityLevel.NONE, SensitivityLevel.LOW):
            return {
                "title": title, "url": url, "content": content,
                "redacted": False, "level": level.name
            }
        result = {
            "title": self._redact_title(title, level),
            "url": self._redact_url(url, level),
            "content": self._redact_content(content, level) if content else None,
            "redacted": True,
            "level": level.name,
        }
        self.redaction_log.append({
            "original_title": title[:50],
            "original_url": url[:50],
            "level": level.name,
            "reason": "sensitivity_rule",
        })
        return result

    def _redact_title(self, title: str, level: SensitivityLevel) -> str:
        if level in (SensitivityLevel.HIGH, SensitivityLevel.CRITICAL):
            return "[REDACTED - Sensitive Content]"
        return title[:20] + "..." if len(title) > 20 else title

    def _redact_url(self, url: str, level: SensitivityLevel) -> str:
        if level in (SensitivityLevel.HIGH, SensitivityLevel.CRITICAL):
            return "[REDACTED URL]"
        return url[:30] + "..." if len(url) > 30 else url

    def _redact_content(self, content: str, level: SensitivityLevel) -> str:
        if level == SensitivityLevel.CRITICAL:
            return "[CONTENT REDACTED]"
        return content[:200] + "..." if len(content) > 200 else content

    def is_sensitive(self, title: str, url: str, content: Optional[str] = None) -> bool:
        return self.analyze(title, url, content) in (SensitivityLevel.HIGH, SensitivityLevel.CRITICAL)

    def filter_tabs(self, tabs: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Split tabs into safe and sensitive."""
        safe = []
        sensitive = []
        for tab in tabs:
            title = tab.get("title", "")
            url = tab.get("url", "")
            if self.is_sensitive(title, url):
                sensitive.append(self.redact(title, url))
            else:
                safe.append(tab)
        return safe, sensitive

    def to_dict(self) -> Dict:
        return {
            "rules": [r.name for r in self.rules],
            "redaction_count": len(self.redaction_log),
            "total_rules": len(self.rules),
        }


__all__ = ["SensitiveTabRedactor", "SensitivityRule", "SensitivityLevel"]
