"""DP Solver - Dynamic programming patterns for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto

class DPProblem(Enum):
    KNAPSACK = auto(); LIS = auto(); LCS = auto(); COIN_CHANGE = auto()

@dataclass
class DPSolver:
    problem_type: DPProblem = DPProblem.KNAPSACK

    def knapsack(self, weights: List[int], values: List[int], capacity: int) -> int:
        dp = [0]*(capacity+1)
        for w, v in zip(weights, values):
            for c in range(capacity, w-1, -1): dp[c] = max(dp[c], dp[c-w]+v)
        return dp[capacity]

    def lis(self, nums: List[int]) -> int:
        dp = [1]*len(nums)
        for i in range(1, len(nums)):
            for j in range(i):
                if nums[i] > nums[j]: dp[i] = max(dp[i], dp[j]+1)
        return max(dp) if dp else 0

    def lcs(self, a: str, b: str) -> int:
        dp = [[0]*(len(b)+1) for _ in range(len(a)+1)]
        for i in range(1, len(a)+1):
            for j in range(1, len(b)+1):
                if a[i-1] == b[j-1]: dp[i][j] = dp[i-1][j-1]+1
                else: dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        return dp[-1][-1]

    def coin_change(self, coins: List[int], amount: int) -> int:
        dp = [float('inf')]*(amount+1); dp[0] = 0
        for c in coins:
            for i in range(c, amount+1): dp[i] = min(dp[i], dp[i-c]+1)
        return dp[amount] if dp[amount] != float('inf') else -1

    def solve(self, *args):
        if self.problem_type == DPProblem.KNAPSACK: return self.knapsack(args[0], args[1], args[2])
        if self.problem_type == DPProblem.LIS: return self.lis(args[0])
        if self.problem_type == DPProblem.LCS: return self.lcs(args[0], args[1])
        if self.problem_type == DPProblem.COIN_CHANGE: return self.coin_change(args[0], args[1])
        return 0

    def stats(self, *args) -> dict:
        return {"problem": self.problem_type.name, "result": self.solve(*args)}

def run():
    for pt in [DPProblem.KNAPSACK, DPProblem.LIS, DPProblem.LCS, DPProblem.COIN_CHANGE]:
        solver = DPSolver(pt)
        if pt == DPProblem.KNAPSACK: print(f"{pt.name}: {solver.solve([1,2,3], [10,15,40], 6)}")
        elif pt == DPProblem.LIS: print(f"{pt.name}: {solver.solve([10,9,2,5,3,7,101,18])}")
        elif pt == DPProblem.LCS: print(f"{pt.name}: {solver.solve('abcde', 'ace')}")
        elif pt == DPProblem.COIN_CHANGE: print(f"{pt.name}: {solver.solve([1,2,5], 11)}")

if __name__ == "__main__": run()
