"""
implementation_guardrails_native.py
MAGNATRIX-OS — Implementation Guardrails

Inspired by engineering-discipline karpathy: Before/during coding guardrails. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class GuardrailCheck:
    check_id: str
    check_type: str
    passed: bool
    message: str


class ImplementationGuardrails:
    """Karpathy-style implementation guardrails for before/during coding."""

    BEFORE_CHECKS = [
        "Read the entire codebase before modifying",
        "Understand the data flow",
        "Check existing tests for patterns",
        "Identify side effects of changes",
        "Plan the minimal change set",
    ]

    DURING_CHECKS = [
        "Write tests before implementation",
        "Keep functions under 50 lines",
        "Use descriptive variable names",
        "Add comments for non-obvious logic",
        "Handle all error cases explicitly",
        "Verify no regression in existing tests",
    ]

    def __init__(self, cache_dir: str = "./guardrails"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.checks: Dict[str, List[GuardrailCheck]] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "checks.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        self.checks[k] = [GuardrailCheck(**c) for c in v]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "checks.json", "w", encoding="utf-8") as f:
            json.dump({k: [asdict(c) for c in v] for k, v in self.checks.items()}, f, indent=2)

    def run_before(self, task_id: str, answers: Dict[str, bool]) -> List[GuardrailCheck]:
        """Run before-coding guardrails."""
        checks = []
        for check in self.BEFORE_CHECKS:
            passed = answers.get(check, False)
            checks.append(GuardrailCheck(
                check_id=f"{task_id}_before_{len(checks)}", check_type="before",
                passed=passed, message=check,
            ))
        self.checks[f"{task_id}_before"] = checks
        self._save()
        return checks

    def run_during(self, task_id: str, answers: Dict[str, bool]) -> List[GuardrailCheck]:
        """Run during-coding guardrails."""
        checks = []
        for check in self.DURING_CHECKS:
            passed = answers.get(check, False)
            checks.append(GuardrailCheck(
                check_id=f"{task_id}_during_{len(checks)}", check_type="during",
                passed=passed, message=check,
            ))
        self.checks[f"{task_id}_during"] = checks
        self._save()
        return checks

    def all_passed(self, task_id: str) -> bool:
        before = self.checks.get(f"{task_id}_before", [])
        during = self.checks.get(f"{task_id}_during", [])
        return all(c.passed for c in before + during)

    def get_stats(self) -> Dict[str, Any]:
        total = sum(len(v) for v in self.checks.values())
        passed = sum(1 for v in self.checks.values() for c in v if c.passed)
        return {"total_checks": total, "passed": passed, "failed": total - passed}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["ImplementationGuardrails", "GuardrailCheck"]