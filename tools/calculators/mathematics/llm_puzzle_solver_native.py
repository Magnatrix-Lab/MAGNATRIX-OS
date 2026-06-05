"""Puzzle Solver — sudoku, sliding tile, state search, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple

@dataclass
class PuzzleSolver:
    def sudoku_valid(self, grid: List[List[int]]) -> bool:
        for row in grid:
            if not self._valid_group(row):
                return False
        for col in range(9):
            if not self._valid_group([grid[r][col] for r in range(9)]):
                return False
        for box_r in range(0, 9, 3):
            for box_c in range(0, 9, 3):
                box = [grid[r][c] for r in range(box_r, box_r + 3) for c in range(box_c, box_c + 3)]
                if not self._valid_group(box):
                    return False
        return True

    def _valid_group(self, nums: List[int]) -> bool:
        seen = set()
        for n in nums:
            if n != 0 and n in seen:
                return False
            seen.add(n)
        return True

    def sliding_tile_solvable(self, tiles: List[int]) -> bool:
        inversions = 0
        for i in range(len(tiles)):
            for j in range(i + 1, len(tiles)):
                if tiles[i] != 0 and tiles[j] != 0 and tiles[i] > tiles[j]:
                    inversions += 1
        return inversions % 2 == 0

    def manhattan_distance(self, state: List[int], goal: List[int]) -> int:
        dist = 0
        for i, val in enumerate(state):
            if val != 0:
                goal_idx = goal.index(val)
                dist += abs(i // 3 - goal_idx // 3) + abs(i % 3 - goal_idx % 3)
        return dist

    def stats(self, grid: List[List[int]]) -> Dict:
        return {"valid": self.sudoku_valid(grid), "filled": sum(1 for row in grid for c in row if c != 0)}

def run():
    ps = PuzzleSolver()
    grid = [
        [5,3,0,0,7,0,0,0,0],
        [6,0,0,1,9,5,0,0,0],
        [0,9,8,0,0,0,0,6,0],
        [8,0,0,0,6,0,0,0,3],
        [4,0,0,8,0,3,0,0,1],
        [7,0,0,0,2,0,0,0,6],
        [0,6,0,0,0,0,2,8,0],
        [0,0,0,4,1,9,0,0,5],
        [0,0,0,0,8,0,0,7,9]
    ]
    print(ps.stats(grid))
    print("Sliding solvable:", ps.sliding_tile_solvable([1,2,3,4,5,6,7,8,0]))

if __name__ == "__main__":
    run()
