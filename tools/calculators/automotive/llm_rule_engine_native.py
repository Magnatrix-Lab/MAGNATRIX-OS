"""Rule Engine — forward chaining, backward chaining, facts, rules, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple

@dataclass
class Rule:
    name: str
    conditions: List[str]
    conclusion: str

class RuleEngine:
    def __init__(self):
        self.facts: Set[str] = set()
        self.rules: List[Rule] = []

    def add_fact(self, fact: str):
        self.facts.add(fact)

    def add_rule(self, rule: Rule):
        self.rules.append(rule)

    def forward_chain(self) -> List[str]:
        new_facts = []
        changed = True
        while changed:
            changed = False
            for rule in self.rules:
                if all(c in self.facts for c in rule.conditions) and rule.conclusion not in self.facts:
                    self.facts.add(rule.conclusion)
                    new_facts.append(rule.conclusion)
                    changed = True
        return new_facts

    def backward_chain(self, goal: str, visited: Optional[Set[str]] = None) -> bool:
        if visited is None:
            visited = set()
        if goal in self.facts:
            return True
        if goal in visited:
            return False
        visited.add(goal)
        for rule in self.rules:
            if rule.conclusion == goal:
                if all(self.backward_chain(c, visited) for c in rule.conditions):
                    return True
        return False

    def stats(self) -> Dict:
        return {"facts": len(self.facts), "rules": len(self.rules)}

def run():
    re = RuleEngine()
    re.add_fact("A")
    re.add_fact("B")
    re.add_rule(Rule("R1", ["A", "B"], "C"))
    re.add_rule(Rule("R2", ["C"], "D"))
    print("Forward:", re.forward_chain())
    print("Backward D:", re.backward_chain("D"))
    print(re.stats())

if __name__ == "__main__":
    run()
