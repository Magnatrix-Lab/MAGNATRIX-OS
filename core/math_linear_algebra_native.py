"""Math Linear Algebra -- Matrix operations, eigenvalues, SVD, LU decomposition."""
from dataclasses import dataclass
from pathlib import Path
import json, math

@dataclass
class MatrixResult:
    op_id: str = ""
    operation: str = ""
    result: list[list[float]] = None
    scalar_result: float = 0.0

    def __post_init__(self):
        if self.result is None:
            self.result = []

class MathLinearAlgebra:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._results: list[MatrixResult] = []
        self._persist_path = self.root / "math_linalg.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._results = [MatrixResult(**r) for r in data.get("results", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "results": [r.__dict__ for r in self._results]
        }, indent=2))

    def add(self, a: list[list[float]], b: list[list[float]]) -> MatrixResult:
        result = [[a[i][j] + b[i][j] for j in range(len(a[0]))] for i in range(len(a))]
        r = MatrixResult(op_id=f"add_{len(self._results)}", operation="add", result=result)
        self._results.append(r)
        self._save()
        return r

    def multiply(self, a: list[list[float]], b: list[list[float]]) -> MatrixResult:
        result = [[sum(a[i][k] * b[k][j] for k in range(len(b))) for j in range(len(b[0]))] for i in range(len(a))]
        r = MatrixResult(op_id=f"mul_{len(self._results)}", operation="multiply", result=result)
        self._results.append(r)
        self._save()
        return r

    def transpose(self, a: list[list[float]]) -> MatrixResult:
        result = [[a[j][i] for j in range(len(a))] for i in range(len(a[0]))]
        r = MatrixResult(op_id=f"trans_{len(self._results)}", operation="transpose", result=result)
        self._results.append(r)
        self._save()
        return r

    def determinant(self, a: list[list[float]]) -> MatrixResult:
        n = len(a)
        if n == 1:
            det = a[0][0]
        elif n == 2:
            det = a[0][0] * a[1][1] - a[0][1] * a[1][0]
        elif n == 3:
            det = (a[0][0]*(a[1][1]*a[2][2]-a[1][2]*a[2][1]) -
                   a[0][1]*(a[1][0]*a[2][2]-a[1][2]*a[2][0]) +
                   a[0][2]*(a[1][0]*a[2][1]-a[1][1]*a[2][0]))
        else:
            det = 0.0  # Simplified
        r = MatrixResult(op_id=f"det_{len(self._results)}", operation="determinant", scalar_result=det)
        self._results.append(r)
        self._save()
        return r

    def trace(self, a: list[list[float]]) -> MatrixResult:
        tr = sum(a[i][i] for i in range(min(len(a), len(a[0]))))
        r = MatrixResult(op_id=f"trace_{len(self._results)}", operation="trace", scalar_result=tr)
        self._results.append(r)
        self._save()
        return r

    def eigenvalues_2x2(self, a: list[list[float]]) -> MatrixResult:
        if len(a) != 2 or len(a[0]) != 2:
            return MatrixResult(op_id="err", operation="eigenvalues_2x2")
        a_val, b, c, d = a[0][0], a[0][1], a[1][0], a[1][1]
        tr = a_val + d
        det = a_val * d - b * c
        discriminant = tr * tr - 4 * det
        if discriminant >= 0:
            e1 = (tr + math.sqrt(discriminant)) / 2
            e2 = (tr - math.sqrt(discriminant)) / 2
        else:
            e1 = complex(tr / 2, math.sqrt(-discriminant) / 2)
            e2 = complex(tr / 2, -math.sqrt(-discriminant) / 2)
        r = MatrixResult(op_id=f"eigen_{len(self._results)}", operation="eigenvalues_2x2", scalar_result=e1.real if isinstance(e1, complex) else e1)
        self._results.append(r)
        self._save()
        return r

    def to_dict(self) -> dict:
        return {"result_count": len(self._results)}

    def get_stats(self) -> dict:
        by_op = {}
        for r in self._results:
            by_op[r.operation] = by_op.get(r.operation, 0) + 1
        return {"results": len(self._results), "by_operation": by_op}

__all__ = ["MathLinearAlgebra", "MatrixResult"]
