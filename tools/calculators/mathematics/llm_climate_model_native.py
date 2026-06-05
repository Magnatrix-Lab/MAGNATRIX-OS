"""Climate Model — temperature anomaly, CO2 correlation, simple, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
import statistics

class ClimateModel:
    def __init__(self, baseline_temp: float = 14.0, climate_sensitivity: float = 3.0):
        self.baseline = baseline_temp
        self.sensitivity = climate_sensitivity
        self.data: List[Dict] = []

    def add_data(self, year: int, co2: float, temp: float):
        self.data.append({"year": year, "co2": co2, "temp": temp})

    def temp_anomaly(self, year: int) -> float:
        d = next((d for d in self.data if d["year"] == year), None)
        return d["temp"] - self.baseline if d else 0.0

    def predict_temp(self, co2_level: float) -> float:
        # Simplified: T = baseline + sensitivity * ln(CO2/280) / ln(2)
        import math
        return self.baseline + self.sensitivity * (math.log(co2_level / 280) / math.log(2))

    def co2_needed(self, target_temp: float) -> float:
        import math
        return 280 * (2 ** ((target_temp - self.baseline) / self.sensitivity))

    def trend(self, years: int = 10) -> float:
        if len(self.data) < 2:
            return 0.0
        recent = self.data[-years:]
        if len(recent) < 2:
            return 0.0
        temps = [d["temp"] for d in recent]
        return (temps[-1] - temps[0]) / len(recent)

    def stats(self) -> Dict:
        return {"data_points": len(self.data), "baseline": self.baseline, "sensitivity": self.sensitivity}

def run():
    cm = ClimateModel(14.0, 3.0)
    cm.add_data(2000, 370, 14.5)
    cm.add_data(2010, 390, 14.7)
    cm.add_data(2020, 415, 15.0)
    print("Anomaly 2020:", cm.temp_anomaly(2020))
    print("Predict 450ppm:", cm.predict_temp(450))
    print(cm.stats())

if __name__ == "__main__":
    run()
