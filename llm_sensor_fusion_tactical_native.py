"""Tactical Sensor Fusion — multi-sensor, track, classify, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class SensorReading:
    sensor_id: str
    x: float
    y: float
    confidence: float
    target_type: str = "unknown"

class TacticalSensorFusion:
    def __init__(self):
        self.readings: List[SensorReading] = []
        self.tracks: Dict[str, List[SensorReading]] = {}

    def add_reading(self, r: SensorReading):
        self.readings.append(r)

    def cluster(self, threshold: float = 10.0) -> List[List[SensorReading]]:
        clusters = []
        used = set()
        for i, r1 in enumerate(self.readings):
            if i in used:
                continue
            cluster = [r1]
            used.add(i)
            for j, r2 in enumerate(self.readings):
                if j in used or i == j:
                    continue
                if math.sqrt((r1.x-r2.x)**2 + (r1.y-r2.y)**2) < threshold:
                    cluster.append(r2)
                    used.add(j)
            clusters.append(cluster)
        return clusters

    def fused_position(self, cluster: List[SensorReading]) -> Tuple[float, float]:
        total_conf = sum(r.confidence for r in cluster)
        if total_conf == 0:
            return 0, 0
        x = sum(r.x * r.confidence for r in cluster) / total_conf
        y = sum(r.y * r.confidence for r in cluster) / total_conf
        return x, y

    def classify(self, cluster: List[SensorReading]) -> str:
        types = {}
        for r in cluster:
            types[r.target_type] = types.get(r.target_type, 0) + r.confidence
        return max(types, key=types.get) if types else "unknown"

    def stats(self) -> Dict:
        return {"readings": len(self.readings), "clusters": len(self.cluster())}

def run():
    tsf = TacticalSensorFusion()
    tsf.add_reading(SensorReading("RADAR", 100, 100, 0.8, "aircraft"))
    tsf.add_reading(SensorReading("EO", 102, 101, 0.7, "aircraft"))
    tsf.add_reading(SensorReading("RADAR", 200, 200, 0.6, "vehicle"))
    clusters = tsf.cluster()
    print(tsf.stats())
    for c in clusters:
        print("Fused:", tsf.fused_position(c), "Class:", tsf.classify(c))

if __name__ == "__main__":
    run()
