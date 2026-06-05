"""Style Transfer — color mapping, texture, histogram, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class StyleTransfer:
    def histogram_match(self, source: List[int], target: List[int]) -> List[int]:
        if not source or not target:
            return source
        src_hist = {}
        tgt_hist = {}
        for v in source:
            src_hist[v] = src_hist.get(v, 0) + 1
        for v in target:
            tgt_hist[v] = tgt_hist.get(v, 0) + 1
        src_cdf = {}
        cum = 0
        for v in sorted(src_hist):
            cum += src_hist[v]
            src_cdf[v] = cum
        tgt_cdf = {}
        cum = 0
        for v in sorted(tgt_hist):
            cum += tgt_hist[v]
            tgt_cdf[v] = cum
        result = []
        for v in source:
            src_rank = src_cdf.get(v, 0) / len(source)
            closest = min(tgt_cdf.keys(), key=lambda x: abs(tgt_cdf[x] / len(target) - src_rank))
            result.append(closest)
        return result

    def color_palette(self, pixels: List[Tuple[int, int, int]], n: int = 5) -> List[Tuple[int, int, int]]:
        if not pixels:
            return []
        buckets = {}
        for r, g, b in pixels:
            key = (r // 51 * 51, g // 51 * 51, b // 51 * 51)
            buckets[key] = buckets.get(key, 0) + 1
        sorted_buckets = sorted(buckets.items(), key=lambda x: x[1], reverse=True)
        return [k for k, v in sorted_buckets[:n]]

    def brightness_adjust(self, pixels: List[int], target_mean: float) -> List[int]:
        if not pixels:
            return []
        mean = sum(pixels) / len(pixels)
        shift = target_mean - mean
        return [max(0, min(255, int(p + shift))) for p in pixels]

    def stats(self, pixels: List[int]) -> Dict:
        if not pixels:
            return {}
        return {"mean": sum(pixels) / len(pixels), "min": min(pixels), "max": max(pixels)}

def run():
    st = StyleTransfer()
    src = [10, 20, 30, 40, 50]
    tgt = [100, 110, 120, 130, 140]
    print("Matched:", st.histogram_match(src, tgt))
    print("Palette:", st.color_palette([(255,0,0),(255,0,0),(0,255,0),(0,0,255),(128,128,128)]))
    print("Adjusted:", st.brightness_adjust([50,60,70], 100))

if __name__ == "__main__":
    run()
