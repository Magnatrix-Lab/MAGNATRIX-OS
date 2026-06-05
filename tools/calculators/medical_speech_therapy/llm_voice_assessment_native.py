"""Native stdlib module: Voice Assessment Calculator
Calculates vocal parameters: jitter, shimmer, NHR, and DSI.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class VoiceAssessmentCalculator:
    fundamental_frequency_hz: float
    jitter_pct: float
    shimmer_pct: float
    noise_to_harmonic_ratio: float

    def dysphonia_severity_index(self) -> float:
        f0 = self.fundamental_frequency_hz
        jit = self.jitter_pct
        shim = self.shimmer_pct
        nhr = self.noise_to_harmonic_ratio
        if f0 == 0 or jit == 0 or shim == 0 or nhr == 0:
            return 0.0
        return (0.13 * f0) + (0.006 * 100 / jit) - (0.008 * shim) - (1.5 * nhr) - 2.5

    def severity(self) -> str:
        dsi = self.dysphonia_severity_index()
        if dsi > 4.0:
            return "normal"
        elif dsi > 2.0:
            return "mild"
        elif dsi > 0.0:
            return "moderate"
        elif dsi > -2.0:
            return "severe"
        return "profound"

    def pitch_range_semitones(self, max_freq_hz: float) -> float:
        if self.fundamental_frequency_hz == 0:
            return 0.0
        return 12 * math.log2(max_freq_hz / self.fundamental_frequency_hz)

    def vocal_efficiency(self, subglottal_pressure_pa: float, airflow_l_s: float) -> float:
        if subglottal_pressure_pa == 0 or airflow_l_s == 0:
            return 0.0
        return self.fundamental_frequency_hz / (subglottal_pressure_pa * airflow_l_s)

    def stats(self) -> Dict:
        return {
            "f0_hz": self.fundamental_frequency_hz,
            "jitter_pct": self.jitter_pct,
            "shimmer_pct": self.shimmer_pct,
            "nhr": self.noise_to_harmonic_ratio,
            "dsi": round(self.dysphonia_severity_index(), 2),
            "severity": self.severity(),
        }

def run():
    vac = VoiceAssessmentCalculator(fundamental_frequency_hz=120, jitter_pct=1.2, shimmer_pct=5.5, noise_to_harmonic_ratio=0.15)
    print(vac.stats())

if __name__ == "__main__":
    run()
