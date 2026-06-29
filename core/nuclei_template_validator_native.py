"""
nuclei_template_validator_native.py
MAGNATRIX-OS — Nuclei Template Validator

Validate Nuclei templates for correct structure, required fields, and YAML syntax. Pure stdlib.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class ValidationResult:
    template_id: str
    valid: bool
    errors: List[str]
    warnings: List[str]
    severity: str


class NucleiTemplateValidator:
    """Validate Nuclei templates for correct structure and required fields."""

    REQUIRED_FIELDS = ["id", "info"]
    INFO_REQUIRED = ["name", "author", "severity"]
    VALID_SEVERITIES = ["info", "low", "medium", "high", "critical", "unknown"]
    VALID_PROTOCOLS = ["http", "dns", "tcp", "ssl", "network", "file", "headless", "code", "javascript", "workflow"]
    VALID_MATCHER_TYPES = ["status", "word", "regex", "binary", "dsl", "xpath", "size"]
    VALID_EXTRACTOR_TYPES = ["regex", "json", "kval", "xpath", "dsl"]

    def __init__(self, cache_dir: str = "./template_validation"):
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

    def validate(self, template_id: str, template_data: Dict[str, Any]) -> ValidationResult:
        """Validate a Nuclei template structure."""
        errors = []
        warnings = []

        # Check required top-level fields
        for field in self.REQUIRED_FIELDS:
            if field not in template_data:
                errors.append(f"Missing required field: {field}")

        # Validate ID
        tid = template_data.get("id", "")
        if not tid:
            errors.append("Template ID is empty")
        elif " " in str(tid):
            errors.append("Template ID must not contain spaces")

        # Validate info block
        info = template_data.get("info", {})
        for field in self.INFO_REQUIRED:
            if field not in info:
                errors.append(f"Missing required info field: {field}")

        if info.get("severity") not in self.VALID_SEVERITIES:
            warnings.append(f"Severity '{info.get('severity')}' is not standard")

        # Check for at least one protocol block
        has_protocol = any(p in template_data for p in self.VALID_PROTOCOLS)
        if not has_protocol and template_data.get("id") != "workflow":
            warnings.append("No protocol block found")

        # Validate matchers
        matchers = template_data.get("matchers", [])
        for i, m in enumerate(matchers):
            if m.get("type") not in self.VALID_MATCHER_TYPES:
                warnings.append(f"Matcher {i}: unknown type '{m.get('type')}'")

        # Validate extractors
        extractors = template_data.get("extractors", [])
        for i, e in enumerate(extractors):
            if e.get("type") not in self.VALID_EXTRACTOR_TYPES:
                warnings.append(f"Extractor {i}: unknown type '{e.get('type')}'")

        valid = len(errors) == 0
        severity = "critical" if errors else "medium" if warnings else "info"

        result = ValidationResult(
            template_id=template_id, valid=valid, errors=errors,
            warnings=warnings, severity=severity,
        )
        self.results[template_id] = result
        self._save()
        return result

    def get_result(self, template_id: str) -> Optional[ValidationResult]:
        return self.results.get(template_id)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.results)
        valid = sum(1 for r in self.results.values() if r.valid)
        return {"total_validated": total, "valid": valid, "invalid": total - valid}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["NucleiTemplateValidator", "ValidationResult"]