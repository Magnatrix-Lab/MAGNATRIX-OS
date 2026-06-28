#!/usr/bin/env python3
"""Forensics Countermeasures Detector for MAGNATRIX-OS."""
from __future__ import annotations
import os, re
from typing import Any, Dict, List, Optional

class ForensicsCountermeasuresDetector:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.anti_forensics_patterns = [
            re.compile(r'\bclear.*history\b|\bhistory\s+-c', re.I),
            re.compile(r'\brm\s+-rf\s+/var/log', re.I),
            re.compile(r'\bshred\s+-u\b', re.I),
            re.compile(r'\bsdelete\b|\bcipher\s+/w', re.I),
            re.compile(r'\bTimeStomp\b|\b timestomp\b', re.I),
        ]
        self.detected: List[Dict[str, Any]] = []
    def scan_logs(self, log_text: str) -> List[Dict[str, Any]]:
        findings = []
        for pat in self.anti_forensics_patterns:
            for m in pat.finditer(log_text):
                findings.append({"pattern": pat.pattern[:30], "position": m.start(), "severity": "high"})
        self.detected.extend(findings)
        return findings
    def scan_files(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        findings = []
        for path in file_paths:
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", errors="ignore") as f:
                    content = f.read()
                for pat in self.anti_forensics_patterns:
                    if pat.search(content):
                        findings.append({"file": path, "pattern": pat.pattern[:30], "severity": "high"})
            except Exception:
                pass
        self.detected.extend(findings)
        return findings
    def to_dict(self): return {"patterns": len(self.anti_forensics_patterns), "detected": len(self.detected)}
