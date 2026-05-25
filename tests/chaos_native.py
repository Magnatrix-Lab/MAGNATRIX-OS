#!/usr/bin/env python3
"""
tests/chaos_native.py
=====================
Chaos Engineering Suite for MAGNATRIX-OS

Provides:
  - Random process kill (simulate node failure)
  - Network partition simulation (Raft)
  - Memory pressure injection
  - File corruption injection
  - Fuzzing harness for boundary functions
"""

from __future__ import annotations

import os
import random
import signal
import subprocess
import time
from typing import Any, Callable, Dict, List, Optional


class ChaosMonkey:
    """Inject chaos into MAGNATRIX-OS components."""

    def __init__(self, seed: int = 42) -> None:
        random.seed(seed)

    def random_kill(self, pid: int, probability: float = 0.1) -> bool:
        """Randomly send SIGKILL to a process."""
        if random.random() < probability:
            try:
                os.kill(pid, signal.SIGKILL)
                return True
            except Exception:
                pass
        return False

    def memory_pressure(self, size_mb: int = 100) -> List[Any]:
        """Allocate memory to simulate pressure."""
        return [bytearray(1024 * 1024) for _ in range(size_mb)]

    def corrupt_file(self, path: str, probability: float = 0.1) -> bool:
        """Randomly corrupt bytes in a file."""
        if random.random() < probability:
            try:
                with open(path, "r+b") as f:
                    data = bytearray(f.read())
                    if data:
                        idx = random.randint(0, len(data) - 1)
                        data[idx] = random.randint(0, 255)
                        f.seek(0)
                        f.write(data)
                        return True
            except Exception:
                pass
        return False

    def network_partition(self, duration_sec: float = 5.0) -> None:
        """Simulate network partition by dropping packets (iptables stub)."""
        print(f"[CHAOS] Network partition for {duration_sec}s")
        time.sleep(duration_sec)


class Fuzzer:
    """Simple fuzzing harness for native functions."""

    def __init__(self) -> None:
        self.results: List[Dict[str, Any]] = []

    def fuzz_string(self, fn: Callable[[str], Any], iterations: int = 100) -> Dict[str, int]:
        """Fuzz a function that takes a string."""
        crashes = 0
        for i in range(iterations):
            # Generate random string
            length = random.randint(0, 1000)
            payload = bytes(random.randint(0, 255) for _ in range(length))
            try:
                fn(payload.decode("utf-8", errors="replace"))
            except (ValueError, TypeError):
                pass  # Expected validation errors
            except Exception:
                crashes += 1
        return {"iterations": iterations, "crashes": crashes}

    def fuzz_bytes(self, fn: Callable[[bytes], Any], iterations: int = 100) -> Dict[str, int]:
        crashes = 0
        for i in range(iterations):
            length = random.randint(0, 10000)
            payload = bytes(random.randint(0, 255) for _ in range(length))
            try:
                fn(payload)
            except (ValueError, TypeError):
                pass
            except Exception:
                crashes += 1
        return {"iterations": iterations, "crashes": crashes}

    def fuzz_dict(self, fn: Callable[[Dict], Any], iterations: int = 100) -> Dict[str, int]:
        crashes = 0
        for i in range(iterations):
            depth = random.randint(0, 5)
            payload = self._random_dict(depth)
            try:
                fn(payload)
            except (ValueError, TypeError):
                pass
            except Exception:
                crashes += 1
        return {"iterations": iterations, "crashes": crashes}

    def _random_dict(self, depth: int) -> Dict[str, Any]:
        if depth <= 0:
            return {}
        result = {}
        for _ in range(random.randint(0, 10)):
            key = "k" + str(random.randint(0, 100))
            t = random.randint(0, 4)
            if t == 0:
                result[key] = random.randint(-1000000, 1000000)
            elif t == 1:
                result[key] = random.random()
            elif t == 2:
                result[key] = "s" * random.randint(0, 100)
            elif t == 3:
                result[key] = self._random_dict(depth - 1)
            else:
                result[key] = None
        return result


def demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS  |  CHAOS ENGINEERING")
    print("=" * 60)
    fuzz = Fuzzer()

    # Fuzz string validator
    sys.path.insert(0, "kernel")
    from validate_input_native import StringValidator
    sv = StringValidator(max_len=100)
    result = fuzz.fuzz_string(lambda s: sv(s), iterations=50)
    print(f"StringValidator fuzz: {result}")

    # Fuzz path guard
    sys.path.insert(0, "storage")
    from file_ops_native import exists
    result = fuzz.fuzz_string(lambda s: exists(s), iterations=50)
    print(f"PathGuard.exists fuzz: {result}")

    print("=" * 60)


if __name__ == "__main__":
    demo()
