"""Dashboard Builder - Metric dashboard generation for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math

class MetricType(Enum):
    GAUGE = auto(); COUNTER = auto(); TREND = auto()

@dataclass
class DashboardBuilder:
    metrics: List[Dict] = field(default_factory=list)
    
    def add_metric(self, name: str, value: float, metric_type: MetricType = MetricType.GAUGE, max_val: float = 100.0) -> None:
        self.metrics.append({"name": name, "value": value, "type": metric_type, "max": max_val})
    
    def render_gauge(self, value: float, max_val: float, width: int = 20) -> str:
        filled = int((value / max_val) * width) if max_val > 0 else 0
        return f"[{'█' * filled}{'░' * (width - filled)}] {value:.1f}/{max_val:.1f}"
    
    def render(self) -> str:
        lines = ["=== Dashboard ===", ""]
        for m in self.metrics:
            if m["type"] == MetricType.GAUGE:
                lines.append(f"{m['name']}: {self.render_gauge(m['value'], m['max'])}")
            elif m["type"] == MetricType.COUNTER:
                lines.append(f"{m['name']}: {m['value']}")
            elif m["type"] == MetricType.TREND:
                lines.append(f"{m['name']}: {m['value']:.2f}")
        return "\n".join(lines)
    
    def stats(self) -> dict:
        return {"metrics": len(self.metrics), "types": len(set(m["type"] for m in self.metrics))}

def run():
    db = DashboardBuilder()
    db.add_metric("CPU", 75.5, MetricType.GAUGE, 100.0)
    db.add_metric("Requests", 1024, MetricType.COUNTER)
    db.add_metric("Latency", 23.4, MetricType.TREND)
    print(db.render())
    print("Stats:", db.stats())

if __name__ == "__main__": run()
