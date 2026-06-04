"""Sonar Processor — beamforming, range detection, bottom classification, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
from math import sin, cos, pi, radians, degrees, sqrt, atan2, fabs, log10, pow, exp

class SonarMode(Enum):
    ACTIVE = auto()
    PASSIVE = auto()
    DVL = auto()  # Doppler Velocity Log

class BottomType(Enum):
    ROCK = auto()
    MUD = auto()
    SAND = auto()
    GRAVEL = auto()

@dataclass
class SonarPing:
    angle: float  # degrees
    range_m: float
    intensity: float  # dB
    two_way_time: float  # seconds
    frequency: float  # Hz

@dataclass
class SonarProcessor:
    sound_speed: float = 1500.0  # m/s
    mode: SonarMode = SonarMode.ACTIVE
    beam_count: int = 64
    beam_width: float = 1.5  # degrees
    max_range: float = 500.0  # meters
    pings: List[SonarPing] = field(default_factory=list)

    def range_resolution(self, pulse_duration: float) -> float:
        """Range resolution in meters."""
        return self.sound_speed * pulse_duration / 2

    def angular_resolution(self, wavelength: float, aperture: float) -> float:
        """Angular resolution in degrees."""
        return degrees(1.22 * wavelength / aperture)

    def add_ping(self, ping: SonarPing) -> None:
        self.pings.append(ping)

    def detect_bottom(self, threshold_db: float = -30.0) -> List[Dict]:
        """Detect bottom returns above threshold."""
        detections = []
        for p in self.pings:
            if p.intensity > threshold_db:
                detections.append({
                    "range": p.range_m,
                    "angle": p.angle,
                    "intensity": p.intensity,
                    "x": p.range_m * cos(radians(p.angle)),
                    "y": p.range_m * sin(radians(p.angle))
                })
        return detections

    def classify_bottom(self, backscatter: List[float]) -> BottomType:
        """Classify bottom type based on backscatter statistics."""
        if not backscatter:
            return BottomType.MUD
        avg = sum(backscatter) / len(backscatter)
        if avg > -15.0:
            return BottomType.ROCK
        elif avg > -25.0:
            return BottomType.GRAVEL
        elif avg > -35.0:
            return BottomType.SAND
        return BottomType.MUD

    def beam_pattern(self, angle: float, main_lobe_width: float = 10.0) -> float:
        """Simplified beam pattern response in dB."""
        return 20 * log10(fabs(cos(radians(angle * 90 / main_lobe_width))) + 1e-10)

    def doppler_shift(self, velocity: float, frequency: float) -> float:
        """Doppler shift in Hz for given velocity (m/s)."""
        return 2 * velocity * frequency / self.sound_speed

    def stats(self) -> Dict[str, float]:
        if not self.pings:
            return {"beam_count": self.beam_count, "sound_speed_ms": self.sound_speed}
        intensities = [p.intensity for p in self.pings]
        ranges = [p.range_m for p in self.pings]
        return {
            "beam_count": self.beam_count,
            "sound_speed_ms": self.sound_speed,
            "ping_count": len(self.pings),
            "max_range_m": max(ranges),
            "avg_intensity_db": sum(intensities) / len(intensities),
            "max_intensity_db": max(intensities)
        }

def run():
    proc = SonarProcessor(beam_count=128, max_range=200)
    for i in range(20):
        proc.add_ping(SonarPing(angle=i*5-50, range_m=50+i*2, intensity=-20+i*0.5, two_way_time=0.1, frequency=50000))
    detections = proc.detect_bottom(threshold_db=-15)
    print(f"Detections: {len(detections)}")
    for d in detections[:3]:
        print(f"  range={d['range']:.1f}m, angle={d['angle']:.1f}°, intensity={d['intensity']:.1f}dB")
    backscatter = [-18, -22, -20, -25, -19]
    print(f"Bottom type: {proc.classify_bottom(backscatter).name}")
    print(f"Doppler shift at 2 m/s, 50kHz: {proc.doppler_shift(2.0, 50000):.1f} Hz")
    print(proc.stats())

if __name__ == "__main__":
    run()
