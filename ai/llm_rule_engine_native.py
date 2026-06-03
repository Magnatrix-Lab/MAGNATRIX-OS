"""LLM Rule Engine — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto

class RuleAction(Enum):
    ALLOW = auto()
    DENY = auto()
    TRANSFORM = auto()
    ALERT = auto()
    LOG = auto()

@dataclass
class Rule:
    id: str
    condition: Callable[[Dict[str, Any]], bool]
    action: RuleAction
    transform: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    priority: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

class RuleEngine:
    def __init__(self) -> None:
        self._rules: List[Rule] = []
        self._history: List[tuple] = []

    def add_rule(self, rule: Rule) -> None:
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority)

    def evaluate(self, data: Dict[str, Any]) -> List[tuple]:
        results = []
        for rule in self._rules:
            try:
                if rule.condition(data):
                    result = {"rule": rule.id, "action": rule.action.name}
                    if rule.action == RuleAction.TRANSFORM and rule.transform:
                        data = rule.transform(data)
                        result["transformed"] = True
                    results.append(result)
                    self._history.append((rule.id, data))
            except Exception as ex:
                results.append({"rule": rule.id, "error": str(ex)})
        return results

    def get_triggered(self) -> List[str]:
        return [h[0] for h in self._history]

    def get_stats(self) -> Dict[str, Any]:
        return {"rules": len(self._rules), "triggers": len(self._history)}

def run() -> None:
    print("Rule Engine test")
    e = RuleEngine()
    e.add_rule(Rule("r1", lambda d: d.get("age", 0) < 18, RuleAction.DENY, priority=1))
    e.add_rule(Rule("r2", lambda d: d.get("role") == "admin", RuleAction.ALLOW, priority=2))
    e.add_rule(Rule("r3", lambda d: d.get("score", 0) > 90, RuleAction.ALERT, priority=3))
    results = e.evaluate({"age": 20, "role": "admin", "score": 95})
    for r in results:
        print("  " + str(r))
    print("  Stats: " + str(e.get_stats()))
    print("Rule Engine test complete.")

if __name__ == "__main__":
    run()
