"""Hash Function - Simple hashing for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import hashlib

class HashType(Enum):
    MD5 = auto(); SHA256 = auto(); CUSTOM = auto()

@dataclass
class HashFunction:
    hash_type: HashType = HashType.SHA256

    def hash(self, data: str) -> str:
        if self.hash_type == HashType.MD5:
            return hashlib.md5(data.encode()).hexdigest()
        elif self.hash_type == HashType.SHA256:
            return hashlib.sha256(data.encode()).hexdigest()
        elif self.hash_type == HashType.CUSTOM:
            h = 0
            for c in data:
                h = (h * 31 + ord(c)) % (2**32)
            return hex(h)[2:]
        return ""

    def verify(self, data: str, expected: str) -> bool:
        return self.hash(data) == expected

    def stats(self, data: str) -> dict:
        return {"type": self.hash_type.name, "hash": self.hash(data)[:16], "length": len(self.hash(data))}

def run():
    hf = HashFunction(HashType.SHA256)
    h = hf.hash("hello world")
    print("Hash:", h[:16])
    print("Verify:", hf.verify("hello world", h))
    print("Stats:", hf.stats("hello world"))

if __name__ == "__main__": run()
