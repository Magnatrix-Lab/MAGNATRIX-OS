#!/usr/bin/env python3
"""
MAGNATRIX-OS — Data Validator & Sanitizer
ai/llm_data_validator_native.py

Features:
- Schema validation (JSON schema, type checking, constraint enforcement)
- PII detection simulation (email, phone, SSN, credit card patterns)
- Input sanitization (strip control chars, normalize unicode, escape sequences)
- Output validation (length limits, forbidden word lists, format checking)
- Validation report with error details and suggestions

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import json
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Pattern, Set, Tuple, Union
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("data_validator")


class ValidationSeverity(enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationStatus(enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"


@dataclass
class ValidationIssue:
    field: str
    message: str
    severity: ValidationSeverity
    suggestion: Optional[str] = None
    code: str = ""


@dataclass
class ValidationResult:
    status: ValidationStatus
    issues: List[ValidationIssue] = field(default_factory=list)
    sanitized: Optional[str] = None
    original_length: int = 0
    sanitized_length: int = 0

    @property
    def has_errors(self) -> bool:
        return any(i.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL) for i in self.issues)

    @property
    def has_critical(self) -> bool:
        return any(i.severity == ValidationSeverity.CRITICAL for i in self.issues)


class PIIPatterns:
    """Pattern-based PII detection."""

    PATTERNS: Dict[str, Pattern] = {
        "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
        "phone": re.compile(r"(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}"),
        "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3,}\d{4}\b"),
        "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    }

    @classmethod
    def detect(cls, text: str) -> Dict[str, List[str]]:
        results: Dict[str, List[str]] = {}
        for name, pattern in cls.PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                results[name] = matches
        return results

    @classmethod
    def redact(cls, text: str, mask: str = "[REDACTED]") -> str:
        for name, pattern in cls.PATTERNS.items():
            text = pattern.sub(f"[{name.upper()}:{mask}]", text)
        return text


class InputSanitizer:
    """Sanitize input strings."""

    @staticmethod
    def strip_control_chars(text: str) -> str:
        return "".join(ch for ch in text if unicodedata.category(ch) not in ("Cc", "Cf"))

    @staticmethod
    def normalize_unicode(text: str) -> str:
        return unicodedata.normalize("NFC", text)

    @staticmethod
    def remove_excessive_whitespace(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def escape_special_chars(text: str) -> str:
        return text.replace("\x00", "").replace("\x1b", "").replace("\u0000", "")

    @staticmethod
    def sanitize(text: str) -> str:
        text = InputSanitizer.escape_special_chars(text)
        text = InputSanitizer.strip_control_chars(text)
        text = InputSanitizer.normalize_unicode(text)
        text = InputSanitizer.remove_excessive_whitespace(text)
        return text


class SchemaValidator:
    """Schema and type validation."""

    def validate(self, data: Any, schema: Dict[str, Any]) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        if not isinstance(data, dict):
            issues.append(ValidationIssue(
                field="root", message="Expected dict", severity=ValidationSeverity.ERROR,
                suggestion="Ensure data is a JSON object",
                code="SCHEMA-001",
            ))
            return issues
        for key, spec in schema.items():
            issues.extend(self._check_field(key, data.get(key), spec, data))
        return issues

    def _check_field(self, name: str, value: Any, spec: Dict[str, Any], parent: Dict) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        required = spec.get("required", False)
        if required and value is None:
            issues.append(ValidationIssue(
                field=name, message=f"Required field '{name}' is missing",
                severity=ValidationSeverity.ERROR, suggestion=f"Provide a value for '{name}'",
                code="REQUIRED-001",
            ))
            return issues
        if value is None:
            return issues
        expected_type = spec.get("type")
        if expected_type and not self._type_match(value, expected_type):
            issues.append(ValidationIssue(
                field=name, message=f"Expected type {expected_type}, got {type(value).__name__}",
                severity=ValidationSeverity.ERROR, suggestion=f"Convert '{name}' to {expected_type}",
                code="TYPE-001",
            ))
        if isinstance(value, str):
            min_len = spec.get("min_length")
            max_len = spec.get("max_length")
            if min_len is not None and len(value) < min_len:
                issues.append(ValidationIssue(
                    field=name, message=f"Length {len(value)} < min {min_len}",
                    severity=ValidationSeverity.WARNING, suggestion=f"Extend '{name}' to at least {min_len} chars",
                    code="LENGTH-001",
                ))
            if max_len is not None and len(value) > max_len:
                issues.append(ValidationIssue(
                    field=name, message=f"Length {len(value)} > max {max_len}",
                    severity=ValidationSeverity.WARNING, suggestion=f"Trim '{name}' to at most {max_len} chars",
                    code="LENGTH-002",
                ))
            pattern = spec.get("pattern")
            if pattern and not re.match(pattern, value):
                issues.append(ValidationIssue(
                    field=name, message=f"Value does not match pattern {pattern}",
                    severity=ValidationSeverity.WARNING, suggestion=f"Check format of '{name}'",
                    code="PATTERN-001",
                ))
        enum_values = spec.get("enum")
        if enum_values is not None and value not in enum_values:
            issues.append(ValidationIssue(
                field=name, message=f"Value '{value}' not in allowed enum",
                severity=ValidationSeverity.ERROR, suggestion=f"Use one of: {enum_values}",
                code="ENUM-001",
            ))
        return issues

    @staticmethod
    def _type_match(value: Any, expected: str) -> bool:
        type_map = {
            "string": str, "integer": int, "number": (int, float),
            "boolean": bool, "array": list, "object": dict, "null": type(None),
        }
        expected_cls = type_map.get(expected)
        if expected_cls is None:
            return True
        return isinstance(value, expected_cls)


class OutputValidator:
    """Validate output against constraints."""

    def __init__(self, max_length: int = 10000, forbidden_words: Optional[List[str]] = None):
        self.max_length = max_length
        self.forbidden_words = set(forbidden_words or [])

    def validate(self, text: str) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        if len(text) > self.max_length:
            issues.append(ValidationIssue(
                field="output", message=f"Output length {len(text)} > max {self.max_length}",
                severity=ValidationSeverity.ERROR, suggestion=f"Reduce output to {self.max_length} chars",
                code="OUTPUT-001",
            ))
        for word in self.forbidden_words:
            if word.lower() in text.lower():
                issues.append(ValidationIssue(
                    field="output", message=f"Forbidden word '{word}' detected",
                    severity=ValidationSeverity.CRITICAL, suggestion=f"Remove or rephrase content containing '{word}'",
                    code="FORBIDDEN-001",
                ))
        return issues

    def check_format(self, text: str, expected_format: str) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        if expected_format == "json":
            try:
                json.loads(text)
            except json.JSONDecodeError as e:
                issues.append(ValidationIssue(
                    field="output", message=f"Invalid JSON: {e}",
                    severity=ValidationSeverity.ERROR, suggestion="Fix JSON syntax",
                    code="FORMAT-001",
                ))
        elif expected_format == "xml":
            if not text.strip().startswith("<"):
                issues.append(ValidationIssue(
                    field="output", message="Does not start with XML tag",
                    severity=ValidationSeverity.WARNING, suggestion="Wrap in proper XML root element",
                    code="FORMAT-002",
                ))
        return issues


class DataValidator:
    """Unified data validation and sanitization engine."""

    def __init__(self, max_output_length: int = 10000, forbidden_words: Optional[List[str]] = None):
        self.schema_validator = SchemaValidator()
        self.output_validator = OutputValidator(max_output_length, forbidden_words)
        self.sanitizer = InputSanitizer()
        self.pii = PIIPatterns()

    def validate_input(self, data: Any, schema: Optional[Dict[str, Any]] = None, sanitize: bool = True) -> ValidationResult:
        issues: List[ValidationIssue] = []
        sanitized = None
        original_length = 0
        sanitized_length = 0

        if isinstance(data, str):
            original_length = len(data)
            if sanitize:
                sanitized = self.sanitizer.sanitize(data)
                sanitized_length = len(sanitized)
                if sanitized != data:
                    issues.append(ValidationIssue(
                        field="input", message="Input was sanitized",
                        severity=ValidationSeverity.INFO, suggestion="Original input contained control characters or invalid unicode",
                        code="SANITIZE-001",
                    ))
            pii_found = self.pii.detect(data)
            if pii_found:
                for pii_type, matches in pii_found.items():
                    issues.append(ValidationIssue(
                        field="input", message=f"Detected {pii_type}: {len(matches)} occurrence(s)",
                        severity=ValidationSeverity.WARNING, suggestion=f"Review and redact {pii_type} if sensitive",
                        code=f"PII-{pii_type.upper()}-001",
                    ))
        if schema:
            issues.extend(self.schema_validator.validate(data, schema))

        status = ValidationStatus.PASS
        if any(i.severity == ValidationSeverity.CRITICAL for i in issues):
            status = ValidationStatus.FAIL
        elif any(i.severity == ValidationSeverity.ERROR for i in issues):
            status = ValidationStatus.PARTIAL

        return ValidationResult(
            status=status, issues=issues, sanitized=sanitized,
            original_length=original_length, sanitized_length=sanitized_length,
        )

    def validate_output(self, text: str, expected_format: Optional[str] = None) -> ValidationResult:
        issues = self.output_validator.validate(text)
        if expected_format:
            issues.extend(self.output_validator.check_format(text, expected_format))
        pii_found = self.pii.detect(text)
        for pii_type, matches in pii_found.items():
            issues.append(ValidationIssue(
                field="output", message=f"Detected {pii_type}: {len(matches)} occurrence(s)",
                severity=ValidationSeverity.WARNING, suggestion=f"Review and redact {pii_type} if sensitive",
                code=f"PII-{pii_type.upper()}-002",
            ))
        status = ValidationStatus.FAIL if any(i.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL) for i in issues) else ValidationStatus.PASS
        return ValidationResult(status=status, issues=issues, original_length=len(text))

    def redact_pii(self, text: str) -> str:
        return self.pii.redact(text)


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Data Validator & Sanitizer")
    print("ai/llm_data_validator_native.py")
    print("=" * 60)

    validator = DataValidator(max_output_length=500, forbidden_words=["password", "secret"])

    # 1. Schema validation
    print("")
    print("[1] Schema Validation")
    schema = {
        "name": {"type": "string", "required": True, "min_length": 2, "max_length": 50},
        "age": {"type": "integer", "required": True},
        "email": {"type": "string", "required": False, "pattern": r"^[^@]+@[^@]+\.[^@]+$"},
    }
    data_ok = {"name": "Alice", "age": 30, "email": "alice@example.com"}
    result = validator.validate_input(data_ok, schema)
    print(f"  Valid data: status={result.status.value}, issues={len(result.issues)}")
    data_bad = {"name": "A", "age": "thirty"}
    result = validator.validate_input(data_bad, schema)
    print(f"  Invalid data: status={result.status.value}, issues={len(result.issues)}")
    for issue in result.issues:
        print(f"    [{issue.severity.value}] {issue.field}: {issue.message}")

    # 2. PII detection
    print("")
    print("[2] PII Detection")
    text = "Contact john.doe@example.com or call 555-123-4567. SSN: 123-45-6789. Card: 4111 1111 1111 1111."
    pii = validator.pii.detect(text)
    for pii_type, matches in pii.items():
        print(f"  {pii_type}: {matches}")
    redacted = validator.redact_pii(text)
    print(f"  Redacted: {redacted}")

    # 3. Input sanitization
    print("")
    print("[3] Input Sanitization")
    dirty = "Hello\x00\x1bworld\u200b\t\t\n\n test"
    result = validator.validate_input(dirty, sanitize=True)
    print(f"  Original: {repr(dirty)}")
    print(f"  Sanitized: {repr(result.sanitized)}")
    print(f"  Issues: {len(result.issues)}")

    # 4. Output validation
    print("")
    print("[4] Output Validation")
    output = "The password is secret123 and it is very long" + "x" * 500
    result = validator.validate_output(output, expected_format="json")
    print(f"  Output status: {result.status.value}, issues: {len(result.issues)}")
    for issue in result.issues:
        print(f"    [{issue.severity.value}] {issue.message}")

    # 5. JSON format check
    print("")
    print("[5] JSON Format Check")
    result = validator.validate_output('{"valid": true}', expected_format="json")
    print(f"  Valid JSON: status={result.status.value}, issues={len(result.issues)}")
    result = validator.validate_output('{"invalid":}', expected_format="json")
    print(f"  Invalid JSON: status={result.status.value}, issues={len(result.issues)}")

    print("" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()
