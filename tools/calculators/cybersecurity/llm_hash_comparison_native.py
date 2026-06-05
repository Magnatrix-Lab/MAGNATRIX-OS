"""Native stdlib module: Hash Comparison Tool
Compares hash values and calculates collision probability.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class HashComparisonTool:
    hash_function: str
    hash_size_bits: int
    num_hashes: int

    def total_possible_hashes(self) -> float:
        return 2 ** self.hash_size_bits

    def collision_probability(self) -> float:
        if self.total_possible_hashes() == 0:
            return 1.0
        n = self.num_hashes
        m = self.total_possible_hashes()
        return 1 - math.exp(-n * (n - 1) / (2 * m))

    def collision_probability_approx_pct(self) -> float:
        return self.collision_probability() * 100

    def birthday_bound(self) -> int:
        return int(math.sqrt(2 * self.total_possible_hashes() * math.log(2)))

    def recommended_max_hashes(self) -> int:
        return int(self.total_possible_hashes() ** 0.5)

    def stats(self) -> Dict:
        return {
            "hash_function": self.hash_function,
            "hash_size_bits": self.hash_size_bits,
            "num_hashes": self.num_hashes,
            "total_possible": f"{self.total_possible_hashes():.2e}",
            "collision_probability_pct": round(self.collision_probability_approx_pct(), 10),
            "birthday_bound": self.birthday_bound(),
            "recommended_max_hashes": self.recommended_max_hashes(),
        }

def run():
    hct = HashComparisonTool(hash_function="SHA-256", hash_size_bits=256, num_hashes=1e15)
    print(hct.stats())

if __name__ == "__main__":
    run()
