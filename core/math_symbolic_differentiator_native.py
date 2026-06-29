"""Math Symbolic Differentiator -- Automatic differentiation, symbolic derivative computation."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class DerivativeResult:
    expr_id: str = ""
    original: str = ""
    variable: str = ""
    derivative: str = ""
    steps: list[str] = None

    def __post_init__(self):
        if self.steps is None:
            self.steps = []

class MathSymbolicDifferentiator:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._results: list[DerivativeResult] = []
        self._rules: dict = {
            "x^n": "n*x^(n-1)",
            "sin(x)": "cos(x)",
            "cos(x)": "-sin(x)",
            "exp(x)": "exp(x)",
            "ln(x)": "1/x",
            "tan(x)": "sec(x)^2",
            "sec(x)": "sec(x)*tan(x)",
            "cot(x)": "-csc(x)^2",
            "csc(x)": "-csc(x)*cot(x)",
            "arcsin(x)": "1/sqrt(1-x^2)",
            "arccos(x)": "-1/sqrt(1-x^2)",
            "arctan(x)": "1/(1+x^2)",
        }
        self._persist_path = self.root / "math_diff.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._results = [DerivativeResult(**r) for r in data.get("results", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "results": [r.__dict__ for r in self._results]
        }, indent=2))

    def differentiate(self, expr_id: str, expr: str, var: str = "x") -> DerivativeResult:
        result = DerivativeResult(expr_id=expr_id, original=expr, variable=var)
        # Simple rule-based differentiation
        expr_clean = expr.strip().replace(" ", "")

        if expr_clean == var:
            result.derivative = "1"
            result.steps.append(f"d/d{var}({var}) = 1")
        elif expr_clean.replace(var, "") == "":
            # Constant * variable
            coeff = expr_clean.replace(var, "")
            coeff = coeff if coeff else "1"
            result.derivative = coeff
            result.steps.append(f"d/d{var}({coeff}*{var}) = {coeff}")
        elif expr_clean in self._rules:
            result.derivative = self._rules[expr_clean].replace("x", var)
            result.steps.append(f"Apply rule: d/d{var}({expr}) = {result.derivative}")
        elif "^" in expr_clean:
            # Power rule
            parts = expr_clean.split("^")
            if len(parts) == 2:
                base = parts[0]
                exp = parts[1]
                if base == var:
                    result.derivative = f"{exp}*{var}^({exp}-1)"
                    result.steps.append(f"Power rule: d/d{var}({var}^{exp}) = {exp}*{var}^({exp}-1)")
                else:
                    result.derivative = f"{exp}*{base}^({exp}-1)*d/d{var}({base})"
                    result.steps.append(f"Chain rule with power")
        else:
            result.derivative = "0"
            result.steps.append(f"Constant: d/d{var}({expr}) = 0")

        self._results.append(result)
        self._save()
        return result

    def add_rule(self, pattern: str, derivative: str) -> None:
        self._rules[pattern] = derivative

    def to_dict(self) -> dict:
        return {"result_count": len(self._results), "rules": len(self._rules)}

    def get_stats(self) -> dict:
        by_var = {}
        for r in self._results:
            by_var[r.variable] = by_var.get(r.variable, 0) + 1
        return {"results": len(self._results), "by_variable": by_var}

__all__ = ["MathSymbolicDifferentiator", "DerivativeResult"]
