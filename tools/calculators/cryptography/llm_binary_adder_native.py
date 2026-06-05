"""Binary Adder — half adder, full adder, ripple carry, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto

class BinaryAdder:
    def __init__(self):
        pass

    def half_adder(self, a: bool, b: bool) -> Tuple[bool, bool]:
        sum_out = a ^ b
        carry_out = a and b
        return sum_out, carry_out

    def full_adder(self, a: bool, b: bool, cin: bool) -> Tuple[bool, bool]:
        s1, c1 = self.half_adder(a, b)
        sum_out, c2 = self.half_adder(s1, cin)
        carry_out = c1 or c2
        return sum_out, carry_out

    def ripple_carry_add(self, a: List[bool], b: List[bool], cin: bool = False) -> Tuple[List[bool], bool]:
        result = []
        carry = cin
        for i in range(max(len(a), len(b))):
            ai = a[i] if i < len(a) else False
            bi = b[i] if i < len(b) else False
            s, carry = self.full_adder(ai, bi, carry)
            result.append(s)
        return result, carry

    def add_int(self, a: int, b: int, bits: int = 8) -> int:
        ab = [(a >> i) & 1 == 1 for i in range(bits)]
        bb = [(b >> i) & 1 == 1 for i in range(bits)]
        result, carry = self.ripple_carry_add(ab, bb)
        out = 0
        for i, r in enumerate(result):
            if r:
                out |= (1 << i)
        return out

    def stats(self) -> Dict:
        return {"type": "ripple_carry_adder"}

def run():
    adder = BinaryAdder()
    print("Half adder 1+1:", adder.half_adder(True, True))
    print("Full adder 1+1+1:", adder.full_adder(True, True, True))
    a = [True, True, False, True]  # 1011 = 11
    b = [True, False, True, True]  # 1101 = 13
    result, carry = adder.ripple_carry_add(a, b)
    print("Ripple carry:", result, "carry:", carry)
    print(adder.add_int(11, 13, 8))
    print(adder.stats())

if __name__ == "__main__":
    run()
