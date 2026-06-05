"""Panorama Stitcher — overlap, alignment, blending, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class PanoramaStitcher:
    images: List[List[List[int]]] = field(default_factory=list)
    """List of images, each image is 2D list of pixel values"""

    def overlap_region(self, img1: List[List[int]], img2: List[List[int]], overlap_pct: float = 0.3) -> int:
        return int(len(img1[0]) * overlap_pct)

    def find_shift(self, img1: List[List[int]], img2: List[List[int]], max_shift: int = 50) -> int:
        best_shift = 0
        best_score = float('inf')
        w1 = len(img1[0]) if img1 else 0
        w2 = len(img2[0]) if img2 else 0
        for shift in range(-max_shift, max_shift + 1):
            score = 0
            overlap = min(w1, w2 + shift) - max(0, shift)
            if overlap <= 0:
                continue
            for row in range(min(len(img1), len(img2))):
                for col in range(max(0, shift), min(w1, w2 + shift)):
                    score += abs(img1[row][col] - img2[row][col - shift])
            if score < best_score:
                best_score = score
                best_shift = shift
        return best_shift

    def blend_linear(self, a: float, b: float, alpha: float) -> float:
        return a * alpha + b * (1 - alpha)

    def stitch_width(self, images: List[List[List[int]]], overlap: float = 0.3) -> int:
        if not images:
            return 0
        total = len(images[0][0]) if images[0] else 0
        for i in range(1, len(images)):
            total += int(len(images[i][0]) * (1 - overlap)) if images[i] else 0
        return total

    def stats(self) -> Dict:
        return {"images": len(self.images), "estimated_width": self.stitch_width(self.images) if self.images else 0}

def run():
    ps = PanoramaStitcher()
    img1 = [[1,2,3,4,5],[1,2,3,4,5]]
    img2 = [[4,5,6,7,8],[4,5,6,7,8]]
    print("Shift:", ps.find_shift(img1, img2))
    print("Stitch width:", ps.stitch_width([img1, img2]))
    print(ps.stats())

if __name__ == "__main__":
    run()
