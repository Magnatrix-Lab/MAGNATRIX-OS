"""Disaster Predictor — earthquake, flood, wildfire risk, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto

class DisasterType(Enum):
    EARTHQUAKE = auto()
    FLOOD = auto()
    WILDFIRE = auto()
    HURRICANE = auto()

class DisasterPredictor:
    def __init__(self):
        self.regions: Dict[str, Dict] = {}

    def add_region(self, region_id: str, seismic_zone: int = 0, elevation: float = 100, vegetation: float = 0.5, rainfall_history: List[float] = None):
        self.regions[region_id] = {
            "seismic": seismic_zone,
            "elevation": elevation,
            "vegetation": vegetation,
            "rainfall": rainfall_history or [],
        }

    def earthquake_risk(self, region_id: str) -> float:
        r = self.regions.get(region_id, {})
        return min(1.0, r.get("seismic", 0) * 0.2)

    def flood_risk(self, region_id: str) -> float:
        r = self.regions.get(region_id, {})
        rainfall = r.get("rainfall", [])
        if not rainfall:
            return 0.0
        avg = sum(rainfall) / len(rainfall)
        elevation_factor = max(0, 1 - r.get("elevation", 100) / 200)
        return min(1.0, avg / 100 * elevation_factor)

    def wildfire_risk(self, region_id: str) -> float:
        r = self.regions.get(region_id, {})
        veg = r.get("vegetation", 0)
        rainfall = r.get("rainfall", [])
        dry = 1 - (sum(rainfall) / len(rainfall) / 100) if rainfall else 0.5
        return min(1.0, veg * dry)

    def overall_risk(self, region_id: str) -> Dict:
        return {
            "earthquake": self.earthquake_risk(region_id),
            "flood": self.flood_risk(region_id),
            "wildfire": self.wildfire_risk(region_id),
        }

    def stats(self) -> Dict:
        return {"regions": len(self.regions)}

def run():
    dp = DisasterPredictor()
    dp.add_region("CA", 4, 50, 0.8, [5, 2, 1, 0, 0])
    dp.add_region("FL", 0, 10, 0.3, [100, 120, 150, 80])
    print(dp.overall_risk("CA"))
    print(dp.overall_risk("FL"))
    print(dp.stats())

if __name__ == "__main__":
    run()
