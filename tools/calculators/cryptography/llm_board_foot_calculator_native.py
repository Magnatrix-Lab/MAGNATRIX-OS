"""Native stdlib module: Board Foot Calculator
Calculates board feet, lumber costs, and yield estimates.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class BoardFootCalculator:
    thickness_in: float
    width_in: float
    length_ft: float
    price_per_board_foot: float = 4.0

    def board_feet(self) -> float:
        return (self.thickness_in * self.width_in * self.length_ft) / 12

    def cost(self) -> float:
        return self.board_feet() * self.price_per_board_foot

    def linear_feet(self) -> float:
        return self.length_ft

    def square_feet(self) -> float:
        return (self.width_in * self.length_ft) / 12

    def metric_volume_m3(self) -> float:
        return (self.thickness_in * 0.0254) * (self.width_in * 0.0254) * (self.length_ft * 0.3048)

    def yield_from_log(self, log_diameter_in: float, log_length_ft: float) -> float:
        log_radius = log_diameter_in / 2
        log_area_sq_in = 3.14159 * log_radius ** 2
        return (log_area_sq_in * log_length_ft * 12) / 1728

    def stats(self) -> Dict:
        return {
            "board_feet": round(self.board_feet(), 2),
            "cost_usd": round(self.cost(), 2),
            "linear_feet": round(self.linear_feet(), 2),
            "square_feet": round(self.square_feet(), 2),
            "metric_volume_m3": round(self.metric_volume_m3(), 4),
        }

def run():
    bfc = BoardFootCalculator(thickness_in=1, width_in=6, length_ft=8, price_per_board_foot=5)
    print(bfc.stats())

if __name__ == "__main__":
    run()
