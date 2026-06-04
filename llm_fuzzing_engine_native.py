"""Fuzzing Engine — random input generation, crash detection, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Optional, Any, Tuple
from enum import Enum, auto
import random
import string
import traceback

class FuzzStrategy(Enum):
    RANDOM = auto()
    MUTATION = auto()
    DICTIONARY = auto()

@dataclass
class FuzzCrash:
    crash_id: str
    input_data: Any
    exception: str
    traceback_str: str
    iteration: int

class FuzzingEngine:
    def __init__(self, strategy: FuzzStrategy = FuzzStrategy.RANDOM):
        self.strategy = strategy
        self.crashes: List[FuzzCrash] = []
        self.iterations = 0
        self.dictionary: List[Any] = []
        self.seed_corpus: List[Any] = []

    def add_dictionary_entry(self, entry: Any):
        self.dictionary.append(entry)

    def add_seed(self, seed: Any):
        self.seed_corpus.append(seed)

    def _generate_random(self, type_hint: str = "string", length: int = 10) -> Any:
        if type_hint == "string":
            return "".join(random.choices(string.printable, k=length))
        elif type_hint == "int":
            return random.randint(-1000000, 1000000)
        elif type_hint == "float":
            return random.uniform(-1000000, 1000000)
        elif type_hint == "bytes":
            return bytes(random.randint(0, 255) for _ in range(length))
        elif type_hint == "list":
            return [random.randint(-100, 100) for _ in range(length)]
        return None

    def _mutate(self, base: Any) -> Any:
        if isinstance(base, str):
            chars = list(base)
            if chars:
                pos = random.randint(0, len(chars) - 1)
                chars[pos] = random.choice(string.printable)
            return "".join(chars)
        elif isinstance(base, (list, bytes)):
            if base:
                pos = random.randint(0, len(base) - 1)
                base = list(base)
                base[pos] = random.randint(0, 255) if isinstance(base, list) else bytes([random.randint(0, 255)])
            return base
        elif isinstance(base, int):
            return base + random.randint(-10, 10)
        elif isinstance(base, float):
            return base + random.uniform(-1, 1)
        return base

    def _generate_input(self) -> Any:
        if self.strategy == FuzzStrategy.DICTIONARY and self.dictionary:
            return random.choice(self.dictionary)
        elif self.strategy == FuzzStrategy.MUTATION and self.seed_corpus:
            return self._mutate(random.choice(self.seed_corpus))
        return self._generate_random()

    def fuzz(self, target: Callable[[Any], Any], iterations: int = 100, type_hint: str = "string") -> List[FuzzCrash]:
        for i in range(iterations):
            self.iterations += 1
            input_data = self._generate_input() if self.strategy != FuzzStrategy.RANDOM else self._generate_random(type_hint)
            try:
                target(input_data)
            except Exception as e:
                crash = FuzzCrash(str(len(self.crashes)), input_data, str(e), traceback.format_exc(), i)
                self.crashes.append(crash)
        return self.crashes

    def stats(self) -> Dict:
        return {"iterations": self.iterations, "crashes": len(self.crashes), "unique_crashes": len(set(c.exception for c in self.crashes))}

def run():
    engine = FuzzingEngine(FuzzStrategy.MUTATION)
    engine.add_seed("hello")
    def target(x):
        if isinstance(x, str) and len(x) > 50:
            raise ValueError("Too long")
    engine.fuzz(target, 100, "string")
    print(engine.stats())

if __name__ == "__main__":
    run()
