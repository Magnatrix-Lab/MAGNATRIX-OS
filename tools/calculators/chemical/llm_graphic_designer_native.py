"""Graphic Designer — layout, composition, golden ratio, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class GraphicDesigner:
    canvas_width_px: int = 1920
    canvas_height_px: int = 1080

    def aspect_ratio(self) -> float:
        return self.canvas_width_px / self.canvas_height_px if self.canvas_height_px > 0 else 0.0

    def golden_sections(self) -> Dict:
        phi = 1.618
        return {"width_major": round(self.canvas_width_px / phi, 1), "height_major": round(self.canvas_height_px / phi, 1)}

    def dpi_scale(self, target_dpi: int = 300) -> float:
        return target_dpi / 72.0

    def print_size_mm(self) -> Dict:
        scale = self.dpi_scale()
        return {"width_mm": round(self.canvas_width_px / scale * 0.03937 * 10, 1), "height_mm": round(self.canvas_height_px / scale * 0.03937 * 10, 1)}

    def stats(self) -> Dict:
        return {"aspect_ratio": round(self.aspect_ratio(), 3), "golden": self.golden_sections()}

def run():
    gd = GraphicDesigner(canvas_width_px=1200, canvas_height_px=800)
    print(gd.stats())

if __name__ == "__main__":
    run()
