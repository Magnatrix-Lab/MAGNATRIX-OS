"""
clarification_engine_native.py
MAGNATRIX-OS — Clarification Engine

Inspired by engineering-discipline: Resolve ambiguity, explore codebase before acting. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class ClarificationResult:
    result_id: str
    original_request: str
    clarified_request: str
    ambiguities: List[str]
    assumptions: List[str]
    codebase_context: Dict[str, Any]
    resolved: bool
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class ClarificationEngine:
    """Resolve ambiguity and explore codebase before acting."""

    AMBIGUITY_PATTERNS = [
        "implement", "fix", "add", "update", "refactor", "optimize",
        "improve", "change", "create", "build", "make", "do",
    ]

    def __init__(self, cache_dir: str = "./clarifications"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.results: Dict[str, ClarificationResult] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "results.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for rid, rd in data.items():
                        self.results[rid] = ClarificationResult(**rd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "results.json", "w", encoding="utf-8") as f:
            json.dump({rid: asdict(r) for rid, r in self.results.items()}, f, indent=2)

    def clarify(self, result_id: str, request: str, codebase_files: Optional[List[str]] = None) -> ClarificationResult:
        """Resolve ambiguity in a user request."""
        ambiguities = []
        assumptions = []

        # Detect ambiguity patterns
        req_lower = request.lower()
        for pattern in self.AMBIGUITY_PATTERNS:
            if pattern in req_lower:
                ambiguities.append(f"'{pattern}' is vague - specify what, where, and how")

        # Check for missing context
        if "this" in req_lower or "that" in req_lower or "it" in req_lower:
            ambiguities.append("Vague pronouns detected - specify target object")
        if "fast" in req_lower or "better" in req_lower:
            ambiguities.append("Relative terms detected - specify metrics")
        if len(request.split()) < 5:
            ambiguities.append("Request too short - provide more detail")

        # Generate assumptions
        if "test" in req_lower:
            assumptions.append("Assuming unit tests are needed")
        if "bug" in req_lower or "fix" in req_lower:
            assumptions.append("Assuming reproduction steps are available")
        if "api" in req_lower or "endpoint" in req_lower:
            assumptions.append("Assuming existing API patterns should be followed")

        codebase_context = {"files_scanned": len(codebase_files or []), "files": codebase_files or []}
        resolved = len(ambiguities) <= 2 and len(assumptions) <= 3

        clarified = request
        if ambiguities:
            clarified += " [CLARIFY: " + "; ".join(ambiguities[:3]) + "]"

        result = ClarificationResult(
            result_id=result_id, original_request=request, clarified_request=clarified,
            ambiguities=ambiguities, assumptions=assumptions, codebase_context=codebase_context, resolved=resolved,
        )
        self.results[result_id] = result
        self._save()
        return result

    def get_result(self, result_id: str) -> Optional[ClarificationResult]:
        return self.results.get(result_id)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.results)
        resolved = sum(1 for r in self.results.values() if r.resolved)
        return {"total": total, "resolved": resolved, "pending": total - resolved}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["ClarificationEngine", "ClarificationResult"]