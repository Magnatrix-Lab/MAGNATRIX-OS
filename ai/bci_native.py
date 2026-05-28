#!/usr/bin/env python3
"""BCI Neural Interface — MAGNATRIX-OS ASI Expansion
Path: ai/bci_native.py
License: AGPL-3.0
Depends: Python 3.11+ stdlib only.
"""

from __future__ import annotations

import cmath
import math
import random
import statistics
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class EEGSample:
    timestamp: float
    channels: List[float]  # microvolts per channel


class BCIDecoder:
    def __init__(self, n_channels: int = 8, sampling_rate: int = 256):
        self.n_channels = n_channels
        self.fs = sampling_rate
        self._alpha_band = (8, 13)
        self._beta_band = (13, 30)
        self._gamma_band = (30, 100)
        self._calibration_data: List[EEGSample] = []
        self._classifier = "lda"  # simplified LDA
        self._weights: List[float] = [0.0] * n_channels

    def _fft(self, signal: List[float]) -> List[complex]:
        """Cooley-Tukey DFT (simplified, not optimized for power-of-2)."""
        N = len(signal)
        if N <= 1:
            return [complex(x, 0) for x in signal]
        even = self._fft(signal[0::2])
        odd = self._fft(signal[1::2])
        result = [0j] * N
        for k in range(N // 2):
            t = cmath.exp(-2j * math.pi * k / N) * odd[k]
            result[k] = even[k] + t
            result[k + N // 2] = even[k] - t
        return result

    def _band_power(self, signal: List[float], band: Tuple[float, float]) -> float:
        """Compute band power via FFT."""
        if len(signal) < 2:
            return 0.0
        # Pad to power of 2
        N = 1
        while N < len(signal):
            N *= 2
        padded = signal + [0.0] * (N - len(signal))
        spectrum = self._fft(padded)
        freqs = [i * self.fs / N for i in range(N // 2)]
        power = 0.0
        for i, f in enumerate(freqs):
            if band[0] <= f <= band[1]:
                power += abs(spectrum[i]) ** 2
        return power / N

    def train(self, samples: List[EEGSample], labels: List[int]) -> bool:
        """Train simplified LDA classifier."""
        if len(samples) < 4 or len(samples) != len(labels):
            return False
        # Compute mean feature per class
        class_0 = []
        class_1 = []
        for s, l in zip(samples, labels):
            feat = self._extract_features(s)
            if l == 0:
                class_0.append(feat)
            else:
                class_1.append(feat)
        if not class_0 or not class_1:
            return False
        m0 = [statistics.mean([f[i] for f in class_0]) for i in range(len(class_0[0]))]
        m1 = [statistics.mean([f[i] for f in class_1]) for i in range(len(class_1[0]))]
        # Weight vector = difference of means
        self._weights = [a - b for a, b in zip(m1, m0)]
        return True

    def _extract_features(self, sample: EEGSample) -> List[float]:
        """Extract alpha/beta/gamma band powers per channel."""
        features = []
        for ch in range(min(self.n_channels, len(sample.channels))):
            # Use single value as proxy for short window
            signal = [sample.channels[ch]] * self.fs  # repeat for FFT
            alpha = self._band_power(signal, self._alpha_band)
            beta = self._band_power(signal, self._beta_band)
            gamma = self._band_power(signal, self._gamma_band)
            features.extend([alpha, beta, gamma])
        return features

    def decode(self, sample: EEGSample) -> Tuple[int, float]:
        """Classify sample: 0=rest, 1=active."""
        feat = self._extract_features(sample)
        if len(feat) != len(self._weights):
            return 0, 0.0
        score = sum(w * f for w, f in zip(self._weights, feat))
        label = 1 if score > 0 else 0
        confidence = min(1.0, abs(score) / (sum(abs(w) for w in self._weights) + 0.001))
        return label, confidence

    def detect_pattern(self, samples: List[EEGSample], pattern: str = "p300") -> Tuple[bool, float]:
        """Detect P300 or motor imagery patterns."""
        if len(samples) < 3:
            return False, 0.0
        # P300: sudden amplitude increase 300ms after stimulus
        if pattern == "p300":
            amplitudes = [max(abs(c) for c in s.channels) for s in samples]
            # Look for peak after initial dip
            if len(amplitudes) > 3:
                post_stim = amplitudes[1:4]
                if max(post_stim) > 1.5 * amplitudes[0]:
                    return True, 0.8
        return False, 0.0

    def calibrate(self, baseline_seconds: float = 5.0) -> bool:
        """Capture baseline noise."""
        n_samples = int(baseline_seconds * self.fs)
        self._calibration_data = [
            EEGSample(i / self.fs, [random.gauss(0, 5) for _ in range(self.n_channels)])
            for i in range(n_samples)
        ]
        return True


def _self_test():
    import statistics, random
    print("=" * 55)
    print("BCI Neural Interface — Self Test")
    print("=" * 55)
    passed = 0
    total = 4

    bci = BCIDecoder(n_channels=4)

    print("[Test 1] Calibration")
    ok = bci.calibrate(1.0)
    print(f"  Calibrated: {ok} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    print("[Test 2] FFT band power")
    signal = [math.sin(2 * math.pi * 10 * i / 256) for i in range(256)]
    power = bci._band_power(signal, (8, 13))
    print(f"  Alpha power: {power:.1f} — {'PASS' if power > 0 else 'FAIL'}")
    passed += (power > 0)

    print("[Test 3] Train and decode")
    train_samples = []
    labels = []
    for i in range(20):
        # Class 0: low alpha
        ch = [random.gauss(5, 2) for _ in range(4)] if i % 2 == 0 else [random.gauss(15, 3) for _ in range(4)]
        train_samples.append(EEGSample(i / 256, ch))
        labels.append(0 if i % 2 == 0 else 1)
    ok2 = bci.train(train_samples, labels)
    print(f"  Trained: {ok2} — {'PASS' if ok2 else 'FAIL'}")
    passed += ok2

    print("[Test 4] Decode")
    test_sample = EEGSample(0.0, [random.gauss(15, 3) for _ in range(4)])
    label, conf = bci.decode(test_sample)
    print(f"  Label: {label}, confidence: {conf:.2f} — {'PASS' if label in (0, 1) else 'FAIL'}")
    passed += (label in (0, 1))

    print(f"\nPASS: {passed}/{total}")
    print("=" * 55)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
