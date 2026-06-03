"""Consensus Proof - Proof-of-work/stake for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum, auto
import hashlib
import time

class ProofType(Enum):
    WORK = auto(); STAKE = auto()

@dataclass
class ConsensusProof:
    proof_type: ProofType = ProofType.WORK
    difficulty: int = 2

    def verify_pow(self, data: str, nonce: int) -> bool:
        h = hashlib.sha256(f"{data}{nonce}".encode()).hexdigest()
        return h.startswith("0" * self.difficulty)

    def find_nonce(self, data: str) -> int:
        nonce = 0
        while not self.verify_pow(data, nonce):
            nonce += 1
        return nonce

    def verify_pos(self, stake: float, random_value: float, threshold: float) -> bool:
        return stake * random_value < threshold

    def stats(self, data: str) -> dict:
        nonce = self.find_nonce(data)
        return {"type": self.proof_type.name, "nonce": nonce, "verified": self.verify_pow(data, nonce)}

def run():
    cp = ConsensusProof(ProofType.WORK, 2)
    print("Nonce:", cp.find_nonce("block1"))
    print("Stats:", cp.stats("block1"))

if __name__ == "__main__": run()
