"""Vector Dimension Reduction — PCA-lite, random projection, feature selection."""
from dataclasses import dataclass
from pathlib import Path
import json, math, random

@dataclass
class ReducedVector:
    original_id: int = 0
    original_dim: int = 0
    reduced_dim: int = 0
    vector: list[float] = None
    method: str = ""

    def __post_init__(self):
        if self.vector is None:
            self.vector = []

class VectorDimensionReduction:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._reduced: list[ReducedVector] = []
        self._projection_matrices: dict[str, list[list[float]]] = {}
        self._persist_path = self.root / "vector_reduction.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._reduced = [ReducedVector(**r) for r in data.get("reduced", [])]
            self._projection_matrices = data.get("matrices", {})

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "reduced": [r.__dict__ for r in self._reduced],
            "matrices": self._projection_matrices
        }, indent=2))

    def pca_lite(self, vector: list[float], target_dim: int) -> ReducedVector:
        # Simplified PCA: take first target_dim components
        reduced = vector[:target_dim] if len(vector) >= target_dim else vector + [0.0] * (target_dim - len(vector))
        result = ReducedVector(original_id=0, original_dim=len(vector), reduced_dim=target_dim, vector=reduced, method="pca_lite")
        self._reduced.append(result)
        self._save()
        return result

    def random_projection(self, vector: list[float], target_dim: int) -> ReducedVector:
        key = f"{len(vector)}_{target_dim}"
        if key not in self._projection_matrices:
            # Generate random Gaussian matrix
            matrix = [[random.gauss(0, 1) for _ in range(len(vector))] for _ in range(target_dim)]
            self._projection_matrices[key] = matrix
        matrix = self._projection_matrices[key]
        reduced = [sum(m[i] * vector[i] for i in range(len(vector))) for m in matrix]
        # Normalize by sqrt(dim)
        reduced = [v / math.sqrt(target_dim) for v in reduced]
        result = ReducedVector(original_id=0, original_dim=len(vector), reduced_dim=target_dim, vector=reduced, method="random_projection")
        self._reduced.append(result)
        self._save()
        return result

    def feature_selection(self, vector: list[float], indices: list[int]) -> ReducedVector:
        reduced = [vector[i] for i in indices if i < len(vector)]
        result = ReducedVector(original_id=0, original_dim=len(vector), reduced_dim=len(reduced), vector=reduced, method="feature_selection")
        self._reduced.append(result)
        self._save()
        return result

    def to_dict(self) -> dict:
        return {"reduced_count": len(self._reduced), "methods": list(set(r.method for r in self._reduced))}

    def get_stats(self) -> dict:
        by_method = {}
        for r in self._reduced:
            by_method[r.method] = by_method.get(r.method, 0) + 1
        return {"reduced": len(self._reduced), "by_method": by_method}

__all__ = ["VectorDimensionReduction", "ReducedVector"]
