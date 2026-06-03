"""LLM Math Engine — Native Python (stdlib only)."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum, auto

class MathEngine:
    def __init__(self) -> None:
        self._history: List[Dict[str, Any]] = []

    def add(self, a: float, b: float) -> float:
        result = a + b
        self._history.append({"op": "add", "a": a, "b": b, "result": result})
        return result

    def subtract(self, a: float, b: float) -> float:
        result = a - b
        self._history.append({"op": "sub", "a": a, "b": b, "result": result})
        return result

    def multiply(self, a: float, b: float) -> float:
        result = a * b
        self._history.append({"op": "mul", "a": a, "b": b, "result": result})
        return result

    def divide(self, a: float, b: float) -> float:
        if b == 0:
            raise ValueError("Division by zero")
        result = a / b
        self._history.append({"op": "div", "a": a, "b": b, "result": result})
        return result

    def power(self, a: float, b: float) -> float:
        result = a ** b
        self._history.append({"op": "pow", "a": a, "b": b, "result": result})
        return result

    def sqrt(self, a: float) -> float:
        if a < 0:
            raise ValueError("Negative sqrt")
        result = math.sqrt(a)
        self._history.append({"op": "sqrt", "a": a, "result": result})
        return result

    def factorial(self, n: int) -> int:
        if n < 0:
            raise ValueError("Negative factorial")
        result = 1
        for i in range(2, n + 1):
            result *= i
        self._history.append({"op": "fact", "n": n, "result": result})
        return result

    def sum_list(self, values: List[float]) -> float:
        result = sum(values)
        self._history.append({"op": "sum", "values": values, "result": result})
        return result

    def mean(self, values: List[float]) -> float:
        if not values:
            return 0.0
        result = sum(values) / len(values)
        self._history.append({"op": "mean", "values": values, "result": result})
        return result

    def std(self, values: List[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = self.mean(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        result = math.sqrt(variance)
        self._history.append({"op": "std", "values": values, "result": result})
        return result

    def get_stats(self) -> Dict[str, Any]:
        return {"operations": len(self._history)}

def run() -> None:
    print("Math Engine test")
    e = MathEngine()
    print("  2+3=" + str(e.add(2, 3)))
    print("  10-4=" + str(e.subtract(10, 4)))
    print("  5*6=" + str(e.multiply(5, 6)))
    print("  20/4=" + str(e.divide(20, 4)))
    print("  2^10=" + str(e.power(2, 10)))
    print("  sqrt(16)=" + str(e.sqrt(16)))
    print("  5!=" + str(e.factorial(5)))
    print("  mean([1,2,3,4,5])=" + str(e.mean([1, 2, 3, 4, 5])))
    print("  std([1,2,3,4,5])=" + str(e.std([1, 2, 3, 4, 5])))
    print("  Stats: " + str(e.get_stats()))
    print("Math Engine test complete.")

if __name__ == "__main__":
    run()
