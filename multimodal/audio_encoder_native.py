#!/usr/bin/env python3
"""
MAGNATRIX-OS | Layer 6 — Audio Encoder
Native audio encoder without librosa/torchaudio.
- Spectrogram via FFT approximation
- Mel-frequency cepstral coefficients (MFCC) native
- Chromagram and zero-crossing rate
- Tempo estimation via autocorrelation
"""
import math, struct, json, time, os, sys, random
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

SAMPLE_RATE = 16000
NFFT = 512
HOP = 256
NUM_MELS = 40
NUM_MFCC = 13


def _hz_to_mel(hz: float) -> float:
    return 2595 * math.log10(1 + hz / 700)


def _mel_to_hz(mel: float) -> float:
    return 700 * (10 ** (mel / 2595) - 1)


def _dft_magnitude(signal: List[float]) -> List[float]:
    n = len(signal)
    mags = []
    for k in range(n // 2 + 1):
        real = sum(signal[t] * math.cos(2 * math.pi * k * t / n) for t in range(n))
        imag = sum(signal[t] * math.sin(2 * math.pi * k * t / n) for t in range(n))
        mags.append(math.sqrt(real * real + imag * imag))
    return mags


def _hamming_window(n: int) -> List[float]:
    return [0.54 - 0.46 * math.cos(2 * math.pi * i / (n - 1)) for i in range(n)]


def _dct2(x: List[float]) -> List[float]:
    n = len(x)
    out = []
    for k in range(NUM_MFCC):
        s = 0.0
        for i in range(n):
            s += x[i] * math.cos(math.pi * k * (i + 0.5) / n)
        out.append(s)
    return out


class MelFilterbank:
    """Build mel-spaced triangular filters."""

    def __init__(self, n_fft: int = NFFT, n_mels: int = NUM_MELS, sr: int = SAMPLE_RATE):
        self.n_fft = n_fft
        self.n_mels = n_mels
        self.sr = sr
        self.filters = self._build()

    def _build(self) -> List[List[float]]:
        low_mel = _hz_to_mel(0)
        high_mel = _hz_to_mel(self.sr // 2)
        points = [_mel_to_hz(low_mel + i * (high_mel - low_mel) / (self.n_mels + 1)) for i in range(self.n_mels + 2)]
        bins = [int(self.n_fft * p / self.sr) for p in points]
        filters = []
        for i in range(1, self.n_mels + 1):
            f = [0.0] * (self.n_fft // 2 + 1)
            for j in range(bins[i - 1], bins[i]):
                if bins[i] - bins[i - 1] > 0:
                    f[j] = (j - bins[i - 1]) / (bins[i] - bins[i - 1])
            for j in range(bins[i], bins[i + 1]):
                if bins[i + 1] - bins[i] > 0:
                    f[j] = (bins[i + 1] - j) / (bins[i + 1] - bins[i])
            filters.append(f)
        return filters

    def apply(self, magnitudes: List[float]) -> List[float]:
        return [sum(m * f for m, f in zip(magnitudes, filt)) for filt in self.filters]


class Spectrogram:
    """Native spectrogram computation."""

    def __init__(self, n_fft: int = NFFT, hop: int = HOP, sr: int = SAMPLE_RATE):
        self.n_fft = n_fft
        self.hop = hop
        self.sr = sr
        self.window = _hamming_window(n_fft)

    def stft(self, signal: List[float]) -> List[List[float]]:
        frames = []
        for i in range(0, len(signal) - self.n_fft, self.hop):
            frame = signal[i:i + self.n_fft]
            if len(frame) < self.n_fft:
                frame += [0.0] * (self.n_fft - len(frame))
            windowed = [frame[j] * self.window[j] for j in range(self.n_fft)]
            mag = _dft_magnitude(windowed)
            frames.append(mag)
        return frames

    def power(self, signal: List[float]) -> List[List[float]]:
        return [[m * m for m in frame] for frame in self.stft(signal)]


class MFCCExtractor:
    """Native MFCC extractor."""

    def __init__(self, sr: int = SAMPLE_RATE, n_mfcc: int = NUM_MFCC, n_mels: int = NUM_MELS, n_fft: int = NFFT, hop: int = HOP):
        self.sr = sr
        self.n_mfcc = n_mfcc
        self.n_fft = n_fft
        self.hop = hop
        self.spectrogram = Spectrogram(n_fft, hop, sr)
        self.mel_fb = MelFilterbank(n_fft, n_mels, sr)

    def extract(self, signal: List[float]) -> List[List[float]]:
        spec = self.spectrogram.stft(signal)
        mfccs = []
        for frame in spec:
            mel_energies = self.mel_fb.apply(frame)
            log_mel = [math.log(max(e, 1e-10)) for e in mel_energies]
            mfcc = _dct2(log_mel)
            mfccs.append(mfcc)
        return mfccs

    def mean_mfcc(self, signal: List[float]) -> List[float]:
        frames = self.extract(signal)
        if not frames:
            return [0.0] * self.n_mfcc
        return [sum(f[i] for f in frames) / len(frames) for i in range(self.n_mfcc)]


class ChromaExtractor:
    """Approximate chromagram (12 pitch classes)."""

    def __init__(self, sr: int = SAMPLE_RATE):
        self.sr = sr
        self.notes = [261.63 * (2 ** (i / 12)) for i in range(12)]  # C4 chromatic scale

    def extract(self, signal: List[float]) -> List[float]:
        # Simple energy around each pitch class
        energies = [0.0] * 12
        for i in range(0, len(signal) - 1024, 512):
            frame = signal[i:i + 1024]
            mag = _dft_magnitude(frame)
            for note_idx, freq in enumerate(self.notes):
                bin_idx = int(len(mag) * freq / (self.sr / 2))
                if 0 <= bin_idx < len(mag):
                    energies[note_idx] += mag[bin_idx]
        norm = sum(energies) + 1e-9
        return [e / norm for e in energies]


class TempoEstimator:
    """Estimate tempo (BPM) via autocorrelation of onset envelope."""

    def __init__(self, sr: int = SAMPLE_RATE):
        self.sr = sr

    def _onset_envelope(self, signal: List[float]) -> List[float]:
        env = []
        for i in range(0, len(signal) - 512, 256):
            frame = signal[i:i + 512]
            mag = _dft_magnitude(frame)
            env.append(sum(mag) / len(mag))
        return env

    def _autocorr(self, x: List[float]) -> List[float]:
        n = len(x)
        mean = sum(x) / n
        x = [v - mean for v in x]
        out = []
        for lag in range(1, min(n // 2, 200)):
            c = sum(x[i] * x[i + lag] for i in range(n - lag))
            out.append((lag, c))
        return out

    def estimate(self, signal: List[float]) -> float:
        env = self._onset_envelope(signal)
        if len(env) < 10:
            return 0.0
        ac = self._autocorr(env)
        if not ac:
            return 0.0
        best_lag, best_c = max(ac, key=lambda t: t[1])
        hop_sec = 256 / self.sr
        period_sec = best_lag * hop_sec
        if period_sec > 0:
            bpm = 60 / period_sec
            return round(min(max(bpm, 30), 300), 1)
        return 0.0


class AudioEncoder:
    """Full audio encoder combining all features."""

    def __init__(self, target_dim: int = 128):
        self.target_dim = target_dim
        self.mfcc = MFCCExtractor()
        self.chroma = ChromaExtractor()
        self.tempo = TempoEstimator()

    def encode(self, signal: List[float]) -> List[float]:
        # MFCC mean
        m = self.mfcc.mean_mfcc(signal)
        # Chroma
        c = self.chroma.extract(signal)
        # Tempo
        bpm = self.tempo.estimate(signal)
        # Zero-crossing rate
        zcr = sum(1 for i in range(1, len(signal)) if signal[i - 1] * signal[i] < 0) / max(len(signal), 1)
        # Energy stats
        energy = sum(abs(s) for s in signal) / max(len(signal), 1)
        peak = max(abs(s) for s in signal) if signal else 0.0
        combined = m + c + [bpm / 300, zcr, energy, peak]
        # Pad to 64
        combined += [0.0] * (64 - len(combined))
        # Project to target_dim
        rng = random.Random(42)
        proj = [[rng.gauss(0, 1) / 8 for _ in range(64)] for _ in range(self.target_dim)]
        out = [sum(combined[i] * proj[j][i] for i in range(64)) for j in range(self.target_dim)]
        out = [max(0.0, v) for v in out]
        norm = math.sqrt(sum(v * v for v in out)) + 1e-9
        return [v / norm for v in out]

    def encode_batch(self, signals: List[List[float]]) -> List[List[float]]:
        return [self.encode(s) for s in signals]


# ─── SELF TESTS ───
if __name__ == "__main__":
    def _sine(freq: float, sec: float, sr: int = SAMPLE_RATE) -> List[float]:
        return [math.sin(2 * math.pi * freq * i / sr) for i in range(int(sr * sec))]

    def _chord(freqs: List[float], sec: float, sr: int = SAMPLE_RATE) -> List[float]:
        samples = int(sr * sec)
        return [sum(math.sin(2 * math.pi * f * i / sr) for f in freqs) / len(freqs) for i in range(samples)]

    tests = []
    def _t(name, fn):
        tests.append((name, fn))

    sig = _sine(440, 0.1)
    _t("spectrogram", lambda: len(Spectrogram().stft(sig)) > 0)
    _t("mfcc_extract", lambda: len(MFCCExtractor().extract(sig)) > 0)
    _t("mfcc_mean", lambda: len(MFCCExtractor().mean_mfcc(sig)) == NUM_MFCC)
    _t("chroma", lambda: len(ChromaExtractor().extract(sig)) == 12)
    _t("tempo", lambda: TempoEstimator().estimate(sig) >= 0)
    _t("audio_encode", lambda: len(AudioEncoder(64).encode(sig)) == 64)
    _t("audio_batch", lambda: len(AudioEncoder(32).encode_batch([sig, sig])) == 2)
    _t("chord_chroma", lambda: ChromaExtractor().extract(_chord([261.63, 329.63, 392.00], 0.1)))
    _t("mel_filterbank", lambda: len(MelFilterbank().apply([1.0] * (NFFT // 2 + 1))) == NUM_MELS)
    _t("normalize", lambda: abs(AudioEncoder(16).encode(sig)[0]) <= 1.0)

    passed = 0
    for name, fn in tests:
        try:
            ok = fn()
            print(f"  {'PASS' if ok else 'FAIL'} {name}")
            if ok:
                passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
    print(f"\nAudio Encoder: {passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)
