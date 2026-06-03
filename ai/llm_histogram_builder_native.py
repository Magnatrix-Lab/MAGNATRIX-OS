"""LLM Histogram Builder — Native Python (stdlib only)."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum, auto

class HistogramBuilder:
    def __init__(self) -> None:
        self._histograms: List[Dict[str, Any]] = []

    def build(self, data: List[float], bins: int = 10) -> Dict[str, Any]:
        if not data:
            return {"bins": [], "min": 0, "max": 0, "count": 0}
        min_val = min(data)
        max_val = max(data)
        bin_width = (max_val - min_val) / bins if max_val != min_val else 1
        counts = [0] * bins
        for val in data:
            idx = min(int((val - min_val) / bin_width), bins - 1)
            counts[idx] += 1
        max_count = max(counts)
        result = {
            "bins": [{"start": min_val + i * bin_width, "end": min_val + (i + 1) * bin_width, "count": counts[i], "density": counts[i] / len(data)} for i in range(bins)],
            "min": min_val, "max": max_val, "count": len(data), "max_count": max_count
        }
        self._histograms.append(result)
        return result

    def render_ascii(self, histogram: Dict[str, Any], width: int = 40) -> str:
        bins = histogram.get("bins", [])
        if not bins:
            return ""
        max_count = histogram.get("max_count", 1)
        lines = ["  " + "Histogram (" + str(histogram["count"]) + " values)"]
        for b in bins:
            label = str(round(b["start"], 1)) + "-" + str(round(b["end"], 1))
            bar_len = int((b["count"] / max_count) * width) if max_count > 0 else 0
            lines.append("  " + label[:12].ljust(12) + " |" + "=" * bar_len + " " + str(b["count"]))
        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        return {"histograms": len(self._histograms)}

def run() -> None:
    print("Histogram Builder test")
    e = HistogramBuilder()
    import random
    data = [random.gauss(50, 10) for _ in range(100)]
    hist = e.build(data, 8)
    print("  Render:\n" + e.render_ascii(hist))
    print("  Stats: " + str(e.get_stats()))
    print("Histogram Builder test complete.")

if __name__ == "__main__":
    run()
