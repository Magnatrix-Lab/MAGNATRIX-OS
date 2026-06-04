"""Object Tracker - Simple tracking by detection for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math

@dataclass
class BoundingBox:
    x: float; y: float; w: float; h: float; label: str = ""

    def iou(self, other: "BoundingBox") -> float:
        ix = max(0, min(self.x + self.w, other.x + other.w) - max(self.x, other.x))
        iy = max(0, min(self.y + self.h, other.y + other.h) - max(self.y, other.y))
        inter = ix * iy
        union = self.w * self.h + other.w * other.h - inter
        return inter / union if union > 0 else 0

@dataclass
class ObjectTracker:
    tracks: Dict[int, BoundingBox] = field(default_factory=dict)
    next_id: int = 0

    def update(self, detections: List[BoundingBox]) -> Dict[int, BoundingBox]:
        matched = set()
        for track_id, track in list(self.tracks.items()):
            best_iou = 0.5
            best_det = None
            for det in detections:
                if det in matched: continue
                iou = track.iou(det)
                if iou > best_iou:
                    best_iou = iou
                    best_det = det
            if best_det:
                self.tracks[track_id] = best_det
                matched.add(best_det)
        for det in detections:
            if det not in matched:
                self.next_id += 1
                self.tracks[self.next_id] = det
        return self.tracks

    def stats(self) -> dict:
        return {"tracks": len(self.tracks), "next_id": self.next_id}

def run():
    ot = ObjectTracker()
    d1 = [BoundingBox(10, 10, 20, 20, "car"), BoundingBox(50, 50, 20, 20, "ped")]
    ot.update(d1)
    d2 = [BoundingBox(11, 11, 20, 20, "car"), BoundingBox(51, 51, 20, 20, "ped")]
    ot.update(d2)
    print("Tracks:", len(ot.tracks))
    print("Stats:", ot.stats())

if __name__ == "__main__": run()
