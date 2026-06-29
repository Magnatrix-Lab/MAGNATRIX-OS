"""
ai_slop_cleaner_native.py
MAGNATRIX-OS — AI Slop Cleaner

Inspired by engineering-discipline clean-ai-slop: Post-generation AI code cleanup. Pure stdlib.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class CleanupResult:
    result_id: str
    file_path: str
    issues_found: List[str]
    cleaned_code: str
    loc_before: int
    loc_after: int


class AISlopCleaner:
    """Post-generation AI code cleanup."""

    SLOP_PATTERNS = {
        "boilerplate_comments": r"^\s*# .*\s*$",  # Over-commented lines
        "redundant_docstrings": r'^\s*""".*?"""\s*$',
        "verbose_prints": r"print\(.*debug.*\)",
        "placeholder_text": r"TODO|FIXME|HACK|XXX|NOTE:",
        "excessive_blank_lines": r"\n\n\n+",
        "ai_fluff": r"I\s+(am|will|would|could|should)|\b(in\s+this\s+code|as\s+you\s+can\s+see)\b",
    }

    def __init__(self, cache_dir: str = "./slop_cleanup"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.results: Dict[str, CleanupResult] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "results.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for rid, rd in data.items():
                        self.results[rid] = CleanupResult(**rd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "results.json", "w", encoding="utf-8") as f:
            json.dump({rid: asdict(r) for rid, r in self.results.items()}, f, indent=2)

    def clean(self, result_id: str, file_path: str, code: str) -> CleanupResult:
        """Clean AI-generated code slop."""
        issues = []
        cleaned = code
        loc_before = len(code.splitlines())

        # Remove excessive blank lines
        cleaned = re.sub(r"\n\n\n+", "\n\n", cleaned)
        if cleaned != code:
            issues.append("Excessive blank lines removed")

        # Remove AI fluff comments
        for label, pattern in self.SLOP_PATTERNS.items():
            if label == "excessive_blank_lines":
                continue
            matches = re.findall(pattern, cleaned, re.IGNORECASE | re.MULTILINE)
            if matches:
                issues.append(f"{label}: {len(matches)} occurrences")
                if label in ["ai_fluff", "verbose_prints"]:
                    cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.MULTILINE)

        # Remove trailing whitespace
        cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)

        loc_after = len(cleaned.splitlines())

        result = CleanupResult(
            result_id=result_id, file_path=file_path, issues_found=issues,
            cleaned_code=cleaned, loc_before=loc_before, loc_after=loc_after,
        )
        self.results[result_id] = result
        self._save()
        return result

    def batch_clean(self, files: Dict[str, str]) -> Dict[str, CleanupResult]:
        return {path: self.clean(f"batch_{i}", path, code) for i, (path, code) in enumerate(files.items())}

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.results)
        total_loc_saved = sum(r.loc_before - r.loc_after for r in self.results.values())
        total_issues = sum(len(r.issues_found) for r in self.results.values())
        return {"total_cleaned": total, "loc_saved": total_loc_saved, "issues_found": total_issues}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["AISlopCleaner", "CleanupResult"]