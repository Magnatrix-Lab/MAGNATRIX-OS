"""Calibration Fitter - Temperature scaling for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict
import math

@dataclass
class CalibrationFitter:
    temperature: float = 1.0

    def fit(self, logits: List[List[float]], labels: List[int]) -> None:
        best_t = 1.0; best_nll = float('inf')
        for t in [0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 3.0, 5.0]:
            nll = 0.0
            for i, logit in enumerate(logits):
                scaled = [l/t for l in logit]
                m = max(scaled)
                exps = [math.exp(s-m) for s in scaled]
                probs = [e/sum(exps) for e in exps]
                nll += -math.log(max(probs[labels[i]], 1e-10))
            if nll < best_nll: best_nll = nll; best_t = t
        self.temperature = best_t

    def calibrate(self, logits: List[float]) -> List[float]:
        scaled = [l/self.temperature for l in logits]
        m = max(scaled)
        exps = [math.exp(s-m) for s in scaled]
        s = sum(exps)
        return [e/s for e in exps]

    def stats(self) -> dict:
        return {"temperature": round(self.temperature, 4)}

def run():
    cf = CalibrationFitter()
    logits = [[2.0, 1.0, 0.1], [0.5, 2.0, 1.0], [1.0, 0.5, 2.0]]
    labels = [0, 1, 2]
    cf.fit(logits, labels)
    print("Calibrated:", [round(p, 4) for p in cf.calibrate([1.0, 2.0, 0.5])])
    print("Stats:", cf.stats())

if __name__ == "__main__": run()
