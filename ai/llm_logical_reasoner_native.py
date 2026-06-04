"""Logical Reasoner - Propositional logic solver for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from enum import Enum, auto

class OpType(Enum):
    AND = auto(); OR = auto(); NOT = auto(); IMPLIES = auto(); ATOM = auto()

@dataclass
class LogicExpr:
    op: OpType
    args: List = field(default_factory=list)
    name: str = ""

@dataclass
class LogicalReasoner:
    facts: Set[str] = field(default_factory=set)
    rules: List[LogicExpr] = field(default_factory=list)

    def add_fact(self, atom: str) -> None:
        self.facts.add(atom)

    def add_rule(self, rule: LogicExpr) -> None:
        self.rules.append(rule)

    def evaluate(self, expr: LogicExpr) -> bool:
        if expr.op == OpType.ATOM: return expr.name in self.facts
        if expr.op == OpType.NOT: return not self.evaluate(expr.args[0])
        if expr.op == OpType.AND: return all(self.evaluate(a) for a in expr.args)
        if expr.op == OpType.OR: return any(self.evaluate(a) for a in expr.args)
        if expr.op == OpType.IMPLIES: return (not self.evaluate(expr.args[0])) or self.evaluate(expr.args[1])
        return False

    def infer(self) -> Set[str]:
        new_facts = set()
        for rule in self.rules:
            if self.evaluate(rule):
                if rule.op == OpType.IMPLIES and rule.args[1].op == OpType.ATOM:
                    new_facts.add(rule.args[1].name)
        self.facts.update(new_facts)
        return self.facts

    def stats(self) -> dict:
        return {"facts": len(self.facts), "rules": len(self.rules)}

def run():
    lr = LogicalReasoner()
    lr.add_fact("rain")
    lr.add_rule(LogicExpr(OpType.IMPLIES, [LogicExpr(OpType.ATOM, name="rain"), LogicExpr(OpType.ATOM, name="wet")]))
    lr.infer()
    print("Facts:", lr.facts)
    print("Stats:", lr.stats())

if __name__ == "__main__": run()
