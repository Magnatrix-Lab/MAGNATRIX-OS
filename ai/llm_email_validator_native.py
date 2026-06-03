"""LLM Email Validator — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class EmailValidator:
    def __init__(self) -> None:
        self._pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        self._disposable_domains: set = {"tempmail.com", "mailinator.com", "guerrillamail.com", "throwaway.com", "fakeinbox.com", "sharklasers.com", "yopmail.com"}
        self._common_domains: set = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "aol.com", "protonmail.com", "live.com", "msn.com"}

    def is_valid_format(self, email: str) -> bool:
        return bool(self._pattern.match(email))

    def validate(self, email: str) -> Dict[str, Any]:
        if not email:
            return {"valid": False, "reason": "empty", "domain": "", "is_disposable": False, "is_common": False}
        if not self.is_valid_format(email):
            return {"valid": False, "reason": "invalid_format", "domain": "", "is_disposable": False, "is_common": False}
        parts = email.split("@")
        if len(parts) != 2:
            return {"valid": False, "reason": "no_at_sign", "domain": "", "is_disposable": False, "is_common": False}
        domain = parts[1].lower()
        is_disposable = domain in self._disposable_domains
        is_common = domain in self._common_domains
        if is_disposable:
            return {"valid": False, "reason": "disposable", "domain": domain, "is_disposable": True, "is_common": False}
        return {"valid": True, "reason": "", "domain": domain, "is_disposable": False, "is_common": is_common}

    def validate_batch(self, emails: List[str]) -> List[Dict[str, Any]]:
        return [self.validate(e) for e in emails]

    def get_domain(self, email: str) -> str:
        if "@" in email:
            return email.split("@")[1].lower()
        return ""

    def get_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        valid = sum(1 for r in results if r["valid"])
        return {"total": len(results), "valid": valid, "invalid": len(results) - valid, "disposable": sum(1 for r in results if r["is_disposable"])}

def run() -> None:
    print("Email Validator test")
    e = EmailValidator()
    emails = ["valid@gmail.com", "invalid@", "user@tempmail.com", "test@outlook.com", "no_at_sign"]
    for em in emails:
        result = e.validate(em)
        print("  " + em + " -> " + ("valid" if result["valid"] else "invalid: " + result["reason"]))
    print("  Stats: " + str(e.get_stats(e.validate_batch(emails))))
    print("Email Validator test complete.")

if __name__ == "__main__":
    run()
