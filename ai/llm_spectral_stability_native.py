"""
llm_spectral_stability_native.py
MAGNATRIX-OS Spectral Stability Engine
Native Python, stdlib only.
Provides spectral radius analysis, stability checking, eigenvalue decomposition,
recurrent stability scoring, and convergence prediction for recurrent systems.

Inspired by OpenMythos spectral radius analysis for recurrent blocks.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple


class StabilityStatus(Enum):
    STABLE = "stable"
    MARGINALLY_STABLE = "marginally_stable"
    UNSTABLE = "unstable"
    UNKNOWN = "unknown"


@dataclass
class SpectralAnalysis:
    matrix_id: str
    spectral_radius: float
    max_eigenvalue: float
    min_eigenvalue: float
    eigenvalue_count: int
    status: StabilityStatus
    convergence_rate: float
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "matrix_id": self.matrix_id, "spectral_radius": round(self.spectral_radius, 6),
            "max_eigenvalue": round(self.max_eigenvalue, 6),
            "min_eigenvalue": round(self.min_eigenvalue, 6),
            "status": self.status.value, "convergence_rate": round(self.convergence_rate, 6),
            "recommendations": self.recommendations,
        }


class SpectralStabilityEngine:
    """
    Spectral stability analysis for recurrent systems.
    Inspired by OpenMythos spectral radius checks.
    """

    def __init__(self, stability_threshold: float = 1.0) -> None:
        self.stability_threshold = stability_threshold
        self._matrices: Dict[str, List[List[float]]] = {}
        self._analyses: Dict[str, SpectralAnalysis] = {}
        self._history: List[Dict[str, Any]] = []

    def register_matrix(self, matrix_id: str, matrix: List[List[float]]) -> None:
        self._matrices[matrix_id] = matrix

    def _compute_2x2_eigenvalues(self, a: float, b: float, c: float, d: float) -> Tuple[float, float]:
        trace = a + d
        det = a * d - b * c
        discriminant = trace * trace - 4 * det
        if discriminant >= 0:
            sqrt_d = math.sqrt(discriminant)
            return (trace + sqrt_d) / 2, (trace - sqrt_d) / 2
        else:
            sqrt_d = math.sqrt(-discriminant)
            real = trace / 2
            imag = sqrt_d / 2
            return math.sqrt(real * real + imag * imag), -math.sqrt(real * real + imag * imag)

    def _compute_eigenvalues_approx(self, matrix: List[List[float]]) -> List[float]:
        # Approximate eigenvalues using power iteration and Gershgorin circles for simplicity
        n = len(matrix)
        if n == 0:
            return []

        # For small matrices, compute characteristic polynomial approximations
        if n == 1:
            return [matrix[0][0]]
        if n == 2:
            e1, e2 = self._compute_2x2_eigenvalues(matrix[0][0], matrix[0][1], matrix[1][0], matrix[1][1])
            return [e1, e2]

        # For larger matrices, use Gershgorin circle estimates + power method for largest eigenvalue
        eigenvalues = []
        for i in range(n):
            center = matrix[i][i]
            radius = sum(abs(matrix[i][j]) for j in range(n) if j != i)
            eigenvalues.append(center + radius)
            eigenvalues.append(center - radius)

        # Power iteration for largest eigenvalue approximation
        vec = [1.0] * n
        for _ in range(20):
            new_vec = [sum(matrix[i][j] * vec[j] for j in range(n)) for i in range(n)]
            norm = math.sqrt(sum(x * x for x in new_vec))
            if norm > 0:
                vec = [x / norm for x in new_vec]

        # Rayleigh quotient
        Av = [sum(matrix[i][j] * vec[j] for j in range(n)) for i in range(n)]
        lambda_max = sum(vec[i] * Av[i] for i in range(n))
        eigenvalues.append(lambda_max)

        return eigenvalues

    def analyze(self, matrix_id: str) -> Optional[SpectralAnalysis]:
        matrix = self._matrices.get(matrix_id)
        if not matrix:
            return None

        eigenvalues = self._compute_eigenvalues_approx(matrix)
        if not eigenvalues:
            return None

        magnitudes = [abs(e) for e in eigenvalues]
        spectral_radius = max(magnitudes) if magnitudes else 0.0
        max_eig = max(eigenvalues)
        min_eig = min(eigenvalues)

        if spectral_radius < 0.9:
            status = StabilityStatus.STABLE
        elif spectral_radius < self.stability_threshold:
            status = StabilityStatus.MARGINALLY_STABLE
        else:
            status = StabilityStatus.UNSTABLE

        convergence_rate = -math.log(max(spectral_radius, 0.001)) if spectral_radius > 0 else float('inf')

        recommendations = []
        if status == StabilityStatus.UNSTABLE:
            recommendations.append("Apply spectral normalization to recurrent weights")
            recommendations.append("Reduce layer norms or add gradient clipping")
        elif status == StabilityStatus.MARGINALLY_STABLE:
            recommendations.append("Monitor for oscillations during training")
            recommendations.append("Consider adding damping terms")
        else:
            recommendations.append("System is stable")

        analysis = SpectralAnalysis(
            matrix_id=matrix_id, spectral_radius=spectral_radius,
            max_eigenvalue=max_eig, min_eigenvalue=min_eig,
            eigenvalue_count=len(eigenvalues), status=status,
            convergence_rate=convergence_rate, recommendations=recommendations
        )
        self._analyses[matrix_id] = analysis
        self._history.append({"matrix_id": matrix_id, "timestamp": 0, "spectral_radius": spectral_radius})
        return analysis

    def is_stable(self, matrix_id: str) -> bool:
        analysis = self._analyses.get(matrix_id)
        if not analysis:
            analysis = self.analyze(matrix_id)
        return analysis.status == StabilityStatus.STABLE if analysis else False

    def get_analysis(self, matrix_id: str) -> Optional[SpectralAnalysis]:
        return self._analyses.get(matrix_id)

    def get_all_analyses(self) -> Dict[str, SpectralAnalysis]:
        return dict(self._analyses)

    def get_stats(self) -> Dict[str, Any]:
        stable = sum(1 for a in self._analyses.values() if a.status == StabilityStatus.STABLE)
        unstable = sum(1 for a in self._analyses.values() if a.status == StabilityStatus.UNSTABLE)
        return {
            "matrices": len(self._matrices), "analyses": len(self._analyses),
            "stable": stable, "unstable": unstable, "marginally_stable": len(self._analyses) - stable - unstable,
        }

    def clear(self) -> None:
        self._matrices.clear()
        self._analyses.clear()
        self._history.clear()


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Spectral Stability Engine")
    print("=" * 60)

    engine = SpectralStabilityEngine(stability_threshold=1.0)

    # Stable matrix (spectral radius < 1)
    stable_matrix = [[0.5, 0.1], [0.1, 0.3]]
    engine.register_matrix("recurrent_1", stable_matrix)

    # Unstable matrix (spectral radius > 1)
    unstable_matrix = [[1.2, 0.1], [0.1, 0.9]]
    engine.register_matrix("recurrent_2", unstable_matrix)

    # 3x3 matrix
    matrix_3x3 = [[0.3, 0.1, 0.0], [0.1, 0.4, 0.05], [0.0, 0.05, 0.2]]
    engine.register_matrix("recurrent_3", matrix_3x3)

    for mid in ["recurrent_1", "recurrent_2", "recurrent_3"]:
        print(f"\n--- Analyze {mid} ---")
        analysis = engine.analyze(mid)
        if analysis:
            print(f"  Spectral radius: {analysis.spectral_radius:.4f}")
            print(f"  Status: {analysis.status.value}")
            print(f"  Convergence rate: {analysis.convergence_rate:.4f}")
            for rec in analysis.recommendations:
                print(f"  -> {rec}")

    print("\n--- Stats ---")
    print(engine.get_stats())

    print("\nSpectral Stability test complete.")


if __name__ == "__main__":
    run()
