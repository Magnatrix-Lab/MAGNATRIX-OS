"""Table Formatter - Data table formatting for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto

class Alignment(Enum):
    LEFT = auto(); RIGHT = auto(); CENTER = auto()

@dataclass
class TableFormatter:
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    alignments: List[Alignment] = field(default_factory=list)
    
    def add_header(self, headers: List[str]) -> None:
        self.headers = headers
        self.alignments = [Alignment.LEFT] * len(headers)
    
    def add_row(self, row: List[str]) -> None:
        self.rows.append(row)
    
    def format(self) -> str:
        if not self.headers: return ""
        col_widths = [max(len(str(r[i])) for r in self.rows + [self.headers]) for i in range(len(self.headers))]
        lines = []
        header_line = " | ".join(f"{h:^{w}}" for h, w in zip(self.headers, col_widths))
        lines.append(header_line)
        lines.append("-" * len(header_line))
        for row in self.rows:
            lines.append(" | ".join(f"{str(v):^{w}}" for v, w in zip(row, col_widths)))
        return "\n".join(lines)
    
    def stats(self) -> dict:
        return {"headers": len(self.headers), "rows": len(self.rows)}

def run():
    tf = TableFormatter()
    tf.add_header(["Name", "Age", "City"])
    tf.add_row(["Alice", "30", "NYC"])
    tf.add_row(["Bob", "25", "LA"])
    tf.add_row(["Charlie", "35", "Chicago"])
    print(tf.format())
    print("Stats:", tf.stats())

if __name__ == "__main__": run()
