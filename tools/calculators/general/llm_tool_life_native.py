"""Tool Life Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class ToolLife:
    cutting_speed_m_per_min: float
    tool_material: str = "hss"
    work_material: str = "steel"
    feed_mm_per_rev: float = 0.2

    def taylor_exponent(self) -> float:
        exponents = {"hss": 0.125, "carbide": 0.25, "ceramic": 0.5, "cbn": 0.3, "diamond": 0.4}
        return exponents.get(self.tool_material, 0.125)

    def reference_speed_m_per_min(self) -> float:
        refs = {"hss": 50, "carbide": 200, "ceramic": 400, "cbn": 300, "diamond": 600}
        return refs.get(self.tool_material, 50)

    def reference_tool_life_min(self) -> float:
        return 60.0

    def tool_life_min(self) -> float:
        n = self.taylor_exponent()
        v_ref = self.reference_speed_m_per_min()
        t_ref = self.reference_tool_life_min()
        if self.cutting_speed_m_per_min <= 0 or v_ref <= 0:
            return 0.0
        return round(t_ref * (v_ref / self.cutting_speed_m_per_min) ** (1 / n), 1)

    def tool_life_part_count(self, cutting_time_per_part_min: float = 5.0) -> int:
        life = self.tool_life_min()
        if cutting_time_per_part_min <= 0:
            return 0
        return int(life / cutting_time_per_part_min)

    def wear_rate_mm_per_min(self) -> float:
        life = self.tool_life_min()
        if life <= 0:
            return 0.0
        return round(0.3 / life, 6)

    def cost_per_part(self, tool_cost: float = 50.0, cutting_time_per_part_min: float = 5.0) -> float:
        count = self.tool_life_part_count(cutting_time_per_part_min)
        if count <= 0:
            return 0.0
        return round(tool_cost / count, 3)

    def optimal_speed_m_per_min(self) -> float:
        return round(self.reference_speed_m_per_min() * 0.8, 1)

    def stats(self) -> Dict[str, float]:
        return {
            "tool_life_min": self.tool_life_min(),
            "tool_life_part_count": self.tool_life_part_count(),
            "wear_rate_mm_per_min": self.wear_rate_mm_per_min(),
        }

    def run(self):
        print("=" * 60)
        print("TOOL LIFE CALCULATOR")
        print("=" * 60)
        tl = ToolLife(
            cutting_speed_m_per_min=250, tool_material="carbide", work_material="steel", feed_mm_per_rev=0.25
        )
        print(f"Speed: {tl.cutting_speed_m_per_min} m/min")
        print(f"Tool: {tl.tool_material}")
        print(f"Taylor exponent: {tl.taylor_exponent():.3f}")
        print(f"Tool life: {tl.tool_life_min():.1f} min")
        print(f"Parts (5 min/part): {tl.tool_life_part_count()}")
        print(f"Wear rate: {tl.wear_rate_mm_per_min():.6f} mm/min")
        print(f"Cost/part: ${tl.cost_per_part():.3f}")
        print(f"Optimal speed: {tl.optimal_speed_m_per_min():.1f} m/min")
        print(f"Stats: {tl.stats()}")

if __name__ == "__main__":
    ToolLife(0).run()
