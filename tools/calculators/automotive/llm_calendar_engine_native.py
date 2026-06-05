"""Calendar Engine — events, recurrence, free/busy, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum, auto
import time

@dataclass
class CalendarEvent:
    event_id: str
    title: str
    start: float
    end: float
    recurring: bool = False
    recurrence_rule: str = ""

class CalendarEngine:
    def __init__(self):
        self.events: List[CalendarEvent] = []
        self.calendar: Dict[str, List[CalendarEvent]] = {}

    def add_event(self, event: CalendarEvent):
        self.events.append(event)
        self.calendar.setdefault(event.title, []).append(event)

    def is_busy(self, check_start: float, check_end: float) -> bool:
        for e in self.events:
            if e.start < check_end and e.end > check_start:
                return True
        return False

    def free_slots(self, day_start: float, day_end: float, slot_duration: float = 3600) -> List[Tuple[float, float]]:
        busy = [(e.start, e.end) for e in self.events if e.start >= day_start and e.end <= day_end]
        busy.sort()
        slots = []
        current = day_start
        for s, e in busy:
            if current + slot_duration <= s:
                slots.append((current, s))
            current = max(current, e)
        if current + slot_duration <= day_end:
            slots.append((current, day_end))
        return slots

    def conflicts(self) -> List[Tuple[CalendarEvent, CalendarEvent]]:
        conflicts = []
        for i, e1 in enumerate(self.events):
            for e2 in self.events[i+1:]:
                if e1.start < e2.end and e2.start < e1.end:
                    conflicts.append((e1, e2))
        return conflicts

    def stats(self) -> Dict:
        return {"events": len(self.events), "conflicts": len(self.conflicts())}

def run():
    cal = CalendarEngine()
    now = time.time()
    cal.add_event(CalendarEvent("1", "Meeting", now, now + 3600))
    cal.add_event(CalendarEvent("2", "Lunch", now + 7200, now + 9000))
    cal.add_event(CalendarEvent("3", "Call", now + 1800, now + 5400))
    print("Busy now:", cal.is_busy(now, now + 100))
    print("Conflicts:", len(cal.conflicts()))
    print(cal.stats())

if __name__ == "__main__":
    run()
