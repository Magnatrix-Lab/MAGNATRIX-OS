"""
llm_data_quality_native.py
MAGNATRIX-OS Data Quality Engine
Native Python, stdlib only.
Provides data profiling, quality scoring, anomaly detection, schema validation, and cleansing rules.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


class QualityDimension(Enum):
    COMPLETENESS = "completeness"
    UNIQUENESS = "uniqueness"
    VALIDITY = "validity"
    CONSISTENCY = "consistency"
    ACCURACY = "accuracy"
    TIMELINESS = "timeliness"


@dataclass
class QualityScore:
    dimension: QualityDimension
    score: float  # 0-1
    issues: List[str] = field(default_factory=list)
    total_records: int = 0
    failed_records: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension.value, "score": round(self.score, 3),
            "issues": self.issues, "total": self.total_records, "failed": self.failed_records,
        }


class DataQualityEngine:
    """Data quality assessment with multi-dimensional scoring."""

    def __init__(self) -> None:
        self._rules: Dict[str, List[Callable]] = {}
        self._profiles: Dict[str, Dict[str, Any]] = {}

    def add_rule(self, column: str, rule: Callable[[Any], bool], description: str = "") -> None:
        self._rules.setdefault(column, []).append((rule, description))

    def profile(self, data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        if not data:
            return {}
        columns = list(data[0].keys())
        profile = {}
        for col in columns:
            values = [row.get(col) for row in data if row.get(col) is not None]
            all_values = [row.get(col) for row in data]
            prof = {
                "count": len(all_values),
                "null_count": sum(1 for v in all_values if v is None),
                "unique_count": len(set(str(v) for v in values)),
                "type": type(values[0]).__name__ if values else "unknown",
            }
            if values and isinstance(values[0], (int, float)):
                prof["min"] = min(values)
                prof["max"] = max(values)
                prof["mean"] = statistics.mean(values) if len(values) > 1 else values[0] if values else 0
            profile[col] = prof
        self._profiles = profile
        return profile

    def assess(self, data: List[Dict[str, Any]]) -> Dict[str, QualityScore]:
        if not data:
            return {}
        results = {}
        total = len(data)

        # Completeness
        null_counts = {}
        for col in data[0].keys():
            null_counts[col] = sum(1 for row in data if row.get(col) is None)
        total_nulls = sum(null_counts.values())
        total_cells = total * len(data[0].keys())
        completeness_score = 1.0 - (total_nulls / total_cells) if total_cells > 0 else 1.0
        results["completeness"] = QualityScore(
            QualityDimension.COMPLETENESS, completeness_score,
            [f"{col}: {null_counts[col]} nulls" for col, count in null_counts.items() if count > 0],
            total, total_nulls
        )

        # Uniqueness
        duplicates = 0
        seen = set()
        for row in data:
            row_tuple = tuple(sorted(row.items()))
            if row_tuple in seen:
                duplicates += 1
            seen.add(row_tuple)
        uniqueness_score = 1.0 - (duplicates / total) if total > 0 else 1.0
        results["uniqueness"] = QualityScore(
            QualityDimension.UNIQUENESS, uniqueness_score,
            [f"{duplicates} duplicate rows"] if duplicates > 0 else [], total, duplicates
        )

        # Validity
        invalid = 0
        for row in data:
            for col, (rule, desc) in [(c, r) for c, rules in self._rules.items() for r in rules]:
                if col in row and not rule(row[col]):
                    invalid += 1
        validity_score = 1.0 - (invalid / total) if total > 0 else 1.0
        results["validity"] = QualityScore(
            QualityDimension.VALIDITY, validity_score, [], total, invalid
        )

        return results

    def overall_score(self, assessment: Dict[str, QualityScore]) -> float:
        if not assessment:
            return 0.0
        return sum(s.score for s in assessment.values()) / len(assessment)

    def cleanse(self, data: List[Dict[str, Any]], fill_defaults: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        cleaned = []
        for row in data:
            new_row = dict(row)
            for col in list(new_row.keys()):
                if new_row[col] is None and fill_defaults and col in fill_defaults:
                    new_row[col] = fill_defaults[col]
            cleaned.append(new_row)
        return cleaned

    def get_profile(self) -> Dict[str, Dict[str, Any]]:
        return self._profiles


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Data Quality Engine")
    print("=" * 60)

    engine = DataQualityEngine()
    engine.add_rule("age", lambda v: isinstance(v, (int, float)) and v >= 0, "Age must be non-negative")
    engine.add_rule("email", lambda v: isinstance(v, str) and "@" in v, "Email must contain @")

    data = [
        {"name": "Alice", "age": 30, "email": "alice@example.com"},
        {"name": "Bob", "age": -5, "email": "bob"},
        {"name": "Charlie", "age": None, "email": "charlie@example.com"},
        {"name": "Alice", "age": 30, "email": "alice@example.com"},  # duplicate
    ]

    print("\n--- Profile ---")
    profile = engine.profile(data)
    for col, prof in profile.items():
        print(f"  {col}: {prof}")

    print("\n--- Assess ---")
    assessment = engine.assess(data)
    for dim, score in assessment.items():
        print(f"  {dim}: {score.to_dict()}")

    print(f"\n--- Overall score: {engine.overall_score(assessment):.3f} ---")

    print("\n--- Cleanse ---")
    cleaned = engine.cleanse(data, fill_defaults={"age": 0})
    for row in cleaned:
        print(f"  {row}")

    print("\nData Quality test complete.")


if __name__ == "__main__":
    run()
