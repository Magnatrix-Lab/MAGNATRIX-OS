"""
comprehension_first_guard_native.py
MAGNATRIX-OS — Comprehension-First Guard

Inspired by Ponytail: "Understand before you modify." Guard that prevents code changes without comprehension. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class ComprehensionCheck:
    check_id: str
    file_path: str
    understood: bool
    coverage: float
    missing_context: List[str]
    approved: bool
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class ComprehensionFirstGuard:
    """Guard that prevents code changes without comprehension."""

    CHECKS = [
        "What does this code do?",
        "Why was it written this way?",
        "What are the side effects?",
        "Who depends on this code?",
        "What tests cover this?",
    ]

    def __init__(self, cache_dir: str = "./comprehension_checks"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.checks: Dict[str, ComprehensionCheck] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "checks.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for cid, cd in data.items():
                        self.checks[cid] = ComprehensionCheck(**cd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "checks.json", "w", encoding="utf-8") as f:
            json.dump({cid: asdict(c) for cid, c in self.checks.items()}, f, indent=2)

    def check(self, check_id: str, file_path: str, context: str,
              answers: Dict[str, str]) -> ComprehensionCheck:
        """Verify comprehension before allowing modification."""
        coverage = 0.0
        missing = []
        for q in self.CHECKS:
            if q in answers and len(answers[q]) > 10:
                coverage += 0.2
            else:
                missing.append(q)
        understood = coverage >= 0.6
        approved = understood and len(missing) <= 2
        result = ComprehensionCheck(
            check_id=check_id, file_path=file_path, understood=understood,
            coverage=round(coverage, 2), missing_context=missing, approved=approved,
        )
        self.checks[check_id] = result
        self._save()
        return result

    def is_approved(self, check_id: str) -> bool:
        c = self.checks.get(check_id)
        return c.approved if c else False

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.checks)
        approved = sum(1 for c in self.checks.values() if c.approved)
        return {"total_checks": total, "approved": approved, "rejected": total - approved}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["ComprehensionFirstGuard", "ComprehensionCheck"]