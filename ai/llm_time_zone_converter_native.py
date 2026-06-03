"""LLM Time Zone Converter — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto
from datetime import datetime, timedelta

class TimeZoneConverter:
    def __init__(self) -> None:
        self._offsets: Dict[str, int] = {
            "UTC": 0, "GMT": 0, "EST": -5, "EDT": -4, "CST": -6, "CDT": -5,
            "MST": -7, "MDT": -6, "PST": -8, "PDT": -7, "IST": 5, "CET": 1,
            "CEST": 2, "JST": 9, "KST": 9, "AEST": 10, "AEDT": 11, "WIB": 7,
            "WITA": 8, "WIT": 9, "SGT": 8, "HKT": 8, "BKK": 7, "MSK": 3,
            "NZST": 12, "NZDT": 13, "BRT": -3, "ART": -3, "CLT": -4,
        }

    def convert(self, dt: datetime, from_zone: str, to_zone: str) -> datetime:
        from_offset = self._offsets.get(from_zone, 0)
        to_offset = self._offsets.get(to_zone, 0)
        diff = (to_offset - from_offset)
        return dt + timedelta(hours=diff)

    def get_offset(self, zone: str) -> int:
        return self._offsets.get(zone, 0)

    def list_zones(self) -> List[str]:
        return sorted(self._offsets.keys())

    def add_zone(self, zone: str, offset: int) -> None:
        self._offsets[zone] = offset

    def get_business_hours_overlap(self, zone1: str, zone2: str, business_start: int = 9, business_end: int = 17) -> List[int]:
        offset1 = self._offsets.get(zone1, 0)
        offset2 = self._offsets.get(zone2, 0)
        diff = offset2 - offset1
        overlap = []
        for hour in range(24):
            local1 = hour
            local2 = (hour + diff) % 24
            if business_start <= local1 < business_end and business_start <= local2 < business_end:
                overlap.append(hour)
        return overlap

    def get_stats(self) -> Dict[str, Any]:
        return {"zones": len(self._offsets), "range": str(min(self._offsets.values())) + " to " + str(max(self._offsets.values()))}

def run() -> None:
    print("Time Zone Converter test")
    e = TimeZoneConverter()
    dt = datetime(2024, 6, 15, 12, 0)
    print("  12:00 UTC -> JST: " + str(e.convert(dt, "UTC", "JST")))
    print("  12:00 UTC -> WIB: " + str(e.convert(dt, "UTC", "WIB")))
    print("  12:00 UTC -> PST: " + str(e.convert(dt, "UTC", "PST")))
    print("  WIB offset: " + str(e.get_offset("WIB")))
    overlap = e.get_business_hours_overlap("WIB", "JST")
    print("  WIB-JST overlap hours: " + str(overlap))
    print("  Stats: " + str(e.get_stats()))
    print("Time Zone Converter test complete.")

if __name__ == "__main__":
    run()
