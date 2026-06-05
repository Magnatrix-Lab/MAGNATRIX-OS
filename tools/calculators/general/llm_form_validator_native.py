"""Form Validator — field validation, sanitization, rules, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any
from enum import Enum, auto
import re

@dataclass
class ValidationError:
    field: str
    message: str
    rule: str

class FormValidator:
    def __init__(self):
        self.rules: Dict[str, List[Dict]] = {}
        self.errors: List[ValidationError] = []

    def add_rule(self, field: str, rule_type: str, **kwargs):
        if field not in self.rules:
            self.rules[field] = []
        self.rules[field].append({"type": rule_type, **kwargs})

    def validate(self, data: Dict) -> List[ValidationError]:
        self.errors = []
        for field, rules in self.rules.items():
            value = data.get(field)
            for rule in rules:
                if rule["type"] == "required" and not value:
                    self.errors.append(ValidationError(field, "Field is required", "required"))
                elif rule["type"] == "min_length" and value and len(str(value)) < rule.get("min", 0):
                    self.errors.append(ValidationError(field, f"Minimum length is {rule.get('min')}", "min_length"))
                elif rule["type"] == "max_length" and value and len(str(value)) > rule.get("max", 1000):
                    self.errors.append(ValidationError(field, f"Maximum length is {rule.get('max')}", "max_length"))
                elif rule["type"] == "pattern" and value and not re.match(rule.get("pattern", ".*"), str(value)):
                    self.errors.append(ValidationError(field, "Invalid format", "pattern"))
                elif rule["type"] == "email" and value and not re.match(r"^[\w.-]+@[\w.-]+\.\w+$", str(value)):
                    self.errors.append(ValidationError(field, "Invalid email", "email"))
                elif rule["type"] == "numeric" and value and not str(value).replace('.', '', 1).isdigit():
                    self.errors.append(ValidationError(field, "Must be numeric", "numeric"))
                elif rule["type"] == "range" and value is not None:
                    try:
                        v = float(value)
                        if v < rule.get("min", float('-inf')) or v > rule.get("max", float('inf')):
                            self.errors.append(ValidationError(field, f"Value out of range", "range"))
                    except:
                        self.errors.append(ValidationError(field, "Invalid number", "range"))
        return self.errors

    def is_valid(self, data: Dict) -> bool:
        return len(self.validate(data)) == 0

    def sanitize(self, data: Dict) -> Dict:
        result = {}
        for k, v in data.items():
            if isinstance(v, str):
                result[k] = v.strip()
            else:
                result[k] = v
        return result

    def stats(self) -> Dict:
        return {"rules": len(self.rules), "errors": len(self.errors)}

def run():
    validator = FormValidator()
    validator.add_rule("name", "required")
    validator.add_rule("email", "email")
    validator.add_rule("age", "numeric")
    validator.add_rule("age", "range", min=0, max=150)
    data = {"name": "Alice", "email": "alice@example.com", "age": "25"}
    print(validator.is_valid(data))
    print(validator.sanitize(data))
    print(validator.stats())

if __name__ == "__main__":
    run()
