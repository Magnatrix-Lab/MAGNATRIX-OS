"""Excavation Logger — context recording, unit tracking, finds registry, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum, auto
from math import sqrt, pow, fabs, log, exp
from datetime import datetime, timedelta
from collections import defaultdict

class ContextType(Enum):
    CUT = auto()
    FILL = auto()
    LAYER = auto()
    STRUCTURE = auto()
    PIT = auto()
    POSTHOLE = auto()

class FindType(Enum):
    ARTIFACT = auto()
    ECofact = auto()
    FEATURE = auto()
    SAMPLE = auto()
    HUMAN_REMAIN = auto()

@dataclass
class ExcavationUnit:
    id: str
    grid_n: int
    grid_e: int
    level: str  # e.g., "spit 1", "layer 2"
    top_elevation_m: float
    bottom_elevation_m: float
    context_type: ContextType
    description: str = ""
    date_opened: datetime = field(default_factory=datetime.now)
    date_closed: Optional[datetime] = None
    excavators: List[str] = field(default_factory=list)

    @property
    def thickness(self) -> float:
        return fabs(self.bottom_elevation_m - self.top_elevation_m)

    @property
    def is_open(self) -> bool:
        return self.date_closed is None

@dataclass
class Find:
    id: str
    unit_id: str
    find_type: FindType
    description: str
    x_local: float  # cm within unit
    y_local: float
    z_local: float
    weight_g: float = 0.0
    date_found: datetime = field(default_factory=datetime.now)
    finder: str = ""
    bag_number: str = ""
    photos: List[str] = field(default_factory=list)

    @property
    def coordinates(self) -> Tuple[float, float, float]:
        return (self.x_local, self.y_local, self.z_local)

class ExcavationLogger:
    def __init__(self, site_name: str = ""):
        self.site_name = site_name
        self.units: Dict[str, ExcavationUnit] = {}
        self.finds: Dict[str, Find] = {}
        self.unit_finds: Dict[str, List[str]] = defaultdict(list)

    def add_unit(self, unit: ExcavationUnit) -> None:
        self.units[unit.id] = unit

    def add_find(self, find: Find) -> None:
        self.finds[find.id] = find
        self.unit_finds[find.unit_id].append(find.id)

    def close_unit(self, unit_id: str, date: datetime = None) -> None:
        if unit_id in self.units:
            self.units[unit_id].date_closed = date or datetime.now()

    def finds_by_unit(self, unit_id: str) -> List[Find]:
        return [self.finds[fid] for fid in self.unit_finds.get(unit_id, [])]

    def finds_by_type(self, find_type: FindType) -> List[Find]:
        return [f for f in self.finds.values() if f.find_type == find_type]

    def units_by_context(self, context_type: ContextType) -> List[ExcavationUnit]:
        return [u for u in self.units.values() if u.context_type == context_type]

    def vertical_distribution(self, bucket_cm: float = 10.0) -> Dict[str, int]:
        """Distribution of finds by depth buckets."""
        dist = defaultdict(int)
        for f in self.finds.values():
            bucket = f"{int(f.z_local // bucket_cm) * bucket_cm}-{int(f.z_local // bucket_cm) * bucket_cm + bucket_cm}"
            dist[bucket] += 1
        return dict(dist)

    def density_by_unit(self) -> Dict[str, float]:
        """Finds per unit volume (approximate)."""
        result = {}
        for uid, fids in self.unit_finds.items():
            u = self.units.get(uid)
            if u:
                volume = 100 * 100 * u.thickness * 100  # cm^3 (1m x 1m x thickness)
                result[uid] = len(fids) / (volume / 1000000) if volume > 0 else 0.0
        return result

    def find_statistics(self) -> Dict[str, int]:
        by_type = defaultdict(int)
        for f in self.finds.values():
            by_type[f.find_type.name] += 1
        return dict(by_type)

    def daily_report(self, date: datetime) -> Dict:
        units_opened = [u.id for u in self.units.values() if u.date_opened.date() == date.date()]
        units_closed = [u.id for u in self.units.values() if u.date_closed and u.date_closed.date() == date.date()]
        finds_today = [f.id for f in self.finds.values() if f.date_found.date() == date.date()]
        return {
            "date": date.strftime("%Y-%m-%d"),
            "units_opened": units_opened,
            "units_closed": units_closed,
            "finds_recorded": finds_today,
            "finds_count": len(finds_today)
        }

    def stats(self) -> Dict[str, float]:
        open_units = sum(1 for u in self.units.values() if u.is_open)
        return {
            "unit_count": len(self.units),
            "open_units": open_units,
            "find_count": len(self.finds),
            "avg_finds_per_unit": len(self.finds) / len(self.units) if self.units else 0.0,
            "find_types": len(self.find_statistics())
        }

def run():
    logger = ExcavationLogger("Site-Java")
    logger.add_unit(ExcavationUnit("U1", 10, 5, "spit 1", 5.0, 4.8, ContextType.LAYER, "dark brown soil"))
    logger.add_unit(ExcavationUnit("U2", 10, 6, "spit 1", 5.0, 4.9, ContextType.FILL, "ash layer"))
    logger.add_find(Find("F1", "U1", FindType.ARTIFACT, "pottery shard", 25, 30, 15, weight_g=45, finder="Alice"))
    logger.add_find(Find("F2", "U1", FindType.ARTIFACT, "stone tool", 40, 20, 12, weight_g=120, finder="Bob"))
    logger.add_find(Find("F3", "U2", FindType.SAMPLE, "charcoal", 10, 10, 5, weight_g=5, finder="Alice"))
    logger.close_unit("U1", datetime(2024, 6, 1, 17, 0, 0))
    print(f"Finds in U1: {len(logger.finds_by_unit('U1'))}")
    print(f"Artifacts: {len(logger.finds_by_type(FindType.ARTIFACT))}")
    print(f"Vertical distribution: {logger.vertical_distribution()}")
    print(logger.daily_report(datetime(2024, 6, 1)))
    print(logger.stats())

if __name__ == "__main__":
    run()
