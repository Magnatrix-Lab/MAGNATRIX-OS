"""Speaker Diarizer - Speaker segmentation for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math

@dataclass
class SpeakerDiarizer:
    similarity_threshold: float = 0.7
    speakers: Dict[int, List[List[float]]] = field(default_factory=dict)
    next_speaker: int = 0

    def cosine(self, a: List[float], b: List[float]) -> float:
        dot = sum(x*y for x, y in zip(a, b))
        norm = math.sqrt(sum(x*x for x in a)) * math.sqrt(sum(x*x for x in b))
        return dot / norm if norm > 0 else 0

    def add_segment(self, features: List[float]) -> int:
        best_speaker = -1
        best_sim = self.similarity_threshold
        for spk, segs in self.speakers.items():
            avg = [sum(s[i] for s in segs) / len(segs) for i in range(len(features))]
            sim = self.cosine(features, avg)
            if sim > best_sim:
                best_sim = sim
                best_speaker = spk
        if best_speaker == -1:
            self.next_speaker += 1
            best_speaker = self.next_speaker
            self.speakers[best_speaker] = []
        self.speakers[best_speaker].append(features)
        return best_speaker

    def stats(self) -> dict:
        return {"speakers": len(self.speakers), "segments": sum(len(s) for s in self.speakers.values())}

def run():
    sd = SpeakerDiarizer(0.8)
    f1 = [1.0, 0.0, 0.0]
    f2 = [0.9, 0.1, 0.0]
    f3 = [0.0, 1.0, 0.0]
    print("Speaker for f1:", sd.add_segment(f1))
    print("Speaker for f2:", sd.add_segment(f2))
    print("Speaker for f3:", sd.add_segment(f3))
    print("Stats:", sd.stats())

if __name__ == "__main__": run()
