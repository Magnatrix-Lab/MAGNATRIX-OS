"""Edge Detector - Sobel edge detection for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List
import math

@dataclass
class EdgeDetector:
    threshold: int = 50

    def sobel(self, image: List[List[int]]) -> List[List[int]]:
        h, w = len(image), len(image[0])
        out = [[0]*w for _ in range(h)]
        gx = [[-1,0,1],[-2,0,2],[-1,0,1]]; gy = [[-1,-2,-1],[0,0,0],[1,2,1]]
        for i in range(1,h-1):
            for j in range(1,w-1):
                sx = sum(image[i+di-1][j+dj-1]*gx[di][dj] for di in range(3) for dj in range(3))
                sy = sum(image[i+di-1][j+dj-1]*gy[di][dj] for di in range(3) for dj in range(3))
                out[i][j] = int(math.sqrt(sx*sx + sy*sy))
        return out

    def detect(self, image: List[List[int]]) -> List[List[int]]:
        edges = self.sobel(image)
        return [[255 if e > self.threshold else 0 for e in row] for row in edges]

    def stats(self, image: List[List[int]]) -> dict:
        edges = self.sobel(image)
        flat = [e for row in edges for e in row]
        return {"max_edge": max(flat), "avg_edge": sum(flat)//len(flat)}

def run():
    img = [[0,0,0,0,0],[0,255,255,255,0],[0,255,0,255,0],[0,255,255,255,0],[0,0,0,0,0]]
    ed = EdgeDetector(100)
    print("Edges:", ed.detect(img))
    print("Stats:", ed.stats(img))

if __name__ == "__main__": run()
