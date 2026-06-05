"""Color Matcher — RGB, HSV, CMYK, palette, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class Color:
    r: int
    g: int
    b: int

    def to_hex(self) -> str:
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"

    def to_hsv(self) -> Tuple[float, float, float]:
        r, g, b = self.r/255, self.g/255, self.b/255
        mx = max(r, g, b)
        mn = min(r, g, b)
        df = mx - mn
        if mx == mn:
            h = 0
        elif mx == r:
            h = (60 * ((g - b) / df) + 360) % 360
        elif mx == g:
            h = (60 * ((b - r) / df) + 120) % 360
        else:
            h = (60 * ((r - g) / df) + 240) % 360
        s = 0 if mx == 0 else df / mx
        return h, s, mx

    def to_cmyk(self) -> Tuple[float, float, float, float]:
        r, g, b = self.r/255, self.g/255, self.b/255
        k = 1 - max(r, g, b)
        c = (1 - r - k) / (1 - k) if k < 1 else 0
        m = (1 - g - k) / (1 - k) if k < 1 else 0
        y = (1 - b - k) / (1 - k) if k < 1 else 0
        return c, m, y, k

class ColorMatcher:
    def distance(self, a: Color, b: Color) -> float:
        return math.sqrt((a.r-b.r)**2 + (a.g-b.g)**2 + (a.b-b.b)**2)

    def complementary(self, c: Color) -> Color:
        h, s, v = c.to_hsv()
        new_h = (h + 180) % 360
        return self._from_hsv(new_h, s, v)

    def triadic(self, c: Color) -> List[Color]:
        h, s, v = c.to_hsv()
        return [self._from_hsv((h + 120) % 360, s, v), self._from_hsv((h + 240) % 360, s, v)]

    def _from_hsv(self, h: float, s: float, v: float) -> Color:
        c = v * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = v - c
        if h < 60: r, g, b = c, x, 0
        elif h < 120: r, g, b = x, c, 0
        elif h < 180: r, g, b = 0, c, x
        elif h < 240: r, g, b = 0, x, c
        elif h < 300: r, g, b = x, 0, c
        else: r, g, b = c, 0, x
        return Color(int((r+m)*255), int((g+m)*255), int((b+m)*255))

    def stats(self, c: Color) -> Dict:
        return {"hex": c.to_hex(), "hsv": c.to_hsv(), "cmyk": c.to_cmyk()}

def run():
    cm = ColorMatcher()
    c = Color(255, 100, 50)
    print(cm.stats(c))
    print("Complementary:", cm.complementary(c).to_hex())
    print("Triadic:", [x.to_hex() for x in cm.triadic(c)])

if __name__ == "__main__":
    run()
