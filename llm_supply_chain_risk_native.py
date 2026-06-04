"""Supply Chain Risk — disruption, resilience scoring, alternative sourcing, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto

class SupplyChainRisk:
    def __init__(self):
        self.suppliers: Dict[str, Dict] = {}
        self.risks: List[Dict] = []

    def add_supplier(self, supplier_id: str, reliability: float, lead_time: float, country_risk: float = 0.1):
        self.suppliers[supplier_id] = {"reliability": reliability, "lead_time": lead_time, "country_risk": country_risk, "alternatives": []}

    def add_alternative(self, supplier_id: str, alt_id: str):
        if supplier_id in self.suppliers:
            self.suppliers[supplier_id]["alternatives"].append(alt_id)

    def risk_score(self, supplier_id: str) -> float:
        s = self.suppliers.get(supplier_id, {})
        return (1 - s.get("reliability", 1)) * 0.4 + (s.get("country_risk", 0)) * 0.3 + (s.get("lead_time", 0) / 100) * 0.3

    def network_risk(self) -> float:
        if not self.suppliers:
            return 0.0
        return sum(self.risk_score(sid) for sid in self.suppliers) / len(self.suppliers)

    def find_alternatives(self, supplier_id: str) -> List[str]:
        return self.suppliers.get(supplier_id, {}).get("alternatives", [])

    def critical_path(self, dependencies: List[List[str]]) -> List[str]:
        # Simple longest chain by risk
        return max(dependencies, key=lambda chain: sum(self.risk_score(s) for s in chain)) if dependencies else []

    def stats(self) -> Dict:
        return {"suppliers": len(self.suppliers), "network_risk": self.network_risk(), "high_risk": len([s for s in self.suppliers if self.risk_score(s) > 0.5])}

def run():
    scr = SupplyChainRisk()
    scr.add_supplier("S1", 0.8, 30, 0.2)
    scr.add_supplier("S2", 0.95, 15, 0.05)
    scr.add_alternative("S1", "S2")
    print("S1 risk:", scr.risk_score("S1"))
    print("Network risk:", scr.network_risk())
    print(scr.stats())

if __name__ == "__main__":
    run()
