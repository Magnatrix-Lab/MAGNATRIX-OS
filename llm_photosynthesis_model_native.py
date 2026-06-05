"""Photosynthesis Model — Farquhar, LUE, CO2 response, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class PhotosynthesisModel:
    vcmax: float = 100.0
    jmax: float = 150.0
    rd: float = 1.0
    co2: float = 400.0
    temp: float = 25.0

    def arrhenius(self, k25: float, ea: float, t: float) -> float:
        import math
        return k25 * math.exp((ea * (t - 25)) / (298.15 * 8.314 * (t + 273.15)))

    def rubisco_limited(self, ci: float = 300.0) -> float:
        import math
        kc = self.arrhenius(404.9, 79.43, self.temp)
        ko = self.arrhenius(278.4, 36.38, self.temp)
        gamma = self.arrhenius(42.75, 37.83, self.temp)
        vcmax_t = self.arrhenius(self.vcmax, 65.33, self.temp)
        return (vcmax_t * (ci - gamma)) / (ci + kc * (1 + 210 / ko))

    def light_limited(self, par: float = 1000.0) -> float:
        import math
        jmax_t = self.arrhenius(self.jmax, 43.54, self.temp)
        theta = 0.7
        alpha = 0.3
        i = alpha * par
        return (i + jmax_t - math.sqrt((i + jmax_t)**2 - 4 * theta * i * jmax_t)) / (2 * theta)

    def net_assimilation(self, par: float = 1000.0, ci: float = 300.0) -> float:
        a_c = self.rubisco_limited(ci)
        a_j = self.light_limited(par)
        return min(a_c, a_j) - self.rd

    def lue(self, par: float = 1000.0) -> float:
        return self.net_assimilation(par) / par if par > 0 else 0.0

    def stats(self, par: float = 1000.0) -> Dict:
        return {"net_assimilation": round(self.net_assimilation(par), 2), "lue": round(self.lue(par), 4)}

def run():
    pm = PhotosynthesisModel(vcmax=80, jmax=120, co2=400, temp=30)
    print(pm.stats())
    print("Rubisco limited:", pm.rubisco_limited())
    print("Light limited:", pm.light_limited())

if __name__ == "__main__":
    run()
