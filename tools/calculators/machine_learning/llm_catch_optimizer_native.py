"""Catch Optimizer — fishing zone allocation, quota tracking, bycatch reduction, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum, auto
from math import sqrt, pow, radians, degrees, sin, cos, atan2, pi, fabs, exp, log
from datetime import datetime, timedelta

class GearType(Enum):
    TRAWL = auto()
    LONGLINE = auto()
    Purse_SEINE = auto()
    GILLNET = auto()
    TRAP = auto()

class SpeciesType(Enum):
    TARGET = auto()
    BYCATCH = auto()
    PROTECTED = auto()

@dataclass
class CatchZone:
    id: str
    lat: float
    lon: float
    depth_m: float
    biomass_index: float  # 0-1 relative abundance
    species_present: List[str] = field(default_factory=list)
    restricted: bool = False

@dataclass
class CatchRecord:
    species: str
    weight_kg: float
    species_type: SpeciesType
    timestamp: datetime
    zone_id: str

@dataclass
class Quota:
    species: str
    total_tons: float
    caught_tons: float = 0.0
    season_start: datetime = field(default_factory=datetime.now)
    season_end: datetime = field(default_factory=datetime.now)

    @property
    def remaining(self) -> float:
        return max(0.0, self.total_tons - self.caught_tons)

    @property
    def utilization(self) -> float:
        return self.caught_tons / self.total_tons if self.total_tons > 0 else 0.0

class CatchOptimizer:
    def __init__(self):
        self.zones: List[CatchZone] = []
        self.quotas: Dict[str, Quota] = {}
        self.records: List[CatchRecord] = []
        self.gear: GearType = GearType.TRAWL

    def add_zone(self, zone: CatchZone) -> None:
        self.zones.append(zone)

    def add_quota(self, quota: Quota) -> None:
        self.quotas[quota.species] = quota

    def add_record(self, record: CatchRecord) -> None:
        self.records.append(record)
        if record.species in self.quotas:
            self.quotas[record.species].caught_tons += record.weight_kg / 1000.0

    def find_best_zones(self, target_species: str, count: int = 3) -> List[CatchZone]:
        candidates = [z for z in self.zones if target_species in z.species_present and not z.restricted]
        candidates.sort(key=lambda z: z.biomass_index, reverse=True)
        return candidates[:count]

    def bycatch_ratio(self, target_species: str) -> float:
        target_weight = sum(r.weight_kg for r in self.records if r.species == target_species and r.species_type == SpeciesType.TARGET)
        bycatch_weight = sum(r.weight_kg for r in self.records if r.species_type == SpeciesType.BYCATCH)
        return bycatch_weight / target_weight if target_weight > 0 else 0.0

    def protected_bycatch_count(self) -> int:
        return sum(1 for r in self.records if r.species_type == SpeciesType.PROTECTED)

    def zone_efficiency(self, zone_id: str) -> float:
        zone_records = [r for r in self.records if r.zone_id == zone_id]
        if not zone_records:
            return 0.0
        total = sum(r.weight_kg for r in zone_records)
        target = sum(r.weight_kg for r in zone_records if r.species_type == SpeciesType.TARGET)
        return target / total if total > 0 else 0.0

    def quota_status(self) -> List[Dict]:
        return [{"species": q.species, "total": q.total_tons, "caught": q.caught_tons, "remaining": q.remaining, "utilization": q.utilization} for q in self.quotas.values()]

    def suggest_trip(self, target_species: str, desired_tons: float) -> Dict:
        zones = self.find_best_zones(target_species)
        total_biomass = sum(z.biomass_index for z in zones)
        plan = []
        for z in zones:
            allocation = desired_tons * (z.biomass_index / total_biomass) if total_biomass > 0 else 0
            plan.append({"zone_id": z.id, "allocation_tons": allocation, "biomass_index": z.biomass_index})
        quota_ok = target_species in self.quotas and self.quotas[target_species].remaining >= desired_tons
        return {"zones": plan, "quota_sufficient": quota_ok, "total_desired": desired_tons}

    def stats(self) -> Dict[str, float]:
        total_catch = sum(r.weight_kg for r in self.records)
        target_catch = sum(r.weight_kg for r in self.records if r.species_type == SpeciesType.TARGET)
        return {
            "zone_count": len(self.zones),
            "quota_count": len(self.quotas),
            "total_catch_kg": total_catch,
            "target_catch_kg": target_catch,
            "bycatch_ratio": self.bycatch_ratio("") if not self.records else 0.0,
            "protected_encounters": self.protected_bycatch_count(),
            "record_count": len(self.records)
        }

def run():
    opt = CatchOptimizer()
    opt.add_zone(CatchZone("Z1", -5.0, 110.0, 50, 0.8, ["tuna", "mackerel"]))
    opt.add_zone(CatchZone("Z2", -6.5, 112.0, 80, 0.6, ["tuna", "shark"]))
    opt.add_zone(CatchZone("Z3", -4.0, 108.0, 30, 0.9, ["tuna", "marlin"]))
    opt.add_quota(Quota("tuna", 100.0))
    opt.add_record(CatchRecord("tuna", 5000, SpeciesType.TARGET, datetime(2024, 6, 1), "Z1"))
    opt.add_record(CatchRecord("shark", 200, SpeciesType.BYCATCH, datetime(2024, 6, 1), "Z1"))
    print(f"Best tuna zones: {[z.id for z in opt.find_best_zones('tuna')]}")
    print(f"Bycatch ratio: {opt.bycatch_ratio('tuna'):.3f}")
    print(f"Quota remaining: {opt.quotas['tuna'].remaining:.1f} tons")
    trip = opt.suggest_trip("tuna", 20.0)
    print(f"Trip suggestion: {trip}")
    print(opt.stats())

if __name__ == "__main__":
    run()
