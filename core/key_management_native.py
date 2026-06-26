#!/usr/bin/env python3
"""Key Management for MAGNATRIX-OS — Encryption key lifecycle."""
from __future__ import annotations
import hashlib, hmac, secrets, time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class Key:
    id: str
    key_bytes: bytes
    algorithm: str = "AES-256"
    created_at: float = field(default_factory=time.time)
    purpose: str = "encryption"

class KeyManagement:
    def __init__(self) -> None:
        self._keys: Dict[str, Key] = {}
        self._key_counter = 0

    def generate_key(self, purpose: str = "encryption", algorithm: str = "AES-256") -> Key:
        self._key_counter += 1
        key_id = f"key_{self._key_counter}_{int(time.time())}"
        key_bytes = secrets.token_bytes(32)
        key = Key(id=key_id, key_bytes=key_bytes, algorithm=algorithm, purpose=purpose)
        self._keys[key_id] = key
        return key

    def get_key(self, key_id: str) -> Optional[Key]:
        return self._keys.get(key_id)

    def rotate_key(self, key_id: str) -> Optional[Key]:
        old = self._keys.get(key_id)
        if old:
            new = self.generate_key(old.purpose, old.algorithm)
            return new
        return None

    def revoke(self, key_id: str) -> bool:
        return self._keys.pop(key_id, None) is not None

    def stats(self) -> Dict[str, Any]:
        return {"keys": len(self._keys), "purposes": list(set(k.purpose for k in self._keys.values()))}
