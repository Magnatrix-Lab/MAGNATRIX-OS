"""Audio Sampler — sampling rate conversion, bit depth, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

class AudioSampler:
    def __init__(self, input_rate: int = 44100, output_rate: int = 22050):
        self.input_rate = input_rate
        self.output_rate = output_rate

    def resample(self, samples: List[float]) -> List[float]:
        ratio = self.output_rate / self.input_rate
        output_len = int(len(samples) * ratio)
        result = []
        for i in range(output_len):
            src_idx = i / ratio
            idx0 = int(src_idx)
            idx1 = min(idx0 + 1, len(samples) - 1)
            frac = src_idx - idx0
            val = samples[idx0] * (1 - frac) + samples[idx1] * frac
            result.append(val)
        return result

    def quantize(self, samples: List[float], bits: int = 8) -> List[int]:
        max_val = 2 ** (bits - 1) - 1
        return [int(max(-max_val, min(max_val, s * max_val))) for s in samples]

    def dequantize(self, samples: List[int], bits: int = 8) -> List[float]:
        max_val = 2 ** (bits - 1) - 1
        return [s / max_val for s in samples]

    def stats(self) -> Dict:
        return {"input_rate": self.input_rate, "output_rate": self.output_rate, "ratio": self.output_rate / self.input_rate}

def run():
    sampler = AudioSampler(44100, 22050)
    samples = [math.sin(2 * math.pi * 440 * t / 44100) for t in range(44100)]
    resampled = sampler.resample(samples)
    quantized = sampler.quantize(samples[:10], 8)
    print("Original:", len(samples), "Resampled:", len(resampled))
    print("Quantized:", quantized)
    print(sampler.stats())

if __name__ == "__main__":
    run()
