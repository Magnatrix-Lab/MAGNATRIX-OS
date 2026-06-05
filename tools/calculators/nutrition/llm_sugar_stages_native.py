"""Sugar Stages — thread, soft ball, hard crack, caramelization, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class SugarStages:
    current_temp: float = 100.0

    def thread(self) -> bool:
        return 110 <= self.current_temp < 112

    def soft_ball(self) -> bool:
        return 112 <= self.current_temp < 116

    def firm_ball(self) -> bool:
        return 118 <= self.current_temp < 120

    def hard_ball(self) -> bool:
        return 121 <= self.current_temp < 130

    def soft_crack(self) -> bool:
        return 132 <= self.current_temp < 143

    def hard_crack(self) -> bool:
        return 146 <= self.current_temp < 154

    def caramel(self) -> bool:
        return 160 <= self.current_temp < 182

    def stage(self) -> str:
        if self.thread(): return "thread"
        elif self.soft_ball(): return "soft ball"
        elif self.firm_ball(): return "firm ball"
        elif self.hard_ball(): return "hard ball"
        elif self.soft_crack(): return "soft crack"
        elif self.hard_crack(): return "hard crack"
        elif self.caramel(): return "caramel"
        elif self.current_temp >= 182: return "burnt"
        return "below thread"

    def caramelization_rate(self) -> float:
        if self.current_temp < 160:
            return 0.0
        return (self.current_temp - 160) * 0.01

    def stats(self) -> Dict:
        return {"stage": self.stage(), "caramelization": round(self.caramelization_rate(), 3)}

def run():
    for t in [100, 115, 125, 140, 150, 170, 190]:
        ss = SugarStages(t)
        print(f"{t}°C: {ss.stats()}")

if __name__ == "__main__":
    run()
