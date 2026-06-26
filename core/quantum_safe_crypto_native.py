#!/usr/bin/env python3
"""
Quantum-Safe Cryptography — MAGNATRIX-OS Post-Quantum Security Module
=======================================================================
Implements hash-based signatures (Lamport-inspired), lattice-inspired key
exchange (Learning With Errors simplified), and SHA-3 (Keccak-f[1600]).

Pure Python stdlib only. No external crypto libraries.
Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import struct
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union


class SHA3:
    """
    Pure Python SHA-3 (Keccak-f[1600]) implementation.
    Supports 224, 256, 384, 512 bit variants.
    """

    _ROUND_CONSTANTS = [
        0x0000000000000001, 0x0000000000008082, 0x800000000000808A,
        0x8000000080008000, 0x000000000000808B, 0x0000000080000001,
        0x8000000080008081, 0x8000000000008009, 0x000000000000008A,
        0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
        0x000000008000808B, 0x800000000000008B, 0x8000000000008089,
        0x8000000000008003, 0x8000000000008002, 0x8000000000000080,
        0x000000000000800A, 0x800000008000000A, 0x8000000080008081,
        0x8000000000008080, 0x0000000080000001, 0x8000000080008008
    ]

    _ROTATION_OFFSETS = [
        [0, 36, 3, 41, 18], [1, 44, 10, 45, 2], [62, 6, 43, 15, 61],
        [28, 55, 25, 39, 56], [27, 20, 39, 8, 14]
    ]

    def __init__(self, variant: int = 256):
        self.variant = variant
        self.capacity = variant * 2
        self.rate = 1600 - self.capacity
        self.delimited_suffix = 0x06
        self._state = [0] * 25
        self._buffer = bytearray()
        self._absorbing = True

    def update(self, data: bytes) -> SHA3:
        if not self._absorbing:
            raise ValueError("Cannot update after squeezing")
        self._buffer.extend(data)
        while len(self._buffer) >= self.rate // 8:
            block = self._buffer[:self.rate // 8]
            self._buffer = self._buffer[self.rate // 8:]
            self._absorb_block(block)
        return self

    def digest(self) -> bytes:
        if self._absorbing:
            self._finalize()
        return self._squeeze(self.variant // 8)

    def hexdigest(self) -> str:
        return self.digest().hex()

    def _absorb_block(self, block: bytes) -> None:
        for i in range(len(block) // 8):
            val = struct.unpack("<Q", block[i*8:(i+1)*8])[0]
            self._state[i] ^= val
        self._keccak_f()

    def _finalize(self) -> None:
        self._buffer.append(self.delimited_suffix)
        padding_len = (self.rate // 8) - (len(self._buffer) % (self.rate // 8))
        if padding_len == 0:
            padding_len = self.rate // 8
        self._buffer.extend([0] * (padding_len - 1))
        self._buffer[-1] |= 0x80
        self._absorb_block(self._buffer[:self.rate // 8])
        self._absorbing = False

    def _squeeze(self, length: int) -> bytes:
        output = bytearray()
        while len(output) < length:
            for i in range(self.rate // 64):
                output.extend(struct.pack("<Q", self._state[i]))
            if len(output) < length:
                self._keccak_f()
        return bytes(output[:length])

    def _keccak_f(self) -> None:
        for round_idx in range(24):
            # Theta
            C = [self._state[x] ^ self._state[x+5] ^ self._state[x+10] ^ self._state[x+15] ^ self._state[x+20] for x in range(5)]
            D = [C[(x-1) % 5] ^ self._rol(C[(x+1) % 5], 1) for x in range(5)]
            for x in range(5):
                for y in range(5):
                    self._state[x + 5*y] ^= D[x]

            # Rho and Pi
            B = [0] * 25
            for x in range(5):
                for y in range(5):
                    B[y + 5*((2*x + 3*y) % 5)] = self._rol(self._state[x + 5*y], self._ROTATION_OFFSETS[x][y])

            # Chi
            for x in range(5):
                for y in range(5):
                    self._state[x + 5*y] = B[x + 5*y] ^ ((~B[(x+1) % 5 + 5*y]) & B[(x+2) % 5 + 5*y])

            # Iota
            self._state[0] ^= self._ROUND_CONSTANTS[round_idx]

    def _rol(self, x: int, n: int) -> int:
        return ((x << n) & 0xFFFFFFFFFFFFFFFF) | (x >> (64 - n))


@dataclass
class HashBasedKeyPair:
    """Lamport-inspired one-time signature key pair."""
    private_key: List[bytes]
    public_key: List[bytes]


class HashBasedSignature:
    """
    Hash-based one-time signature scheme (Lamport-inspired).
    
    Uses 256-bit security: 256 private key pairs, each 32 bytes.
    Signature reveals half of the private key (one-time use only).
    """

    def __init__(self, security_bits: int = 256):
        self.security_bits = security_bits
        self._hash_fn = SHA3(256)

    def generate_keypair(self) -> HashBasedKeyPair:
        """Generate a fresh one-time key pair."""
        private_key = [secrets.token_bytes(32) for _ in range(self.security_bits)]
        public_key = [self._hash(private_key[i]) for i in range(self.security_bits)]
        return HashBasedKeyPair(private_key=private_key, public_key=public_key)

    def sign(self, message: bytes, keypair: HashBasedKeyPair) -> List[bytes]:
        """Sign a message. Each keypair can only be used ONCE."""
        msg_hash = self._hash(message)
        bits = self._bytes_to_bits(msg_hash)
        signature = []
        for i, bit in enumerate(bits[:self.security_bits]):
            if bit == 1:
                signature.append(keypair.private_key[i])
            else:
                signature.append(self._hash(keypair.private_key[i]))
        return signature

    def verify(self, message: bytes, signature: List[bytes], public_key: List[bytes]) -> bool:
        """Verify a signature against a public key."""
        if len(signature) != self.security_bits or len(public_key) != self.security_bits:
            return False
        msg_hash = self._hash(message)
        bits = self._bytes_to_bits(msg_hash)
        for i, bit in enumerate(bits[:self.security_bits]):
            expected = public_key[i]
            if bit == 1:
                if self._hash(signature[i]) != expected:
                    return False
            else:
                if signature[i] != expected:
                    return False
        return True

    def _hash(self, data: bytes) -> bytes:
        return SHA3(256).update(data).digest()

    def _bytes_to_bits(self, data: bytes) -> List[int]:
        return [(byte >> shift) & 1 for byte in data for shift in range(8)]


@dataclass
class LatticeKeyPair:
    """Lattice-inspired key pair (simplified LWE)."""
    public_key: Tuple[List[int], List[int]]  # (A, b)
    private_key: List[int]  # s


class LatticeKeyExchange:
    """
    Simplified lattice-inspired key exchange (Learning With Errors concept).
    
    Uses a small modulus and dimension for demonstration.
    Not production-grade but shows the lattice concept.
    """

    def __init__(self, dimension: int = 64, modulus: int = 257, noise_bound: int = 4):
        self.dimension = dimension
        self.modulus = modulus
        self.noise_bound = noise_bound

    def generate_keypair(self) -> LatticeKeyPair:
        """Generate a lattice key pair."""
        A = [secrets.randbelow(self.modulus) for _ in range(self.dimension)]
        s = [secrets.randbelow(self.modulus) for _ in range(self.dimension)]
        e = [secrets.randbelow(self.noise_bound * 2 + 1) - self.noise_bound for _ in range(self.dimension)]
        b = [(A[i] * s[i] + e[i]) % self.modulus for i in range(self.dimension)]
        return LatticeKeyPair(public_key=(A, b), private_key=s)

    def encapsulate(self, public_key: Tuple[List[int], List[int]]) -> Tuple[bytes, List[int]]:
        """Encapsulate: generate shared secret and ciphertext."""
        A, b = public_key
        r = [secrets.randbelow(self.modulus) for _ in range(self.dimension)]
        e1 = [secrets.randbelow(self.noise_bound * 2 + 1) - self.noise_bound for _ in range(self.dimension)]
        u = [(A[i] * r[i] + e1[i]) % self.modulus for i in range(self.dimension)]
        v = sum(b[i] * r[i] for i in range(self.dimension)) % self.modulus
        shared_secret = SHA3(256).update(struct.pack("<" + "Q" * self.dimension, *u) + v.to_bytes(8, "little")).digest()
        return shared_secret, u

    def decapsulate(self, ciphertext: List[int], keypair: LatticeKeyPair) -> bytes:
        """Decapsulate: recover shared secret from ciphertext."""
        u = ciphertext
        s = keypair.private_key
        v = sum(u[i] * s[i] for i in range(self.dimension)) % self.modulus
        return SHA3(256).update(struct.pack("<" + "Q" * self.dimension, *u) + v.to_bytes(8, "little")).digest()


class QuantumSafeCrypto:
    """
    Top-level quantum-safe cryptography module for MAGNATRIX-OS.
    
    Provides: SHA-3 hashing, HMAC-SHA3, hash-based signatures,
    lattice-inspired key exchange, and random entropy pooling.
    """

    CAPABILITIES = ["crypto", "hashing", "signatures", "key_exchange", "quantum_safe"]

    def __init__(self, repo_root: str = "."):
        self.repo_root = repo_root
        self._entropy_pool = bytearray()
        self._lock = threading.Lock()
        self._hash_sig = HashBasedSignature(256)
        self._lwe = LatticeKeyExchange(64, 257, 4)
        self._keypairs: Dict[str, HashBasedKeyPair] = {}

    # ---- SHA-3 Interface ----

    def sha3_256(self, data: bytes) -> bytes:
        return SHA3(256).update(data).digest()

    def sha3_512(self, data: bytes) -> bytes:
        return SHA3(512).update(data).digest()

    def hmac_sha3(self, key: bytes, data: bytes) -> bytes:
        """HMAC using SHA-3-256."""
        return hmac.new(key, data, lambda d=b"": SHA3(256).update(d).digest()).digest()

    # ---- Hash-Based Signature ----

    def generate_signature_keypair(self, label: str = "default") -> List[bytes]:
        """Generate a one-time signature keypair. Returns public key."""
        kp = self._hash_sig.generate_keypair()
        self._keypairs[label] = kp
        return kp.public_key

    def sign(self, message: bytes, label: str = "default") -> List[bytes]:
        """Sign a message with a stored keypair."""
        kp = self._keypairs.get(label)
        if not kp:
            raise ValueError(f"No keypair found for label: {label}")
        return self._hash_sig.sign(message, kp)

    def verify_signature(self, message: bytes, signature: List[bytes], public_key: List[bytes]) -> bool:
        return self._hash_sig.verify(message, signature, public_key)

    # ---- Lattice Key Exchange ----

    def generate_lattice_keypair(self) -> Dict[str, Any]:
        """Generate a lattice key pair for key exchange."""
        kp = self._lwe.generate_keypair()
        return {
            "public_key": {"A": kp.public_key[0], "b": kp.public_key[1]},
            "private_key": kp.private_key,
        }

    def encapsulate_secret(self, public_key: Dict[str, Any]) -> Tuple[bytes, List[int]]:
        """Generate shared secret and ciphertext."""
        A = public_key["A"]
        b = public_key["b"]
        return self._lwe.encapsulate((A, b))

    def decapsulate_secret(self, ciphertext: List[int], private_key: List[int]) -> bytes:
        """Recover shared secret from ciphertext."""
        kp = LatticeKeyPair(public_key=([], []), private_key=private_key)
        return self._lwe.decapsulate(ciphertext, kp)

    # ---- Entropy ----

    def feed_entropy(self, data: bytes) -> None:
        """Feed external entropy into the pool."""
        with self._lock:
            self._entropy_pool.extend(data)

    def get_random(self, length: int) -> bytes:
        """Get cryptographically random bytes."""
        with self._lock:
            if len(self._entropy_pool) >= length:
                result = bytes(self._entropy_pool[:length])
                self._entropy_pool = self._entropy_pool[length:]
                return result
        return secrets.token_bytes(length)

    def handle_message(self, message: Dict[str, Any]) -> Any:
        """Message router handler."""
        action = message.get("action", "")
        if action == "hash":
            return self.sha3_256(message["data"].encode() if isinstance(message["data"], str) else message["data"]).hex()
        elif action == "sign":
            return [s.hex() for s in self.sign(message["data"].encode(), message.get("label", "default"))]
        elif action == "verify":
            sig = [bytes.fromhex(s) for s in message["signature"]]
            pk = [bytes.fromhex(p) for p in message["public_key"]]
            return self.verify_signature(message["data"].encode(), sig, pk)
        elif action == "generate_keypair":
            return [p.hex() for p in self.generate_signature_keypair(message.get("label", "default"))]
        return None

    def on_event(self, event) -> None:
        """Event handler for integration."""
        pass
