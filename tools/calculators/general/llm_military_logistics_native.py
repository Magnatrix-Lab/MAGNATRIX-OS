"""Native stdlib module: Military Logistics Calculator
Calculates supply chain requirements for military operations.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class UnitRequirement:
    unit_name: str
    personnel: int
    fuel_liters_per_day: float
    food_kg_per_day: float
    ammo_kg_per_day: float
    water_liters_per_day: float

@dataclass
class MilitaryLogisticsCalculator:
    operation_name: str
    duration_days: int
    units: List[UnitRequirement] = field(default_factory=list)
    transport_capacity_kg: float = 10000

    def total_personnel(self) -> int:
        return sum(u.personnel for u in self.units)

    def total_fuel_liters(self) -> float:
        return sum(u.fuel_liters_per_day for u in self.units) * self.duration_days

    def total_food_kg(self) -> float:
        return sum(u.food_kg_per_day for u in self.units) * self.duration_days

    def total_ammo_kg(self) -> float:
        return sum(u.ammo_kg_per_day for u in self.units) * self.duration_days

    def total_water_liters(self) -> float:
        return sum(u.water_liters_per_day for u in self.units) * self.duration_days

    def total_supply_weight_kg(self) -> float:
        return self.total_fuel_liters() * 0.85 + self.total_food_kg() + self.total_ammo_kg() + self.total_water_liters()

    def transport_trips_needed(self) -> int:
        if self.transport_capacity_kg == 0:
            return 0
        return int(self.total_supply_weight_kg() / self.transport_capacity_kg) + 1

    def daily_supply_requirement_kg(self) -> float:
        return self.total_supply_weight_kg() / self.duration_days

    def stats(self) -> Dict:
        return {
            "operation": self.operation_name,
            "duration_days": self.duration_days,
            "total_personnel": self.total_personnel(),
            "total_fuel_liters": round(self.total_fuel_liters(), 1),
            "total_food_kg": round(self.total_food_kg(), 1),
            "total_ammo_kg": round(self.total_ammo_kg(), 1),
            "total_water_liters": round(self.total_water_liters(), 1),
            "supply_weight_kg": round(self.total_supply_weight_kg(), 1),
            "transport_trips": self.transport_trips_needed(),
        }

def run():
    mlc = MilitaryLogisticsCalculator(
        operation_name="Desert Shield",
        duration_days=30,
        units=[
            UnitRequirement("Infantry Battalion", 800, 500, 2400, 200, 4000),
            UnitRequirement("Armor Company", 150, 3000, 450, 500, 750),
            UnitRequirement("Artillery Battery", 100, 1000, 300, 800, 500),
        ]
    )
    print(mlc.stats())

if __name__ == "__main__":
    run()
