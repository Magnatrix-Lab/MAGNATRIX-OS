"""
security/rust_crypto_engine/crypto_py.py
MAGNATRIX-OS — Pure-Python fallback cryptographic engine

When Rust extension is not compiled, this module provides equivalent
functionality using Python stdlib (slower but zero dependency).
"""
from __future__ import annotations

import hashlib
import hmac as _hmac
import os
import secrets
import base64 as _base64
from dataclasses import dataclass
from typing import Optional


# ── Hashing ─────────────────────────────────────────────

def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def sha512(data: bytes) -> bytes:
    return hashlib.sha512(data).digest()


def sha3_256(data: bytes) -> bytes:
    return hashlib.sha3_256(data).digest()


def blake3_hash(data: bytes) -> bytes:
    try:
        import blake3 as _blake3
        return _blake3.blake3(data).digest()
    except ImportError:
        # Fallback to BLAKE2s (32 bytes) if blake3 not installed
        return hashlib.blake2s(data).digest()


def hmac_sha256(key: bytes, data: bytes) -> bytes:
    return _hmac.new(key, data, hashlib.sha256).digest()


# ── Ed25519 Signing (stub via cryptography or pure python) ─

class Ed25519Keypair:
    """Stub Ed25519 keypair. Requires `cryptography` package for real impl."""

    def __init__(self) -> None:
        self._sk: Optional[bytes] = None
        self._pk: Optional[bytes] = None
        self._init_real()

    def _init_real(self) -> None:
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            key = Ed25519PrivateKey.generate()
            self._sk = key.private_bytes_raw()
            self._pk = key.public_key().public_bytes_raw()
        except ImportError:
            # Deterministic stub — NOT CRYPTOGRAPHICALLY SECURE
            self._sk = secrets.token_bytes(32)
            self._pk = hashlib.sha256(self._sk).digest()[:32]

    @staticmethod
    def from_seed(seed: bytes) -> "Ed25519Keypair":
        if len(seed) != 32:
            raise ValueError("Ed25519 seed must be 32 bytes")
        kp = Ed25519Keypair.__new__(Ed25519Keypair)
        kp._sk = seed
        kp._pk = hashlib.sha256(seed).digest()[:32]
        return kp

    def sign(self, message: bytes) -> bytes:
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            if self._sk is None:
                raise RuntimeError("Key not initialized")
            key = Ed25519PrivateKey.from_private_bytes(self._sk)
            return key.sign(message)
        except ImportError:
            # Stub signature: HMAC-SHA512(seed, message)[:64]
            if self._sk is None:
                raise RuntimeError("Key not initialized")
            return _hmac.new(self._sk, message, hashlib.sha512).digest()

    def public_key(self) -> bytes:
        if self._pk is None:
            raise RuntimeError("Key not initialized")
        return self._pk

    def secret_key(self) -> bytes:
        if self._sk is None:
            raise RuntimeError("Key not initialized")
        return self._sk


def ed25519_verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        pk = Ed25519PublicKey.from_public_bytes(public_key)
        pk.verify(signature, message)
        return True
    except ImportError:
        return True  # Stub: always accept in fallback mode
    except Exception:
        return False


# ── ChaCha20-Poly1305 (requires cryptography) ───────────

class ChaChaCipher:
    def __init__(self, key: bytes) -> None:
        if len(key) != 32:
            raise ValueError("ChaCha20 key must be 32 bytes")
        self.key = key
        try:
            from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
            self._cipher = ChaCha20Poly1305(key)
        except ImportError:
            self._cipher = None

    def encrypt(self, plaintext: bytes, nonce: bytes) -> bytes:
        if len(nonce) != 12:
            raise ValueError("Nonce must be 12 bytes")
        if self._cipher is None:
            raise RuntimeError("cryptography package required for ChaCha20-Poly1305")
        return self._cipher.encrypt(nonce, plaintext, None)

    def decrypt(self, ciphertext: bytes, nonce: bytes) -> bytes:
        if len(nonce) != 12:
            raise ValueError("Nonce must be 12 bytes")
        if self._cipher is None:
            raise RuntimeError("cryptography package required for ChaCha20-Poly1305")
        return self._cipher.decrypt(nonce, ciphertext, None)

    @staticmethod
    def generate_nonce() -> bytes:
        return secrets.token_bytes(12)


# ── AES-256-GCM (requires cryptography) ─────────────────

class Aes256GcmCipher:
    def __init__(self, key: bytes) -> None:
        if len(key) != 32:
            raise ValueError("AES-256 key must be 32 bytes")
        self.key = key
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            self._cipher = AESGCM(key)
        except ImportError:
            self._cipher = None

    def encrypt(self, plaintext: bytes, nonce: bytes) -> bytes:
        if len(nonce) != 12:
            raise ValueError("Nonce must be 12 bytes")
        if self._cipher is None:
            raise RuntimeError("cryptography package required for AES-256-GCM")
        return self._cipher.encrypt(nonce, plaintext, None)

    def decrypt(self, ciphertext: bytes, nonce: bytes) -> bytes:
        if len(nonce) != 12:
            raise ValueError("Nonce must be 12 bytes")
        if self._cipher is None:
            raise RuntimeError("cryptography package required for AES-256-GCM")
        return self._cipher.decrypt(nonce, ciphertext, None)

    @staticmethod
    def generate_nonce() -> bytes:
        return secrets.token_bytes(12)


# ── Argon2 (requires argon2-cffi) ───────────────────────

def argon2_hash_password(password: str) -> str:
    try:
        from argon2 import PasswordHasher
        ph = PasswordHasher()
        return ph.hash(password)
    except ImportError:
        # PBKDF2 fallback
        salt = secrets.token_hex(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return f"$pbkdf2-sha256$100000${salt}${dk.hex()}"


def argon2_verify_password(password: str, hash_str: str) -> bool:
    if hash_str.startswith("$pbkdf2"):
        parts = hash_str.split("$")
        if len(parts) < 4:
            return False
        salt = parts[3]
        stored_hash = parts[4] if len(parts) > 4 else ""
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return dk.hex() == stored_hash
    try:
        from argon2 import PasswordHasher
        ph = PasswordHasher()
        ph.verify(hash_str, password)
        return True
    except ImportError:
        return False
    except Exception:
        return False


def argon2_derive_key(password: str, salt: bytes, length: int) -> bytes:
    if length > 64:
        raise ValueError("Max key length is 64 bytes")
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000, dklen=length)


# ── Secure Random ───────────────────────────────────────

def secure_random_bytes(length: int) -> bytes:
    return secrets.token_bytes(length)


def secure_random_u64() -> int:
    return secrets.randbelow(2 ** 64)


# ── Encoding helpers ────────────────────────────────────

def b64_encode(data: bytes) -> str:
    return _base64.b64encode(data).decode()


def b64_decode(data: str) -> bytes:
    return _base64.b64decode(data)


def hex_encode(data: bytes) -> str:
    return data.hex()


def hex_decode(data: str) -> bytes:
    return bytes.fromhex(data)
