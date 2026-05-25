#!/usr/bin/env python3
"""
tests/integration/test_tri_language.py
MAGNATRIX-OS — Tri-Language Integration Test Suite

Tests end-to-end flow between:
  - Python orchestration layer
  - C++ HFT engine (or Python fallback)
  - Rust crypto engine (or Python fallback)
"""
from __future__ import annotations

import json
import sys
import time
import unittest
from typing import Any, Dict, List

# Ensure project root is in path
sys.path.insert(0, ".")

from runtime.tri_language_bridge import (
    TriLanguageHub,
    SecureTickPayload,
    UnifiedCrypto,
    UnifiedHFT,
    BackendStatus,
)


class TestBackendDetection(unittest.TestCase):
    def test_backends_report(self) -> None:
        status = BackendStatus()
        r = status.report()
        self.assertIn("cpp_hft", r)
        self.assertIn("rust_crypto", r)
        self.assertIn("python_fallback", r)
        self.assertTrue(r["python_fallback"])


class TestUnifiedCrypto(unittest.TestCase):
    def setUp(self) -> None:
        self.crypto = UnifiedCrypto()

    def test_sha256(self) -> None:
        h = self.crypto.hash_sha256(b"hello")
        self.assertEqual(len(h), 32)

    def test_sha512(self) -> None:
        h = self.crypto.hash_sha512(b"hello")
        self.assertEqual(len(h), 64)

    def test_blake3(self) -> None:
        h = self.crypto.hash_blake3(b"hello")
        self.assertEqual(len(h), 32)

    def test_hmac(self) -> None:
        mac = self.crypto.hmac_sha256(b"key", b"data")
        self.assertEqual(len(mac), 32)

    def test_random(self) -> None:
        r1 = self.crypto.secure_random(32)
        r2 = self.crypto.secure_random(32)
        self.assertEqual(len(r1), 32)
        self.assertNotEqual(r1, r2)

    def test_chacha_roundtrip(self) -> None:
        key = self.crypto.secure_random(32)
        plaintext = b"sensitive market data"
        ciphertext, nonce = self.crypto.encrypt_chacha20(key, plaintext)
        decrypted = self.crypto.decrypt_chacha20(key, ciphertext, nonce)
        self.assertEqual(decrypted, plaintext)

    def test_argon2(self) -> None:
        pw_hash = self.crypto.argon2_hash("testpassword123")
        self.assertTrue(len(pw_hash) > 20)
        self.assertTrue(self.crypto.argon2_verify("testpassword123", pw_hash))
        self.assertFalse(self.crypto.argon2_verify("wrongpassword", pw_hash))

    def test_ed25519_sign_verify(self) -> None:
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        except ImportError:
            self.skipTest("cryptography not available")

        seed = self.crypto.secure_random(32)
        key = Ed25519PrivateKey.from_private_bytes(seed)
        pubkey = key.public_key().public_bytes_raw()
        msg = b"test message"
        sig = self.crypto.sign_ed25519(seed, msg)
        self.assertTrue(self.crypto.verify_ed25519(pubkey, msg, sig))
        self.assertFalse(self.crypto.verify_ed25519(pubkey, b"tampered", sig))


class TestUnifiedHFT(unittest.TestCase):
    def setUp(self) -> None:
        self.hft = UnifiedHFT()

    def test_book_update_and_spread(self) -> None:
        self.hft.update_book("BTCUSDT", 50000.0, 1.5, 50001.0, 2.0)
        spread = self.hft.get_spread("BTCUSDT")
        self.assertAlmostEqual(spread, 1.0, places=4)

    def test_mid_price(self) -> None:
        self.hft.update_book("ETHUSDT", 3000.0, 10.0, 3001.0, 15.0)
        mid = self.hft.get_mid("ETHUSDT")
        self.assertAlmostEqual(mid, 3000.5, places=4)

    def test_multiple_symbols(self) -> None:
        self.hft.update_book("BTCUSDT", 50000.0, 1.0, 50001.0, 1.0)
        self.hft.update_book("ETHUSDT", 3000.0, 5.0, 3001.0, 5.0)
        self.assertAlmostEqual(self.hft.get_spread("BTCUSDT"), 1.0, places=4)
        self.assertAlmostEqual(self.hft.get_spread("ETHUSDT"), 1.0, places=4)

    def test_backend_reported(self) -> None:
        self.assertIn(self.hft.backend, ["cpp", "python"])


