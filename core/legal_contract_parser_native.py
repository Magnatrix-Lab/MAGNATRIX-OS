#!/usr/bin/env python3
"""Legal Contract Parser for MAGNATRIX-OS."""
from __future__ import annotations
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

class LegalContractParser:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.risk_patterns = {
            "unlimited_liability": re.compile(r"unlimited liability|full liability", re.I),
            "no_termination": re.compile(r"no.*termination|irrevocable", re.I),
            "auto_renewal": re.compile(r"automatic.*renew|auto-renew", re.I),
            "indemnification": re.compile(r"indemnif|hold harmless", re.I),
        }
    def extract_clauses(self, text: str) -> List[Dict[str, str]]:
        clauses = []
        for match in re.finditer(r"(?:Section|Clause|Article)\s+\d+[.:]\s*(.*?)(?=\n(?:Section|Clause|Article)\s+\d|\Z)", text, re.S):
            clauses.append({"title": match.group(0).split('\n')[0], "text": match.group(1)[:200]})
        return clauses
    def score_risk(self, text: str) -> Dict[str, Any]:
        risk_score = 0
        findings = []
        for name, pattern in self.risk_patterns.items():
            if pattern.search(text):
                risk_score += 1
                findings.append(name)
        return {"risk_score": risk_score, "findings": findings, "level": "HIGH" if risk_score > 2 else "MEDIUM" if risk_score > 0 else "LOW"}
    def to_dict(self): return {"risk_patterns": len(self.risk_patterns)}
