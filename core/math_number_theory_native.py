"""Math Number Theory -- GCD, modular inverse, prime sieve, factorization."""
from dataclasses import dataclass
from pathlib import Path
import json, math

@dataclass
class NumberTheoryResult:
    op: str = ""
    inputs: list = None
    result = None
    prime_factors: list[int] = None

    def __post_init__(self):
        if self.inputs is None:
            self.inputs = []
        if self.prime_factors is None:
            self.prime_factors = []

class MathNumberTheory:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._results: list[NumberTheoryResult] = []
        self._primes_cache: list[int] = []
        self._persist_path = self.root / "math_number_theory.json"
        self._load()
        if not self._primes_cache:
            self._primes_cache = self._sieve(1000)

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._results = [NumberTheoryResult(**r) for r in data.get("results", [])]
            self._primes_cache = data.get("primes", [])

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "results": [r.__dict__ for r in self._results],
            "primes": self._primes_cache
        }, indent=2))

    def _sieve(self, n: int) -> list[int]:
        sieve = [True] * (n + 1)
        sieve[0] = sieve[1] = False
        for i in range(2, int(math.sqrt(n)) + 1):
            if sieve[i]:
                for j in range(i * i, n + 1, i):
                    sieve[j] = False
        return [i for i in range(2, n + 1) if sieve[i]]

    def gcd(self, a: int, b: int) -> int:
        while b:
            a, b = b, a % b
        r = NumberTheoryResult(op="gcd", inputs=[a, b], result=a)
        self._results.append(r)
        self._save()
        return a

    def lcm(self, a: int, b: int) -> int:
        g = self.gcd(a, b)
        l = abs(a * b) // g if g != 0 else 0
        r = NumberTheoryResult(op="lcm", inputs=[a, b], result=l)
        self._results.append(r)
        self._save()
        return l

    def modular_inverse(self, a: int, m: int) -> int | None:
        def extended_gcd(a, b):
            if b == 0:
                return (a, 1, 0)
            g, x1, y1 = extended_gcd(b, a % b)
            return (g, y1, x1 - (a // b) * y1)
        g, x, _ = extended_gcd(a % m, m)
        if g != 1:
            return None
        inv = x % m
        r = NumberTheoryResult(op="modular_inverse", inputs=[a, m], result=inv)
        self._results.append(r)
        self._save()
        return inv

    def factorize(self, n: int) -> list[int]:
        factors = []
        d = 2
        while d * d <= n:
            while n % d == 0:
                factors.append(d)
                n //= d
            d += 1
        if n > 1:
            factors.append(n)
        r = NumberTheoryResult(op="factorize", inputs=[n], prime_factors=factors)
        self._results.append(r)
        self._save()
        return factors

    def is_prime(self, n: int) -> bool:
        if n < 2:
            return False
        for p in self._primes_cache:
            if p * p > n:
                break
            if n % p == 0:
                return False
        return True

    def to_dict(self) -> dict:
        return {"result_count": len(self._results), "primes_cached": len(self._primes_cache)}

    def get_stats(self) -> dict:
        by_op = {}
        for r in self._results:
            by_op[r.op] = by_op.get(r.op, 0) + 1
        return {"results": len(self._results), "by_operation": by_op, "primes_cached": len(self._primes_cache)}

__all__ = ["MathNumberTheory", "NumberTheoryResult"]
