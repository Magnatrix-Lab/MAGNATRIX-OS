#!/usr/bin/env python3
"""Patch Generator for MAGNATRIX-OS."""
from __future__ import annotations
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

class PatchGenerator:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.patches: List[Dict[str, Any]] = []
    def generate_diff(self, original: str, modified: str) -> str:
        lines1 = original.splitlines()
        lines2 = modified.splitlines()
        diff = []
        for i, (a, b) in enumerate(zip(lines1, lines2)):
            if a != b:
                diff.append(f"- {a}")
                diff.append(f"+ {b}")
        return "\n".join(diff)
    def check_compatibility(self, patch: str, codebase: str) -> bool:
        # Simplified: check if removed lines exist in codebase
        for line in patch.splitlines():
            if line.startswith("- "):
                target = line[2:]
                if target not in codebase:
                    return False
        return True
    def to_dict(self): return {"patches": len(self.patches)}
