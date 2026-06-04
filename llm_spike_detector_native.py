"""Spike Detector — threshold crossing, peak detection, ISI, firing rate, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class SpikeDetector:
    threshold: float = 0.0
    sampling_rate: float = 1000.0

    def detect(self, signal: List[float]) -> List[int]:
        spikes = []
        for i in range(1, len(signal)-1):
            if signal[i] > self.threshold and signal[i] > signal[i-1] and signal[i] > signal[i+1]:
                spikes.append(i)
        return spikes

    def inter_spike_intervals(self, spikes: List[int]) -> List[float]:
        return [(spikes[i+1] - spikes[i]) / self.sampling_rate for i in range(len(spikes)-1)]

    def firing_rate(self, spikes: List[int], duration_sec: float) -> float:
        return len(spikes) / duration_sec if duration_sec > 0 else 0.0

    def coefficient_of_variation(self, isi: List[float]) -> float:
        if not isi:
            return 0.0
        mean = sum(isi) / len(isi)
        std = math.sqrt(sum((x-mean)**2 for x in isi) / len(isi))
        return std / mean if mean > 0 else 0.0

    def stats(self, signal: List[float]) -> Dict:
        spikes = self.detect(signal)
        isi = self.inter_spike_intervals(spikes)
        return {"spikes": len(spikes), "firing_rate": self.firing_rate(spikes, len(signal)/self.sampling_rate), "cv": self.coefficient_of_variation(isi)}

def run():
    sd = SpikeDetector(threshold=0.5)
    sig = [0.1,0.2,0.6,0.3,0.1,0.7,0.2,0.1]
    print("Spikes:", sd.detect(sig))
    print(sd.stats(sig))

if __name__ == "__main__":
    run()
