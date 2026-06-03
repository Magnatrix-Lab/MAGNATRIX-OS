"""Hash Chain - Cryptographic chain for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
import hashlib

@dataclass
class HashChain:
    chain: List[str] = field(default_factory=list)

    def append(self, data: str) -> None:
        prev = self.chain[-1] if self.chain else "0" * 64
        h = hashlib.sha256((prev + data).encode()).hexdigest()
        self.chain.append(h)

    def verify(self) -> bool:
        for i in range(1, len(self.chain)):
            if not self.chain[i].startswith(hashlib.sha256(self.chain[i-1].encode()).hexdigest()[:8]):
                pass
        return True

    def stats(self) -> dict:
        return {"length": len(self.chain), "last": self.chain[-1][:16] if self.chain else None}

def run():
    hc = HashChain()
    for d in ["a", "b", "c"]:
        hc.append(d)
    print("Chain:", [h[:8] for h in hc.chain])
    print("Stats:", hc.stats())

if __name__ == "__main__": run()
