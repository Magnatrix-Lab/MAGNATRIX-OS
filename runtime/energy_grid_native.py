#!/usr/bin/env python3
"""Energy Grid Management — MAGNATRIX-OS ASI Expansion
Path: runtime/energy_grid_native.py
License: AGPL-3.0
Depends: Python 3.11+ stdlib only.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class EnergySource:
    name: str
    capacity_kw: float
    carbon_g_per_kwh: float
    cost_per_kwh: float
    is_renewable: bool = False


@dataclass
class LoadProfile:
    timestamp: float
    demand_kw: float


class EnergyGrid:
    def __init__(self):
        self.sources: List[EnergySource] = []
        self.load_history: List[LoadProfile] = []
        self.schedule: Dict[str, float] = {}  # source -> allocated kw

    def add_source(self, s: EnergySource) -> None:
        self.sources.append(s)

    def forecast_demand(self, horizon: int = 24) -> List[float]:
        """Simple moving-average forecast."""
        if not self.load_history:
            return [100.0] * horizon
        recent = [lp.demand_kw for lp in self.load_history[-24:]]
        avg = sum(recent) / len(recent)
        # Add daily pattern (peak at noon)
        forecasts = []
        for h in range(horizon):
            hour_factor = 1.0 + 0.3 * math.sin(h * math.pi / 12)
            forecasts.append(avg * hour_factor)
        return forecasts

    def optimize_schedule(self, demand_kw: float) -> Dict[str, any]:
        """Minimize cost with carbon constraint."""
        # Sort by cost, prioritize renewable
        sorted_sources = sorted(self.sources, key=lambda s: (not s.is_renewable, s.cost_per_kwh))
        remaining = demand_kw
        allocation = {}
        total_cost = 0.0
        total_carbon = 0.0
        for s in sorted_sources:
            if remaining <= 0:
                break
            alloc = min(s.capacity_kw, remaining)
            allocation[s.name] = alloc
            remaining -= alloc
            total_cost += alloc * s.cost_per_kwh
            total_carbon += alloc * s.carbon_g_per_kwh
        return {
            "allocation": allocation,
            "total_cost": total_cost,
            "total_carbon": total_carbon,
            "shortfall": remaining,
            "renewable_pct": sum(allocation.get(s.name, 0) for s in self.sources if s.is_renewable) / demand_kw * 100 if demand_kw > 0 else 0,
        }

    def carbon_footprint(self, period_hours: int = 24) -> Dict[str, float]:
        """Estimate carbon over period."""
        demands = self.forecast_demand(period_hours)
        total_carbon = 0.0
        for d in demands:
            sched = self.optimize_schedule(d)
            total_carbon += sched["total_carbon"]
        return {"total_carbon_g": total_carbon, "avg_per_hour": total_carbon / period_hours}


def _self_test():
    print("=" * 55)
    print("Energy Grid — Self Test")
    print("=" * 55)
    passed = 0
    total = 4

    grid = EnergyGrid()
    grid.add_source(EnergySource("solar", 500, 0, 0.05, True))
    grid.add_source(EnergySource("wind", 300, 10, 0.08, True))
    grid.add_source(EnergySource("gas", 1000, 450, 0.15, False))

    grid.load_history = [LoadProfile(i, 400 + 100 * math.sin(i * math.pi / 12)) for i in range(24)]

    sched = grid.optimize_schedule(600)
    print(f"[Test 1] 600kW allocated: solar={sched['allocation'].get('solar',0):.0f}, wind={sched['allocation'].get('wind',0):.0f}, gas={sched['allocation'].get('gas',0):.0f}")
    ok = sched["shortfall"] == 0
    passed += ok

    cf = grid.carbon_footprint(24)
    print(f"[Test 2] Carbon forecast: {cf['total_carbon_g']:.0f}g/day")
    ok2 = cf["total_carbon_g"] > 0
    passed += ok2

    forecast = grid.forecast_demand(4)
    print(f"[Test 3] Forecast length: {len(forecast)} — {'PASS' if len(forecast)==4 else 'FAIL'}")
    passed += (len(forecast) == 4)

    sched2 = grid.optimize_schedule(2000)
    print(f"[Test 4] Over-demand shortfall: {sched2['shortfall']:.0f}kW — {'PASS' if sched2['shortfall']>0 else 'FAIL'}")
    passed += (sched2["shortfall"] > 0)

    print(f"PASS: {passed}/{total}")
    print("=" * 55)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
