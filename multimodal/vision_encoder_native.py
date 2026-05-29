#!/usr/bin/env python3
"""
MAGNATRIX-OS | Layer 6 — Vision Encoder
Native image encoder without OpenCV/PIL (pure Python buffer ops).
- RAW RGB pixel statistics as features
- Haar-like feature approximation (integral image)
- Histogram of Oriented Gradients (HOG) approximation
- SIFT-like keypoint descriptor simulation
"""
import math, struct, json, hashlib, time, os, sys, random
from typing import List, Dict, Optional, Tuple
from collections import defaultdict, Counter


class RawImageBuffer:
    """Minimal image buffer representation (width, height, RGB list)."""

    def __init__(self, width: int, height: int, pixels: List[Tuple[int, int, int]]):
        self.width = width
        self.height = height
        self.pixels = pixels

    def __getitem__(self, xy: Tuple[int, int]) -> Tuple[int, int, int]:
        x, y = xy
        idx = y * self.width + x
        return self.pixels[idx] if 0 <= idx < len(self.pixels) else (0, 0, 0)

    @classmethod
    def from_gradient(cls, w: int, h: int):
        """Create a synthetic gradient image for testing."""
        pixels = []
        for y in range(h):
            for x in range(w):
                r = int(255 * x / max(w - 1, 1))
                g = int(255 * y / max(h - 1, 1))
                b = 128
                pixels.append((r, g, b))
        return cls(w, h, pixels)

    @classmethod
    def from_noise(cls, w: int, h: int, seed: int = 42):
        rng = random.Random(seed)
        pixels = [(rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255)) for _ in range(w * h)]
        return cls(w, h, pixels)


