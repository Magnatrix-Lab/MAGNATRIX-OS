"""Native stdlib module: Electrical Load Calculator
Calculates home electrical load, circuit sizing, and breaker requirements.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class CircuitType(Enum):
    GENERAL = "general"
    KITCHEN = "kitchen"
    BATHROOM = "bathroom"
    HVAC = "hvac"
    APPLIANCE = "appliance"

@dataclass
class ElectricalLoad:
    appliance_name: str
    wattage: float
    voltage: float = 120.0
    circuit_type: CircuitType = CircuitType.GENERAL
    duty_factor: float = 0.8

@dataclass
class ElectricalLoadCalculator:
    dwelling_name: str
    loads: List[ElectricalLoad] = field(default_factory=list)

    def total_wattage(self) -> float:
        return sum(l.wattage for l in self.loads)

    def diversified_wattage(self) -> float:
        return sum(l.wattage * l.duty_factor for l in self.loads)

    def total_amperage(self) -> float:
        return sum((l.wattage / l.voltage) for l in self.loads)

    def diversified_amperage(self) -> float:
        return sum((l.wattage * l.duty_factor / l.voltage) for l in self.loads)

    def by_circuit(self) -> Dict[str, float]:
        totals = {}
        for l in self.loads:
            totals[l.circuit_type.value] = totals.get(l.circuit_type.value, 0) + l.wattage
        return totals

    def main_breaker_size_a(self) -> int:
        total = self.diversified_amperage()
        if total <= 60:
            return 60
        elif total <= 100:
            return 100
        elif total <= 150:
            return 150
        elif total <= 200:
            return 200
        return 250

    def stats(self) -> Dict:
        return {
            "dwelling": self.dwelling_name,
            "total_wattage": round(self.total_wattage(), 1),
            "diversified_wattage": round(self.diversified_wattage(), 1),
            "total_amperage": round(self.total_amperage(), 1),
            "diversified_amperage": round(self.diversified_amperage(), 1),
            "main_breaker_a": self.main_breaker_size_a(),
            "by_circuit": {k: round(v, 1) for k, v in self.by_circuit().items()},
        }

def run():
    elc = ElectricalLoadCalculator(
        dwelling_name="House A",
        loads=[
            ElectricalLoad("refrigerator", 800, 120, CircuitType.KITCHEN, 0.9),
            ElectricalLoad("microwave", 1200, 120, CircuitType.KITCHEN, 0.3),
            ElectricalLoad("water_heater", 4500, 240, CircuitType.APPLIANCE, 0.8),
            ElectricalLoad("HVAC", 5000, 240, CircuitType.HVAC, 0.7),
            ElectricalLoad("lighting", 800, 120, CircuitType.GENERAL, 0.6),
            ElectricalLoad("outlets", 1200, 120, CircuitType.GENERAL, 0.4),
        ]
    )
    print(elc.stats())

if __name__ == "__main__":
    run()
