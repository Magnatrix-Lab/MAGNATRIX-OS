"""Image Preprocessor - Basic image processing for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum, auto

class FilterType(Enum):
    GRAYSCALE = auto(); BLUR = auto(); SHARPEN = auto(); INVERT = auto()

@dataclass
class ImagePreprocessor:
    width: int = 8; height: int = 8

    def grayscale(self, image: List[List[List[int]]]) -> List[List[int]]:
        return [[int(0.299*p[0] + 0.587*p[1] + 0.114*p[2]) for p in row] for row in image]

    def invert(self, image: List[List[List[int]]]) -> List[List[List[int]]]:
        return [[[255-c for c in p] for p in row] for row in image]

    def apply(self, image: List[List[List[int]]], filt: FilterType) -> any:
        if filt == FilterType.GRAYSCALE: return self.grayscale(image)
        if filt == FilterType.INVERT: return self.invert(image)
        return image

    def stats(self, image: List[List[List[int]]]) -> dict:
        flat = [c for row in image for p in row for c in p]
        return {"width": len(image[0]), "height": len(image), "avg": sum(flat)//len(flat) if flat else 0}

def run():
    img = [[[255,0,0],[0,255,0]], [[0,0,255],[255,255,255]]]
    proc = ImagePreprocessor()
    print("Gray:", proc.grayscale(img))
    print("Stats:", proc.stats(img))

if __name__ == "__main__": run()
