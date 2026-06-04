"""GDPR Anonymizer — PII detection, masking, k-anonymity, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum, auto
import re
import hashlib

class PIIType(Enum):
    EMAIL = auto()
    PHONE = auto()
    NAME = auto()
    ADDRESS = auto()
    ID_NUMBER = auto()
    IP_ADDRESS = auto()

@dataclass
class AnonymizationRule:
    pii_type: PIIType
    pattern: str
    replacement: str

class GDPRAnonymizer:
    def __init__(self, k: int = 5):
        self.k = k
        self.rules: List[AnonymizationRule] = []
        self.mask_char = "*"
        self._default_rules()

    def _default_rules(self):
        self.rules.append(AnonymizationRule(PIIType.EMAIL, r"[\w.-]+@[\w.-]+\.\w+", "[EMAIL]"))
        self.rules.append(AnonymizationRule(PIIType.PHONE, r"\d{3}[-.]?\d{3}[-.]?\d{4}", "[PHONE]"))
        self.rules.append(AnonymizationRule(PIIType.IP_ADDRESS, r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", "[IP]"))
        self.rules.append(AnonymizationRule(PIIType.NAME, r"[A-Z][a-z]+\s[A-Z][a-z]+", "[NAME]"))

    def mask(self, text: str, pii_type: Optional[PIIType] = None) -> str:
        result = text
        for rule in self.rules:
            if pii_type is None or rule.pii_type == pii_type:
                result = re.sub(rule.pattern, rule.replacement, result)
        return result

    def hash_token(self, value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()[:16]

    def pseudonymize(self, data: Dict, sensitive_keys: List[str]) -> Dict:
        result = dict(data)
        for key in sensitive_keys:
            if key in result:
                result[key] = self.hash_token(str(result[key]))
        return result

    def check_k_anonymity(self, data: List[Dict], quasi_identifiers: List[str]) -> bool:
        groups = {}
        for row in data:
            key = tuple(row.get(k) for k in quasi_identifiers)
            groups[key] = groups.get(key, 0) + 1
        return all(count >= self.k for count in groups.values())

    def generalize(self, value: any, level: int) -> any:
        if isinstance(value, int):
            return (value // (10 ** level)) * (10 ** level)
        elif isinstance(value, str):
            return value[:max(len(value) - level, 1)] + self.mask_char * level
        return value

    def stats(self) -> Dict:
        return {"k": self.k, "rules": len(self.rules), "mask_char": self.mask_char}

def run():
    anon = GDPRAnonymizer(k=2)
    text = "Contact John Smith at john.smith@example.com or 555-123-4567"
    print(anon.mask(text))
    data = [{"name": "Alice", "age": 30, "zip": "12345"}, {"name": "Bob", "age": 35, "zip": "12345"}, {"name": "Charlie", "age": 30, "zip": "12345"}]
    print(anon.check_k_anonymity(data, ["age", "zip"]))
    print(anon.pseudonymize({"name": "Alice", "email": "a@b.com"}, ["name", "email"]))
    print(anon.stats())

if __name__ == "__main__":
    run()
