"""Data Profiler — schema, types, distributions, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum, auto
import math
from collections import Counter

class DataType(Enum):
    NUMERIC = auto()
    CATEGORICAL = auto()
    TEXT = auto()
    BOOLEAN = auto()
    DATETIME = auto()
    NULL = auto()

@dataclass
class ColumnProfile:
    name: str
    dtype: DataType
    count: int = 0
    null_count: int = 0
    unique_count: int = 0
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    mean: Optional[float] = None
    std: Optional[float] = None
    top_values: List[Tuple[Any, int]] = field(default_factory=list)
    histogram: Dict[str, int] = field(default_factory=dict)

class DataProfiler:
    def __init__(self):
        self.profiles: Dict[str, ColumnProfile] = {}
        self.row_count: int = 0

    def _infer_type(self, values: List[Any]) -> DataType:
        non_null = [v for v in values if v is not None]
        if not non_null:
            return DataType.NULL
        if all(isinstance(v, bool) for v in non_null):
            return DataType.BOOLEAN
        if all(isinstance(v, (int, float)) for v in non_null):
            return DataType.NUMERIC
        if all(isinstance(v, str) for v in non_null):
            if len(set(non_null)) / len(non_null) < 0.1:
                return DataType.CATEGORICAL
            return DataType.TEXT
        return DataType.CATEGORICAL

    def profile(self, data: List[Dict]):
        if not data:
            return
        self.row_count = len(data)
        columns = list(data[0].keys())
        for col in columns:
            values = [row.get(col) for row in data]
            dtype = self._infer_type(values)
            non_null = [v for v in values if v is not None]
            profile = ColumnProfile(col, dtype, len(values), len(values) - len(non_null), len(set(non_null)))
            if dtype == DataType.NUMERIC and non_null:
                nums = [float(v) for v in non_null]
                profile.min_val = min(nums)
                profile.max_val = max(nums)
                profile.mean = sum(nums) / len(nums)
                profile.std = math.sqrt(sum((x - profile.mean) ** 2 for x in nums) / len(nums)) if len(nums) > 1 else 0
            if dtype in (DataType.CATEGORICAL, DataType.TEXT, DataType.BOOLEAN) and non_null:
                counts = Counter(non_null)
                profile.top_values = counts.most_common(5)
                profile.histogram = dict(counts)
            self.profiles[col] = profile

    def get_profile(self, column: str) -> Optional[ColumnProfile]:
        return self.profiles.get(column)

    def summary(self) -> Dict:
        return {"rows": self.row_count, "columns": len(self.profiles), "profiles": {name: {"dtype": p.dtype.name, "nulls": p.null_count, "unique": p.unique_count} for name, p in self.profiles.items()}}

    def stats(self) -> Dict:
        return self.summary()

def run():
    data = [
        {"name": "Alice", "age": 30, "score": 85.5, "active": True},
        {"name": "Bob", "age": 25, "score": 92.0, "active": False},
        {"name": "Charlie", "age": 35, "score": 78.0, "active": True},
        {"name": "Alice", "age": 28, "score": 88.0, "active": None},
    ]
    profiler = DataProfiler()
    profiler.profile(data)
    print(profiler.summary())

if __name__ == "__main__":
    run()
