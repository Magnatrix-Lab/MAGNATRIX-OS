"""MAGNATRIX-OS Rust Cryptographic Engine Python bindings.

Provides high-performance cryptographic primitives:
  - Hashing: SHA-256/512, SHA3-256, BLAKE3, HMAC-SHA256
  - Signing: Ed25519
  - Encryption: ChaCha20-Poly1305, AES-256-GCM
  - KDF: Argon2 password hashing + key derivation
  - Random: CSPRNG

Build (optional for Rust speedup):
    cd security/rust_crypto_engine
    cargo build --release
    # or with maturin:
    pip install maturin
    maturin develop --release

Usage:
    from security.rust_crypto_engine import (
        sha256, sha512, blake3_hash,
        Ed25519Keypair, ed25519_verify,
        ChaChaCipher, Aes256GcmCipher,
        argon2_hash_password, argon2_verify_password,
        secure_random_bytes, b64_encode, hex_encode,
    )
"""

# Try Rust extension first, fall back to pure Python
try:
    from ._magnatrix_crypto import (
        sha256,
        sha512,
        sha3_256,
        blake3_hash,
        hmac_sha256,
        Ed25519Keypair,
        ed25519_verify,
        ChaChaCipher,
        Aes256GcmCipher,
        argon2_hash_password,
        argon2_verify_password,
        argon2_derive_key,
        secure_random_bytes,
        secure_random_u64,
        b64_encode,
        b64_decode,
        hex_encode,
        hex_decode,
    )
    _BACKEND = "rust"
except ImportError:
    # Pure Python fallback
    from .crypto_py import (
        sha256,
        sha512,
        sha3_256,
        blake3_hash,
        hmac_sha256,
        Ed25519Keypair,
        ed25519_verify,
        ChaChaCipher,
        Aes256GcmCipher,
        argon2_hash_password,
        argon2_verify_password,
        argon2_derive_key,
        secure_random_bytes,
        secure_random_u64,
        b64_encode,
        b64_decode,
        hex_encode,
        hex_decode,
    )
    _BACKEND = "python"

__all__ = [
    "sha256",
    "sha512",
    "sha3_256",
    "blake3_hash",
    "hmac_sha256",
    "Ed25519Keypair",
    "ed25519_verify",
    "ChaChaCipher",
    "Aes256GcmCipher",
    "argon2_hash_password",
    "argon2_verify_password",
    "argon2_derive_key",
    "secure_random_bytes",
    "secure_random_u64",
    "b64_encode",
    "b64_decode",
    "hex_encode",
    "hex_decode",
]
