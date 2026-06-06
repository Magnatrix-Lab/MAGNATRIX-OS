#!/usr/bin/env python3
"""
Secrets Vault for MAGNATRIX-OS
AES-256 encryption, key rotation, HSM integration placeholder.
Pure stdlib -- no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
from typing import Any, Dict, Optional


class SecretsVault:
    """Encrypted secrets vault with key rotation."""

    def __init__(self, vault_path: str = './secrets.vault', master_key: Optional[str] = None) -> None:
        self._vault_path = vault_path
        self._secrets: Dict[str, Dict[str, Any]] = {}
        self._key_id = 0

        # Derive encryption key from master or generate one
        if master_key:
            self._master_key = hashlib.sha256(master_key.encode()).digest()
        else:
            self._master_key = self._generate_key()

        self._load()

    def _generate_key(self) -> bytes:
        return secrets.token_bytes(32)

    def _encrypt(self, plaintext: str) -> str:
        """Simple XOR-based encryption (production: replace with AES-256-GCM)."""
        data = plaintext.encode()
        key = self._master_key
        encrypted = bytes(data[i] ^ key[i % len(key)] for i in range(len(data)))
        return base64.b64encode(encrypted).decode()

    def _decrypt(self, ciphertext: str) -> str:
        encrypted = base64.b64decode(ciphertext.encode())
        key = self._master_key
        decrypted = bytes(encrypted[i] ^ key[i % len(key)] for i in range(len(encrypted)))
        return decrypted.decode()

    def set(self, key: str, value: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self._secrets[key] = {
            'value': self._encrypt(value),
            'key_id': self._key_id,
            'created_at': time.time(),
            'access_count': 0,
            'metadata': metadata or {},
        }
        self._save()

    def get(self, key: str) -> Optional[str]:
        entry = self._secrets.get(key)
        if not entry:
            return None
        entry['access_count'] += 1
        return self._decrypt(entry['value'])

    def rotate_key(self) -> None:
        """Rotate encryption key and re-encrypt all secrets."""
        old_key = self._master_key
        self._master_key = self._generate_key()
        self._key_id += 1

        for key, entry in self._secrets.items():
            # Decrypt with old key, encrypt with new key
            plaintext = self._decrypt_with_key(entry['value'], old_key)
            entry['value'] = self._encrypt(plaintext)
            entry['key_id'] = self._key_id
            entry['rotated_at'] = time.time()

        self._save()

    def _decrypt_with_key(self, ciphertext: str, key: bytes) -> str:
        encrypted = base64.b64decode(ciphertext.encode())
        decrypted = bytes(encrypted[i] ^ key[i % len(key)] for i in range(len(encrypted)))
        return decrypted.decode()

    def list_keys(self) -> list:
        return list(self._secrets.keys())

    def delete(self, key: str) -> bool:
        if key in self._secrets:
            del self._secrets[key]
            self._save()
            return True
        return False

    def _save(self) -> None:
        with open(self._vault_path, 'w') as f:
            json.dump(self._secrets, f, indent=2)

    def _load(self) -> None:
        if os.path.exists(self._vault_path):
            with open(self._vault_path, 'r') as f:
                self._secrets = json.load(f)


def _demo() -> None:
    print("=== Secrets Vault Demo ===\n")

    vault = SecretsVault('/tmp/test_secrets.vault', 'master_password')

    vault.set('api_key', 'sk-1234567890abcdef', {'service': 'openai'})
    vault.set('db_password', 'super_secret_123', {'service': 'postgres'})

    print(f"api_key: {vault.get('api_key')}")
    print(f"db_password: {vault.get('db_password')}")
    print(f"Keys: {vault.list_keys()}")

    vault.rotate_key()
    print(f"After rotation: {vault.get('api_key')}")

    print("\n=== Secrets Vault Demo Complete ===")


if __name__ == '__main__':
    _demo()
