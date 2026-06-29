"""Quant PCA Factor Extractor - PCA for term structure dimensionality reduction."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class PCAFactor:
    factor_id: str
    component_index: int
    explained_variance_ratio: float
    loadings: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "factor_id": self.factor_id,
            "component_index": self.component_index,
            "explained_variance_ratio": round(self.explained_variance_ratio, 4),
            "loadings_count": len(self.loadings),
        }


@dataclass
class FactorProjection:
    projection_id: str
    timestamp: float
    scores: List[float] = field(default_factory=list)
    reconstruction_error: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "projection_id": self.projection_id,
            "timestamp": self.timestamp,
            "scores": [round(s, 4) for s in self.scores],
            "reconstruction_error": round(self.reconstruction_error, 6),
        }


class QuantPCAFactorExtractor:
    """PCA-based factor extraction for yield curve dimensionality reduction."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "quant_pca"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.factors: List[PCAFactor] = []
        self.projections: List[FactorProjection] = []
        self.mean_vector: List[float] = []
        self.eigenvectors: List[List[float]] = []
        self._load_state()

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for f in data.get("factors", []):
                    self.factors.append(PCAFactor(**f))
                for p in data.get("projections", []):
                    self.projections.append(FactorProjection(**p))
                self.mean_vector = data.get("mean_vector", [])
                self.eigenvectors = data.get("eigenvectors", [])
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {
            "factors": [f.to_dict() for f in self.factors],
            "projections": [p.to_dict() for p in self.projections],
            "mean_vector": self.mean_vector,
            "eigenvectors": self.eigenvectors,
        }
        state_file.write_text(json.dumps(state, indent=2))

    def _mean(self, data: List[List[float]]) -> List[float]:
        if not data or not data[0]:
            return []
        n = len(data)
        d = len(data[0])
        return [sum(data[i][j] for i in range(n)) / n for j in range(d)]

    def _covariance(self, data: List[List[float]]) -> List[List[float]]:
        n = len(data)
        d = len(data[0])
        mean = self._mean(data)
        centered = [[row[j] - mean[j] for j in range(d)] for row in data]
        cov = [[sum(centered[i][j] * centered[i][k] for i in range(n)) / n for k in range(d)] for j in range(d)]
        return cov

    def _power_iteration(self, matrix: List[List[float]], max_iter: int = 100) -> Tuple[List[float], float]:
        """Power iteration to find dominant eigenvector and eigenvalue."""
        n = len(matrix)
        vec = [1.0] * n
        for _ in range(max_iter):
            new_vec = [sum(matrix[i][j] * vec[j] for j in range(n)) for i in range(n)]
            norm = math.sqrt(sum(x * x for x in new_vec))
            if norm == 0:
                break
            vec = [x / norm for x in new_vec]
        eigenval = sum(vec[i] * sum(matrix[i][j] * vec[j] for j in range(n)) for i in range(n))
        return vec, eigenval

    def _deflate(self, matrix: List[List[float]], eigenvec: List[float]) -> List[List[float]]:
        """Deflate matrix by removing component along eigenvector."""
        n = len(matrix)
        return [[matrix[i][j] - eigenvec[i] * eigenvec[j] for j in range(n)] for i in range(n)]

    def fit(self, data: List[List[float]], n_components: int = 3) -> List[PCAFactor]:
        """Fit PCA on yield curve data (each row is a curve observation)."""
        if not data or not data[0]:
            return []
        self.mean_vector = self._mean(data)
        centered = [[row[j] - self.mean_vector[j] for j in range(len(row))] for row in data]
        cov = self._covariance(centered)

        self.factors = []
        self.eigenvectors = []
        total_var = sum(cov[i][i] for i in range(len(cov)))

        for k in range(min(n_components, len(cov))):
            vec, val = self._power_iteration(cov)
            explained = val / max(total_var, 1e-10) if total_var > 0 else 0.0
            factor = PCAFactor(
                factor_id=f"pca_factor_{k}",
                component_index=k,
                explained_variance_ratio=explained,
                loadings=[round(x, 4) for x in vec],
            )
            self.factors.append(factor)
            self.eigenvectors.append(vec)
            cov = self._deflate(cov, vec)

        self._save_state()
        return self.factors

    def transform(self, observation: List[float]) -> FactorProjection:
        """Project a single observation into factor space."""
        if not self.eigenvectors or not self.mean_vector:
            return FactorProjection(projection_id="empty", timestamp=0.0)
        centered = [observation[i] - self.mean_vector[i] for i in range(len(self.mean_vector))]
        scores = []
        for vec in self.eigenvectors:
            score = sum(centered[i] * vec[i] for i in range(len(centered)))
            scores.append(round(score, 4))

        # Reconstruct and compute error
        reconstructed = [self.mean_vector[i] + sum(scores[j] * self.eigenvectors[j][i] for j in range(len(scores))) for i in range(len(self.mean_vector))]
        error = math.sqrt(sum((observation[i] - reconstructed[i]) ** 2 for i in range(len(observation)))) / max(1, len(observation))

        proj = FactorProjection(
            projection_id=f"proj_{len(self.projections)}",
            timestamp=0.0,
            scores=scores,
            reconstruction_error=round(error, 6),
        )
        self.projections.append(proj)
        self._save_state()
        return proj

    def cumulative_variance(self) -> float:
        return round(sum(f.explained_variance_ratio for f in self.factors), 4)

    def get_stats(self) -> Dict:
        return {
            "factors_total": len(self.factors),
            "projections_total": len(self.projections),
            "cumulative_variance_explained": self.cumulative_variance(),
            "data_dimension": len(self.mean_vector),
        }

    def to_dict(self) -> Dict:
        return {
            "factors": [f.to_dict() for f in self.factors],
            "projections": [p.to_dict() for p in self.projections],
            "stats": self.get_stats(),
        }


__all__ = ["QuantPCAFactorExtractor", "PCAFactor", "FactorProjection"]
