"""Native stdlib module: Fuel Burn Calculator
Calculates aircraft fuel burn, range, and endurance for flight planning.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class AircraftType(Enum):
    SINGLE_PISTON = "single_piston"
    MULTI_PISTON = "multi_piston"
    TURBOPROP = "turboprop"
    JET = "jet"
    WIDE_BODY = "wide_body"

@dataclass
class FuelBurnCalculator:
    aircraft_type: AircraftType
    distance_nm: float
    cruise_speed_kts: float
    fuel_flow_kg_hr: float
    fuel_capacity_kg: float
    alternate_fuel_nm: float = 50
    contingency_pct: float = 5.0
    final_reserve_min: float = 30

    def flight_time_hr(self) -> float:
        if self.cruise_speed_kts == 0:
            return 0.0
        return self.distance_nm / self.cruise_speed_kts

    def trip_fuel_kg(self) -> float:
        return self.flight_time_hr() * self.fuel_flow_kg_hr

    def alternate_fuel_kg(self) -> float:
        if self.cruise_speed_kts == 0:
            return 0.0
        return (self.alternate_fuel_nm / self.cruise_speed_kts) * self.fuel_flow_kg_hr

    def contingency_fuel_kg(self) -> float:
        return self.trip_fuel_kg() * (self.contingency_pct / 100)

    def final_reserve_fuel_kg(self) -> float:
        return self.fuel_flow_kg_hr * (self.final_reserve_min / 60)

    def total_required_fuel_kg(self) -> float:
        return self.trip_fuel_kg() + self.alternate_fuel_kg() + self.contingency_fuel_kg() + self.final_reserve_fuel_kg()

    def fuel_margin_kg(self) -> float:
        return self.fuel_capacity_kg - self.total_required_fuel_kg()

    def max_range_nm(self) -> float:
        if self.fuel_flow_kg_hr == 0:
            return 0.0
        usable_fuel = self.fuel_capacity_kg - self.alternate_fuel_kg() - self.contingency_fuel_kg() - self.final_reserve_fuel_kg()
        return (usable_fuel / self.fuel_flow_kg_hr) * self.cruise_speed_kts

    def endurance_hr(self) -> float:
        if self.fuel_flow_kg_hr == 0:
            return 0.0
        return self.fuel_capacity_kg / self.fuel_flow_kg_hr

    def stats(self) -> Dict:
        return {
            "aircraft": self.aircraft_type.value,
            "distance_nm": self.distance_nm,
            "flight_time_hr": round(self.flight_time_hr(), 2),
            "trip_fuel_kg": round(self.trip_fuel_kg(), 1),
            "alternate_fuel_kg": round(self.alternate_fuel_kg(), 1),
            "contingency_fuel_kg": round(self.contingency_fuel_kg(), 1),
            "final_reserve_kg": round(self.final_reserve_fuel_kg(), 1),
            "total_required_kg": round(self.total_required_fuel_kg(), 1),
            "fuel_margin_kg": round(self.fuel_margin_kg(), 1),
            "max_range_nm": round(self.max_range_nm(), 1),
            "endurance_hr": round(self.endurance_hr(), 2),
        }

def run():
    fbc = FuelBurnCalculator(aircraft_type=AircraftType.JET, distance_nm=500, cruise_speed_kts=450, fuel_flow_kg_hr=2500, fuel_capacity_kg=15000, alternate_fuel_nm=100, contingency_pct=5, final_reserve_min=30)
    print(fbc.stats())

if __name__ == "__main__":
    run()
