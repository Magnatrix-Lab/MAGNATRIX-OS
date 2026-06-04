"""Cron Parser — expression parsing, next execution, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum, auto
import time
import re

class CronParser:
    def __init__(self, expression: str = "* * * * *"):
        self.expression = expression
        self.fields = ["minute", "hour", "day_of_month", "month", "day_of_week"]
        self.values = self._parse(expression)

    def _parse_field(self, field: str, min_val: int, max_val: int) -> Set[int]:
        result = set()
        for part in field.split(','):
            if part == '*':
                result.update(range(min_val, max_val + 1))
            elif '/' in part:
                base, step = part.split('/')
                step = int(step)
                start = min_val if base == '*' else int(base)
                result.update(range(start, max_val + 1, step))
            elif '-' in part:
                start, end = map(int, part.split('-'))
                result.update(range(start, end + 1))
            else:
                result.add(int(part))
        return result

    def _parse(self, expression: str) -> Dict[str, Set[int]]:
        parts = expression.split()
        if len(parts) != 5:
            parts = ['*'] * 5
        ranges = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]
        return {field: self._parse_field(parts[i], *ranges[i]) for i, field in enumerate(self.fields)}

    def next_execution(self, now: float = None) -> float:
        now = now or time.time()
        tm = time.localtime(now)
        for offset in range(1, 60 * 24 * 366):
            test = now + offset * 60
            t = time.localtime(test)
            if (t.tm_min in self.values["minute"] and
                t.tm_hour in self.values["hour"] and
                t.tm_mday in self.values["day_of_month"] and
                t.tm_mon in self.values["month"] and
                t.tm_wday in self.values["day_of_week"]):
                return test
        return now

    def stats(self) -> Dict:
        return {"expression": self.expression, "fields": {k: len(v) for k, v in self.values.items()}}

def run():
    cron = CronParser("0 9 * * 1")
    print("Next Monday 9AM:", cron.next_execution())
    print(cron.stats())

if __name__ == "__main__":
    run()
