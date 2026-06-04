"""Decision Support System — rule-based recommendation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Optional, Any
from enum import Enum, auto
import math

class RuleOperator(Enum):
    EQ = auto()
    GT = auto()
    LT = auto()
    GTE = auto()
    LTE = auto()
    IN = auto()

@dataclass
class DecisionRule:
    rule_id: str
    conditions: List[Dict]
    action: Dict
    priority: int = 0
    weight: float = 1.0

class DecisionSupportSystem:
    def __init__(self):
        self.rules: List[DecisionRule] = []
        self.knowledge_base: Dict = {}

    def add_rule(self, rule: DecisionRule):
        self.rules.append(rule)
        self.rules.sort(key=lambda r: (-r.priority, -r.weight))

    def _evaluate_condition(self, condition: Dict, facts: Dict) -> bool:
        op = condition.get("op", "EQ")
        field = condition.get("field")
        value = condition.get("value")
        fact_val = facts.get(field)
        if op == "EQ":
            return fact_val == value
        elif op == "GT":
            return fact_val is not None and fact_val > value
        elif op == "LT":
            return fact_val is not None and fact_val < value
        elif op == "GTE":
            return fact_val is not None and fact_val >= value
        elif op == "LTE":
            return fact_val is not None and fact_val <= value
        elif op == "IN":
            return fact_val in value if isinstance(value, list) else False
        return False

    def evaluate(self, facts: Dict) -> List[Dict]:
        triggered = []
        for rule in self.rules:
            if all(self._evaluate_condition(c, facts) for c in rule.conditions):
                triggered.append({"rule_id": rule.rule_id, "action": rule.action, "priority": rule.priority, "weight": rule.weight})
        return triggered

    def recommend(self, facts: Dict) -> Optional[Dict]:
        triggered = self.evaluate(facts)
        if not triggered:
            return None
        return triggered[0]

    def add_knowledge(self, key: str, value: Any):
        self.knowledge_base[key] = value

    def stats(self) -> Dict:
        return {"rules": len(self.rules), "knowledge_entries": len(self.knowledge_base), "avg_priority": sum(r.priority for r in self.rules) / len(self.rules) if self.rules else 0}

def run():
    dss = DecisionSupportSystem()
    dss.add_rule(DecisionRule("r1", [{"field": "temperature", "op": "GT", "value": 30}], {"action": "cool", "level": 3}, priority=2))
    dss.add_rule(DecisionRule("r2", [{"field": "temperature", "op": "LT", "value": 15}], {"action": "heat", "level": 2}, priority=1))
    dss.add_rule(DecisionRule("r3", [{"field": "humidity", "op": "GT", "value": 80}, {"field": "temperature", "op": "GT", "value": 25}], {"action": "dehumidify", "level": 1}, priority=3))
    print(dss.evaluate({"temperature": 35, "humidity": 85}))
    print(dss.recommend({"temperature": 10, "humidity": 40}))
    print(dss.stats())

if __name__ == "__main__":
    run()
