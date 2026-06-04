"""Truth Table Generator — all combinations, expression eval, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Callable
from enum import Enum, auto
import itertools

class TruthTable:
    def __init__(self, variables: List[str]):
        self.variables = variables
        self.rows: List[Dict] = []

    def generate(self, expressions: Dict[str, Callable]) -> List[Dict]:
        self.rows = []
        n = len(self.variables)
        for combo in itertools.product([False, True], repeat=n):
            assignment = {self.variables[i]: combo[i] for i in range(n)}
            row = dict(assignment)
            for name, expr in expressions.items():
                row[name] = expr(**assignment)
            self.rows.append(row)
        return self.rows

    def format(self) -> str:
        if not self.rows:
            return ""
        headers = list(self.rows[0].keys())
        lines = [" | ".join(headers)]
        lines.append("-" * (len(lines[0])))
        for row in self.rows:
            lines.append(" | ".join("1" if row[h] else "0" for h in headers))
        return "".join(lines)

    def stats(self) -> Dict:
        return {"variables": len(self.variables), "rows": len(self.rows)}

def run():
    tt = TruthTable(["A", "B", "C"])
    expressions = {
        "F1": lambda A, B, C: A and B,
        "F2": lambda A, B, C: A or C,
        "F3": lambda A, B, C: (A and B) or not C,
    }
    tt.generate(expressions)
    print(tt.format())
    print(tt.stats())

if __name__ == "__main__":
    run()
