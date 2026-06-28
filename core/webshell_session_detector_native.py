#!/usr/bin/env python3
"""Webshell Session Detector for MAGNATRIX-OS."""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional

class WebshellSessionDetector:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.webshell_patterns = [
            re.compile(r'cmd\.exe|/bin/sh|bash\s+-c', re.I),
            re.compile(r'eval\s*\(|exec\s*\(|system\s*\(', re.I),
            re.compile(r'password|passwd|shadow|sam', re.I),
            re.compile(r'whoami|id\s|uname|net\s+user', re.I),
        ]
        self.session_history: List[Dict[str, Any]] = []
    def analyze_request(self, method: str, path: str, body: str, headers: Dict[str, str]) -> Dict[str, Any]:
        score = 0
        findings = []
        combined = f"{method} {path} {body}"
        for pat in self.webshell_patterns:
            if pat.search(combined):
                score += 1
                findings.append(pat.pattern[:30])
        result = {"score": score, "findings": findings, "is_suspicious": score >= 2, "path": path}
        self.session_history.append(result)
        return result
    def detect_session(self, sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        suspicious = [s for s in sessions if s.get("is_suspicious", False)]
        return suspicious
    def to_dict(self): return {"patterns": len(self.webshell_patterns), "sessions": len(self.session_history)}
