#!/usr/bin/env python3
"""Intrusion Forensics Engine for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import re

class IntrusionForensicsEngine:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.attack_signatures = {
            "sql_injection": re.compile(r"('|\"|\bUNION\b|\bSELECT\b|\bINSERT\b|\bDROP\b).*[\-;#]", re.I),
            "xss": re.compile(r"<script|javascript:|onload=|onerror=", re.I),
            "brute_force": re.compile(r"401|403|login.*failed", re.I),
        }
        self.logs: List[Dict[str, Any]] = []
    def analyze_log(self, log_entry: str) -> Dict[str, Any]:
        findings = []
        for attack, pattern in self.attack_signatures.items():
            if pattern.search(log_entry):
                findings.append(attack)
        return {"entry": log_entry[:100], "findings": findings, "severity": "HIGH" if findings else "LOW"}
    def reconstruct_timeline(self, logs: List[str]) -> List[Dict[str, Any]]:
        timeline = []
        for log in logs:
            analysis = self.analyze_log(log)
            timeline.append(analysis)
        return timeline
    def to_dict(self): return {"signatures": len(self.attack_signatures)}
