"""Balance Optimizer — DPS, HP, economy, power scaling, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class BalanceOptimizer:
    dps: float = 10.0
    hp: float = 100.0
    defense: float = 5.0

    def time_to_kill(self, target_hp: float = 100.0, target_def: float = 5.0) -> float:
        effective_dps = max(0.1, self.dps - target_def * 0.5)
        return target_hp / effective_dps

    def survivability(self, incoming_dps: float = 10.0) -> float:
        effective_incoming = max(0.1, incoming_dps - self.defense * 0.5)
        return self.hp / effective_incoming

    def power_score(self) -> float:
        return math.sqrt(self.dps * self.hp) + self.defense

    def stats(self) -> Dict:
        return {"ttk_s": round(self.time_to_kill(), 2), "survivability_s": round(self.survivability(), 2), "power": round(self.power_score(), 2)}

def run():
    bo = BalanceOptimizer(dps=15, hp=120, defense=8)
    print(bo.stats())

if __name__ == "__main__":
    run()
