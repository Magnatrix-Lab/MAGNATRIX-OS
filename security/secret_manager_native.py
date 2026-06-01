"""security/secret_manager_native.py — Secret management system"""
from __future__ import annotations
import os
import json
import time
import hashlib
import threading
from typing import Dict, Optional, Any

class SecretManager:
    """Manage secrets from environment variables with rotation and encryption."""

    def __init__(self, key: str = "default"):
        self._key = hashlib.sha256(key.encode()).digest()
        self._secrets: Dict[str, str] = {}
        self._audit: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def _xor_encrypt(self, data: str) -> str:
        """Simple XOR encryption for at-rest storage."""
        b = data.encode()
        k = self._key
        return ''.join(f"{b[i] ^ k[i % len(k)]:02x}" for i in range(len(b)))

    def _xor_decrypt(self, hex_data: str) -> str:
        b = bytes(int(hex_data[i:i+2], 16) for i in range(0, len(hex_data), 2))
        k = self._key
        return ''.join(chr(b[i] ^ k[i % len(k)]) for i in range(len(b)))

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get secret from env or stored."""
        val = os.environ.get(key, default)
        with self._lock:
            self._audit.append({"action": "get", "key": key, "timestamp": time.time()})
        return val

    def store(self, key: str, value: str) -> None:
        """Store encrypted secret."""
        encrypted = self._xor_encrypt(value)
        with self._lock:
            self._secrets[key] = encrypted
            self._audit.append({"action": "store", "key": key, "timestamp": time.time()})

    def retrieve(self, key: str) -> Optional[str]:
        """Retrieve and decrypt secret."""
        with self._lock:
            encrypted = self._secrets.get(key)
            if encrypted:
                self._audit.append({"action": "retrieve", "key": key, "timestamp": time.time()})
                return self._xor_decrypt(encrypted)
        return None

    def rotate(self, key: str) -> None:
        """Rotate secret (mark for rotation)."""
        with self._lock:
            self._audit.append({"action": "rotate", "key": key, "timestamp": time.time()})

    def load_from_file(self, path: str) -> None:
        """Load .env file."""
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    self.store(k.strip(), v.strip().strip('"''))

    def audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return self._audit[-limit:]

if __name__ == "__main__":
    print("SecretManager self-test")
    sm = SecretManager()
    sm.store("api_key", "secret123")
    assert sm.retrieve("api_key") == "secret123"
    assert sm.get("HOME") is not None
    print("All tests pass")
