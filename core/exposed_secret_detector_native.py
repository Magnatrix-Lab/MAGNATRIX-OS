"""
exposed_secret_detector_native.py
MAGNATRIX-OS — Exposed Secret Detector

Inspired by Frogy2.0: Detect exposed secrets, API keys, tokens, and credentials in web responses. Pure stdlib.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class ExposedSecret:
    secret_type: str
    location: str
    snippet: str
    severity: str
    confidence: float
    line_number: int = 0


class ExposedSecretDetector:
    """Detect exposed secrets in web responses and source code."""

    PATTERNS = {
        "aws_key": r'AKIA[0-9A-Z]{16}',
        "aws_secret": r'[0-9a-zA-Z/+]{40}',
        "github_token": r'ghp_[0-9a-zA-Z]{36}',
        "slack_token": r'xox[baprs]-[0-9a-zA-Z]{10,48}',
        "api_key_generic": r'api[_-]?key["\']?\s*[:=]\s*["\']?[a-zA-Z0-9]{32,}',
        "password": r'password["\']?\s*[:=]\s*["\'][^"\']{4,}',
        "private_key": r'-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----',
        "jwt": r'eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*',
    }

    def __init__(self, data_dir: str = "./exposed_secrets"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.findings: List[ExposedSecret] = []
        self._load()

    def _load(self) -> None:
        file = self.data_dir / "findings.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.findings = [ExposedSecret(**d) for d in data]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.data_dir / "findings.json", "w", encoding="utf-8") as f:
            json.dump([asdict(f) for f in self.findings], f, indent=2)

    def scan(self, content: str, location: str = "") -> List[ExposedSecret]:
        """Scan content for exposed secrets."""
        findings = []
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            for secret_type, pattern in self.PATTERNS.items():
                for match in re.finditer(pattern, line, re.IGNORECASE):
                    severity = "critical" if secret_type in ["aws_key", "private_key", "github_token"] else "high"
                    finding = ExposedSecret(
                        secret_type=secret_type, location=location,
                        snippet=match.group()[:50], severity=severity,
                        confidence=0.9, line_number=line_num,
                    )
                    findings.append(finding)
        self.findings.extend(findings)
        self._save()
        return findings

    def get_by_severity(self, severity: str) -> List[ExposedSecret]:
        return [f for f in self.findings if f.severity == severity]

    def get_stats(self) -> Dict[str, Any]:
        by_type = {}
        for f in self.findings:
            by_type[f.secret_type] = by_type.get(f.secret_type, 0) + 1
        return {"total_findings": len(self.findings), "by_type": by_type}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["ExposedSecretDetector", "ExposedSecret"]