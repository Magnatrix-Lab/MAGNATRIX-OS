"""Calibration Engine — Min/max, percentile, entropy range."""
from dataclasses import dataclass
from pathlib import Path
import json, math

@dataclass
class CalibrationRange:
    tensor_name: str = ""
    min_val: float = 0.0
    max_val: float = 0.0
    per_channel: bool = False
    method: str = "minmax"  # minmax | percentile | entropy

class QuantizationCalibrationEngine:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._ranges: list[CalibrationRange] = []
        self._config = {"method": "minmax", "percentile": 99.99, "num_bins": 2048}
        self._persist_path = self.root / "calibration.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._ranges = [CalibrationRange(**r) for r in data.get("ranges", [])]
            self._config = data.get("config", self._config)

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "ranges": [r.__dict__ for r in self._ranges],
            "config": self._config
        }, indent=2))

    def calibrate_minmax(self, values: list[float], tensor_name: str) -> CalibrationRange:
        r = CalibrationRange(tensor_name=tensor_name, min_val=min(values), max_val=max(values), method="minmax")
        self._ranges.append(r)
        self._save()
        return r

    def calibrate_percentile(self, values: list[float], tensor_name: str, percentile: float = 99.99) -> CalibrationRange:
        sorted_vals = sorted(values)
        idx = int(len(sorted_vals) * percentile / 100)
        idx = min(idx, len(sorted_vals) - 1)
        r = CalibrationRange(tensor_name=tensor_name, min_val=-sorted_vals[idx], max_val=sorted_vals[idx], method="percentile")
        self._ranges.append(r)
        self._save()
        return r

    def calibrate_entropy(self, values: list[float], tensor_name: str, num_bins: int = 2048) -> CalibrationRange:
        # Simplified entropy calibration: find threshold that minimizes KL divergence
        min_v, max_v = min(values), max(values)
        if max_v == min_v:
            r = CalibrationRange(tensor_name=tensor_name, min_val=min_v, max_val=max_v, method="entropy")
        else:
            # Find best threshold by scanning candidates (simplified)
            best = max_v
            for candidate in [max_v * (i / 10.0) for i in range(1, 11)]:
                clipped = [min(max(v, -candidate), candidate) for v in values]
                # Simplified score: minimize total squared error
                err = sum((v - c) ** 2 for v, c in zip(values, clipped))
                if err < sum((v - min(max(v, -best), best)) ** 2 for v in values):
                    best = candidate
            r = CalibrationRange(tensor_name=tensor_name, min_val=-best, max_val=best, method="entropy")
        self._ranges.append(r)
        self._save()
        return r

    def get_range(self, tensor_name: str) -> CalibrationRange | None:
        for r in self._ranges:
            if r.tensor_name == tensor_name:
                return r
        return None

    def to_dict(self) -> dict:
        return {"range_count": len(self._ranges), "methods": list(set(r.method for r in self._ranges))}

    def get_stats(self) -> dict:
        return {"ranges": len(self._ranges), "by_method": {m: sum(1 for r in self._ranges if r.method == m) for m in set(r.method for r in self._ranges)}}

__all__ = ["QuantizationCalibrationEngine", "CalibrationRange"]
