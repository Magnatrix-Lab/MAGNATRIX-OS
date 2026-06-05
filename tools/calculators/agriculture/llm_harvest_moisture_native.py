"""Harvest Moisture Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class HarvestMoisture:
    crop_type: str
    wet_weight_kg: float
    moisture_percent: float
    target_moisture_percent: float

    def dry_weight_kg(self) -> float:
        return round(self.wet_weight_kg * (1 - self.moisture_percent / 100.0), 2)

    def target_weight_kg(self) -> float:
        dry = self.dry_weight_kg()
        if self.target_moisture_percent >= 100:
            return 0.0
        return round(dry / (1 - self.target_moisture_percent / 100.0), 2)

    def water_to_remove_kg(self) -> float:
        return round(self.wet_weight_kg - self.target_weight_kg(), 2)

    def shrink_percent(self) -> float:
        if self.wet_weight_kg <= 0:
            return 0.0
        return round(self.water_to_remove_kg() / self.wet_weight_kg * 100, 2)

    def safe_storage_moisture(self) -> float:
        safe = {"corn": 14.0, "wheat": 13.0, "rice": 14.0, "soybean": 13.0, "barley": 12.5}
        return safe.get(self.crop_type, 14.0)

    def is_safe_for_storage(self) -> bool:
        return self.moisture_percent <= self.safe_storage_moisture()

    def drying_energy_kwh(self) -> float:
        water = self.water_to_remove_kg()
        return round(water * 0.8, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "dry_weight_kg": self.dry_weight_kg(),
            "water_to_remove_kg": self.water_to_remove_kg(),
            "shrink_percent": self.shrink_percent(),
        }

    def run(self):
        print("=" * 60)
        print("HARVEST MOISTURE CALCULATOR")
        print("=" * 60)
        hm = HarvestMoisture(
            crop_type="corn", wet_weight_kg=1000, moisture_percent=25, target_moisture_percent=14
        )
        print(f"Crop: {hm.crop_type}")
        print(f"Wet weight: {hm.wet_weight_kg} kg @ {hm.moisture_percent}%")
        print(f"Dry weight: {hm.dry_weight_kg():.2f} kg")
        print(f"Target weight: {hm.target_weight_kg():.2f} kg")
        print(f"Water to remove: {hm.water_to_remove_kg():.2f} kg")
        print(f"Shrink: {hm.shrink_percent():.2f}%")
        print(f"Safe storage: {hm.safe_storage_moisture():.1f}%")
        print(f"Safe for storage: {hm.is_safe_for_storage()}")
        print(f"Drying energy: {hm.drying_energy_kwh():.2f} kWh")
        print(f"Stats: {hm.stats()}")

if __name__ == "__main__":
    HarvestMoisture("corn", 0, 0, 0).run()
