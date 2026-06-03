"""Diffusion Sampler - Diffusion model sampling for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
import random
import math

@dataclass
class DiffusionSampler:
    timesteps: int = 10; beta_start: float = 1e-4; beta_end: float = 0.02
    betas: List[float] = field(default_factory=list)
    alphas: List[float] = field(default_factory=list)

    def __post_init__(self):
        if not self.betas:
            self.betas = [self.beta_start + (self.beta_end - self.beta_start) * i / self.timesteps for i in range(self.timesteps)]
            self.alphas = [1.0 - b for b in self.betas]

    def forward_diffusion(self, x0: List[float], t: int) -> List[float]:
        noise = [random.gauss(0,1) for _ in x0]
        a = self.alphas[t]
        return [math.sqrt(a)*x0[i] + math.sqrt(1-a)*noise[i] for i in range(len(x0))]

    def denoise_step(self, xt: List[float], t: int, predicted_noise: List[float]) -> List[float]:
        a = self.alphas[t]
        return [(xt[i] - math.sqrt(1-a)*predicted_noise[i]) / math.sqrt(a) for i in range(len(xt))]

    def stats(self) -> dict:
        return {"timesteps": self.timesteps, "beta_range": (self.beta_start, self.beta_end)}

def run():
    ds = DiffusionSampler(5)
    x0 = [1.0, 0.5, 0.0]
    xt = ds.forward_diffusion(x0, 2)
    print("Noisy:", [round(v,4) for v in xt])
    print("Stats:", ds.stats())

if __name__ == "__main__": run()
