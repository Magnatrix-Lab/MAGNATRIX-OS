#!/usr/bin/env python3
"""Data Quality Engine for MAGNATRIX-OS — Schema validation, data quality checks."""
from __future__ import annotations
import json, re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

@dataclass
class QualityRule:
    field: str
    check: str  # not_null, type, regex, range, unique
    params: Dict[str, Any] = field(default_factory=dict)

class DataQualityEngine:
    def __init__(self) -> None:
        self._rules: List[QualityRule] = []
        self._violations: List[Dict[str, Any]] = []

    def add_rule(self, rule: QualityRule) -> None:
        self._rules.append(rule)

    def validate(self, record: Dict[str, Any]) -> Dict[str, Any]:
        errors = []
        for rule in self._rules:
            value = record.get(rule.field)
            if rule.check == "not_null" and (value is None or value == ""):
                errors.append({"field": rule.field, "check": "not_null", "msg": "Value is null"})
            elif rule.check == "type" and not isinstance(value, eval(rule.params.get("type", "str"))):
                errors.append({"field": rule.field, "check": "type", "msg": f"Expected {rule.params.get('type')}"})
            elif rule.check == "regex" and value and not re.match(rule.params.get("pattern", ".*"), str(value)):
                errors.append({"field": rule.field, "check": "regex", "msg": "Pattern mismatch"})
            elif rule.check == "range":
                mn, mx = rule.params.get("min"), rule.params.get("max")
                if value is not None and ((mn is not None and value < mn) or (mx is not None and value > mx)):
                    errors.append({"field": rule.field, "check": "range", "msg": f"Out of range [{mn}, {mx}]"})
        return {"valid": len(errors) == 0, "errors": errors}

    def stats(self) -> Dict[str, Any]:
        return {"rules": len(self._rules), "violations": len(self._violations)}
