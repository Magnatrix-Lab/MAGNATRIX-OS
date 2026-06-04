"""Key Exchange - Diffie-Hellman for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import random
import math

@dataclass
class KeyExchange:
    p: int = 23
    g: int = 5

    def generate_private_key(self) -> int:
        return random.randint(1, self.p - 1)

    def generate_public_key(self, private_key: int) -> int:
        return pow(self.g, private_key, self.p)

    def generate_shared_secret(self, private_key: int, public_key: int) -> int:
        return pow(public_key, private_key, self.p)

    def exchange(self) -> Tuple[int, int, int]:
        alice_private = self.generate_private_key()
        alice_public = self.generate_public_key(alice_private)
        bob_private = self.generate_private_key()
        bob_public = self.generate_public_key(bob_private)
        alice_shared = self.generate_shared_secret(alice_private, bob_public)
        bob_shared = self.generate_shared_secret(bob_private, alice_public)
        return alice_shared, bob_shared, alice_public

    def stats(self) -> dict:
        return {"p": self.p, "g": self.g}

def run():
    ke = KeyExchange(23, 5)
    alice_shared, bob_shared, alice_public = ke.exchange()
    print("Alice shared:", alice_shared)
    print("Bob shared:", bob_shared)
    print("Match:", alice_shared == bob_shared)
    print("Stats:", ke.stats())

if __name__ == "__main__": run()
