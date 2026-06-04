"""Image Segmenter - Region growing segmentation for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Set
from enum import Enum, auto
from collections import deque

@dataclass
class ImageSegmenter:
    threshold: float = 10.0

    def segment(self, image: List[List[int]], seed: Tuple[int, int]) -> Set[Tuple[int, int]]:
        h, w = len(image), len(image[0])
        visited = set()
        queue = deque([seed])
        visited.add(seed)
        seed_val = image[seed[0]][seed[1]]
        region = {seed}
        while queue:
            i, j = queue.popleft()
            for di, dj in [(-1,0),(1,0),(0,-1),(0,1)]:
                ni, nj = i + di, j + dj
                if 0 <= ni < h and 0 <= nj < w and (ni, nj) not in visited:
                    if abs(image[ni][nj] - seed_val) <= self.threshold:
                        visited.add((ni, nj))
                        region.add((ni, nj))
                        queue.append((ni, nj))
        return region

    def stats(self, image: List[List[int]], seed: Tuple[int, int]) -> dict:
        region = self.segment(image, seed)
        return {"region_size": len(region), "threshold": self.threshold}

def run():
    seg = ImageSegmenter(5)
    img = [[0,0,0,255,255],[0,0,0,255,255],[0,0,0,255,255],[255,255,255,255,255],[255,255,255,255,255]]
    region = seg.segment(img, (1, 1))
    print("Region size:", len(region))
    print("Stats:", seg.stats(img, (1, 1)))

if __name__ == "__main__": run()
