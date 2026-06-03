"""
llm_output_validator_native.py
MAGNATRIX-OS Output Validator Engine
Native Python, stdlib only.
Provides output validation, format checking, safety scoring, and content policy enforcement.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional


class ValidationStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    NEEDS_REVIEW = "needs_review"


class ContentPolicy(Enum):
    SAFE = "safe"
    SENSITIVE = "sensitive"
    HARMFUL = "harmful"
    UNKNOWN = "unknown"


@dataclass
class ValidationResult:
    status: ValidationStatus
    checks: Dict[str, Any]
    issues: List[str]
    safety_score: float
    policy: ContentPolicy
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value, "checks": self.checks, "issues": self.issues,
            "safety_score": self.safety_score, "policy": self.policy.value,
        }


class OutputValidatorEngine:
    """Output validation with format checking and safety scoring."""

    def __init__(self) -> None:
        self._format_validators: Dict[str, Callable[[str], bool]] = {}
        self._content_filters: List[Tuple[str, float]] = []  # pattern, penalty
        self._required_elements: Dict[str, List[str]] = {}  # format -> required elements

    def register_format_validator(self, format_name: str, validator: Callable[[str], bool]) -> None:
        self._format_validators[format_name] = validator

    def add_content_filter(self, pattern: str, penalty: float) -> None:
        self._content_filters.append((re.compile(pattern, re.IGNORECASE), penalty))

    def add_required_element(self, format_name: str, element: str) -> None:
        self._required_elements.setdefault(format_name, []).append(element)

    def validate(self, output: str, expected_format: Optional[str] = None, required_elements: Optional[List[str]] = None) -> ValidationResult:
        checks = {}
        issues = []
        safety_score = 1.0
        policy = ContentPolicy.SAFE

        # Length check
        checks["length"] = len(output) > 0
        if not checks["length"]:
            issues.append("Empty output")

        # Format validation
        if expected_format and expected_format in self._format_validators:
            checks["format"] = self._format_validators[expected_format](output)
            if not checks["format"]:
                issues.append(f"Format validation failed for {expected_format}")

        # Required elements
        elements = required_elements or self._required_elements.get(expected_format, [])
        for element in elements:
            if element not in output:
                issues.append(f"Missing required element: {element}")
        checks["required_elements"] = len([e for e in elements if e in output]) == len(elements) if elements else True

        # Content safety
        for pattern, penalty in self._content_filters:
            matches = pattern.findall(output)
            if matches:
                safety_score -= penalty * len(matches)
                issues.append(f"Content filter matched: {pattern.pattern[:30]}...")

        safety_score = max(0.0, min(1.0, safety_score))

        if safety_score < 0.3:
            policy = ContentPolicy.HARMFUL
        elif safety_score < 0.7:
            policy = ContentPolicy.SENSITIVE

        # Determine status
        if issues and safety_score < 0.5:
            status = ValidationStatus.FAIL
        elif issues:
            status = ValidationStatus.WARNING
        else:
            status = ValidationStatus.PASS

        return ValidationResult(status, checks, issues, safety_score, policy)

    def validate_json(self, output: str, schema: Optional[Dict[str, type]] = None) -> ValidationResult:
        issues = []
        try:
            data = json.loads(output)
            checks = {"json_valid": True}
            if schema:
                for key, expected_type in schema.items():
                    if key not in data:
                        issues.append(f"Missing key: {key}")
                    elif not isinstance(data[key], expected_type):
                        issues.append(f"Type mismatch for {key}: expected {expected_type.__name__}")
                checks["schema"] = len(issues) == 0
            else:
                checks["schema"] = True
        except json.JSONDecodeError as e:
            checks = {"json_valid": False}
            issues.append(f"Invalid JSON: {e}")

        return ValidationResult(
            ValidationStatus.PASS if not issues else ValidationStatus.FAIL,
            checks, issues, 1.0, ContentPolicy.SAFE
        )

    def get_stats(self) -> Dict[str, Any]:
        return {
            "format_validators": len(self._format_validators),
            "content_filters": len(self._content_filters),
            "required_elements": sum(len(v) for v in self._required_elements.values()),
        }


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Output Validator Engine")
    print("=" * 60)

    engine = OutputValidatorEngine()

    engine.register_format_validator("json", lambda s: s.strip().startswith(("{", "[")))
    engine.add_content_filter(r"\b(hate|kill|attack|bomb)\b", 0.3)
    engine.add_required_element("report", "summary")

    outputs = [
        "This is a safe response with summary.",
        "This response contains hate speech and attack language.",
        "{\"name\": \"Alice\", \"age\": 30}",
        "invalid json {",
    ]

    for output in outputs:
        print(f"\n--- Validating: {output[:50]}...")
        if output.strip().startswith(("{", "[")):
            result = engine.validate_json(output, {"name": str, "age": int})
        else:
            result = engine.validate(output, expected_format="report")
        print(f"  Status: {result.status.value}")
        print(f"  Safety: {result.safety_score:.2f}")
        print(f"  Issues: {result.issues}")

    print("\nOutput Validator test complete.")


if __name__ == "__main__":
    run()
