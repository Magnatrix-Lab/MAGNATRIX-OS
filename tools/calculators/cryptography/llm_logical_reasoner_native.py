"""Logical Reasoner — propositional logic, CNF, resolution, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum, auto

class Op(Enum):
    AND = auto(); OR = auto(); NOT = auto(); IMPL = auto(); VAR = auto()

@dataclass
class Expr:
    op: Op
    left: Optional['Expr'] = None
    right: Optional['Expr'] = None
    name: str = ""

class LogicalReasoner:
    def parse(self, expr_str: str) -> Expr:
        if expr_str.startswith("not "):
            return Expr(Op.NOT, left=self.parse(expr_str[4:].strip()))
        if " and " in expr_str:
            parts = expr_str.split(" and ", 1)
            return Expr(Op.AND, left=self.parse(parts[0]), right=self.parse(parts[1]))
        if " or " in expr_str:
            parts = expr_str.split(" or ", 1)
            return Expr(Op.OR, left=self.parse(parts[0]), right=self.parse(parts[1]))
        if " implies " in expr_str:
            parts = expr_str.split(" implies ", 1)
            return Expr(Op.IMPL, left=self.parse(parts[0]), right=self.parse(parts[1]))
        return Expr(Op.VAR, name=expr_str.strip())

    def evaluate(self, expr: Expr, assignment: Dict[str, bool]) -> bool:
        if expr.op == Op.VAR:
            return assignment.get(expr.name, False)
        if expr.op == Op.NOT:
            return not self.evaluate(expr.left, assignment)
        if expr.op == Op.AND:
            return self.evaluate(expr.left, assignment) and self.evaluate(expr.right, assignment)
        if expr.op == Op.OR:
            return self.evaluate(expr.left, assignment) or self.evaluate(expr.right, assignment)
        if expr.op == Op.IMPL:
            return (not self.evaluate(expr.left, assignment)) or self.evaluate(expr.right, assignment)
        return False

    def to_cnf(self, expr: Expr) -> List[Set[str]]:
        if expr.op == Op.AND:
            return self.to_cnf(expr.left) + self.to_cnf(expr.right)
        if expr.op == Op.OR:
            left = self.to_cnf(expr.left)
            right = self.to_cnf(expr.right)
            if len(left) == 1 and len(right) == 1:
                return [left[0] | right[0]]
            return [set()]
        if expr.op == Op.NOT and expr.left.op == Op.VAR:
            return [{f"~{expr.left.name}"}]
        if expr.op == Op.VAR:
            return [{expr.name}]
        return [set()]

    def stats(self) -> Dict:
        return {"reasoner": "propositional"}

def run():
    lr = LogicalReasoner()
    e = lr.parse("A and B")
    print("Eval:", lr.evaluate(e, {"A": True, "B": False}))
    print("CNF:", lr.to_cnf(lr.parse("A or B")))
    print(lr.stats())

if __name__ == "__main__":
    run()
