"""Native stdlib module: Range of Motion Calculator
Calculates joint ROM, deficits, and functional percentages.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class JointMeasurement:
    joint_name: str
    movement: str
    normal_rom_deg: float
    measured_rom_deg: float
    side: str = "right"

@dataclass
class RangeOfMotionCalculator:
    patient_name: str
    measurements: List[JointMeasurement] = field(default_factory=list)

    def deficit_deg(self, m: JointMeasurement) -> float:
        return max(0, m.normal_rom_deg - m.measured_rom_deg)

    def functional_pct(self, m: JointMeasurement) -> float:
        if m.normal_rom_deg == 0:
            return 0.0
        return (m.measured_rom_deg / m.normal_rom_deg) * 100

    def total_deficit_deg(self) -> float:
        return sum(self.deficit_deg(m) for m in self.measurements)

    def avg_functional_pct(self) -> float:
        if not self.measurements:
            return 0.0
        return sum(self.functional_pct(m) for m in self.measurements) / len(self.measurements)

    def severely_limited_joints(self) -> List[str]:
        return [f"{m.joint_name} ({m.movement})" for m in self.measurements if self.functional_pct(m) < 50]

    def normal_joints(self) -> List[str]:
        return [f"{m.joint_name} ({m.movement})" for m in self.measurements if self.functional_pct(m) >= 90]

    def by_joint(self) -> Dict[str, Dict]:
        return {
            f"{m.joint_name}_{m.movement}": {
                "normal": m.normal_rom_deg,
                "measured": m.measured_rom_deg,
                "deficit": round(self.deficit_deg(m), 1),
                "functional_pct": round(self.functional_pct(m), 1),
            }
            for m in self.measurements
        }

    def stats(self) -> Dict:
        return {
            "patient": self.patient_name,
            "joints_measured": len(self.measurements),
            "total_deficit_deg": round(self.total_deficit_deg(), 1),
            "avg_functional_pct": round(self.avg_functional_pct(), 1),
            "severely_limited": self.severely_limited_joints(),
            "normal_joints": self.normal_joints(),
        }

def run():
    rom = RangeOfMotionCalculator(
        patient_name="Patient-A",
        measurements=[
            JointMeasurement("shoulder", "flexion", 180, 150),
            JointMeasurement("shoulder", "abduction", 180, 120),
            JointMeasurement("elbow", "flexion", 150, 145),
            JointMeasurement("wrist", "extension", 70, 45),
            JointMeasurement("hip", "flexion", 120, 100),
            JointMeasurement("knee", "flexion", 135, 125),
            JointMeasurement("ankle", "dorsiflexion", 20, 10),
        ]
    )
    print(rom.stats())

if __name__ == "__main__":
    run()