class IntegralImage:
    """Integral image for fast rectangular feature summation."""

    def __init__(self, img: RawImageBuffer, channel: int = 0):
        self.w = img.width
        self.h = img.height
        self._integral = [[0.0] * (self.w + 1) for _ in range(self.h + 1)]
        for y in range(self.h):
            row_sum = 0.0
            for x in range(self.w):
                row_sum += img[x, y][channel]
                self._integral[y + 1][x + 1] = self._integral[y][x + 1] + row_sum

    def rect_sum(self, x: int, y: int, w: int, h: int) -> float:
        """Sum of rectangle using integral image."""
        x1, y1 = x, y
        x2, y2 = x + w, y + h
        return (
            self._integral[y2][x2] - self._integral[y1][x2]
            - self._integral[y2][x1] + self._integral[y1][x1]
        )

    def haar_features(self, img: RawImageBuffer) -> List[float]:
        """Extract Haar-like features (edge/line/rectangle)."""
        features = []
        step_x = max(1, self.w // 8)
        step_y = max(1, self.h // 8)
        for y in range(0, self.h - step_y, step_y):
            for x in range(0, self.w - step_x, step_x):
                # Horizontal edge feature
                left = self.rect_sum(x, y, step_x // 2, step_y)
                right = self.rect_sum(x + step_x // 2, y, step_x // 2, step_y)
                features.append(left - right)
                # Vertical edge feature
                top = self.rect_sum(x, y, step_x, step_y // 2)
                bottom = self.rect_sum(x, y + step_y // 2, step_x, step_y // 2)
                features.append(top - bottom)
        return features


class HOGApproximation:
    """Approximate HOG features using gradient histograms."""

    def __init__(self, bins: int = 9, cell_size: int = 8):
        self.bins = bins
        self.cell_size = cell_size

    def _gradient(self, img: RawImageBuffer, x: int, y: int) -> Tuple[float, float]:
        """Simple central difference gradient."""
        dx = (img[min(x + 1, img.width - 1), y][0] - img[max(x - 1, 0), y][0]) / 2.0
        dy = (img[x, min(y + 1, img.height - 1)][0] - img[x, max(y - 1, 0)][0]) / 2.0
        return dx, dy

    def _angle_bin(self, dx: float, dy: float) -> int:
        angle = math.degrees(math.atan2(dy, dx)) % 180
        return int(angle / (180 / self.bins)) % self.bins

    def extract(self, img: RawImageBuffer) -> List[float]:
        cells_x = img.width // self.cell_size
        cells_y = img.height // self.cell_size
        histograms = []
        for cy in range(cells_y):
            for cx in range(cells_x):
                hist = [0.0] * self.bins
                for y in range(cy * self.cell_size, (cy + 1) * self.cell_size):
                    for x in range(cx * self.cell_size, (cx + 1) * self.cell_size):
                        dx, dy = self._gradient(img, x, y)
                        mag = math.sqrt(dx * dx + dy * dy)
                        b = self._angle_bin(dx, dy)
                        hist[b] += mag
                histograms.extend(hist)
        # Normalize
        norm = math.sqrt(sum(h * h for h in histograms)) + 1e-9
        return [h / norm for h in histograms]


class KeypointDescriptor:
    """SIFT-like keypoint descriptor simulation."""

    def __init__(self, patch_size: int = 16):
        self.patch_size = patch_size

    def extract(self, img: RawImageBuffer, x: int, y: int) -> List[float]:
        """Extract descriptor around a keypoint."""
        half = self.patch_size // 2
        desc = []
        for dy in range(-half, half, 4):
            for dx in range(-half, half, 4):
                px = min(max(x + dx, 0), img.width - 1)
                py = min(max(y + dy, 0), img.height - 1)
                # Simple gradient stats in 4x4 sub-region
                gx_list = []
                gy_list = []
                for sy in range(4):
                    for sx in range(4):
                        ix = min(px + sx, img.width - 1)
                        iy = min(py + sy, img.height - 1)
                        grad_x = (img[min(ix + 1, img.width - 1), iy][0] - img[max(ix - 1, 0), iy][0]) / 2.0
                        grad_y = (img[ix, min(iy + 1, img.height - 1)][0] - img[ix, max(iy - 1, 0)][0]) / 2.0
                        gx_list.append(abs(grad_x))
                        gy_list.append(abs(grad_y))
                desc.append(sum(gx_list) / len(gx_list))
                desc.append(sum(gy_list) / len(gy_list))
        # Normalize
        norm = math.sqrt(sum(d * d for d in desc)) + 1e-9
        return [d / norm for d in desc]

    def detect_keypoints(self, img: RawImageBuffer, max_points: int = 20) -> List[Tuple[int, int]]:
        """Simple corner detection via gradient magnitude."""
        points = []
        for y in range(2, img.height - 2, 4):
            for x in range(2, img.width - 2, 4):
                dx = (img[x + 1, y][0] - img[x - 1, y][0]) / 2.0
                dy = (img[x, y + 1][0] - img[x, y - 1][0]) / 2.0
                mag = dx * dx + dy * dy
                points.append((mag, x, y))
        points.sort(reverse=True)
        return [(x, y) for _, x, y in points[:max_points]]


class VisionEncoder:
    """Full vision encoder combining features."""

    def __init__(self, target_dim: int = 512):
        self.target_dim = target_dim
        self.hog = HOGApproximation()
        self.keypoint = KeypointDescriptor()

    def encode(self, img: RawImageBuffer) -> List[float]:
        """Encode image into fixed-size vector."""
        # Color statistics
        r_vals = [p[0] for p in img.pixels]
        g_vals = [p[1] for p in img.pixels]
        b_vals = [p[2] for p in img.pixels]
        color_stats = [
            sum(r_vals) / len(r_vals), max(r_vals) - min(r_vals),
            sum(g_vals) / len(g_vals), max(g_vals) - min(g_vals),
            sum(b_vals) / len(b_vals), max(b_vals) - min(b_vals),
        ]
        # HOG
        hog_feats = self.hog.extract(img)
        # Keypoint descriptors (concatenate top few)
        kps = self.keypoint.detect_keypoints(img, max_points=5)
        kp_desc = []
        for x, y in kps:
            kp_desc.extend(self.keypoint.extract(img, x, y)[:20])  # truncate for efficiency
        # Combine and project to target_dim
        combined = color_stats + hog_feats[:100] + kp_desc[:100]
        combined += [0.0] * (256 - len(combined))  # pad to 256
        # Random projection to target_dim
        rng = random.Random(42)
        proj = [[rng.gauss(0, 1) / 16 for _ in range(256)] for _ in range(self.target_dim)]
        out = [sum(combined[i] * proj[j][i] for i in range(256)) for j in range(self.target_dim)]
        # ReLU + normalize
        out = [max(0.0, v) for v in out]
        norm = math.sqrt(sum(v * v for v in out)) + 1e-9
        return [v / norm for v in out]

    def encode_batch(self, images: List[RawImageBuffer]) -> List[List[float]]:
        return [self.encode(img) for img in images]


# ─── SELF TESTS ───
if __name__ == "__main__":
    tests = []
    def _t(name, fn):
        tests.append((name, fn))

    img = RawImageBuffer.from_gradient(64, 64)
    _t("buffer_access", lambda: img[0, 0] == (0, 0, 128))
    _t("integral_sum", lambda: IntegralImage(img).rect_sum(0, 0, 10, 10) > 0)
    _t("haar_features", lambda: len(IntegralImage(img).haar_features(img)) > 0)
    _t("hog_extract", lambda: len(HOGApproximation().extract(img)) > 0)
    _t("keypoint_detect", lambda: len(KeypointDescriptor().detect_keypoints(img)) > 0)
    _t("keypoint_desc", lambda: len(KeypointDescriptor().extract(img, 32, 32)) > 0)
    _t("vision_encode", lambda: len(VisionEncoder(128).encode(img)) == 128)
    _t("vision_batch", lambda: len(VisionEncoder(64).encode_batch([img, img])) == 2)
    _t("noise_image", lambda: len(VisionEncoder(32).encode(RawImageBuffer.from_noise(32, 32))) == 32)
    _t("normalize", lambda: abs(VisionEncoder(16).encode(img)[0]) <= 1.0)

    passed = 0
    for name, fn in tests:
        try:
            ok = fn()
            print(f"  {'PASS' if ok else 'FAIL'} {name}")
            if ok:
                passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
    print(f"\nVision Encoder: {passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)
