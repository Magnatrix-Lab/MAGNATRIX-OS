"""LLM Date Parser — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum, auto
from datetime import datetime, timedelta

class DateFormat(Enum):
    ISO8601 = auto()
    US = auto()
    EUROPEAN = auto()
    RELATIVE = auto()
    CUSTOM = auto()

class DateParser:
    def __init__(self) -> None:
        self._formats = [
            (r"(\d{4})-(\d{2})-(\d{2})", lambda m: (int(m.group(1)), int(m.group(2)), int(m.group(3)))),
            (r"(\d{2})/(\d{2})/(\d{4})", lambda m: (int(m.group(3)), int(m.group(1)), int(m.group(2)))),
            (r"(\d{2})-(\d{2})-(\d{4})", lambda m: (int(m.group(3)), int(m.group(2)), int(m.group(1)))),
            (r"(\d{1,2})\s+(\w+)\s+(\d{4})", lambda m: self._parse_text_month(m.group(2), int(m.group(1)), int(m.group(3)))),
        ]
        self._months = {
            "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
            "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6,
            "july": 7, "jul": 7, "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
            "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12
        }

    def _parse_text_month(self, month_str: str, day: int, year: int) -> Tuple[int, int, int]:
        month = self._months.get(month_str.lower(), 1)
        return (year, month, day)

    def parse(self, text: str) -> Optional[datetime]:
        for pattern, extractor in self._formats:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    year, month, day = extractor(match)
                    return datetime(year, month, day)
                except (ValueError, TypeError):
                    continue
        return None

    def parse_relative(self, text: str, reference: Optional[datetime] = None) -> Optional[datetime]:
        ref = reference or datetime.now()
        text_lower = text.lower()
        if "today" in text_lower:
            return ref
        if "tomorrow" in text_lower:
            return ref + timedelta(days=1)
        if "yesterday" in text_lower:
            return ref - timedelta(days=1)
        match = re.search(r"(\d+)\s+days?\s+ago", text_lower)
        if match:
            return ref - timedelta(days=int(match.group(1)))
        match = re.search(r"in\s+(\d+)\s+days?", text_lower)
        if match:
            return ref + timedelta(days=int(match.group(1)))
        return None

    def format(self, dt: datetime, fmt: str = "%Y-%m-%d") -> str:
        return dt.strftime(fmt)

    def duration_between(self, start: datetime, end: datetime) -> Dict[str, int]:
        delta = end - start
        return {"days": delta.days, "hours": delta.seconds // 3600, "minutes": (delta.seconds % 3600) // 60, "seconds": delta.seconds % 60}

    def get_stats(self) -> Dict[str, Any]:
        return {"formats": len(self._formats), "months": len(self._months)}

def run() -> None:
    print("Date Parser test")
    e = DateParser()
    print("  ISO: " + str(e.parse("2024-01-15")))
    print("  US: " + str(e.parse("01/15/2024")))
    print("  EU: " + str(e.parse("15-01-2024")))
    print("  Text: " + str(e.parse("15 January 2024")))
    print("  Relative today: " + str(e.parse_relative("today")))
    print("  Relative 3 days ago: " + str(e.parse_relative("3 days ago")))
    print("  Format: " + e.format(datetime(2024, 1, 15), "%B %d, %Y"))
    print("  Stats: " + str(e.get_stats()))
    print("Date Parser test complete.")

if __name__ == "__main__":
    run()
