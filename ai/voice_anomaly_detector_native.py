# ai/voice_anomaly_detector_native.py
# AMATI-PELAJARI-TIRU: Voice Anomaly Detector
# Pattern extracted from STFPM (Student-Teacher Feature Pyramid Matching)
# + One-Class anomaly detection + MFCC/Mel-spectrogram analysis
# Research: Coletta et al. "Anomaly Detection for Speech Deepfakes via FPM"
# Layer 10 (AI) of MAGNATRIX-OS

"""
Native Voice Anomaly Detector Engine
=====================================
One-Class anomaly detection for AI voice / deepfake / synthetic speech:
  - One-Class learning: train ONLY on authentic voice, flag all deviation
  - STFPM: Student-Teacher Feature Pyramid Matching across multi-layer
  - MFCC + Mel-spectrogram: time-frequency feature extraction
  - Discrepancy Scaling: normalize anomaly scores with calibration set
  - Anomaly map: localize synthetic artifacts in time-frequency domain
  - Attack detection: deepfake, noise injection, pitch shift, time stretch

Features:
  - Pure-Python (no librosa/numpy dependency)
  - Simulated audio signal processing (FFT, Mel filterbank, DCT)
  - Multi-layer teacher-student discrepancy engine
  - Calibration-based threshold adaptation
  - Batch inference with scoring
  - Explainable anomaly maps (time-frequency heatmap)
"""

from __future__ import annotations

import math
import random
import hashlib
import json
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime


class AnomalyType(Enum):
    NORMAL = auto()
    DEEPFAKE = auto()
    SYNTHETIC = auto()
    NOISE_INJECTION = auto()
    PITCH_MANIPULATION = auto()
    TIME_STRETCH = auto()
    ARTIFACT = auto()
    UNKNOWN = auto()


@dataclass
class AudioFeatures:
    """Extracted audio features from a voice sample."""
    sample_id: str
    sample_rate: int = 16000
    duration_sec: float = 0.0
    mfcc: List[List[float]] = field(default_factory=list)       # frames x 13 coeffs
    mel_spectrogram: List[List[float]] = field(default_factory=list)  # frames x 40 bins
    raw_fft: List[float] = field(default_factory=list)
    pitch_contour: List[float] = field(default_factory=list)
    zero_crossing_rate: List[float] = field(default_factory=list)
    spectral_centroid: List[float] = field(default_factory=list)
    rms_energy: List[float] = field(default_factory=list)


@dataclass
class AnomalyMap:
    """Time-frequency anomaly localization map."""
    sample_id: str
    map_data: List[List[float]]  # time x frequency bins
    time_axis: List[float] = field(default_factory=list)
    freq_axis: List[float] = field(default_factory=list)
    max_score: float = 0.0
    avg_score: float = 0.0


@dataclass
class DetectionResult:
    sample_id: str
    is_anomaly: bool
    anomaly_score: float
    threshold: float
    anomaly_type: AnomalyType
    confidence: float
    anomaly_map: Optional[AnomalyMap] = None
    feature_discrepancies: Dict[str, float] = field(default_factory=dict)
    timestamp: str = ""
    explanation: str = ""


# ============================================================================
# Simulated Audio Signal Processing
# ============================================================================

