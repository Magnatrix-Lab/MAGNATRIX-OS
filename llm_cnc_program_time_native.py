"""CNC Program Time Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class Move:
    distance_mm: float
    feed_mm_per_min: float
    rapid: bool = False

@dataclass
class CNCProgramTime:
    moves: List[Move]
    tool_changes: int = 2
    setup_time_min: float = 15.0
    rapids_feed_mm_per_min: float = 5000.0

    def rapid_time_min(self) -> float:
        total = 0.0
        for move in self.moves:
            if move.rapid and move.feed_mm_per_min > 0:
                total += move.distance_mm / self.rapids_feed_mm_per_min
        return round(total, 2)

    def cutting_time_min(self) -> float:
        total = 0.0
        for move in self.moves:
            if not move.rapid and move.feed_mm_per_min > 0:
                total += move.distance_mm / move.feed_mm_per_min
        return round(total, 2)

    def tool_change_time_min(self, change_time_sec: float = 10.0) -> float:
        return round(self.tool_changes * change_time_sec / 60.0, 2)

    def total_cycle_time_min(self) -> float:
        return round(self.rapid_time_min() + self.cutting_time_min() + self.tool_change_time_min() + self.setup_time_min, 2)

    def parts_per_hour(self) -> float:
        cycle = self.total_cycle_time_min()
        if cycle <= 0:
            return 0.0
        return round(60 / cycle, 2)

    def utilization_percent(self) -> float:
        total = self.total_cycle_time_min()
        if total <= 0:
            return 0.0
        return round(self.cutting_time_min() / total * 100, 2)

    def cost_per_part(self, machine_rate_per_h: float = 50.0) -> float:
        return round(self.total_cycle_time_min() / 60.0 * machine_rate_per_h, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "cutting_time_min": self.cutting_time_min(),
            "total_cycle_time_min": self.total_cycle_time_min(),
            "parts_per_hour": self.parts_per_hour(),
        }

    def run(self):
        print("=" * 60)
        print("CNC PROGRAM TIME CALCULATOR")
        print("=" * 60)
        moves = [
            Move(100, 500, rapid=True), Move(50, 200, rapid=False),
            Move(200, 300, rapid=False), Move(100, 500, rapid=True)
        ]
        cnc = CNCProgramTime(moves, tool_changes=2, setup_time_min=10)
        print(f"Moves: {len(cnc.moves)}")
        print(f"Rapid time: {cnc.rapid_time_min():.2f} min")
        print(f"Cutting time: {cnc.cutting_time_min():.2f} min")
        print(f"Tool change: {cnc.tool_change_time_min():.2f} min")
        print(f"Total cycle: {cnc.total_cycle_time_min():.2f} min")
        print(f"Parts/hour: {cnc.parts_per_hour():.2f}")
        print(f"Utilization: {cnc.utilization_percent():.2f}%")
        print(f"Cost/part: ${cnc.cost_per_part():.2f}")
        print(f"Stats: {cnc.stats()}")

if __name__ == "__main__":
    CNCProgramTime([]).run()
