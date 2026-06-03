"""Signal Denoiser - Noise reduction for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List
from enum import Enum, auto
import math

class DenoiseMethod(Enum):
    THRESHOLD = auto(); MOVING_AVG = auto(); MEDIAN = auto()

@dataclass
class SignalDenoiser:
    method: DenoiseMethod = DenoiseMethod.THRESHOLD
    threshold: float = 0.5; window: int = 3

    def denoise(self, signal: List[float]) -> List[float]:
        if self.method == DenoiseMethod.THRESHOLD:
            return [0.0 if abs(x) < self.threshold else x for x in signal]
        if self.method == DenoiseMethod.MOVING_AVG:
            return [sum(signal[max(0,i-self.window+1):i+1])/len(signal[max(0,i-self.window+1):i+1]) for i in range(len(signal))]
        if self.method == DenoiseMethod.MEDIAN:
            return [sorted(signal[max(0,i-self.window//2):min(len(signal),i+self.window//2+1)])[len(signal[max(0,i-self.window//2):min(len(signal),i+self.window//2+1)])//2] for i in range(len(signal))]
        return signal

    def stats(self, signal: List[float]) -> dict:
        denoised = self.denoise(signal)
        mse = sum((s-d)**2 for s,d in zip(signal, denoised))/len(signal)
        return {"method": self.method.name, "mse": round(mse,4)}

def run():
    sd = SignalDenoiser(DenoiseMethod.MEDIAN, window=3)
    signal = [1.0, 1.1, 5.0, 1.2, 1.0, 0.9, 1.1]
    print("Denoised:", [round(v,4) for v in sd.denoise(signal)])
    print("Stats:", sd.stats(signal))

if __name__ == "__main__": run()
