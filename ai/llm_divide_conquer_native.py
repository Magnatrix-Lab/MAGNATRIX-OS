"""Divide Conquer - Divide and conquer for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
from enum import Enum, auto

class DCProblem(Enum):
    MERGESORT = auto(); MAXSUBARRAY = auto(); CLOSESTPAIR = auto()

@dataclass
class DivideConquer:
    problem_type: DCProblem = DCProblem.MERGESORT

    def merge_sort(self, arr: List[float]) -> List[float]:
        if len(arr) <= 1: return arr
        mid = len(arr)//2
        left = self.merge_sort(arr[:mid])
        right = self.merge_sort(arr[mid:])
        return self._merge(left, right)

    def _merge(self, a: List[float], b: List[float]) -> List[float]:
        result = []; i = j = 0
        while i < len(a) and j < len(b):
            if a[i] <= b[j]: result.append(a[i]); i += 1
            else: result.append(b[j]); j += 1
        result.extend(a[i:]); result.extend(b[j:])
        return result

    def max_subarray(self, arr: List[float]) -> Tuple[int, int, float]:
        return self._max_subarray(arr, 0, len(arr)-1)

    def _max_subarray(self, arr, l, r):
        if l == r: return (l, r, arr[l])
        mid = (l+r)//2
        left = self._max_subarray(arr, l, mid)
        right = self._max_subarray(arr, mid+1, r)
        cross = self._max_crossing(arr, l, mid, r)
        return max([left, right, cross], key=lambda x: x[2])

    def _max_crossing(self, arr, l, mid, r):
        left_sum = float('-inf'); s = 0; max_left = mid
        for i in range(mid, l-1, -1):
            s += arr[i]
            if s > left_sum: left_sum = s; max_left = i
        right_sum = float('-inf'); s = 0; max_right = mid+1
        for i in range(mid+1, r+1):
            s += arr[i]
            if s > right_sum: right_sum = s; max_right = i
        return (max_left, max_right, left_sum + right_sum)

    def solve(self, *args):
        if self.problem_type == DCProblem.MERGESORT: return self.merge_sort(args[0])
        if self.problem_type == DCProblem.MAXSUBARRAY: return self.max_subarray(args[0])
        return None

    def stats(self, *args) -> dict:
        return {"problem": self.problem_type.name, "result": self.solve(*args)}

def run():
    dc = DivideConquer(DCProblem.MERGESORT)
    print("Sorted:", dc.solve([3,1,4,1,5,9,2,6]))
    dc.problem_type = DCProblem.MAXSUBARRAY
    print("Max subarray:", dc.solve([-2,1,-3,4,-1,2,1,-5,4]))

if __name__ == "__main__": run()
