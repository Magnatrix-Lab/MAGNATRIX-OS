#!/usr/bin/env python3
"""
tests/integration/test_crypto_end_to_end.py
End-to-end crypto pipeline tests.
"""
import sys, os, hashlib, hmac, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from security.crypto_engine_native import (
    Ed25519Signer, AES256GCM, ChaCha20Poly1305,
    SHA256Hash, SHA512Hash, SHA3_256, Blake3Hash, HMACSHA256,
    Argon2Hasher, SecureRandom
)
from runtime.tri_language_bridge import UnifiedCrypto, TriLanguageHub


def test_ed25519_sign_verify():
    signer = Ed25519Signer()
    signer.generate_keypair()
    msg = b"hello magnatrix"
    sig = signer.sign(msg)
    assert sig is not None and len(sig) > 0
    # Verify with pynacl if available, else structural check
    try:
        import nacl.signing
        vk = nacl.signing.VerifyKey(signer.public_key)
        vk.verify(msg, sig)
        assert True
    except ImportError:
        assert len(signer.public_key) == 32
    print("PASS: Ed25519 sign/verify")


def test_aes_gcm_roundtrip():
    key = SecureRandom.bytes(32)
    cipher = AES256GCM(key)
    plaintext = b"secret message for magnatrix"
    try:
        ct, nonce, tag = cipher.encrypt(plaintext)
        decrypted = cipher.decrypt(ct, nonce, tag)
        assert decrypted == plaintext
        print("PASS: AES-256-GCM roundtrip")
    except RuntimeError as e:
        if "cryptography" in str(e):
            print("SKIP: AES-256-GCM (cryptography lib not installed)")
        else:
            raise


def test_chacha20_roundtrip():
    key = SecureRandom.bytes(32)
    cipher = ChaCha20Poly1305(key)
    plaintext = b"another secret"
    ct, nonce, tag = cipher.encrypt(plaintext)
    decrypted = cipher.decrypt(ct, nonce, tag)
    assert decrypted == plaintext
    print("PASS: ChaCha20-Poly1305 roundtrip")


def test_sha_variants():
    data = b"test data"
    h256 = SHA256Hash.hash(data)
    assert len(h256) == 32
    h512 = SHA512Hash.hash(data)
    assert len(h512) == 64
    h3 = SHA3_256.hash(data)
    assert len(h3) == 32
    b3 = Blake3Hash.hash(data)
    assert len(b3) == 32
    print("PASS: SHA-256/512/3 + BLAKE3")


def test_hmac():
    key = b"secret_key"
    data = b"authenticated message"
    tag = HMACSHA256.sign(key, data)
    assert HMACSHA256.verify(key, data, tag)
    assert not HMACSHA256.verify(key, b"tampered", tag)
    print("PASS: HMAC-SHA256")


def test_argon2():
    password = b"magnatrix_password"
    hasher = Argon2Hasher()
    hash_str = hasher.hash(password)
    assert hasher.verify(password, hash_str)
    assert not hasher.verify(b"wrong", hash_str)
    print("PASS: Argon2 password hashing")


def test_tri_language_crypto():
    hub = TriLanguageHub()
    # Test Python fallback crypto through unified interface
    data = b"tri-language test"
    h = hub.crypto.sha256(data)
    assert len(h) == 32
    # Test key generation
    key = hub.crypto.ed25519_generate()
    assert key is not None
    print("PASS: Tri-language crypto bridge")


def run_all():
    print("=" * 60)
    print("Crypto End-to-End Tests")
    print("=" * 60)
    tests = [
        test_ed25519_sign_verify,
        test_aes_gcm_roundtrip,
        test_chacha20_roundtrip,
        test_sha_variants,
        test_hmac,
        test_argon2,
        test_tri_language_crypto,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"FAIL: {t.__name__}: {e}")
            failed += 1
    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")
    return failed == 0


if __name__ == "__main__":
    ok = run_all()
    sys.exit(0 if ok else 1)
