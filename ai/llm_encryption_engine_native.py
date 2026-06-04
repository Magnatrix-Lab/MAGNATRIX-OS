"""Encryption Engine - Symmetric encryption for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import hashlib
import base64

class CipherType(Enum):
    CAESAR = auto(); XOR = auto(); AES = auto()

@dataclass
class EncryptionEngine:
    cipher_type: CipherType = CipherType.XOR
    key: str = "default_key"
    
    def _derive_key(self, length: int) -> bytes:
        return hashlib.sha256(self.key.encode()).digest()[:length]
    
    def encrypt(self, plaintext: str) -> str:
        if self.cipher_type == CipherType.CAESAR:
            shift = sum(ord(c) for c in self.key) % 26
            return "".join(chr((ord(c) - 65 + shift) % 26 + 65) if c.isupper() else chr((ord(c) - 97 + shift) % 26 + 97) if c.islower() else c for c in plaintext)
        elif self.cipher_type == CipherType.XOR:
            key_bytes = self._derive_key(1)
            encrypted = bytes([ord(c) ^ key_bytes[0] for c in plaintext])
            return base64.b64encode(encrypted).decode()
        return plaintext
    
    def decrypt(self, ciphertext: str) -> str:
        if self.cipher_type == CipherType.CAESAR:
            shift = sum(ord(c) for c in self.key) % 26
            return "".join(chr((ord(c) - 65 - shift) % 26 + 65) if c.isupper() else chr((ord(c) - 97 - shift) % 26 + 97) if c.islower() else c for c in ciphertext)
        elif self.cipher_type == CipherType.XOR:
            key_bytes = self._derive_key(1)
            encrypted = base64.b64decode(ciphertext)
            return "".join(chr(b ^ key_bytes[0]) for b in encrypted)
        return ciphertext
    
    def stats(self) -> dict:
        return {"cipher": self.cipher_type.name, "key_hash": hashlib.sha256(self.key.encode()).hexdigest()[:8]}

def run():
    ee = EncryptionEngine(CipherType.XOR, "secret")
    msg = "Hello World"
    encrypted = ee.encrypt(msg)
    decrypted = ee.decrypt(encrypted)
    print(f"Original: {msg}")
    print(f"Encrypted: {encrypted}")
    print(f"Decrypted: {decrypted}")
    print("Stats:", ee.stats())

if __name__ == "__main__": run()
