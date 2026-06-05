"""Native stdlib module: Wallet Security Calculator
Calculates wallet security scores and recovery phrase entropy.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class WalletSecurityCalculator:
    mnemonic_words: int = 12
    has_hardware_wallet: bool = False
    has_2fa: bool = False
    has_backup: bool = False
    has_multisig: bool = False
    password_length: int = 0

    def phrase_entropy_bits(self) -> float:
        wordlist_size = 2048
        return math.log2(wordlist_size) * self.mnemonic_words

    def possible_combinations(self) -> float:
        return 2048 ** self.mnemonic_words

    def security_score(self) -> int:
        score = 0
        if self.mnemonic_words >= 24:
            score += 30
        elif self.mnemonic_words >= 12:
            score += 20
        if self.has_hardware_wallet:
            score += 25
        if self.has_2fa:
            score += 15
        if self.has_backup:
            score += 15
        if self.has_multisig:
            score += 15
        if self.password_length >= 16:
            score += 10
        elif self.password_length >= 8:
            score += 5
        return min(100, score)

    def security_level(self) -> str:
        s = self.security_score()
        if s >= 80:
            return "excellent"
        elif s >= 60:
            return "good"
        elif s >= 40:
            return "moderate"
        elif s >= 20:
            return "weak"
        return "very_weak"

    def brute_force_resistance(self) -> str:
        entropy = self.phrase_entropy_bits()
        if entropy >= 256:
            return "infeasible"
        elif entropy >= 128:
            return "very_high"
        elif entropy >= 64:
            return "high"
        return "moderate"

    def stats(self) -> Dict:
        return {
            "mnemonic_words": self.mnemonic_words,
            "entropy_bits": round(self.phrase_entropy_bits(), 1),
            "possible_combinations": f"{self.possible_combinations():.2e}",
            "security_score": self.security_score(),
            "security_level": self.security_level(),
            "brute_force_resistance": self.brute_force_resistance(),
        }

def run():
    wsc = WalletSecurityCalculator(mnemonic_words=24, has_hardware_wallet=True, has_2fa=True, has_backup=True, has_multisig=False, password_length=16)
    print(wsc.stats())

if __name__ == "__main__":
    run()
