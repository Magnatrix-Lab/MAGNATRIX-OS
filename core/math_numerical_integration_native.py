"""Math Numerical Integration -- Simpson, trapezoid, Monte Carlo methods."""
from dataclasses import dataclass
from pathlib import Path
import json, random

@dataclass
class IntegrationResult:
    integral_id: str = ""
    method: str = ""
    value: float = 0.0
    a: float = 0.0
    b: float = 0.0
    n: int = 0

class MathNumericalIntegration:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._results: list[IntegrationResult] = []
        self._persist_path = self.root / "math_integration.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._results = [IntegrationResult(**r) for r in data.get("results", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "results": [r.__dict__ for r in self._results]
        }, indent=2))

    def trapezoid(self, integral_id: str, f, a: float, b: float, n: int = 100) -> IntegrationResult:
        h = (b - a) / n
        total = 0.5 * (f(a) + f(b))
        for i in range(1, n):
            total += f(a + i * h)
        result = IntegrationResult(
            integral_id=integral_id, method="trapezoid",
            value=total * h, a=a, b=b, n=n
        )
        self._results.append(result)
        self._save()
        return result

    def simpson(self, integral_id: str, f, a: float, b: float, n: int = 100) -> IntegrationResult:
        if n % 2 == 1:
            n += 1
        h = (b - a) / n
        total = f(a) + f(b)
        for i in range(1, n):
            x = a + i * h
            if i % 2 == 0:
                total += 2 * f(x)
            else:
                total += 4 * f(x)
        result = IntegrationResult(
            integral_id=integral_id, method="simpson",
            value=total * h / 3, a=a, b=b, n=n
        )
        self._results.append(result)
        self._save()
        return result

    def monte_carlo(self, integral_id: str, f, a: float, b: float, n: int = 10000) -> IntegrationResult:
        total = 0.0
        for _ in range(n):
            x = a + random.random() * (b - a)
            total += f(x)
        result = IntegrationResult(
            integral_id=integral_id, method="monte_carlo",
            value=total * (b - a) / n, a=a, b=b, n=n
        )
        self._results.append(result)
        self._save()
        return result

    def to_dict(self) -> dict:
        return {"result_count": len(self._results)}

    def get_stats(self) -> dict:
        by_method = {}
        for r in self._results:
            by_method[r.method] = by_method.get(r.method, 0) + 1
        return {"results": len(self._results), "by_method": by_method}

__all__ = ["MathNumericalIntegration", "IntegrationResult"]
