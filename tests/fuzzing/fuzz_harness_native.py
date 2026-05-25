#!/usr/bin/env python3
"""
tests/fuzzing/fuzz_harness_native.py
====================================
Fuzzing Harness for MAGNATRIX-OS

Property-based testing + random input generation for boundary functions.
"""

from __future__ import annotations

import random
import string
from typing import Any, Callable, List, Tuple


class FuzzHarness:
    """Generate random inputs to test boundary functions."""

    @staticmethod
    def random_string(min_len: int = 0, max_len: int = 1000) -> str:
        length = random.randint(min_len, max_len)
        chars = string.ascii_letters + string.digits + string.punctuation + "\x00\n\r\t"
        return "".join(random.choice(chars) for _ in range(length))

    @staticmethod
    def random_bytes(min_len: int = 0, max_len: int = 10000) -> bytes:
        length = random.randint(min_len, max_len)
        return bytes(random.randint(0, 255) for _ in range(length))

    @staticmethod
    def random_int(min_val: int = -10**9, max_val: int = 10**9) -> int:
        return random.randint(min_val, max_val)

    @staticmethod
    def random_dict(max_keys: int = 10, max_depth: int = 3) -> dict:
        if max_depth <= 0:
            return random.choice([None, True, False, random.randint(0, 100), FuzzHarness.random_string(0, 20)])
        result = {}
        for _ in range(random.randint(0, max_keys)):
            key = FuzzHarness.random_string(1, 20)
            val_type = random.randint(0, 4)
            if val_type == 0:
                result[key] = FuzzHarness.random_string(0, 100)
            elif val_type == 1:
                result[key] = FuzzHarness.random_int()
            elif val_type == 2:
                result[key] = FuzzHarness.random_dict(max_keys // 2, max_depth - 1)
            elif val_type == 3:
                result[key] = [FuzzHarness.random_int() for _ in range(random.randint(0, 10))]
            else:
                result[key] = None
        return result

    @staticmethod
    def fuzz(func: Callable, iterations: int = 1000, arg_generators: List[Callable] = None) -> Tuple[int, int, List[Exception]]:
        """Fuzz a function with random inputs.
        Returns (passed, total, exceptions)."""
        passed = 0
        exceptions = []
        for i in range(iterations):
            try:
                if arg_generators:
                    args = [g() for g in arg_generators]
                    func(*args)
                else:
                    func(FuzzHarness.random_string())
                passed += 1
            except Exception as e:
                exceptions.append(e)
        return passed, iterations, exceptions


def demo():
    print("=" * 60)
    print("MAGNATRIX-OS  |  FUZZ HARNESS DEMO")
    print("=" * 60)

    # Fuzz string length
    passed, total, excs = FuzzHarness.fuzz(len, 1000, [FuzzHarness.random_string])
    print(f"Fuzzing len(): {passed}/{total} passed, {len(excs)} exceptions")

    # Fuzz hash (should not crash)
    def safe_hash(s: str):
        return hash(s) % (2**31)
    passed, total, excs = FuzzHarness.fuzz(safe_hash, 500, [FuzzHarness.random_string])
    print(f"Fuzzing hash(): {passed}/{total} passed, {len(excs)} exceptions")

    print("=" * 60)


if __name__ == "__main__":
    demo()
