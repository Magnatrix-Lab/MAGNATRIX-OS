"""Feature Extractor - Image feature extraction for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict
import math

@dataclass
class FeatureExtractor:

    def histogram(self, image: List[List[int]]) -> Dict[int, int]:
        hist = {}
        for row in image:
            for p in row:
                hist[p] = hist.get(p, 0) + 1
        return hist

    def moments(self, image: List[List[int]]) -> Dict[str, float]:
        h, w = len(image), len(image[0])
        m00 = sum(image[i][j] for i in range(h) for j in range(w))
        if m00 == 0: return {}
        m10 = sum(i*image[i][j] for i in range(h) for j in range(w))
        m01 = sum(j*image[i][j] for i in range(h) for j in range(w))
        cx, cy = m10/m00, m01/m00
        return {"area": m00, "cx": round(cx,2), "cy": round(cy,2)}

    def stats(self, image: List[List[int]]) -> dict:
        hist = self.histogram(image)
        return {"bins": len(hist), "moments": self.moments(image)}

def run():
    img = [[0,0,255],[0,255,255],[255,255,255]]
    fe = FeatureExtractor()
    print("Histogram:", fe.histogram(img))
    print("Moments:", fe.moments(img))
    print("Stats:", fe.stats(img))

if __name__ == "__main__": run()
