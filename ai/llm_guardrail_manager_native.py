"""LLM Guardrail Manager — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto

class GuardrailAction(Enum):
    ALLOW = auto()
    BLOCK = auto()
    FLAG = auto()
    REDACT = auto()

@dataclass
class GuardrailRule:
    id: str
    pattern: str
    action: GuardrailAction
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)

class GuardrailManager:
    def __init__(self) -> None:
        self._rules: List[GuardrailRule] = []
        self._handlers: Dict[GuardrailAction, Callable[[str, GuardrailRule], str]] = {}

    def add_rule(self, rule: GuardrailRule) -> None:
        self._rules.append(rule)

    def set_handler(self, action: GuardrailAction, handler: Callable[[str, GuardrailRule], str]) -> None:
        self._handlers[action] = handler

    def check(self, text: str) -> List[Dict[str, Any]]:
        results = []
        for rule in self._rules:
            if re.search(rule.pattern, text, re.IGNORECASE):
                handler = self._handlers.get(rule.action, lambda t, r: t)
                modified = handler(text, rule)
                results.append({"rule": rule.id, "action": rule.action.name, "matched": True, "modified": modified})
        return results

    def get_stats(self) -> Dict[str, Any]:
        return {"rules": len(self._rules), "actions": {a.name: sum(1 for r in self._rules if r.action == a) for a in GuardrailAction}}

def run() -> None:
    print("Guardrail Manager test")
    e = GuardrailManager()
    e.add_rule(GuardrailRule("r1", r"\b(password|secret|key)\b", GuardrailAction.REDACT, "Redact sensitive keywords"))
    e.add_rule(GuardrailRule("r2", r"\b(hack|exploit|attack)\b", GuardrailAction.FLAG, "Flag security terms"))
    e.set_handler(GuardrailAction.REDACT, lambda t, r: re.sub(r.rule.pattern, "[REDACTED]", t, flags=re.IGNORECASE))
    text = "My password is secret123 and I will hack the system."
    results = e.check(text)
    for r in results:
        print("  " + str(r))
    print("Guardrail Manager test complete.")

if __name__ == "__main__":
    run()
