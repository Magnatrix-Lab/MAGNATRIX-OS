"""Math Statistics -- Distributions, hypothesis testing, descriptive stats."""
from dataclasses import dataclass
from pathlib import Path
import json, math, statistics

@dataclass
class StatsResult:
    dataset_id: str = ""
    n: int = 0
    mean: float = 0.0
    median: float = 0.0
    std: float = 0.0
    variance: float = 0.0
    min: float = 0.0
    max: float = 0.0
    quartiles: list[float] = None

    def __post_init__(self):
        if self.quartiles is None:
            self.quartiles = []

class MathStatistics:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._datasets: dict[str, list[float]] = {}
        self._results: list[StatsResult] = []
        self._persist_path = self.root / "math_stats.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._datasets = {k: v for k, v in data.get("datasets", {}).items()}
            self._results = [StatsResult(**r) for r in data.get("results", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "datasets": self._datasets,
            "results": [r.__dict__ for r in self._results]
        }, indent=2))

    def add_dataset(self, dataset_id: str, data: list[float]) -> None:
        self._datasets[dataset_id] = data
        self._save()

    def analyze(self, dataset_id: str) -> StatsResult:
        data = self._datasets.get(dataset_id, [])
        if not data:
            return StatsResult(dataset_id=dataset_id)
        n = len(data)
        mean = statistics.mean(data)
        median = statistics.median(data)
        std = statistics.stdev(data) if n > 1 else 0.0
        variance = statistics.variance(data) if n > 1 else 0.0
        sorted_data = sorted(data)
        q1 = sorted_data[n // 4] if n > 0 else 0.0
        q3 = sorted_data[3 * n // 4] if n > 0 else 0.0
        result = StatsResult(
            dataset_id=dataset_id, n=n, mean=mean, median=median,
            std=std, variance=variance, min=min(data), max=max(data),
            quartiles=[q1, q3]
        )
        self._results.append(result)
        self._save()
        return result

    def correlation(self, dataset_a: str, dataset_b: str) -> float:
        a = self._datasets.get(dataset_a, [])
        b = self._datasets.get(dataset_b, [])
        if len(a) != len(b) or len(a) == 0:
            return 0.0
        mean_a = sum(a) / len(a)
        mean_b = sum(b) / len(b)
        num = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(len(a)))
        den_a = math.sqrt(sum((x - mean_a) ** 2 for x in a))
        den_b = math.sqrt(sum((x - mean_b) ** 2 for x in b))
        if den_a == 0 or den_b == 0:
            return 0.0
        return num / (den_a * den_b)

    def t_test(self, dataset_a: str, dataset_b: str) -> dict:
        a = self._datasets.get(dataset_a, [])
        b = self._datasets.get(dataset_b, [])
        if not a or not b:
            return {"error": "Empty dataset"}
        mean_a = sum(a) / len(a)
        mean_b = sum(b) / len(b)
        var_a = statistics.variance(a) if len(a) > 1 else 0.0
        var_b = statistics.variance(b) if len(b) > 1 else 0.0
        se = math.sqrt(var_a / len(a) + var_b / len(b))
        t_stat = (mean_a - mean_b) / se if se > 0 else 0.0
        return {"t_statistic": round(t_stat, 4), "mean_a": mean_a, "mean_b": mean_b}

    def to_dict(self) -> dict:
        return {"dataset_count": len(self._datasets), "result_count": len(self._results)}

    def get_stats(self) -> dict:
        by_dataset = {}
        for r in self._results:
            by_dataset[r.dataset_id] = by_dataset.get(r.dataset_id, 0) + 1
        return {"datasets": len(self._datasets), "results": len(self._results)}

__all__ = ["MathStatistics", "StatsResult"]
