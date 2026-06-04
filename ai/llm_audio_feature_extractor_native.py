"""Audio Feature Extractor - MFCC-like features for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math

@dataclass
class AudioFeatureExtractor:
    n_mfcc: int = 13
    frame_size: int = 256

    def extract_energy(self, frame: List[float]) -> float:
        return sum(x*x for x in frame) / len(frame) if frame else 0

    def extract_zero_crossing_rate(self, frame: List[float]) -> float:
        if len(frame) < 2: return 0
        return sum(1 for i in range(len(frame)-1) if frame[i]*frame[i+1] < 0) / (len(frame)-1)

    def extract_features(self, audio: List[float]) -> List[Dict]:
        features = []
        for i in range(0, len(audio), self.frame_size):
            frame = audio[i:i+self.frame_size]
            if len(frame) < self.frame_size: break
            features.append({
                "energy": self.extract_energy(frame),
                "zcr": self.extract_zero_crossing_rate(frame)
            })
        return features

    def stats(self, audio: List[float]) -> dict:
        features = self.extract_features(audio)
        return {"frames": len(features), "avg_energy": round(sum(f["energy"] for f in features)/len(features), 4) if features else 0}

def run():
    afe = AudioFeatureExtractor(13, 10)
    audio = [math.sin(2*math.pi*440*i/8000) for i in range(100)]
    features = afe.extract_features(audio)
    print("Features:", len(features))
    print("Stats:", afe.stats(audio))

if __name__ == "__main__": run()
