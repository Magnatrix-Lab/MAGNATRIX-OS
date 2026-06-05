"""Native stdlib module: Timecode Calculator
Calculates timecode conversions, frame counts, and duration for video editing.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class FrameRate(Enum):
    FPS_24 = 24
    FPS_25 = 25
    FPS_30 = 30
    FPS_60 = 60

@dataclass
class TimecodeCalculator:
    hours: int
    minutes: int
    seconds: int
    frames: int
    frame_rate: FrameRate

    def total_frames(self) -> int:
        return ((self.hours * 3600 + self.minutes * 60 + self.seconds) * self.frame_rate.value) + self.frames

    def total_seconds(self) -> float:
        return self.total_frames() / self.frame_rate.value

    def duration_from_frames(self, total_frames: int) -> str:
        fps = self.frame_rate.value
        total_seconds = total_frames // fps
        remaining_frames = total_frames % fps
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}:{remaining_frames:02d}"

    def add_frames(self, frames_to_add: int) -> str:
        return self.duration_from_frames(self.total_frames() + frames_to_add)

    def subtract_frames(self, frames_to_subtract: int) -> str:
        return self.duration_from_frames(max(0, self.total_frames() - frames_to_subtract))

    def timecode_string(self) -> str:
        return f"{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}:{self.frames:02d}"

    def stats(self) -> Dict:
        return {
            "timecode": self.timecode_string(),
            "frame_rate": self.frame_rate.value,
            "total_frames": self.total_frames(),
            "total_seconds": round(self.total_seconds(), 3),
        }

def run():
    tc = TimecodeCalculator(hours=1, minutes=23, seconds=45, frames=12, frame_rate=FrameRate.FPS_24)
    print(tc.stats())
    print(f"Add 500 frames: {tc.add_frames(500)}")

if __name__ == "__main__":
    run()
