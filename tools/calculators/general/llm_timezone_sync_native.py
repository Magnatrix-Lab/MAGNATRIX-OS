"""Timezone Sync — GMT offset, leap second, atomic time, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class TimezoneSync:
    gmt_offset: float = 0.0
    dst_active: bool = False
    leap_seconds: int = 37

    def local_to_utc(self, hour: float) -> float:
        return hour - self.gmt_offset - (1 if self.dst_active else 0)

    def utc_to_local(self, hour: float) -> float:
        return hour + self.gmt_offset + (1 if self.dst_active else 0)

    def tai_offset(self) -> float:
        return self.gmt_offset + self.leap_seconds / 3600

    def is_dst_transition(self, month: int, day: int, region: str = "US") -> bool:
        if region == "US" and month == 3 and day == 10:
            return True
        if region == "EU" and month == 3 and day == 31:
            return True
        return False

    def stats(self) -> Dict:
        return {"offset": self.gmt_offset, "dst": self.dst_active, "leap_seconds": self.leap_seconds, "tai": self.tai_offset()}

def run():
    ts = TimezoneSync(gmt_offset=-5, dst_active=True, leap_seconds=37)
    print(ts.stats())
    print("12 local to UTC:", ts.local_to_utc(12))

if __name__ == "__main__":
    run()
