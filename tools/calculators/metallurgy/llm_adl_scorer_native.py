"""ADL Scorer -- Katz, IADL, functional independence, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class ADLScorer:
    katz_items: Dict[str, bool] = field(default_factory=dict)
    iadl_items: Dict[str, bool] = field(default_factory=dict)

    def katz_score(self) -> int:
        return sum(1 for v in self.katz_items.values() if v)

    def katz_index(self) -> str:
        s = self.katz_score()
        if s == 6: return "A - independent"
        elif s >= 4: return "B - slight dependence"
        elif s >= 2: return "C - moderate dependence"
        return "D - severe dependence"

    def iadl_score(self) -> int:
        return sum(1 for v in self.iadl_items.values() if v)

    def iadl_level(self) -> str:
        s = self.iadl_score()
        if s == 8: return "independent"
        elif s >= 6: return "mild dependence"
        elif s >= 4: return "moderate dependence"
        elif s >= 2: return "severe dependence"
        return "total dependence"

    def overall_function(self) -> str:
        katz = self.katz_score()
        iadl = self.iadl_score()
        if katz == 6 and iadl >= 6: return "independent"
        elif katz >= 4 and iadl >= 4: return "semi-independent"
        elif katz >= 2: return "dependent with assistance"
        return "fully dependent"

    def improvement_target(self) -> List[str]:
        return [k for k, v in self.katz_items.items() if not v] + [k for k, v in self.iadl_items.items() if not v]

    def stats(self) -> Dict:
        return {"katz": self.katz_score(), "iadl": self.iadl_score(), "function": self.overall_function()}

def run():
    adl = ADLScorer(
        katz_items={"bathing": True, "dressing": True, "toileting": True, "transfer": False, "continence": True, "feeding": True},
        iadl_items={"phone": True, "shopping": True, "food prep": False, "housekeeping": False, "laundry": False, "transport": True, "medication": True, "finances": True}
    )
    print(adl.stats())
    print("Targets:", adl.improvement_target())

if __name__ == "__main__":
    run()
