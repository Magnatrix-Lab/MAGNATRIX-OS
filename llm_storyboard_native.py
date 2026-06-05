"""Storyboard Planner — panels, timing, composition, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class StoryboardPlanner:
    panels: int = 12
    seconds_per_panel: float = 3.0
    aspect: str = "16:9"

    def total_duration(self) -> float:
        return self.panels * self.seconds_per_panel

    def frame_size(self, base_width: int = 1920) -> Dict:
        ratios = {"16:9": 9/16, "4:3": 3/4, "1:1": 1.0, "2.39:1": 1/2.39}
        return {"width": base_width, "height": int(base_width * ratios.get(self.aspect, 9/16))}

    def panel_allocation(self, scene_types: List[str]) -> List[Dict]:
        if not scene_types:
            return []
        per_scene = math.ceil(self.panels / len(scene_types))
        return [{"scene": s, "panels": min(per_scene, self.panels - i * per_scene)} for i, s in enumerate(scene_types)]

    def stats(self) -> Dict:
        return {"duration_s": round(self.total_duration(), 2), "frame": self.frame_size()}

def run():
    sp = StoryboardPlanner(panels=20, seconds_per_panel=2.5, aspect="2.39:1")
    print(sp.stats())

if __name__ == "__main__":
    run()
