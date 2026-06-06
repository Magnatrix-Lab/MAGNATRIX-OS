#!/usr/bin/env python3
"""
Crypto Utilities for MAGNATRIX-OS
Symmetric encryption, hashing, signing, key derivation, and
secure random generation. Native stdlib only (hashlib, hmac, secrets).

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import base64
import dataclasses
import hashlib
import hmac
import json
import os
import secrets
import struct
import time
from typing import Any, Dict, Optional, Tuple


class CryptoUtilities:
    """Native-only cryptography utilities for MAGNATRIX-OS."""

    # ------------------------------------------------------------------
    # Hashing
    # ------------------------------------------------------------------

    @staticmethod
    def sha256(data: str | bytes) -> str:
        if isinstance(data, str):
            data = data.encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def sha512(data: str | bytes) -> str:
        if isinstance(data, str):
            data = data.encode("utf-8")
        return hashlib.sha512(data).hexdigest()

    @staticmethod
    def blake2b(data: str | bytes, digest_size: int = 32) -> str:
        if isinstance(data, str):
            data = data.encode("utf-8")
        return hashlib.blake2b(data, digest_size=digest_size).hexdigest()

    @staticmethod
    def hash_file(path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    # ------------------------------------------------------------------
    # Key Derivation
    # ------------------------------------------------------------------

    @staticmethod
    def pbkdf2(password: str, salt: Optional[bytes] = None, iterations: int = 100_000, dklen: int = 32) -> Tuple[bytes, bytes]:
        if salt is None:
            salt = secrets.token_bytes(16)
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=dklen)
        return key, salt

    @staticmethod
    def scrypt(password: str, salt: Optional[bytes] = None, n: int = 2**14, r: int = 8, p: int = 1, dklen: int = 32) -> Tuple[bytes, bytes]:
        if salt is None:
            salt = secrets.token_bytes(16)
        key = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=dklen)
        return key, salt

    # ------------------------------------------------------------------
    # HMAC
    # ------------------------------------------------------------------

    @staticmethod
    def hmac_sha256(key: bytes, message: str | bytes) -> str:
        if isinstance(message, str):
            message = message.encode("utf-8")
        return hmac.new(key, message, hashlib.sha256).hexdigest()

    @staticmethod
    def hmac_verify(key: bytes, message: str | bytes, signature: str) -> bool:
        expected = CryptoUtilities.hmac_sha256(key, message)
        return hmac.compare_digest(expected, signature)

    # ------------------------------------------------------------------
    # Symmetric Encryption (XOR + PBKDF2)
    # ------------------------------------------------------------------

    @staticmethod
    def encrypt(plaintext: str, password: str) -> Dict[str, str]:
        key, salt = CryptoUtilities.pbkdf2(password, iterations=100_000)
        data = plaintext.encode("utf-8")
        key_cycle = key * (len(data) // len(key) + 1)
        ciphertext = bytes(b ^ key_cycle[i] for i, b in enumerate(data))
        return {
            "ciphertext": base64.b64encode(ciphertext).decode(),
            "salt": base64.b64encode(salt).decode(),
            "iterations": "100000",
        }

    @staticmethod
    def decrypt(enc_dict: Dict[str, str], password: str) -> str:
        salt = base64.b64decode(enc_dict["salt"])
        iterations = int(enc_dict.get("iterations", "100000"))
        key, _ = CryptoUtilities.pbkdf2(password, salt=salt, iterations=iterations)
        ciphertext = base64.b64decode(enc_dict["ciphertext"])
        key_cycle = key * (len(ciphertext) // len(key) + 1)
        plaintext = bytes(b ^ key_cycle[i] for i, b in enumerate(ciphertext))
        return plaintext.decode("utf-8")

    # ------------------------------------------------------------------
    # Secure Random
    # ------------------------------------------------------------------

    @staticmethod
    def random_bytes(n: int) -> bytes:
        return secrets.token_bytes(n)

    @staticmethod
    def random_hex(n: int) -> str:
        return secrets.token_hex(n)

    @staticmethod
    def random_urlsafe(n: int) -> str:
        return secrets.token_urlsafe(n)

    @staticmethod
    def random_int(min_val: int, max_val: int) -> int:
        return secrets.randbelow(max_val - min_val + 1) + min_val

    # ------------------------------------------------------------------
    # Password Hashing
    # ------------------------------------------------------------------

    @staticmethod
    def hash_password(password: str) -> str:
        salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
        return f"pbkdf2:sha256:200000${salt}${hashed}"

    @staticmethod
    def verify_password(password: str, stored: str) -> bool:
        try:
            _, algo, iterations, salt_hash = stored.split("$", 3)
            salt, hashed = salt_hash.rsplit("$", 1)
            iters = int(iterations)
            check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iters).hex()
            return hmac.compare_digest(hashed, check)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Checksum / Merkle
    # ------------------------------------------------------------------

    @staticmethod
    def merkle_root(hashes: list[str]) -> str:
        """Build a simple Merkle tree root from a list of hashes."""
        if not hashes:
            return CryptoUtilities.sha256("")
        current = hashes[:]
        while len(current) > 1:
            next_level = []
            for i in range(0, len(current), 2):
                left = current[i]
                right = current[i + 1] if i + 1 < len(current) else left
                next_level.append(CryptoUtilities.sha256(left + right))
            current = next_level
        return current[0]

    # ------------------------------------------------------------------
    # Time-based OTP (TOTP simulation)
    # ------------------------------------------------------------------

    @staticmethod
    def totp(secret: str, time_step: int = 30, digits: int = 6) -> str:
        t = int(time.time()) // time_step
        msg = struct.pack(">Q", t)
        key = secret.encode()
        h = hmac.new(key, msg, hashlib.sha1).digest()
        offset = h[-1] & 0x0F
        code = struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF
        return str(code % (10 ** digits)).zfill(digits)

    # ------------------------------------------------------------------
    # Nonce / Timestamp
    # ------------------------------------------------------------------

    @staticmethod
    def generate_nonce() -> str:
        return f"{time.time()}{secrets.token_hex(8)}"


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== Crypto Utilities Demo ===\n")
    # Hashing
    msg = "MAGNATRIX-OS"
    print(f"SHA-256: {CryptoUtilities.sha256(msg)[:32]}...")
    print(f"SHA-512: {CryptoUtilities.sha512(msg)[:32]}...")
    print(f"BLAKE2b: {CryptoUtilities.blake2b(msg)[:32]}...")
    # Symmetric encryption
    enc = CryptoUtilities.encrypt("Secret message", "password123")
    print(f"\nEncrypted: {enc['ciphertext'][:40]}...")
    dec = CryptoUtilities.decrypt(enc, "password123")
    print(f"Decrypted: {dec}")
    # Password hashing
    phash = CryptoUtilities.hash_password("my_password")
    print(f"\nPassword hash: {phash[:50]}...")
    print(f"Verify correct: {CryptoUtilities.verify_password('my_password', phash)}")
    print(f"Verify wrong: {CryptoUtilities.verify_password('wrong', phash)}")
    # HMAC
    key = b"secret_key"
    sig = CryptoUtilities.hmac_sha256(key, "message")
    print(f"\nHMAC: {sig[:32]}...")
    print(f"Verify: {CryptoUtilities.hmac_verify(key, 'message', sig)}")
    # TOTP
    totp = CryptoUtilities.totp("base32secret3232")
    print(f"\nTOTP: {totp}")
    # Merkle
    hashes = [CryptoUtilities.sha256(f"block_{i}") for i in range(4)]
    root = CryptoUtilities.merkle_root(hashes)
    print(f"Merkle root: {root[:32]}...")
    # Random
    print(f"\nRandom hex: {CryptoUtilities.random_hex(16)}")
    print(f"Random URL-safe: {CryptoUtilities.random_urlsafe(16)}")


if __name__ == "__main__":
    _demo()
