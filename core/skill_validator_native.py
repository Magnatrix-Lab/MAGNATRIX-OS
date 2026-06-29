
"""
skill_validator_native.py
MAGNATRIX-OS — Skill Validator

Validate skill schemas, scan for security issues,
and check cross-platform compatibility.
Inspired by SkillKit validation and scanner.

Pure Python standard library.
"""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum, auto


class ValidationSeverity(Enum):
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()


@dataclass
class ValidationIssue:
    severity: ValidationSeverity
    code: str
    message: str
    line: Optional[int] = None
    suggestion: str = ""


class SkillValidator:
    """Validate skill files for correctness and security."""

    # Security patterns to flag
    DANGEROUS_PATTERNS = [
        (r"\b(rm\s+-rf|del\s+/[fq]|format\s+[a-z]:|mkfs\.)", "Dangerous filesystem command"),
        (r"\b(curl\s+.*\|\s*sh|wget\s+.*\|\s*sh)", "Remote pipe execution"),
        (r"\b(eval\s*\(|exec\s*\(|system\s*\()", "Dynamic code execution"),
        (r"\b(api[_-]?key|token|password|secret)\s*[:=]\s*[\"'][^\"']{10,}[\"']", "Hardcoded credentials"),
        (r"\b(0\.0\.0\.0|localhost|127\.0\.0\.1):\d+", "Local network access"),
    ]

    # Required sections for valid skill
    REQUIRED_SECTIONS = ["name", "description", "content"]

    def __init__(self):
        self.issues: List[ValidationIssue] = []

    def validate(self, skill_content: str, skill_name: str = "") -> List[ValidationIssue]:
        self.issues = []
        self._check_required_sections(skill_content)
        self._check_security_issues(skill_content)
        self._check_length(skill_content)
        self._check_formatting(skill_content)
        self._check_placeholders(skill_content)
        return self.issues

    def _check_required_sections(self, content: str) -> None:
        content_lower = content.lower()
        for section in self.REQUIRED_SECTIONS:
            if section not in content_lower:
                self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_SECTION",
                    message=f"Required section '{section}' not found",
                    suggestion=f"Add a {section} section to the skill",
                ))

    def _check_security_issues(self, content: str) -> None:
        for pattern, desc in self.DANGEROUS_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    code="SECURITY_RISK",
                    message=f"Potential security risk: {desc}",
                    line=content[:match.start()].count("\n") + 1,
                    suggestion="Review and remove potentially dangerous commands",
                ))

    def _check_length(self, content: str) -> None:
        lines = content.splitlines()
        if len(lines) < 3:
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="TOO_SHORT",
                message="Skill is too short (< 3 lines)",
                suggestion="Add more detailed instructions",
            ))
        if len(content) > 50000:
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="TOO_LONG",
                message="Skill exceeds 50000 characters",
                suggestion="Consider splitting into multiple skills",
            ))

    def _check_formatting(self, content: str) -> None:
        if "\t" in content:
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="TABS_USED",
                message="Tabs found in content — use spaces for consistency",
                suggestion="Replace tabs with spaces",
            ))
        if content.count("```") % 2 != 0:
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="UNMATCHED_CODE_BLOCK",
                message="Unmatched code block markers (```)",
                suggestion="Ensure all code blocks are properly closed",
            ))

    def _check_placeholders(self, content: str) -> None:
        placeholders = re.findall(r"\{\{([^}]+)\}\}", content)
        if placeholders:
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                code="PLACEHOLDERS_FOUND",
                message=f"Placeholders found: {', '.join(set(placeholders))}",
                suggestion="Ensure placeholders are documented",
            ))

    def is_valid(self, content: str) -> bool:
        issues = self.validate(content)
        return not any(i.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL) for i in issues)

    def get_score(self, content: str) -> float:
        """Return a validation score 0.0-1.0."""
        issues = self.validate(content)
        if not issues:
            return 1.0
        deductions = {
            ValidationSeverity.CRITICAL: 0.5,
            ValidationSeverity.ERROR: 0.2,
            ValidationSeverity.WARNING: 0.05,
            ValidationSeverity.INFO: 0.0,
        }
        score = 1.0 - sum(deductions.get(i.severity, 0.1) for i in issues)
        return max(0.0, score)

    def to_dict(self) -> Dict:
        return {
            "dangerous_patterns": len(self.DANGEROUS_PATTERNS),
            "required_sections": self.REQUIRED_SECTIONS,
        }


__all__ = ["SkillValidator", "ValidationIssue", "ValidationSeverity"]
