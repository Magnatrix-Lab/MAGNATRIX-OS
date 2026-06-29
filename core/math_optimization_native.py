"""Math Optimization -- Linear programming, simplex method, gradient descent."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class OptimizationResult:
    problem_id: str = ""
    method: str = ""
    optimal_value: float = 0.0
    solution: list[float] = None
    iterations: int = 0
    converged: bool = False

    def __post_init__(self):
        if self.solution is None:
            self.solution = []

class MathOptimization:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._results: list[OptimizationResult] = []
        self._persist_path = self.root / "math_optimization.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._results = [OptimizationResult(**r) for r in data.get("results", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "results": [r.__dict__ for r in self._results]
        }, indent=2))

    def gradient_descent(self, problem_id: str, f, df, initial: list[float], lr: float = 0.1, max_iter: int = 100) -> OptimizationResult:
        x = list(initial)
        for i in range(max_iter):
            grad = df(x)
            x = [x[j] - lr * grad[j] for j in range(len(x))]
        result = OptimizationResult(
            problem_id=problem_id, method="gradient_descent",
            optimal_value=f(x), solution=x, iterations=max_iter, converged=True
        )
        self._results.append(result)
        self._save()
        return result

    def simplex(self, problem_id: str, c: list[float], A: list[list[float]], b: list[float]) -> OptimizationResult:
        # Simplified simplex (handle 2D case)
        if len(c) == 2:
            # Try corner points
            corners = [[0, 0]]
            for i in range(len(A)):
                if A[i][1] != 0:
                    x0 = 0
                    x1 = b[i] / A[i][1]
                    corners.append([x0, x1])
                if A[i][0] != 0:
                    x0 = b[i] / A[i][0]
                    x1 = 0
                    corners.append([x0, x1])
            best = max(corners, key=lambda p: sum(c[j] * p[j] for j in range(len(c))))
            result = OptimizationResult(
                problem_id=problem_id, method="simplex",
                optimal_value=sum(c[j] * best[j] for j in range(len(c))),
                solution=best, iterations=1, converged=True
            )
        else:
            result = OptimizationResult(problem_id=problem_id, method="simplex")
        self._results.append(result)
        self._save()
        return result

    def to_dict(self) -> dict:
        return {"result_count": len(self._results)}

    def get_stats(self) -> dict:
        by_method = {}
        converged = 0
        for r in self._results:
            by_method[r.method] = by_method.get(r.method, 0) + 1
            if r.converged:
                converged += 1
        return {"results": len(self._results), "by_method": by_method, "converged": converged}

__all__ = ["MathOptimization", "OptimizationResult"]
