#!/usr/bin/env python3
"""Reality Sensor Mesh — MAGNATRIX-OS ASI Expansion
Path: runtime/sensor_mesh_native.py
License: AGPL-3.0
Depends: Python 3.11+ stdlib only.

IoT/camera/satellite data ingestion with spatial indexing and anomaly detection.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class SensorReading:
    sensor_id: str
    timestamp: float
    value: float
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class SensorMesh:
    def __init__(self, cell_size: float = 10.0):
        self.cell_size = cell_size
        self.readings: List[SensorReading] = []
        self._spatial_grid: Dict[Tuple[int, int, int], List[SensorReading]] = {}
        self._anomaly_threshold = 3.0  # MAD multiplier

    def ingest(self, reading: SensorReading) -> None:
        self.readings.append(reading)
        cell = self._cell(reading.x, reading.y, reading.z)
        self._spatial_grid.setdefault(cell, []).append(reading)

    def _cell(self, x: float, y: float, z: float) -> Tuple[int, int, int]:
        return (int(x // self.cell_size), int(y // self.cell_size), int(z // self.cell_size))

    def fuse(self, sensor_ids: List[str], window_seconds: float = 60.0) -> Dict[str, float]:
        """Multi-sensor fusion via averaging within time window."""
        if not self.readings:
            return {}
        max_ts = max(r.timestamp for r in self.readings)
        filtered = [r for r in self.readings if r.sensor_id in sensor_ids and r.timestamp >= max_ts - window_seconds]
        if not filtered:
            return {}
        by_sensor = {}
        for r in filtered:
            by_sensor.setdefault(r.sensor_id, []).append(r.value)
        return {sid: statistics.mean(vals) for sid, vals in by_sensor.items()}

    def detect_anomaly(self, sensor_id: str, window: int = 50) -> List[Tuple[float, float]]:
        """Detect anomalies using Median Absolute Deviation."""
        vals = [r.value for r in self.readings if r.sensor_id == sensor_id]
        if len(vals) < window:
            return []
        recent = vals[-window:]
        median = statistics.median(recent)
        mad = statistics.median([abs(v - median) for v in recent]) or 1e-6
        anomalies = []
        for ts, r in enumerate(self.readings):
            if r.sensor_id != sensor_id:
                continue
            z_score = 0.6745 * (r.value - median) / mad
            if abs(z_score) > self._anomaly_threshold:
                anomalies.append((r.timestamp, r.value))
        return anomalies

    def query_spatial(self, x: float, y: float, z: float, radius: float) -> List[SensorReading]:
        """Query readings within radius."""
        result = []
        for r in self.readings:
            dist = math.sqrt((r.x - x) ** 2 + (r.y - y) ** 2 + (r.z - z) ** 2)
            if dist <= radius:
                result.append(r)
        return result


def _self_test():
    print("=" * 55)
    print("Sensor Mesh — Self Test")
    print("=" * 55)
    passed = 0
    total = 4

    mesh = SensorMesh(cell_size=5.0)

    # Ingest normal readings
    for i in range(100):
        mesh.ingest(SensorReading("temp_1", i, 20.0 + random.gauss(0, 1), x=i, y=0, z=0))
    # Ingest anomaly
    mesh.ingest(SensorReading("temp_1", 101, 50.0, x=101, y=0, z=0))

    print("[Test 1] Ingest 101 readings")
    ok = len(mesh.readings) == 101
    print(f"  Count: {len(mesh.readings)} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    print("[Test 2] Spatial fusion")
    fused = mesh.fuse(["temp_1"], window_seconds=200)
    print(f"  Fused mean: {fused.get('temp_1', 0):.1f} — {'PASS' if 'temp_1' in fused else 'FAIL'}")
    passed += ('temp_1' in fused)

    print("[Test 3] Anomaly detection")
    anomalies = mesh.detect_anomaly("temp_1", window=20)
    print(f"  Anomalies detected: {len(anomalies)} — {'PASS' if len(anomalies) >= 1 else 'FAIL'}")
    passed += (len(anomalies) >= 1)

    print("[Test 4] Spatial query")
    nearby = mesh.query_spatial(50, 0, 0, 10)
    print(f"  Nearby readings: {len(nearby)} — {'PASS' if len(nearby) > 0 else 'FAIL'}")
    passed += (len(nearby) > 0)

    print(f"\nPASS: {passed}/{total}")
    print("=" * 55)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import random, sys
    sys.exit(_self_test())
