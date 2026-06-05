"""Native stdlib module: Container Load Calculator
Calculates container stowage, weight distribution, and lashing forces.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class CargoItem:
    name: str
    weight_kg: float
    length_m: float
    width_m: float
    height_m: float

@dataclass
class ContainerLoadCalculator:
    container_type: str
    max_weight_kg: float
    internal_length_m: float
    internal_width_m: float
    internal_height_m: float
    cargo: List[CargoItem] = field(default_factory=list)

    def total_cargo_weight_kg(self) -> float:
        return sum(c.weight_kg for c in self.cargo)

    def total_cargo_volume_m3(self) -> float:
        return sum(c.length_m * c.width_m * c.height_m for c in self.cargo)

    def container_volume_m3(self) -> float:
        return self.internal_length_m * self.internal_width_m * self.internal_height_m

    def volume_utilization_pct(self) -> float:
        if self.container_volume_m3() == 0:
            return 0.0
        return (self.total_cargo_volume_m3() / self.container_volume_m3()) * 100

    def weight_utilization_pct(self) -> float:
        if self.max_weight_kg == 0:
            return 0.0
        return (self.total_cargo_weight_kg() / self.max_weight_kg) * 100

    def remaining_weight_kg(self) -> float:
        return max(0, self.max_weight_kg - self.total_cargo_weight_kg())

    def center_of_gravity_m(self) -> float:
        if self.total_cargo_weight_kg() == 0:
            return self.internal_length_m / 2
        weighted_sum = sum(c.weight_kg * (c.length_m / 2) for c in self.cargo)
        return weighted_sum / self.total_cargo_weight_kg()

    def stats(self) -> Dict:
        return {
            "container": self.container_type,
            "cargo_items": len(self.cargo),
            "total_weight_kg": round(self.total_cargo_weight_kg(), 1),
            "total_volume_m3": round(self.total_cargo_volume_m3(), 2),
            "volume_utilization_pct": round(self.volume_utilization_pct(), 1),
            "weight_utilization_pct": round(self.weight_utilization_pct(), 1),
            "remaining_weight_kg": round(self.remaining_weight_kg(), 1),
        }

def run():
    clc = ContainerLoadCalculator(
        container_type="40ft HC",
        max_weight_kg=28000,
        internal_length_m=12.03,
        internal_width_m=2.35,
        internal_height_m=2.69,
        cargo=[
            CargoItem("Pallets A", 8000, 1.2, 0.8, 1.5),
            CargoItem("Pallets B", 6000, 1.0, 1.0, 1.2),
            CargoItem("Boxes C", 4000, 2.0, 1.5, 1.0),
        ]
    )
    print(clc.stats())

if __name__ == "__main__":
    run()
