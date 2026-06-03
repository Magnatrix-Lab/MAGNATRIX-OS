"""LLM Tempo Calculator — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class TempoCalculator:
    def __init__(self) -> None:
        self._tap_times: List[float] = []
        self._last_tap: float = 0.0

    def tap(self, timestamp: float) -> Optional[float]:
        if self._last_tap > 0:
            interval = timestamp - self._last_tap
            if 0.1 < interval < 3.0:
                self._tap_times.append(interval)
                if len(self._tap_times) > 8:
                    self._tap_times.pop(0)
        self._last_tap = timestamp
        return self.get_bpm()

    def get_bpm(self) -> Optional[float]:
        if not self._tap_times:
            return None
        avg = sum(self._tap_times) / len(self._tap_times)
        if avg > 0:
            return 60.0 / avg
        return None

    def get_ms_per_beat(self) -> Optional[float]:
        bpm = self.get_bpm()
        if bpm and bpm > 0:
            return 60000.0 / bpm
        return None

    def get_ms_per_bar(self, beats_per_bar: int = 4) -> Optional[float]:
        ms = self.get_ms_per_beat()
        if ms:
            return ms * beats_per_bar
        return None

    def reset(self) -> None:
        self._tap_times.clear()
        self._last_tap = 0.0

    def get_stats(self) -> Dict[str, Any]:
        return {"taps": len(self._tap_times), "bpm": self.get_bpm(), "ms_per_beat": self.get_ms_per_beat()}

def run() -> None:
    print("Tempo Calculator test")
    e = TempoCalculator()
    for i in range(8):
        bpm = e.tap(i * 0.5 + 0.1)
    print("  BPM: " + str(e.get_bpm()))
    print("  MS per beat: " + str(e.get_ms_per_beat()))
    print("  MS per bar: " + str(e.get_ms_per_bar(4)))
    print("  Stats: " + str(e.get_stats()))
    print("Tempo Calculator test complete.")

if __name__ == "__main__":
    run()
