"""Native stdlib module: Password Entropy Calculator
Calculates password entropy, strength, and brute-force resistance.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class PasswordEntropyCalculator:
    password: str

    def _charset_size(self) -> int:
        size = 0
        if any(c.islower() for c in self.password):
            size += 26
        if any(c.isupper() for c in self.password):
            size += 26
        if any(c.isdigit() for c in self.password):
            size += 10
        special_chars = set('!@#$%^&*()_+-=[]{}|;\':\"./<>?')
        if any(c in special_chars for c in self.password):
            size += 32
        return size

    def entropy_bits(self) -> float:
        charset = self._charset_size()
        if charset == 0:
            return 0.0
        return len(self.password) * math.log2(charset)

    def strength(self) -> str:
        e = self.entropy_bits()
        if e < 28:
            return "very_weak"
        elif e < 36:
            return "weak"
        elif e < 60:
            return "reasonable"
        elif e < 100:
            return "strong"
        return "very_strong"

    def brute_force_attempts(self) -> float:
        charset = self._charset_size()
        return charset ** len(self.password)

    def estimated_crack_time_seconds(self, guesses_per_second: float = 1e12) -> float:
        if guesses_per_second == 0:
            return float('inf')
        return self.brute_force_attempts() / guesses_per_second

    def stats(self, guesses_per_second: float = 1e12) -> Dict:
        return {
            "length": len(self.password),
            "charset_size": self._charset_size(),
            "entropy_bits": round(self.entropy_bits(), 1),
            "strength": self.strength(),
            "brute_force_attempts": f"{self.brute_force_attempts():.2e}",
            "est_crack_time_sec": round(self.estimated_crack_time_seconds(guesses_per_second), 2),
        }

def run():
    pec = PasswordEntropyCalculator(password="Tr0ub4dor&3!")
    print(pec.stats())

if __name__ == "__main__":
    run()
