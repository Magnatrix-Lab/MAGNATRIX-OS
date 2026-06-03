"""LLM Regression Engine — Native Python (stdlib only)."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum, auto

class RegressionEngine:
    def __init__(self) -> None:
        pass

    def linear_regression(self, x: List[float], y: List[float]) -> Dict[str, float]:
        if len(x) != len(y) or len(x) < 2:
            return {"slope": 0.0, "intercept": 0.0, "r2": 0.0}
        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        ss_xy = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        ss_xx = sum((x[i] - mean_x) ** 2 for i in range(n))
        ss_yy = sum((y[i] - mean_y) ** 2 for i in range(n))
        slope = ss_xy / ss_xx if ss_xx != 0 else 0.0
        intercept = mean_y - slope * mean_x
        r2 = (ss_xy ** 2) / (ss_xx * ss_yy) if ss_xx != 0 and ss_yy != 0 else 0.0
        return {"slope": slope, "intercept": intercept, "r2": r2}

    def predict(self, x: float, model: Dict[str, float]) -> float:
        return model["slope"] * x + model["intercept"]

    def polynomial_regression(self, x: List[float], y: List[float], degree: int = 2) -> List[float]:
        if len(x) != len(y) or len(x) < degree + 1:
            return [0.0] * (degree + 1)
        n = len(x)
        X = [[x[i] ** j for j in range(degree + 1)] for i in range(n)]
        Xt = [[X[j][i] for j in range(n)] for i in range(degree + 1)]
        XtX = [[sum(Xt[i][k] * X[k][j] for k in range(n)) for j in range(degree + 1)] for i in range(degree + 1)]
        Xty = [sum(Xt[i][j] * y[j] for j in range(n)) for i in range(degree + 1)]
        coeffs = self._solve_linear_system(XtX, Xty)
        return coeffs

    def _solve_linear_system(self, A: List[List[float]], b: List[float]) -> List[float]:
        n = len(A)
        aug = [A[i] + [b[i]] for i in range(n)]
        for i in range(n):
            pivot = aug[i][i]
            if abs(pivot) < 1e-10:
                continue
            for j in range(i, n + 1):
                aug[i][j] /= pivot
            for k in range(n):
                if k != i:
                    factor = aug[k][i]
                    for j in range(i, n + 1):
                        aug[k][j] -= factor * aug[i][j]
        return [aug[i][n] for i in range(n)]

    def mse(self, actual: List[float], predicted: List[float]) -> float:
        if len(actual) != len(predicted) or not actual:
            return 0.0
        return sum((actual[i] - predicted[i]) ** 2 for i in range(len(actual))) / len(actual)

    def rmse(self, actual: List[float], predicted: List[float]) -> float:
        return math.sqrt(self.mse(actual, predicted))

    def get_stats(self, x: List[float], y: List[float]) -> Dict[str, Any]:
        model = self.linear_regression(x, y)
        predicted = [self.predict(xi, model) for xi in x]
        return {"model": model, "rmse": self.rmse(y, predicted), "predictions": len(predicted)}

def run() -> None:
    print("Regression Engine test")
    e = RegressionEngine()
    x = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    y = [2.1, 4.0, 6.1, 7.8, 10.2, 12.0, 13.9, 16.1, 17.8, 20.0]
    model = e.linear_regression(x, y)
    print("  Slope: " + str(model["slope"]) + ", Intercept: " + str(model["intercept"]))
    print("  R2: " + str(model["r2"]))
    print("  Predict x=11: " + str(e.predict(11, model)))
    predicted = [e.predict(xi, model) for xi in x]
    print("  RMSE: " + str(e.rmse(y, predicted)))
    print("  Stats: " + str(e.get_stats(x, y)))
    print("Regression Engine test complete.")

if __name__ == "__main__":
    run()
