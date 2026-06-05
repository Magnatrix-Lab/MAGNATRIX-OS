"""Board Evaluator — chess, checkers, connectivity, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class BoardEvaluator:
    board: List[List[str]] = field(default_factory=list)
    """2D grid, empty = ''"""

    def piece_count(self, piece: str) -> int:
        return sum(row.count(piece) for row in self.board)

    def center_control(self, piece: str) -> int:
        if not self.board:
            return 0
        rows = len(self.board)
        cols = len(self.board[0]) if self.board else 0
        count = 0
        for r in range(rows//2 - 1, rows//2 + 1):
            for c in range(cols//2 - 1, cols//2 + 1):
                if 0 <= r < rows and 0 <= c < cols and self.board[r][c] == piece:
                    count += 1
        return count

    def mobility_estimate(self, piece: str) -> int:
        return self.piece_count(piece) * 2

    def material_score(self, values: Dict[str, int]) -> int:
        return sum(self.piece_count(p) * v for p, v in values.items())

    def winning_position(self, player: str, values: Dict[str, int]) -> bool:
        return self.material_score(values) > 0

    def stats(self, piece: str) -> Dict:
        return {"count": self.piece_count(piece), "center": self.center_control(piece)}

def run():
    be = BoardEvaluator([
        ["R","N","B","Q","K","B","N","R"],
        ["P","P","P","P","P","P","P","P"],
        [""]*8,
        [""]*8,
        [""]*8,
        [""]*8,
        ["p","p","p","p","p","p","p","p"],
        ["r","n","b","q","k","b","n","r"]
    ])
    print(be.stats("P"))
    print("Material:", be.material_score({"P": 1, "N": 3, "B": 3, "R": 5, "Q": 9}))

if __name__ == "__main__":
    run()
