"""Math Polynomial -- Polynomial arithmetic, root finding, interpolation."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class Polynomial:
    coeffs: list[float] = None
    variable: str = "x"

    def __post_init__(self):
        if self.coeffs is None:
            self.coeffs = [0.0]

class MathPolynomial:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._polynomials: list[Polynomial] = []
        self._operations: list[dict] = []
        self._persist_path = self.root / "math_polynomial.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._polynomials = [Polynomial(**p) for p in data.get("polynomials", [])]
            self._operations = data.get("operations", [])

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "polynomials": [p.__dict__ for p in self._polynomials],
            "operations": self._operations
        }, indent=2))

    def add(self, p1: Polynomial, p2: Polynomial) -> Polynomial:
        max_len = max(len(p1.coeffs), len(p2.coeffs))
        c1 = p1.coeffs + [0] * (max_len - len(p1.coeffs))
        c2 = p2.coeffs + [0] * (max_len - len(p2.coeffs))
        result = Polynomial(coeffs=[c1[i] + c2[i] for i in range(max_len)])
        self._polynomials.append(result)
        self._operations.append({"op": "add", "p1": p1.coeffs, "p2": p2.coeffs, "result": result.coeffs})
        self._save()
        return result

    def multiply(self, p1: Polynomial, p2: Polynomial) -> Polynomial:
        result = [0.0] * (len(p1.coeffs) + len(p2.coeffs) - 1)
        for i in range(len(p1.coeffs)):
            for j in range(len(p2.coeffs)):
                result[i + j] += p1.coeffs[i] * p2.coeffs[j]
        result_poly = Polynomial(coeffs=result)
        self._polynomials.append(result_poly)
        self._operations.append({"op": "multiply", "p1": p1.coeffs, "p2": p2.coeffs, "result": result})
        self._save()
        return result_poly

    def evaluate(self, p: Polynomial, x: float) -> float:
        result = 0.0
        for i, c in enumerate(p.coeffs):
            result += c * (x ** i)
        return result

    def derivative(self, p: Polynomial) -> Polynomial:
        if len(p.coeffs) <= 1:
            return Polynomial(coeffs=[0.0])
        result = Polynomial(coeffs=[(i + 1) * p.coeffs[i + 1] for i in range(len(p.coeffs) - 1)])
        self._polynomials.append(result)
        self._save()
        return result

    def newton_roots(self, p: Polynomial, guess: float = 1.0, iterations: int = 10) -> list[float]:
        dp = self.derivative(p)
        x = guess
        for _ in range(iterations):
            fx = self.evaluate(p, x)
            dfx = self.evaluate(dp, x)
            if abs(dfx) < 1e-10:
                break
            x = x - fx / dfx
        return [x]

    def to_dict(self) -> dict:
        return {"polynomial_count": len(self._polynomials), "operations": len(self._operations)}

    def get_stats(self) -> dict:
        by_op = {}
        for op in self._operations:
            by_op[op["op"]] = by_op.get(op["op"], 0) + 1
        return {"polynomials": len(self._polynomials), "by_operation": by_op}

__all__ = ["MathPolynomial", "Polynomial"]
