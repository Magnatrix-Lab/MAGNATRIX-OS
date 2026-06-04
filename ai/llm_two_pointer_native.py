"""Two Pointer - Two pointer technique for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum, auto

class TwoPointerProblem(Enum):
    TWOSUM = auto(); THREESUM = auto(); PALINDROME = auto()

@dataclass
class TwoPointer:
    problem_type: TwoPointerProblem = TwoPointerProblem.TWOSUM

    def two_sum(self, arr: List[int], target: int) -> Optional[Tuple[int, int]]:
        arr = sorted(arr)
        left, right = 0, len(arr)-1
        while left < right:
            s = arr[left] + arr[right]
            if s == target: return (arr[left], arr[right])
            elif s < target: left += 1
            else: right -= 1
        return None

    def three_sum(self, arr: List[int], target: int = 0) -> List[Tuple[int, int, int]]:
        arr = sorted(arr); result = []
        for i in range(len(arr)-2):
            if i > 0 and arr[i] == arr[i-1]: continue
            left, right = i+1, len(arr)-1
            while left < right:
                s = arr[i] + arr[left] + arr[right]
                if s == target: result.append((arr[i], arr[left], arr[right])); left += 1; right -= 1
                elif s < target: left += 1
                else: right -= 1
        return result

    def palindrome(self, s: str) -> bool:
        left, right = 0, len(s)-1
        while left < right:
            if s[left] != s[right]: return False
            left += 1; right -= 1
        return True

    def solve(self, *args):
        if self.problem_type == TwoPointerProblem.TWOSUM: return self.two_sum(args[0], args[1])
        if self.problem_type == TwoPointerProblem.THREESUM: return self.three_sum(args[0], args[1] if len(args) > 1 else 0)
        if self.problem_type == TwoPointerProblem.PALINDROME: return self.palindrome(args[0])
        return None

    def stats(self, *args) -> dict:
        return {"problem": self.problem_type.name, "result": self.solve(*args)}

def run():
    tp = TwoPointer(TwoPointerProblem.TWOSUM)
    print("Two sum:", tp.solve([2,7,11,15], 9))
    tp.problem_type = TwoPointerProblem.PALINDROME
    print("Palindrome:", tp.solve("racecar"))

if __name__ == "__main__": run()
