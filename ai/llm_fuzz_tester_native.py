"""LLM Fuzz Tester — Native Python (stdlib only)."""
from __future__ import annotations
import random, string
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto

class FuzzStrategy(Enum):
    RANDOM = auto()
    BOUNDARY = auto()
    MUTATION = auto()
    GRAMMATICAL = auto()

@dataclass
class FuzzResult:
    id: str
    input_data: str
    output_data: str
    exception: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class FuzzTester:
    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)
        self._results: List[FuzzResult] = []

    def random_string(self, min_len: int = 1, max_len: int = 100) -> str:
        length = self._rng.randint(min_len, max_len)
        chars = string.ascii_letters + string.digits + string.punctuation + " \t\n"
        return "".join(self._rng.choice(chars) for _ in range(length))

    def boundary_string(self) -> str:
        candidates = ["", "a", "a" * 1000, "\x00", "\xff", "<script>", "' OR '1'='1", "; DROP TABLE", "\n" * 100, " " * 1000]
        return self._rng.choice(candidates)

    def mutate(self, base: str) -> str:
        if not base:
            return self.random_string()
        pos = self._rng.randint(0, len(base) - 1)
        chars = list(base)
        chars[pos] = self._rng.choice(string.printable)
        return "".join(chars)

    def generate(self, strategy: FuzzStrategy, count: int, base: Optional[str] = None) -> List[str]:
        inputs = []
        for _ in range(count):
            if strategy == FuzzStrategy.RANDOM:
                inputs.append(self.random_string())
            elif strategy == FuzzStrategy.BOUNDARY:
                inputs.append(self.boundary_string())
            elif strategy == FuzzStrategy.MUTATION and base:
                inputs.append(self.mutate(base))
            else:
                inputs.append(self.random_string())
        return inputs

    def test(self, target_fn: Callable[[str], str], inputs: List[str]) -> List[FuzzResult]:
        for i, inp in enumerate(inputs):
            try:
                out = target_fn(inp)
                result = FuzzResult("f" + str(i), inp, out)
            except Exception as ex:
                result = FuzzResult("f" + str(i), inp, "", str(ex))
            self._results.append(result)
        return self._results

    def get_stats(self) -> Dict[str, Any]:
        errors = [r for r in self._results if r.exception]
        return {"total": len(self._results), "errors": len(errors), "error_rate": len(errors) / len(self._results) if self._results else 0.0}

def run() -> None:
    print("Fuzz Tester test")
    e = FuzzTester(seed=42)
    inputs = e.generate(FuzzStrategy.RANDOM, 5)
    results = e.test(lambda x: x.upper(), inputs)
    for r in results:
        print("  " + r.id + ": " + ("ERROR: " + r.exception if r.exception else "OK"))
    print("  Stats: " + str(e.get_stats()))
    print("Fuzz Tester test complete.")

if __name__ == "__main__":
    run()