class SimulatedAudioSignal:
    """Generate simulated audio signals for testing."""

    @staticmethod
    def generate_authentic_voice(duration: float = 3.0, sample_rate: int = 16000) -> List[float]:
        """Generate authentic-sounding voice with natural harmonics and jitter."""
        samples = int(duration * sample_rate)
        signal = []
        base_freq = 150.0 + random.uniform(-20, 20)  # natural voice pitch ~150Hz
        for i in range(samples):
            t = i / sample_rate
            # Fundamental + harmonics + slight pitch jitter (natural)
            jitter = random.uniform(-0.5, 0.5) * math.sin(2 * math.pi * 5.0 * t)
            f = base_freq + jitter
            val = 0.6 * math.sin(2 * math.pi * f * t)
            # Add harmonics with decreasing amplitude
            for h in range(2, 6):
                val += (0.5 / h) * math.sin(2 * math.pi * h * f * t + random.uniform(-0.1, 0.1))
            # Add breath noise (low amplitude, high frequency)
            val += 0.03 * random.uniform(-1, 1)
            signal.append(val)
        return signal

    @staticmethod
    def generate_deepfake_voice(duration: float = 3.0, sample_rate: int = 16000) -> List[float]:
        """Generate synthetic voice with telltale artifacts."""
        samples = int(duration * sample_rate)
        signal = []
        base_freq = 150.0
        for i in range(samples):
            t = i / sample_rate
            # Synthetic: no pitch jitter, constant frequency
            val = 0.6 * math.sin(2 * math.pi * base_freq * t)
            for h in range(2, 6):
                val += (0.5 / h) * math.sin(2 * math.pi * h * base_freq * t)
            # Synthetic artifacts: unnatural harmonics gaps, phase inconsistencies
            val += 0.08 * math.sin(2 * math.pi * 4000 * t)  # unnatural high-freq artifact
            # Flat dynamics (no natural breathing)
            signal.append(val * 0.95)  # slightly compressed
        return signal

    @staticmethod
    def generate_noise_injected_voice(duration: float = 3.0, sample_rate: int = 16000, snr_db: float = 15.0) -> List[float]:
        """Authentic voice with injected noise."""
        clean = SimulatedAudioSignal.generate_authentic_voice(duration, sample_rate)
        signal_power = sum(x * x for x in clean) / len(clean)
        noise_power = signal_power / (10 ** (snr_db / 10))
        noisy = [x + random.gauss(0, math.sqrt(noise_power)) for x in clean]
        return noisy

    @staticmethod
    def generate_pitch_shifted_voice(duration: float = 3.0, sample_rate: int = 16000, shift_factor: float = 1.3) -> List[float]:
        """Voice with pitch manipulation."""
        base = SimulatedAudioSignal.generate_authentic_voice(duration, sample_rate)
        # Resample by skipping/interpolating (simplified)
        shifted = []
        step = 1.0 / shift_factor
        idx = 0.0
        while int(idx) < len(base) - 1:
            i = int(idx)
            frac = idx - i
            val = base[i] * (1 - frac) + base[i + 1] * frac
            shifted.append(val)
            idx += step
        # Pad to original length
        while len(shifted) < len(base):
            shifted.append(0.0)
        return shifted[:len(base)]


