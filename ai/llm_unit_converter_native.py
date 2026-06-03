"""LLM Unit Converter — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class UnitCategory(Enum):
    LENGTH = auto()
    WEIGHT = auto()
    TEMPERATURE = auto()
    TIME = auto()
    DATA = auto()
    SPEED = auto()

class UnitConverter:
    def __init__(self) -> None:
        self._conversions: Dict[Tuple[str, str], float] = {
            ("m", "km"): 0.001, ("km", "m"): 1000,
            ("m", "cm"): 100, ("cm", "m"): 0.01,
            ("m", "mm"): 1000, ("mm", "m"): 0.001,
            ("ft", "m"): 0.3048, ("m", "ft"): 3.28084,
            ("in", "cm"): 2.54, ("cm", "in"): 0.393701,
            ("kg", "g"): 1000, ("g", "kg"): 0.001,
            ("lb", "kg"): 0.453592, ("kg", "lb"): 2.20462,
            ("s", "ms"): 1000, ("ms", "s"): 0.001,
            ("min", "s"): 60, ("s", "min"): 1/60,
            ("h", "min"): 60, ("min", "h"): 1/60,
            ("B", "KB"): 1/1024, ("KB", "B"): 1024,
            ("KB", "MB"): 1/1024, ("MB", "KB"): 1024,
            ("MB", "GB"): 1/1024, ("GB", "MB"): 1024,
            ("mps", "kph"): 3.6, ("kph", "mps"): 1/3.6,
        }

    def convert(self, value: float, from_unit: str, to_unit: str) -> float:
        if from_unit == to_unit:
            return value
        key = (from_unit, to_unit)
        if key in self._conversions:
            return value * self._conversions[key]
        if from_unit == "C" and to_unit == "F":
            return value * 9/5 + 32
        if from_unit == "F" and to_unit == "C":
            return (value - 32) * 5/9
        if from_unit == "C" and to_unit == "K":
            return value + 273.15
        if from_unit == "K" and to_unit == "C":
            return value - 273.15
        raise ValueError("Unsupported conversion: " + from_unit + " to " + to_unit)

    def convert_temperature(self, value: float, from_unit: str, to_unit: str) -> float:
        return self.convert(value, from_unit, to_unit)

    def batch_convert(self, values: List[float], from_unit: str, to_unit: str) -> List[float]:
        return [self.convert(v, from_unit, to_unit) for v in values]

    def get_supported_units(self) -> List[str]:
        units = set()
        for from_u, to_u in self._conversions.keys():
            units.add(from_u)
            units.add(to_u)
        units.update(["C", "F", "K"])
        return sorted(list(units))

    def get_stats(self) -> Dict[str, Any]:
        return {"conversions": len(self._conversions), "units": len(self.get_supported_units())}

def run() -> None:
    print("Unit Converter test")
    e = UnitConverter()
    print("  1000m -> km: " + str(e.convert(1000, "m", "km")))
    print("  32F -> C: " + str(e.convert(32, "F", "C")))
    print("  1GB -> MB: " + str(e.convert(1, "GB", "MB")))
    print("  60mph -> kph: " + str(e.convert(60, "mps", "kph") * 1000/3600))
    print("  Batch: " + str(e.batch_convert([1, 2, 3], "kg", "lb")))
    print("  Units: " + str(len(e.get_supported_units())))
    print("  Stats: " + str(e.get_stats()))
    print("Unit Converter test complete.")

if __name__ == "__main__":
    run()
