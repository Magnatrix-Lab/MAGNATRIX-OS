"""Object Detector - Sliding window detection for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class ObjectDetector:
    window_size: int = 3; stride: int = 1; threshold: float = 0.8

    def template_match(self, image: List[List[int]], template: List[List[int]]) -> List[Tuple[int,int,float]]:
        h, w = len(image), len(image[0])
        th, tw = len(template), len(template[0])
        matches = []
        for i in range(0, h-th+1, self.stride):
            for j in range(0, w-tw+1, self.stride):
                score = sum(image[i+di][j+dj] == template[di][dj] for di in range(th) for dj in range(tw)) / (th*tw)
                if score >= self.threshold:
                    matches.append((i,j,round(score,4)))
        return matches

    def stats(self, image: List[List[int]]) -> dict:
        return {"size": f"{len(image)}x{len(image[0])}", "window": self.window_size}

def run():
    img = [[1,0,0,1],[0,1,1,0],[0,1,1,0],[1,0,0,1]]
    tmpl = [[1,0],[0,1]]
    od = ObjectDetector(2, 1, 0.5)
    print("Matches:", od.template_match(img, tmpl))
    print("Stats:", od.stats(img))

if __name__ == "__main__": run()
