"""Renewable Energy Planner — solar, wind, storage sizing, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto

class RenewableEnergyPlanner:
    def __init__(self, demand: float = 1000):
        self.demand = demand
        self.solar_capacity = 0.0
        self.wind_capacity = 0.0
        self.storage_capacity = 0.0
        self.solar_profile: List[float] = []
        self.wind_profile: List[float] = []

    def set_solar_profile(self, hourly: List[float]):
        self.solar_profile = hourly

    def set_wind_profile(self, hourly: List[float]):
        self.wind_profile = hourly

    def size_system(self, solar_fraction: float = 0.6, wind_fraction: float = 0.4, storage_hours: float = 4):
        avg_solar = sum(self.solar_profile) / len(self.solar_profile) if self.solar_profile else 0.5
        avg_wind = sum(self.wind_profile) / len(self.wind_profile) if self.wind_profile else 0.3
        self.solar_capacity = self.demand * solar_fraction / (avg_solar + 1e-6)
        self.wind_capacity = self.demand * wind_fraction / (avg_wind + 1e-6)
        self.storage_capacity = self.demand * storage_hours
        return {"solar_kw": self.solar_capacity, "wind_kw": self.wind_capacity, "storage_kwh": self.storage_capacity}

    def generation(self, hour: int) -> float:
        solar_gen = self.solar_capacity * (self.solar_profile[hour % len(self.solar_profile)] if self.solar_profile else 0.5)
        wind_gen = self.wind_capacity * (self.wind_profile[hour % len(self.wind_profile)] if self.wind_profile else 0.3)
        return solar_gen + wind_gen

    def match_demand(self, hours: int = 24) -> List[float]:
        return [self.generation(h) - self.demand for h in range(hours)]

    def stats(self) -> Dict:
        return {"demand": self.demand, "solar": self.solar_capacity, "wind": self.wind_capacity, "storage": self.storage_capacity}

def run():
    rep = RenewableEnergyPlanner(500)
    rep.set_solar_profile([0, 0, 0, 0, 0, 0.1, 0.3, 0.5, 0.7, 0.8, 0.9, 1.0, 1.0, 0.9, 0.8, 0.6, 0.4, 0.2, 0.1, 0, 0, 0, 0, 0])
    rep.set_wind_profile([0.5, 0.6, 0.7, 0.6, 0.5, 0.4, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.4, 0.5, 0.6, 0.7, 0.6, 0.5, 0.5])
    print(rep.size_system())
    print(rep.stats())

if __name__ == "__main__":
    run()
