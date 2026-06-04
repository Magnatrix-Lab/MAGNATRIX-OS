"""Backtracker - Backtracking for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Callable
from enum import Enum, auto

class BacktrackProblem(Enum):
    NQUEEN = auto(); SUDOKU = auto(); SUBSET = auto()

@dataclass
class Backtracker:
    problem_type: BacktrackProblem = BacktrackProblem.NQUEEN
    solutions: List[List] = field(default_factory=list)

    def n_queen(self, n: int = 4) -> List[List[int]]:
        self.solutions = []
        self._n_queen_helper([], n)
        return self.solutions

    def _n_queen_helper(self, board: List[int], n: int) -> None:
        if len(board) == n: self.solutions.append(board[:]); return
        row = len(board)
        for col in range(n):
            if all(board[r] != col and abs(board[r]-col) != row-r for r in range(row)):
                board.append(col)
                self._n_queen_helper(board, n)
                board.pop()

    def subsets(self, nums: List[int]) -> List[List[int]]:
        result = []
        self._subsets_helper(nums, 0, [], result)
        return result

    def _subsets_helper(self, nums, idx, current, result):
        result.append(current[:])
        for i in range(idx, len(nums)):
            current.append(nums[i])
            self._subsets_helper(nums, i+1, current, result)
            current.pop()

    def solve(self, *args):
        if self.problem_type == BacktrackProblem.NQUEEN: return self.n_queen(args[0])
        if self.problem_type == BacktrackProblem.SUBSET: return self.subsets(args[0])
        return []

    def stats(self, *args) -> dict:
        result = self.solve(*args)
        return {"problem": self.problem_type.name, "solutions": len(result)}

def run():
    bt = Backtracker(BacktrackProblem.NQUEEN)
    print("N-Queen solutions:", len(bt.solve(4)))
    bt.problem_type = BacktrackProblem.SUBSET
    print("Subsets:", len(bt.solve([1,2,3])))

if __name__ == "__main__": run()