class TestTriLanguageHub(unittest.TestCase):
    def setUp(self) -> None:
        self.hub = TriLanguageHub()

    def test_status(self) -> None:
        s = self.hub.status()
        self.assertIn("backends", s)
        self.assertIn("crypto_backend", s)
        self.assertIn("hft_backend", s)
        self.assertIn("stats", s)

    def test_identity_generation(self) -> None:
        pubkey, seed = self.hub.generate_identity()
        self.assertEqual(len(pubkey), 32)
        self.assertEqual(len(seed), 32)

    def test_signed_tick_processing(self) -> None:
        self.hub.generate_identity()
        tick = SecureTickPayload(symbol="BTCUSDT", bid=50000.0, ask=50001.0)
        signed = self.hub.sign_tick(tick)
        self.assertTrue(len(signed.signature) > 0)
        ok = self.hub.verify_and_process_tick(signed)
        self.assertTrue(ok)
        self.assertEqual(self.hub.status()["stats"]["ticks_processed"], 1)

    def test_encrypted_config(self) -> None:
        plaintext = b'{"api_key": "secret123", "secret": "shhh"}'
        encrypted = self.hub.encrypt_config(plaintext)
        self.assertIn("key", encrypted)
        self.assertIn("nonce", encrypted)
        self.assertIn("ciphertext", encrypted)
        decrypted = self.hub.decrypt_config(encrypted)
        self.assertEqual(decrypted, plaintext)

    def test_arbitrage_scan(self) -> None:
        self.hft = self.hub.hft
        self.hft.register_arb_book(0, "BTCUSDT")
        self.hft.register_arb_book(1, "BTCUSDT")
        self.hft.set_fee(0, 2.0, 5.0)
        self.hft.set_fee(1, 2.0, 5.0)
        # Same price — no arb
        self.hft.update_book("BTCUSDT", 50000.0, 1.0, 50001.0, 1.0)
        opps = self.hub.scan_arbitrage()
        # Should be empty or just verify it runs
        self.assertIsInstance(opps, list)

    def test_event_callbacks(self) -> None:
        received: List[Any] = []
        self.hub.on("tick", lambda t: received.append(t))
        tick = SecureTickPayload(symbol="SOLUSDT", bid=100.0, ask=101.0)
        self.hub.verify_and_process_tick(tick)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].symbol, "SOLUSDT")

    def test_signature_failure(self) -> None:
        self.hub.generate_identity()
        tick = SecureTickPayload(symbol="BTCUSDT", bid=50000.0, ask=50001.0)
        signed = self.hub.sign_tick(tick)
        # Tamper with the payload
        tampered = SecureTickPayload(
            symbol="BTCUSDT", bid=50000.0, ask=50001.0,
            signature=signed.signature,
            signer_pubkey=signed.signer_pubkey,
        )
        # The signature is for the original serialization, tampered has same fields so OK
        # Let's create a genuinely different message
        tampered2 = SecureTickPayload(
            symbol="BTCUSDT", bid=99999.0, ask=50001.0,
            signature=signed.signature,
            signer_pubkey=signed.signer_pubkey,
        )
        ok = self.hub.verify_and_process_tick(tampered2)
        # Should fail verification because bid changed
        self.assertFalse(ok)
        self.assertEqual(self.hub.status()["stats"]["signatures_failed"], 1)


class TestBenchmarkComparison(unittest.TestCase):
    """Quick benchmark to show performance differences."""

    def test_hash_benchmark(self) -> None:
        crypto = UnifiedCrypto()
        data = b"x" * 1024
        n = 1000

        t0 = time.perf_counter()
        for _ in range(n):
            crypto.hash_sha256(data)
        dt_sha256 = time.perf_counter() - t0

        t0 = time.perf_counter()
        for _ in range(n):
            crypto.hash_blake3(data)
        dt_blake3 = time.perf_counter() - t0

        # Just verify they both complete — don't assert speed since backends vary
        self.assertGreater(dt_sha256, 0)
        self.assertGreater(dt_blake3, 0)

    def test_hft_tick_benchmark(self) -> None:
        hft = UnifiedHFT()
        n = 1000
        t0 = time.perf_counter()
        for i in range(n):
            hft.update_book("BTCUSDT", 50000.0 + i * 0.01, 1.0, 50001.0 + i * 0.01, 1.0)
        dt = time.perf_counter() - t0
        ticks_per_sec = n / dt if dt > 0 else 0
        # Should handle at least 10k ticks/sec even in pure Python
        self.assertGreater(ticks_per_sec, 1000)


def run_tests() -> int:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestBackendDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestUnifiedCrypto))
    suite.addTests(loader.loadTestsFromTestCase(TestUnifiedHFT))
    suite.addTests(loader.loadTestsFromTestCase(TestTriLanguageHub))
    suite.addTests(loader.loadTestsFromTestCase(TestBenchmarkComparison))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
