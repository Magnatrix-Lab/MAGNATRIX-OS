"""Native stdlib module: Reverb Calculator
Calculates reverb time, pre-delay, and room dimensions for acoustics.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class ReverbCalculator:
    room_length_m: float
    room_width_m: float
    room_height_m: float
    total_absorption: float
    volume_m3: float = 0.0

    def _volume(self) -> float:
        if self.volume_m3 > 0:
            return self.volume_m3
        return self.room_length_m * self.room_width_m * self.room_height_m

    def rt60_s(self) -> float:
        v = self._volume()
        if self.total_absorption == 0:
            return 0.0
        return 0.161 * v / self.total_absorption

    def pre_delay_ms(self, distance_from_source_m: float) -> float:
        speed_of_sound = 343
        if speed_of_sound == 0:
            return 0.0
        return (distance_from_source_m / speed_of_sound) * 1000

    def critical_distance_m(self, directivity_q: float = 1) -> float:
        v = self._volume()
        if self.total_absorption == 0:
            return 0.0
        return 0.057 * math.sqrt(directivity_q * v / self.total_absorption)

    def room_mode_freq_hz(self, mode_l: int, mode_w: int, mode_h: int) -> float:
        speed_of_sound = 343
        c = speed_of_sound / 2
        return c * math.sqrt((mode_l / self.room_length_m)**2 + (mode_w / self.room_width_m)**2 + (mode_h / self.room_height_m)**2)

    def stats(self) -> Dict:
        import math
        return {
            "room_volume_m3": round(self._volume(), 1),
            "rt60_s": round(self.rt60_s(), 2),
            "pre_delay_ms": round(self.pre_delay_ms(3), 1),
            "critical_distance_m": round(self.critical_distance_m(), 2),
            "first_axial_mode_hz": round(self.room_mode_freq_hz(1, 0, 0), 1),
        }

def run():
    import math
    rc = ReverbCalculator(room_length_m=5, room_width_m=4, room_height_m=2.8, total_absorption=12, volume_m3=56)
    print(rc.stats())

if __name__ == "__main__":
    run()
