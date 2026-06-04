"""Symmetric Cipher - Caesar/substitution for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import random

class CipherType(Enum):
    CAESAR = auto(); SUBSTITUTION = auto(); VIGENERE = auto()

@dataclass
class SymmetricCipher:
    cipher_type: CipherType = CipherType.CAESAR
    key: str = ""

    def encrypt(self, plaintext: str) -> str:
        if self.cipher_type == CipherType.CAESAR:
            shift = int(self.key) if self.key.isdigit() else 3
            return "".join(chr((ord(c) + shift - 65) % 26 + 65) if c.isupper() else chr((ord(c) + shift - 97) % 26 + 97) if c.islower() else c for c in plaintext)
        elif self.cipher_type == CipherType.SUBSTITUTION:
            if not self.key:
                alphabet = list("abcdefghijklmnopqrstuvwxyz")
                shuffled = alphabet[:]
                random.shuffle(shuffled)
                self.key = "".join(shuffled)
            mapping = {chr(97+i): self.key[i] for i in range(26)}
            return "".join(mapping.get(c.lower(), c) for c in plaintext)
        elif self.cipher_type == CipherType.VIGENERE:
            if not self.key: self.key = "key"
            result = ""
            for i, c in enumerate(plaintext):
                if c.isalpha():
                    shift = ord(self.key[i % len(self.key)].lower()) - 97
                    base = 65 if c.isupper() else 97
                    result += chr((ord(c) - base + shift) % 26 + base)
                else:
                    result += c
            return result
        return plaintext

    def decrypt(self, ciphertext: str) -> str:
        if self.cipher_type == CipherType.CAESAR:
            shift = int(self.key) if self.key.isdigit() else 3
            return self.encrypt(ciphertext)  # Caesar is symmetric
        return ciphertext

    def stats(self) -> dict:
        return {"type": self.cipher_type.name, "key_length": len(self.key)}

def run():
    sc = SymmetricCipher(CipherType.CAESAR, "3")
    encrypted = sc.encrypt("Hello World")
    print("Encrypted:", encrypted)
    print("Stats:", sc.stats())

if __name__ == "__main__": run()
