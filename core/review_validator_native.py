"""
review_validator_native.py
MAGNATRIX-OS — Review Validator

Inspired by engineering-discipline: Information-isolated verification of work. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class ReviewResult:
    review_id: str
    plan_id: str
    reviewer_id: str
    findings: List[str]
    severity: str  # low, medium, high
    approved: bool
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class ReviewValidator:
    """Information-isolated verification of work."""

    REVIEW_CHECKS = [
        "Does the code match the plan?",
        "Are all edge cases handled?",
        "Are there security concerns?",
        "Is the code readable and maintainable?",
        "Do tests cover the new behavior?",
        "Is there any duplicate code?",
    ]

    def __init__(self, cache_dir: str = "./reviews"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.reviews: Dict[str, ReviewResult] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "reviews.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for rid, rd in data.items():
                        self.reviews[rid] = ReviewResult(**rd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "reviews.json", "w", encoding="utf-8") as f:
            json.dump({rid: asdict(r) for rid, r in self.reviews.items()}, f, indent=2)

    def review(self, review_id: str, plan_id: str, reviewer_id: str,
               code_changes: List[str], context: Dict[str, Any]) -> ReviewResult:
        """Perform information-isolated review."""
        findings = []
        severity = "low"

        # Check for common issues
        for change in code_changes:
            if "TODO" in change or "FIXME" in change or "HACK" in change:
                findings.append("Unresolved markers found in code")
                severity = "medium"
            if "print(" in change and "test" not in change.lower():
                findings.append("Debug print statements in production code")
                severity = "medium"
            if len(change) > 500 and "\n" in change:
                findings.append("Large code block - consider breaking down")

        # Check for missing tests
        has_test = any("test" in c.lower() for c in code_changes)
        if not has_test and len(code_changes) > 1:
            findings.append("No test changes detected - add tests")

        # Check for documentation
        has_doc = any("doc" in c.lower() or "readme" in c.lower() for c in code_changes)
        if not has_doc and len(code_changes) > 2:
            findings.append("Consider updating documentation")

        approved = len(findings) <= 2 and severity in ["low"]

        result = ReviewResult(
            review_id=review_id, plan_id=plan_id, reviewer_id=reviewer_id,
            findings=findings, severity=severity, approved=approved,
        )
        self.reviews[review_id] = result
        self._save()
        return result

    def get_review(self, review_id: str) -> Optional[ReviewResult]:
        return self.reviews.get(review_id)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.reviews)
        approved = sum(1 for r in self.reviews.values() if r.approved)
        return {"total_reviews": total, "approved": approved, "rejected": total - approved}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["ReviewValidator", "ReviewResult"]