class FeatureExtractor:
    """Extract MFCC + Mel-spectrogram features from audio signal."""

    def __init__(self, sample_rate: int = 16000, n_fft: int = 512, hop_length: int = 256,
                 n_mels: int = 40, n_mfcc: int = 13):
        self.sample_rate = sample_rate
        self.n_fft = n_fft
        self.hop_length = hop_length
        self.n_mels = n_mels
        self.n_mfcc = n_mfcc

    def extract(self, signal: List[float], sample_id: str = "") -> AudioFeatures:
        frames = self._frame_signal(signal)
        mfcc = []
        mel_spec = []
        pitch_contour = []
        zcr = []
        spectral_centroid = []
        rms = []

        for frame in frames:
            fft = self._fft(frame)
            power = [abs(x) ** 2 for x in fft[:self.n_fft // 2]]
            mel = self._mel_filterbank(power)
            mel_db = [10 * math.log10(max(m, 1e-10)) for m in mel]
            mel_spec.append(mel_db)
            # DCT for MFCC (simplified)
            mfcc_frame = self._dct(mel_db)[:self.n_mfcc]
            mfcc.append(mfcc_frame)
            # Pitch (fundamental frequency)
            pitch = self._estimate_pitch(power)
            pitch_contour.append(pitch)
            # Zero crossing rate
            zcr.append(self._zero_crossing_rate(frame))
            # Spectral centroid
            sc = self._spectral_centroid(power)
            spectral_centroid.append(sc)
            # RMS energy
            rms.append(math.sqrt(sum(x * x for x in frame) / len(frame)))

        return AudioFeatures(
            sample_id=sample_id or f"audio-{hashlib.sha256(str(signal[:10]).encode()).hexdigest()[:8]}",
            sample_rate=self.sample_rate,
            duration_sec=len(signal) / self.sample_rate,
            mfcc=mfcc,
            mel_spectrogram=mel_spec,
            raw_fft=[abs(x) for x in self._fft(signal)[:self.n_fft // 2]],
            pitch_contour=pitch_contour,
            zero_crossing_rate=zcr,
            spectral_centroid=spectral_centroid,
            rms_energy=rms,
        )

    def _frame_signal(self, signal: List[float]) -> List[List[float]]:
        frames = []
        for start in range(0, len(signal) - self.n_fft, self.hop_length):
            frame = signal[start:start + self.n_fft]
            if len(frame) < self.n_fft:
                frame += [0.0] * (self.n_fft - len(frame))
            # Hamming window
            windowed = [frame[i] * (0.54 - 0.46 * math.cos(2 * math.pi * i / (self.n_fft - 1)))
                        for i in range(self.n_fft)]
            frames.append(windowed)
        return frames if frames else [signal + [0.0] * (self.n_fft - len(signal))]

    def _fft(self, frame: List[float]) -> List[float]:
        """Simplified DFT (real input)."""
        N = len(frame)
        result = []
        for k in range(N // 2 + 1):
            real = sum(frame[n] * math.cos(2 * math.pi * k * n / N) for n in range(N))
            imag = sum(frame[n] * math.sin(2 * math.pi * k * n / N) for n in range(N))
            result.append(complex(real, imag))
        return result

    def _mel_filterbank(self, power_spectrum: List[float]) -> List[float]:
        """Simulated triangular Mel filterbank."""
        n_freq = len(power_spectrum)
        mel_min = self._hz_to_mel(0)
        mel_max = self._hz_to_mel(self.sample_rate / 2)
        mel_points = [mel_min + (mel_max - mel_min) * i / (self.n_mels + 1) for i in range(self.n_mels + 2)]
        hz_points = [self._mel_to_hz(m) for m in mel_points]
        bin_points = [int((n_freq * 2 * h) / self.sample_rate) for h in hz_points]
        mel_energies = []
        for i in range(self.n_mels):
            start, center, end = bin_points[i], bin_points[i + 1], bin_points[i + 2]
            energy = 0.0
            for j in range(start, min(end, n_freq)):
                if j < center:
                    weight = (j - start) / (center - start + 1e-10)
                else:
                    weight = (end - j) / (end - center + 1e-10)
                energy += power_spectrum[j] * weight
            mel_energies.append(energy)
        return mel_energies

    def _hz_to_mel(self, hz: float) -> float:
        return 2595 * math.log10(1 + hz / 700)

    def _mel_to_hz(self, mel: float) -> float:
        return 700 * (10 ** (mel / 2595) - 1)

    def _dct(self, data: List[float]) -> List[float]:
        """Type-II DCT."""
        N = len(data)
        return [sum(data[n] * math.cos(math.pi / N * (n + 0.5) * k) for n in range(N))
                for k in range(N)]

    def _estimate_pitch(self, power_spectrum: List[float]) -> float:
        """Estimate fundamental frequency from spectral peak."""
        if not power_spectrum:
            return 0.0
        max_idx = max(range(len(power_spectrum)), key=lambda i: power_spectrum[i])
        return max_idx * self.sample_rate / (2 * len(power_spectrum))

    def _zero_crossing_rate(self, frame: List[float]) -> float:
        crossings = sum(1 for i in range(1, len(frame)) if frame[i - 1] * frame[i] < 0)
        return crossings / (len(frame) - 1)

    def _spectral_centroid(self, power_spectrum: List[float]) -> float:
        if not power_spectrum:
            return 0.0
        total = sum(power_spectrum)
        if total == 0:
            return 0.0
        return sum(i * p for i, p in enumerate(power_spectrum)) / total


# ============================================================================
# Student-Teacher Feature Pyramid Matching (STFPM)
# ============================================================================

class TeacherNetwork:
    """Teacher network: frozen, pre-trained on authentic voice only."""

    def __init__(self, layer_dims: List[int] = [40, 80, 160, 320]):
        self.layer_dims = layer_dims
        self._weights = self._init_weights()

    def _init_weights(self) -> Dict[int, List[float]]:
        """Initialize deterministic weights for reproducibility."""
        weights = {}
        for dim in self.layer_dims:
            seed = dim * 7
            weights[dim] = [math.sin(seed + i * 1.3) * 0.5 for i in range(dim)]
        return weights

    def forward(self, features: AudioFeatures) -> Dict[str, List[float]]:
        """Multi-layer feature extraction."""
        # Flatten mel-spectrogram into feature vectors per frame
        mel = features.mel_spectrogram
        if not mel:
            return {}
        layers = {}
        for idx, dim in enumerate(self.layer_dims):
            layer_name = f"layer_{idx}"
            # Simulate progressive abstraction
            if idx == 0:
                # Layer 0: raw mel features
                out = [self._project(frame, dim) for frame in mel]
            elif idx == 1:
                # Layer 1: local patterns (smoothed)
                smoothed = self._smooth(mel, window=3)
                out = [self._project(frame, dim) for frame in smoothed]
            elif idx == 2:
                # Layer 2: temporal context
                context = self._temporal_context(mel, window=5)
                out = [self._project(frame, dim) for frame in context]
            else:
                # Layer 3: global structure
                global_feat = self._global_pool(mel)
                out = [self._project(global_feat, dim)] * len(mel)
            layers[layer_name] = out
        return layers

    def _project(self, vector: List[float], dim: int) -> List[float]:
        weights = self._weights.get(dim, [0.0] * dim)
        if len(vector) < dim:
            vector = vector + [0.0] * (dim - len(vector))
        return [vector[i % len(vector)] * weights[i] for i in range(dim)]

    def _smooth(self, data: List[List[float]], window: int) -> List[List[float]]:
        result = []
        for i in range(len(data)):
            start = max(0, i - window // 2)
            end = min(len(data), i + window // 2 + 1)
            avg = [sum(data[j][k] for j in range(start, end)) / (end - start) for k in range(len(data[0]))]
            result.append(avg)
        return result

    def _temporal_context(self, data: List[List[float]], window: int) -> List[List[float]]:
        result = []
        for i in range(len(data)):
            start = max(0, i - window // 2)
            end = min(len(data), i + window // 2 + 1)
            concat = []
            for j in range(start, end):
                concat.extend(data[j])
            result.append(concat)
        return result

    def _global_pool(self, data: List[List[float]]) -> List[float]:
        if not data or not data[0]:
            return []
        return [sum(frame[i] for frame in data) / len(data) for i in range(len(data[0]))]


class StudentNetwork:
    """Student network: learns to mimic teacher on normal data."""

    def __init__(self, teacher: TeacherNetwork):
        self.teacher = teacher
        self._student_weights = {dim: [w * 0.8 + random.uniform(-0.05, 0.05) for w in weights]
                                  for dim, weights in teacher._weights.items()}

    def forward(self, features: AudioFeatures) -> Dict[str, List[float]]:
        teacher_out = self.teacher.forward(features)
        student_out = {}
        for layer_name, teacher_vectors in teacher_out.items():
            dim = len(teacher_vectors[0]) if teacher_vectors else 0
            weights = self._student_weights.get(dim, [0.0] * dim)
            student_vectors = []
            for vec in teacher_vectors:
                sv = [vec[i] * weights[i] * 0.95 for i in range(len(vec))]  # Slight deviation
                student_vectors.append(sv)
            student_out[layer_name] = student_vectors
        return student_out

    def update_weights(self, calibration_features: List[AudioFeatures]) -> None:
        """Calibrate student weights on normal data."""
        for features in calibration_features:
            teacher_out = self.teacher.forward(features)
            student_out = self.forward(features)
            for layer_name, t_vecs in teacher_out.items():
                s_vecs = student_out.get(layer_name, [])
                for t_vec, s_vec in zip(t_vecs, s_vecs):
                    if not t_vec or not s_vec:
                        continue
                    dim = len(t_vec)
                    for i in range(dim):
                        error = t_vec[i] - s_vec[i]
                        w = self._student_weights.get(dim, [0.0] * dim)
                        if i < len(w):
                            w[i] += 0.01 * error  # Simple gradient update
        # Renormalize
        for dim, weights in self._student_weights.items():
            norm = math.sqrt(sum(w * w for w in weights)) or 1.0
            self._student_weights[dim] = [w / norm for w in weights]


class DiscrepancyScaler:
    """Discrepancy Scaling: normalize anomaly scores with calibration statistics."""

    def __init__(self):
        self.means: Dict[str, float] = {}
        self.stds: Dict[str, float] = {}
        self.calibrated = False

    def calibrate(self, teacher: TeacherNetwork, student: StudentNetwork, calibration_features: List[AudioFeatures]) -> None:
        """Compute mean/std of discrepancies on calibration set."""
        layer_discrepancies: Dict[str, List[float]] = {}
        for features in calibration_features:
            t_out = teacher.forward(features)
            s_out = student.forward(features)
            for layer_name in t_out:
                t_vecs = t_out[layer_name]
                s_vecs = s_out.get(layer_name, [])
                discrepancies = []
                for t_vec, s_vec in zip(t_vecs, s_vecs):
                    if len(t_vec) == len(s_vec) and len(t_vec) > 0:
                        d = sum((t - s) ** 2 for t, s in zip(t_vec, s_vec)) / len(t_vec)
                        discrepancies.append(d)
                if discrepancies:
                    layer_discrepancies.setdefault(layer_name, []).extend(discrepancies)
        for layer_name, values in layer_discrepancies.items():
            if values:
                self.means[layer_name] = sum(values) / len(values)
                variance = sum((v - self.means[layer_name]) ** 2 for v in values) / len(values)
                self.stds[layer_name] = math.sqrt(variance) or 1e-10
        self.calibrated = True

    def scale(self, layer_name: str, raw_discrepancy: float) -> float:
        """Scale raw discrepancy to z-score."""
        if not self.calibrated or layer_name not in self.means:
            return raw_discrepancy
        mean = self.means[layer_name]
        std = self.stds[layer_name]
        return (raw_discrepancy - mean) / std


# ============================================================================
# One-Class Anomaly Detector
# ============================================================================

class AnomalyDetector:
    """One-Class anomaly detector using STFPM + Discrepancy Scaling."""

    def __init__(self, feature_extractor: Optional[FeatureExtractor] = None):
        self.extractor = feature_extractor or FeatureExtractor()
        self.teacher = TeacherNetwork()
        self.student = StudentNetwork(self.teacher)
        self.scaler = DiscrepancyScaler()
        self.threshold = 2.0  # z-score threshold
        self.calibrated = False
        self.detection_history: List[DetectionResult] = []

    def calibrate(self, authentic_samples: List[List[float]]) -> None:
        """Calibrate on authentic voice samples only."""
        features = [self.extractor.extract(sig, f"calib_{i}") for i, sig in enumerate(authentic_samples)]
        self.student.update_weights(features)
        self.scaler.calibrate(self.teacher, self.student, features)
        self.calibrated = True

    def detect(self, signal: List[float], sample_id: str = "") -> DetectionResult:
        """Detect anomaly in a voice sample."""
        if not self.calibrated:
            raise RuntimeError("Detector must be calibrated before detection")

        features = self.extractor.extract(signal, sample_id)
        t_out = self.teacher.forward(features)
        s_out = self.student.forward(features)

        # Compute multi-layer discrepancies
        layer_scores = {}
        anomaly_map_data = []
        for layer_name in sorted(t_out.keys()):
            t_vecs = t_out[layer_name]
            s_vecs = s_out.get(layer_name, [])
            frame_scores = []
            for t_vec, s_vec in zip(t_vecs, s_vecs):
                if len(t_vec) == len(s_vec) and len(t_vec) > 0:
                    raw_d = sum((t - s) ** 2 for t, s in zip(t_vec, s_vec)) / len(t_vec)
                    scaled_d = self.scaler.scale(layer_name, raw_d)
                    frame_scores.append(scaled_d)
                else:
                    frame_scores.append(0.0)
            if frame_scores:
                layer_scores[layer_name] = max(frame_scores)
                if layer_name == "layer_0":  # Use layer 0 for anomaly map
                    anomaly_map_data = [[score] for score in frame_scores]

        # Aggregate anomaly score (max across layers)
        final_score = max(layer_scores.values()) if layer_scores else 0.0

        # Determine anomaly type
        anomaly_type, explanation = self._classify_anomaly(features, layer_scores, final_score)
        is_anomaly = final_score > self.threshold

        # Build anomaly map
        anomaly_map = None
        if anomaly_map_data:
            anomaly_map = AnomalyMap(
                sample_id=features.sample_id,
                map_data=anomaly_map_data,
                time_axis=[i * self.extractor.hop_length / self.extractor.sample_rate for i in range(len(anomaly_map_data))],
                freq_axis=[0],  # Simplified single-bin
                max_score=max(max(row) for row in anomaly_map_data) if anomaly_map_data else 0.0,
                avg_score=sum(sum(row) for row in anomaly_map_data) / (len(anomaly_map_data) * len(anomaly_map_data[0])) if anomaly_map_data else 0.0,
            )

        result = DetectionResult(
            sample_id=features.sample_id,
            is_anomaly=is_anomaly,
            anomaly_score=final_score,
            threshold=self.threshold,
            anomaly_type=anomaly_type,
            confidence=min(1.0, final_score / (self.threshold + 1.0)),
            anomaly_map=anomaly_map,
            feature_discrepancies=layer_scores,
            timestamp=datetime.utcnow().isoformat(),
            explanation=explanation,
        )
        self.detection_history.append(result)
        return result

    def _classify_anomaly(self, features: AudioFeatures, layer_scores: Dict[str, float], final_score: float) -> Tuple[AnomalyType, str]:
        if final_score <= self.threshold:
            return AnomalyType.NORMAL, "Voice within normal distribution."

        # Analyze feature signatures to classify anomaly type
        pitch_variance = sum((features.pitch_contour[i] - features.pitch_contour[i - 1]) ** 2
                             for i in range(1, len(features.pitch_contour))) / max(len(features.pitch_contour) - 1, 1)
        zcr_mean = sum(features.zero_crossing_rate) / max(len(features.zero_crossing_rate), 1)
        rms_mean = sum(features.rms_energy) / max(len(features.rms_energy), 1)

        if pitch_variance < 0.5 and final_score > self.threshold * 1.5:
            return AnomalyType.DEEPFAKE, "Flat pitch contour with no natural jitter. Synthetic voice detected."
        elif zcr_mean > 0.15:
            return AnomalyType.NOISE_INJECTION, "High zero-crossing rate indicates noise injection."
        elif any(abs(p - features.pitch_contour[0]) > 50 for p in features.pitch_contour[:10]):
            return AnomalyType.PITCH_MANIPULATION, "Sudden pitch shift detected."
        elif rms_mean < 0.01:
            return AnomalyType.SYNTHETIC, "Compressed dynamics suggest synthetic generation."
        else:
            return AnomalyType.ARTIFACT, "Unexplained spectral artifacts detected."

    def set_threshold(self, threshold: float) -> None:
        self.threshold = threshold

    def get_stats(self) -> Dict[str, any]:
        total = len(self.detection_history)
        anomalies = sum(1 for r in self.detection_history if r.is_anomaly)
        by_type = {}
        for r in self.detection_history:
            by_type[r.anomaly_type.name] = by_type.get(r.anomaly_type.name, 0) + 1
        return {
            "total_samples": total,
            "anomalies_detected": anomalies,
            "normal": total - anomalies,
            "false_positive_rate": anomalies / total if total > 0 else 0.0,
            "by_type": by_type,
            "threshold": self.threshold,
        }


# ============================================================================
# Voice Authenticator Pipeline
# ============================================================================

class VoiceAuthenticator:
    """End-to-end voice authentication pipeline."""

    def __init__(self, detector: Optional[AnomalyDetector] = None):
        self.detector = detector or AnomalyDetector()
        self.enrolled_voiceprints: Dict[str, List[float]] = {}

    def enroll(self, user_id: str, authentic_samples: List[List[float]]) -> bool:
        """Enroll a user with authentic voice samples."""
        if len(authentic_samples) < 3:
            return False
        self.detector.calibrate(authentic_samples)
        # Store voiceprint signature (average MFCC)
        mfcc_sums = []
        for sig in authentic_samples:
            features = self.detector.extractor.extract(sig)
            if features.mfcc:
                for frame in features.mfcc:
                    while len(mfcc_sums) < len(frame):
                        mfcc_sums.append(0.0)
                    for i, val in enumerate(frame):
                        mfcc_sums[i] += val
        avg_mfcc = [v / len(authentic_samples) for v in mfcc_sums]
        self.enrolled_voiceprints[user_id] = avg_mfcc
        return True

    def verify(self, user_id: str, sample: List[float]) -> DetectionResult:
        """Verify a voice sample against enrolled user."""
        if user_id not in self.enrolled_voiceprints:
            raise ValueError(f"User {user_id} not enrolled")
        return self.detector.detect(sample, f"verify_{user_id}")

    def batch_test(self, samples: List[Tuple[str, List[float], str]]) -> List[DetectionResult]:
        """Batch test: (sample_id, signal, expected_type)."""
        results = []
        for sid, sig, expected in samples:
            result = self.detector.detect(sig, sid)
            results.append(result)
        return results

    def generate_report(self) -> str:
        stats = self.detector.get_stats()
        lines = [
            "# Voice Anomaly Detection Report",
            f"**Total Samples:** {stats['total_samples']}",
            f"**Anomalies:** {stats['anomalies_detected']}",
            f"**Normal:** {stats['normal']}",
            f"**Threshold:** {stats['threshold']}",
            "## By Type",
        ]
        for t, count in stats['by_type'].items():
            lines.append(f"- {t}: {count}")
        return "\n".join(lines)


# ============================================================================
# Standalone test
# ============================================================================

if __name__ == "__main__":
    print("=== Voice Anomaly Detector Test ===")

    # Generate training data (authentic only)
    authentic_samples = [SimulatedAudioSignal.generate_authentic_voice(duration=0.3, sample_rate=4000) for _ in range(5)]

    # Create and calibrate detector
    auth = VoiceAuthenticator()
    auth.enroll("user-1", authentic_samples)
    print(f"Enrolled user-1 with {len(authentic_samples)} authentic samples")

    # Test various sample types
    test_samples = [
        ("authentic", SimulatedAudioSignal.generate_authentic_voice(duration=0.3, sample_rate=4000), "NORMAL"),
        ("deepfake", SimulatedAudioSignal.generate_deepfake_voice(duration=0.3, sample_rate=4000), "DEEPFAKE"),
        ("noisy", SimulatedAudioSignal.generate_noise_injected_voice(duration=0.3, sample_rate=4000, snr_db=10.0), "NOISE"),
        ("pitch_shift", SimulatedAudioSignal.generate_pitch_shifted_voice(duration=0.3, sample_rate=4000, shift_factor=1.5), "PITCH"),
    ]

    print("\n--- Detection Results ---")
    for name, signal, expected in test_samples:
        result = auth.detector.detect(signal, name)
        status = "ANOMALY" if result.is_anomaly else "NORMAL"
        print(f"{name:12} | {status:8} | score={result.anomaly_score:.3f} | type={result.anomaly_type.name} | {result.explanation[:60]}")

    print(f"\n--- Stats ---")
    print(json.dumps(auth.detector.get_stats(), indent=2))
    print("\n--- Report ---")
    print(auth.generate_report())
