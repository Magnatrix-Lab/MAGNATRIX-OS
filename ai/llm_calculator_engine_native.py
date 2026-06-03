"""LLM Calculator Engine — Native Python (stdlib only)."""
from __future__ import annotations
import math, re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from enum import Enum, auto

class CalculatorEngine:
    def __init__(self) -> None:
        self._history: List[str] = []
        self._variables: Dict[str, float] = {}

    def evaluate(self, expression: str) -> float:
        expr = expression.strip()
        self._history.append(expr)
        expr = self._preprocess(expr)
        try:
            safe_dict = {
                "sin": math.sin, "cos": math.cos, "tan": math.tan,
                "sqrt": math.sqrt, "log": math.log, "log10": math.log10,
                "exp": math.exp, "abs": abs, "pow": pow,
                "pi": math.pi, "e": math.e,
                "max": max, "min": min, "sum": sum,
                "floor": math.floor, "ceil": math.ceil, "round": round,
            }
            safe_dict.update(self._variables)
            result = eval(expr, {"__builtins__": {}}, safe_dict)
            return float(result)
        except Exception as ex:
            raise ValueError("Invalid expression: " + str(ex))

    def _preprocess(self, expr: str) -> str:
        expr = re.sub(r'\^\^', '**', expr)
        expr = re.sub(r'\^(?!\^)', '**', expr)
        return expr

    def set_variable(self, name: str, value: float) -> None:
        self._variables[name] = value

    def get_variable(self, name: str) -> Optional[float]:
        return self._variables.get(name)

    def solve_linear(self, a: float, b: float) -> Optional[float]:
        if a == 0:
            return None
        return -b / a

    def solve_quadratic(self, a: float, b: float, c: float) -> List[float]:
        if a == 0:
            return [self.solve_linear(b, c)] if b != 0 else []
        discriminant = b * b - 4 * a * c
        if discriminant < 0:
            return []
        elif discriminant == 0:
            return [-b / (2 * a)]
        sqrt_d = math.sqrt(discriminant)
        return [(-b + sqrt_d) / (2 * a), (-b - sqrt_d) / (2 * a)]

    def factorial(self, n: int) -> int:
        if n < 0:
            raise ValueError("Negative factorial")
        result = 1
        for i in range(2, n + 1):
            result *= i
        return result

    def fibonacci(self, n: int) -> int:
        if n < 0:
            return 0
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b

    def get_stats(self) -> Dict[str, Any]:
        return {"history": len(self._history), "variables": len(self._variables)}

def run() -> None:
    print("Calculator Engine test")
    e = CalculatorEngine()
    print("  2+3*4=" + str(e.evaluate("2 + 3 * 4")))
    print("  sin(pi/2)=" + str(e.evaluate("sin(pi/2)")))
    print("  sqrt(16)=" + str(e.evaluate("sqrt(16)")))
    e.set_variable("x", 10)
    print("  x+5=" + str(e.evaluate("x + 5")))
    print("  Quadratic: " + str(e.solve_quadratic(1, -5, 6)))
    print("  Fibonacci(10)=" + str(e.fibonacci(10)))
    print("  Stats: " + str(e.get_stats()))
    print("Calculator Engine test complete.")

if __name__ == "__main__":
    run()
