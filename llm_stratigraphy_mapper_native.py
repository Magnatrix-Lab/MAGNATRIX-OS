"""Stratigraphy Mapper — layer sequence, correlation, facies analysis, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
from math import sqrt, pow, fabs, log, exp
from datetime import datetime, timedelta

class LithologyType(Enum):
    SANDSTONE = auto()
    SHALE = auto()
    LIMESTONE = auto()
    CLAY = auto()
    SILTSTONE = auto()
    CONGLOMERATE = auto()
    VOLCANIC = auto()
    ORGANIC = auto()

class DepositionalEnvironment(Enum):
    FLUVIAL = auto()
    MARINE = auto()
    LACUSTRINE = auto()
    AEOLIAN = auto()
    GLACIAL = auto()
    DELTAIC = auto()
    REEF = auto()

@dataclass
class StratigraphicLayer:
    id: str
    top_depth_m: float
    bottom_depth_m: float
    lithology: LithologyType
    environment: DepositionalEnvironment
    color: str = ""
    grain_size_mm: float = 0.0
    fossil_content: List[str] = field(default_factory=list)
    age_ma: float = 0.0  # million years ago
    description: str = ""

    @property
    def thickness(self) -> float:
        return fabs(self.bottom_depth_m - self.top_depth_m)

    def grain_size_category(self) -> str:
        if self.grain_size_mm < 0.004:
            return "clay"
        elif self.grain_size_mm < 0.063:
            return "silt"
        elif self.grain_size_mm < 2.0:
            return "sand"
        elif self.grain_size_mm < 64.0:
            return "gravel"
        return "boulder"

class StratigraphicColumn:
    def __init__(self, name: str, location: str = ""):
        self.name = name
        self.location = location
        self.layers: List[StratigraphicLayer] = []

    def add_layer(self, layer: StratigraphicLayer) -> None:
        self.layers.append(layer)
        self.layers.sort(key=lambda l: l.top_depth_m)

    def total_thickness(self) -> float:
        return sum(l.thickness for l in self.layers)

    def layer_at_depth(self, depth_m: float) -> Optional[StratigraphicLayer]:
        for l in self.layers:
            if l.top_depth_m <= depth_m <= l.bottom_depth_m:
                return l
        return None

    def lithology_percentages(self) -> Dict[str, float]:
        total = self.total_thickness()
        if total == 0:
            return {}
        counts = {}
        for l in self.layers:
            name = l.lithology.name
            counts[name] = counts.get(name, 0.0) + l.thickness
        return {k: v / total * 100 for k, v in counts.items()}

    def find_unconformities(self) -> List[Tuple[float, float]]:
        """Find gaps between layers."""
        gaps = []
        for i in range(len(self.layers) - 1):
            gap = self.layers[i+1].top_depth_m - self.layers[i].bottom_depth_m
            if gap > 0.1:
                gaps.append((self.layers[i].bottom_depth_m, self.layers[i+1].top_depth_m))
        return gaps

    def correlate_with(self, other: 'StratigraphicColumn', age_tolerance_ma: float = 1.0) -> List[Tuple[str, str]]:
        """Find correlated layers based on age and lithology."""
        matches = []
        for l1 in self.layers:
            for l2 in other.layers:
                if fabs(l1.age_ma - l2.age_ma) <= age_tolerance_ma and l1.lithology == l2.lithology:
                    matches.append((l1.id, l2.id))
        return matches

    def facies_sequence(self) -> List[DepositionalEnvironment]:
        return [l.environment for l in self.layers]

    def stats(self) -> Dict[str, float]:
        ages = [l.age_ma for l in self.layers if l.age_ma > 0]
        return {
            "layer_count": len(self.layers),
            "total_thickness_m": self.total_thickness(),
            "unconformity_count": len(self.find_unconformities()),
            "oldest_age_ma": max(ages) if ages else 0.0,
            "youngest_age_ma": min(ages) if ages else 0.0,
            "lithology_variety": len(self.lithology_percentages())
        }

class StratigraphyMapper:
    def __init__(self):
        self.columns: Dict[str, StratigraphicColumn] = {}

    def add_column(self, column: StratigraphicColumn) -> None:
        self.columns[column.name] = column

    def map_correlations(self, col_a: str, col_b: str) -> List[Tuple[str, str]]:
        if col_a not in self.columns or col_b not in self.columns:
            return []
        return self.columns[col_a].correlate_with(self.columns[col_b])

    def regional_thickness(self, lithology: LithologyType) -> Dict[str, float]:
        return {name: sum(l.thickness for l in col.layers if l.lithology == lithology) for name, col in self.columns.items()}

    def stats(self) -> Dict[str, int]:
        return {
            "column_count": len(self.columns),
            "total_layers": sum(len(c.layers) for c in self.columns.values())
        }

def run():
    col = StratigraphicColumn("Site-A", "Java Basin")
    col.add_layer(StratigraphicLayer("L1", 0, 5, LithologyType.CLAY, DepositionalEnvironment.LACUSTRINE, "grey", 0.002, [], 0.01))
    col.add_layer(StratigraphicLayer("L2", 5, 12, LithologyType.SANDSTONE, DepositionalEnvironment.FLUVIAL, "yellow", 0.5, [], 0.5))
    col.add_layer(StratigraphicLayer("L3", 12, 15, LithologyType.LIMESTONE, DepositionalEnvironment.MARINE, "white", 0.1, ["foraminifera"], 2.0))
    col2 = StratigraphicColumn("Site-B", "Java Basin")
    col2.add_layer(StratigraphicLayer("M1", 0, 4, LithologyType.CLAY, DepositionalEnvironment.LACUSTRINE, "grey", 0.003, [], 0.01))
    col2.add_layer(StratigraphicLayer("M2", 4, 11, LithologyType.SANDSTONE, DepositionalEnvironment.FLUVIAL, "yellow", 0.4, [], 0.5))
    mapper = StratigraphyMapper()
    mapper.add_column(col)
    mapper.add_column(col2)
    print(f"Correlations: {mapper.map_correlations('Site-A', 'Site-B')}")
    print(f"Lithology %: {col.lithology_percentages()}")
    print(f"Unconformities: {col.find_unconformities()}")
    print(col.stats())
    print(mapper.stats())

if __name__ == "__main__":
    run()
