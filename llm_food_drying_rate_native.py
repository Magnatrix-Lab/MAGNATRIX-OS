"""Food Drying Rate Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class FoodDryingRate:
    initial_moisture_percent: float
    final_moisture_percent: float
    product_weight_kg: float
    drying_area_sqm: float
    air_temp_c: float = 60.0
    air_velocity_ms: float = 2.0
    air_humidity_percent: float = 30.0

    def moisture_to_remove_kg(self) -> float:
        return round(self.product_weight_kg * (self.initial_moisture_percent - self.final_moisture_percent) / 100.0, 3)

    def drying_rate_kg_per_h(self) -> float:
        if self.drying_area_sqm <= 0:
            return 0.0
        rh_factor = 1 - self.air_humidity_percent / 100.0
        temp_factor = (self.air_temp_c / 60.0) ** 1.5
        velocity_factor = (self.air_velocity_ms / 2.0) ** 0.5
        rate = 0.5 * self.drying_area_sqm * rh_factor * temp_factor * velocity_factor
        return round(rate, 3)

    def drying_time_hours(self) -> float:
        rate = self.drying_rate_kg_per_h()
        if rate <= 0:
            return 0.0
        return round(self.moisture_to_remove_kg() / rate, 2)

    def water_activity_initial(self) -> float:
        return round(self.initial_moisture_percent / 100.0, 3)

    def water_activity_final(self) -> float:
        return round(self.final_moisture_percent / 100.0, 3)

    def shelf_life_estimate_months(self) -> float:
        aw = self.water_activity_final()
        if aw <= 0.6:
            return 12.0
        elif aw <= 0.8:
            return 6.0
        else:
            return 1.0

    def energy_required_kwh(self) -> float:
        latent_heat = 2260
        moisture = self.moisture_to_remove_kg()
        return round(moisture * latent_heat / 3600.0, 3)

    def stats(self) -> Dict[str, float]:
        return {
            "moisture_to_remove_kg": self.moisture_to_remove_kg(),
            "drying_rate_kg_per_h": self.drying_rate_kg_per_h(),
            "drying_time_hours": self.drying_time_hours(),
        }

    def run(self):
        print("=" * 60)
        print("FOOD DRYING RATE CALCULATOR")
        print("=" * 60)
        dry = FoodDryingRate(
            initial_moisture_percent=85, final_moisture_percent=12,
            product_weight_kg=100, drying_area_sqm=20,
            air_temp_c=70, air_velocity_ms=3.0, air_humidity_percent=25
        )
        print(f"Moisture: {dry.initial_moisture_percent}% -> {dry.final_moisture_percent}%")
        print(f"Moisture to remove: {dry.moisture_to_remove_kg():.3f} kg")
        print(f"Drying rate: {dry.drying_rate_kg_per_h():.3f} kg/h")
        print(f"Drying time: {dry.drying_time_hours():.2f} h")
        print(f"Water activity: {dry.water_activity_initial():.3f} -> {dry.water_activity_final():.3f}")
        print(f"Shelf life: {dry.shelf_life_estimate_months():.1f} months")
        print(f"Energy: {dry.energy_required_kwh():.3f} kWh")
        print(f"Stats: {dry.stats()}")

if __name__ == "__main__":
    FoodDryingRate(0, 0, 0, 0).run()
