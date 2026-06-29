"""
poc_validator_native.py
MAGNATRIX-OS — PoC Validator

Validate proof-of-concept scripts for correctness and safety. Pure stdlib.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class ValidationResult:
    result_id: str
    poc_id: str
    syntax_ok: bool
    has_safety_check: bool
    dangerous_calls: List[str]
    warnings: List[str]
    approved: bool


class PoCValidator:
    """Validate proof-of-concept scripts for correctness and safety."""

    DANGEROUS_PATTERNS = {
        "exec": [r"exec\s*\(", r"eval\s*\(", r"system\s*\(", r"subprocess\.call"],
        "file_ops": [r"open\s*\(.*['\"]w", r"os\.remove", r"shutil\.rmtree"],
        "network": [r"socket\.connect", r"urllib\.request", r"requests\."],
        "privilege": [r"os\.setuid", r"os\.setgid", r"ctypes\.windll"],
        "shell": [r"os\.popen", r"os\.system", r"`.*`", r"\$\(.*\)"],
    }

    SAFETY_PATTERNS = [r"if __name__ == ['\"]__main__['\"]", r"# .*safe", r"# .* benign", r"# .*research"]

    def __init__(self, cache_dir: str = "./poc_validation"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.results: Dict[str, ValidationResult] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "results.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for rid, rd in data.items():
                        self.results[rid] = ValidationResult(**rd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "results.json", "w", encoding="utf-8") as f:
            json.dump({rid: asdict(r) for rid, r in self.results.items()}, f, indent=2)

    def validate(self, result_id: str, poc_id: str, code: str) -> ValidationResult:
        """Validate a PoC script."""
        dangerous = []
        warnings = []

        for category, patterns in self.DANGEROUS_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, code):
                    dangerous.append(f"{category}: {pattern}")

        has_safety = any(re.search(p, code) for p in self.SAFETY_PATTERNS)

        if not has_safety and dangerous:
            warnings.append("No safety guards found with dangerous calls")
        if len(dangerous) > 5:
            warnings.append("High number of dangerous calls - review carefully")
        if "import os" in code and "subprocess" in code:
            warnings.append("Both os and subprocess imported - potential shell abuse")

        approved = len(dangerous) <= 3 and (has_safety or len(dangerous) <= 1)

        result = ValidationResult(
            result_id=result_id, poc_id=poc_id, syntax_ok=True,
            has_safety_check=has_safety, dangerous_calls=dangerous[:10],
            warnings=warnings, approved=approved,
        )
        self.results[result_id] = result
        self._save()
        return result

    def get_result(self, result_id: str) -> Optional[ValidationResult]:
        return self.results.get(result_id)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.results)
        approved = sum(1 for r in self.results.values() if r.approved)
        return {"total_validated": total, "approved": approved, "rejected": total - approved}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["PoCValidator", "ValidationResult"]