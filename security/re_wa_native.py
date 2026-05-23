#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAGNATRIX-OS — RE-WA Native Integration
═══════════════════════════════════════════════════════════════════════════════
AMATI-PELAJARI-TIRU dari technocode/RE-WA

Pola yang ditiru:
• WhatsApp protocol reverse engineering — registration, key exchange, encryption
• Signal Protocol (libsignal) integration — X3DH, Double Ratchet, prekeys
• AES-256-GCM encryption — WhatsApp symmetric cipher implementation
• Token generation — iOS (MD5-based) & Android (PBKDF2+HMAC-SHA1+image-based)
• Recovery token decryption — AES-128-OFB dengan PBKDF2 key derivation
• Shared data analysis — NSUserDefaults AES-128-CBC encryption
• WhatsApp Web multi-device protocol — WebSocket + protobuf message parsing
• Protocol endpoint documentation — v.whatsapp.net API surface mapping
• Cryptographic analysis tools — key validation, entropy measurement
• Network traffic inspector — protobuf deconstruction, metadata extraction

Layer: Security (9) — Messaging Protocol Analysis Engine
Versi: Phase 5 — RE-WA Native Signal/WhatsApp Protocol Analyzer
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import struct
import time
import urllib.parse
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable


# ─────────────────────────────────────────────────────────────────────────────
# 0. UTILITAS DASAR
# ─────────────────────────────────────────────────────────────────────────────


def _now_iso() -> str:
    from datetime import datetime
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _bytes_to_hex(data: bytes) -> str:
    return data.hex()


def _hex_to_bytes(data: str) -> bytes:
    return bytes.fromhex(data)


def _b64_urlsafe(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _xor_strings(s1: str, s2: str) -> str:
    """XOR dua string character-by-character."""
    return "".join(chr(ord(a) ^ ord(b)) for a, b in zip(s1, s2))


# ─────────────────────────────────────────────────────────────────────────────
# 1. SIGNAL PROTOCOL ENGINE — X3DH & Double Ratchet
# ─────────────────────────────────────────────────────────────────────────────


class SignalCurve25519:
    """
    Simplified Curve25519 key operations untuk Signal Protocol.
    Production: gunakan cryptography library (NaCl/PyNaCl).
    Native: key generation, key agreement, signing.
    """

    @staticmethod
    def generate_identity_keypair() -> Dict[str, Any]:
        """Generate identity keypair (simplified — mock untuk native demo)."""
        private_key = secrets.token_bytes(32)
        public_key = b"\x05" + secrets.token_bytes(32)  # DJB key type prefix
        return {
            "private_key": private_key,
            "public_key": public_key,
            "key_type": "DJB",
            "type_byte": 0x05,
        }

    @staticmethod
    def generate_registration_id() -> int:
        """Generate 16-bit registration ID."""
        return secrets.randbelow(16380) + 1

    @staticmethod
    def generate_prekeys(start_id: int = 1, count: int = 100) -> List[Dict[str, Any]]:
        """Generate batch prekeys."""
        prekeys = []
        for i in range(count):
            kp = SignalCurve25519.generate_identity_keypair()
            prekeys.append({
                "id": start_id + i,
                "public_key": kp["public_key"],
                "private_key": kp["private_key"],
            })
        return prekeys

    @staticmethod
    def generate_signed_prekey(identity_keypair: Dict[str, Any],
                                signed_prekey_id: int = 5) -> Dict[str, Any]:
        """Generate signed prekey ditandatangani dengan identity key."""
        spk = SignalCurve25519.generate_identity_keypair()
        # Signature: identity private key signs signed prekey public key
        signature = hmac.new(
            identity_keypair["private_key"],
            spk["public_key"],
            hashlib.sha256,
        ).digest()[:64]  # 64-byte Ed25519-style signature (simplified)
        return {
            "id": signed_prekey_id,
            "key_pair": spk,
            "signature": signature,
        }


@dataclass
class SignalSession:
    """Satu Signal Protocol session state."""
    session_id: str
    remote_registration_id: int
    remote_identity_key: bytes
    local_identity_key: Dict[str, Any]
    root_key: bytes = b""
    sending_chain_key: bytes = b""
    receiving_chain_key: bytes = b""
    sending_ratchet_keypair: Optional[Dict[str, Any]] = None
    receiving_ratchet_public_key: Optional[bytes] = None
    created_at: str = field(default_factory=_now_iso)


class SignalProtocolEngine:
    """
    Engine untuk Signal Protocol (libsignal-compatible):
    • Key generation: identity, prekeys, signed prekey
    • Session establishment: X3DH key agreement
    • Double Ratchet: symmetric ratchet + Diffie-Hellman ratchet
    • Message encryption/decryption dengan chain keys
    """

    def __init__(self) -> None:
        self.sessions: Dict[str, SignalSession] = {}
        self.identity_keypair: Optional[Dict[str, Any]] = None
        self.prekeys: List[Dict[str, Any]] = []
        self.signed_prekey: Optional[Dict[str, Any]] = None
        self.registration_id: int = 0

    def initialize(self) -> Dict[str, Any]:
        """Initialize Signal client: generate all keys."""
        self.identity_keypair = SignalCurve25519.generate_identity_keypair()
        self.registration_id = SignalCurve25519.generate_registration_id()
        self.prekeys = SignalCurve25519.generate_prekeys(start_id=1, count=100)
        self.signed_prekey = SignalCurve25519.generate_signed_prekey(
            self.identity_keypair, signed_prekey_id=5
        )
        return {
            "registration_id": self.registration_id,
            "identity_public_key": _bytes_to_hex(self.identity_keypair["public_key"]),
            "prekeys_count": len(self.prekeys),
            "signed_prekey_id": self.signed_prekey["id"],
            "signed_prekey_signature": _bytes_to_hex(self.signed_prekey["signature"]),
        }

    def establish_session(self, remote_registration_id: int,
                         remote_identity_key: bytes,
                         remote_prekey: bytes,
                         remote_prekey_id: int,
                         remote_signed_prekey: bytes,
                         remote_signed_prekey_signature: bytes) -> SignalSession:
        """
        X3DH key agreement untuk establish session dengan remote.
        Simplified: derive shared secret dari key exchange.
        """
        session_id = f"sess-{secrets.token_hex(8)}"

        # Mock shared secret derivation
        shared_secret = hashlib.sha256(
            self.identity_keypair["private_key"] + remote_identity_key + remote_prekey
        ).digest()

        # KDF untuk root key
        root_key = hashlib.sha256(shared_secret + b"root").digest()
        chain_key = hashlib.sha256(shared_secret + b"chain").digest()

        session = SignalSession(
            session_id=session_id,
            remote_registration_id=remote_registration_id,
            remote_identity_key=remote_identity_key,
            local_identity_key=self.identity_keypair,
            root_key=root_key,
            sending_chain_key=chain_key,
            receiving_chain_key=chain_key,
        )
        self.sessions[session_id] = session
        return session

    def encrypt_message(self, session_id: str, plaintext: bytes) -> Dict[str, Any]:
        """Encrypt message menggunakan Double Ratchet."""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Symmetric ratchet step
        message_key = hashlib.sha256(session.sending_chain_key + b"message").digest()[:32]
        session.sending_chain_key = hashlib.sha256(session.sending_chain_key + b"next").digest()

        # Mock AES-256-CBC encryption (production: use proper AEAD)
        iv = secrets.token_bytes(16)
        # Simplified: XOR dengan message key untuk demo
        ciphertext = bytes(p ^ message_key[i % 32] for i, p in enumerate(plaintext))

        return {
            "ciphertext": _bytes_to_hex(ciphertext),
            "iv": _bytes_to_hex(iv),
            "message_key": _bytes_to_hex(message_key),
            "session_id": session_id,
        }

    def decrypt_message(self, session_id: str, ciphertext: bytes, iv: bytes) -> bytes:
        """Decrypt message."""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        message_key = hashlib.sha256(session.receiving_chain_key + b"message").digest()[:32]
        session.receiving_chain_key = hashlib.sha256(session.receiving_chain_key + b"next").digest()

        plaintext = bytes(c ^ message_key[i % 32] for i, c in enumerate(ciphertext))
        return plaintext

    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        session = self.sessions.get(session_id)
        if not session:
            return None
        return {
            "session_id": session.session_id,
            "remote_registration_id": session.remote_registration_id,
            "root_key_hash": hashlib.sha256(session.root_key).hexdigest()[:16],
            "created_at": session.created_at,
        }


# ─────────────────────────────────────────────────────────────────────────────
# 2. WHATSAPP ENCRYPTION ENGINE — AES-256-GCM & AES-128
# ─────────────────────────────────────────────────────────────────────────────


class WhatsAppEncryptionEngine:
    """
    Engine untuk WhatsApp-specific encryption:
    • AES-256-GCM: symmetric cipher utama WhatsApp
    • AES-128-CBC: NSUserDefaults encryption (iOS)
    • AES-128-OFB: Recovery token decryption (Android)
    • PBKDF2 key derivation untuk various token types
    """

    # WhatsApp AES-256-GCM constants
    GCM_IV = b"\x00" * 12  # 96-bit zero IV
    GCM_TAG_LENGTH = 12  # 96-bit auth tag

    @staticmethod
    def aes256_gcm_encrypt(plaintext: bytes, key: bytes,
                           associated_data: bytes = b"") -> bytes:
        """
        Encrypt menggunakan AES-256-GCM (WhatsApp standard).
        Production: gunakan cryptography library.
        Native: mock implementation untuk analysis & research.
        """
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend

        iv = secrets.token_bytes(12)
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        if associated_data:
            encryptor.authenticate_additional_data(associated_data)
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        return iv + ciphertext + encryptor.tag

    @staticmethod
    def aes256_gcm_decrypt(ciphertext: bytes, key: bytes,
                           associated_data: bytes = b"") -> bytes:
        """Decrypt AES-256-GCM."""
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend

        iv = ciphertext[:12]
        tag = ciphertext[-16:]
        ct = ciphertext[12:-16]
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(iv, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        if associated_data:
            decryptor.authenticate_additional_data(associated_data)
        return decryptor.update(ct) + decryptor.finalize()

    @classmethod
    def aes128_cbc_encrypt(cls, plaintext: bytes, key: bytes,
                            iv: Optional[bytes] = None) -> bytes:
        """AES-128-CBC encryption (iOS NSUserDefaults)."""
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import padding

        if iv is None:
            iv = b"\x00" * 16
        padder = padding.PKCS7(128).padder()
        padded = padder.update(plaintext) + padder.finalize()
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        return iv + encryptor.update(padded) + encryptor.finalize()

    @classmethod
    def aes128_cbc_decrypt(cls, ciphertext: bytes, key: bytes) -> bytes:
        """AES-128-CBC decryption."""
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import padding

        iv = ciphertext[:16]
        ct = ciphertext[16:]
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        padded = decryptor.update(ct) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        return unpadder.update(padded) + unpadder.finalize()

    @classmethod
    def aes128_ofb_decrypt(cls, ciphertext: bytes, key: bytes,
                            iv: bytes) -> bytes:
        """AES-128-OFB decryption (Android recovery token)."""
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend

        cipher = Cipher(algorithms.AES(key), modes.OFB(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()

    @staticmethod
    def pbkdf2_derive_key(password: bytes, salt: bytes,
                          iterations: int = 16,
                          keylen: int = 16) -> bytes:
        """PBKDF2-HMAC-SHA1 key derivation."""
        return hashlib.pbkdf2_hmac("sha1", password, salt, iterations, keylen)

    @staticmethod
    def hmac_sha1(key: bytes, data: bytes) -> bytes:
        """HMAC-SHA1 untuk Android token generation."""
        return hmac.new(key, data, hashlib.sha1).digest()

    @classmethod
    def generate_hmac_sha1_token(cls, key: bytes, data: bytes) -> bytes:
        """
        Generate token menggunakan HMAC-SHA1 (iPad/opad method).
        Meniru Android token generation dari RE-WA.
        """
        # Pad key ke 64 bytes
        if len(key) > 64:
            key = hashlib.sha1(key).digest()
        key = key.ljust(64, b"\x00")

        opad = bytes(b"\x5c" ^ k for k in key)
        ipad = bytes(b"\x36" ^ k for k in key)

        inner = hashlib.sha1(ipad + data).digest()
        outer = hashlib.sha1(opad + inner).digest()
        return base64.b64encode(outer)


# ─────────────────────────────────────────────────────────────────────────────
# 3. TOKEN GENERATOR — iOS & Android Registration Tokens
# ─────────────────────────────────────────────────────────────────────────────


class WhatsAppTokenGenerator:
    """
    Generator untuk WhatsApp registration & recovery tokens:
    • iOS token: MD5-based
    • Android token: PBKDF2 + HMAC-SHA1 dengan image-based key
    • Recovery token decryption
    """

    # iOS constants
    IOS_WA_STRING = "0a1mLfGUIBVrMKF1RdvLI5lkRBvof6vn0fD2QRSM"
    IOS_PACKAGE_MD5 = "a200e8c6b58fda4c7d569aacfa2119a7"  # WhatsApp iOS package

    # Android constants
    ANDROID_WA_PREFIX_B64 = "Y29tLndoYXRzYXBw"
    ANDROID_SIGNATURE_B64 = (
        "MIIDMjCCAvCgAwIBAgIETCU2pDALBgcqhkjOOAQDBQAwfDELMAkGA1UEBhMCVVMxEzARBgNVBAgTCkNhbGlmb3JuaWEx"
        "FDASBgNVBAcTC1NhbnRhIENsYXJhMRYwFAYDVQQKEw1XaGF0c0FwcCBJbmMuMRQwEgYDVQQLEwtFbmdpbmVlcmluZzEU"
        "MBIGA1UEAxMLQnJpYW4gQWN0b24wHhcNMTAwNjI1MjMwNzE2WhcNNDQwMjE1MjMwNzE2WjB8MQswCQYDVQQGEwJVUzET"
        "MBEGA1UECBMKQ2FsaWZvcm5pYTEUMBIGA1UEBxMLU2FudGEgQ2xhcmExFjAUBgNVBAoTDVdoYXRzQXBwIEluYy4xFDAS"
        "BgNVBAsTC0VuZ2luZWVyaW5nMRQwEgYDVQQDEwtCcmlhbiBBY3RvbjCCAbgwggEsBgcqhkjOOAQBMIIBHwKBgQD9f1OB"
        "HXUSKVLfSpwu7OTn9hG3UjzvRADDHj+AtlEmaUVdQCJR+1k9jVj6v8X1ujD2y5tVbNeBO4AdNG/yZmC3a5lQpaSfn+gE"
        "exAiwk+7qdf+t8Yb+DtX58aophUPBPuD9tPFHsMCNVQTWhaRMvZ1864rYdcq7/IiAxmd0UgBxwIVAJdgUI8VIwvMspK5"
        "gqLrhAvwWBz1AoGBAPfhoIXWmz3ey7yrXDa4V7l5lK+7+jrqgvlXTAs9B4JnUVlXjrrUWU/mcQcQgYC0SRZxI+hMKBYTt"
        "88JMozIpuE8FnqLVHyNKOCjrh4rs6Z1kW6jfwv6ITVi8ftiegEkO8yk8b6oUZCJqIPf4VrlnwaSi2ZegHtVJWQBTDv+z0"
        "kqA4GFAAKBgQDRGYtLgWh7zyRtQainJfCpiaUbzjJuhMgo4fVWZIvXHaSHBU1t5w//S0lDK2hiqkj8KpMWGywVov9eZxZy"
        "37V26dEqr/c2m5qZ0E+ynSu7sqUD7kGx/zeIcGT0H+KAVgkGNQCo5Uc0koLRWYHNtYoIvt5R3X6YZylbPftF/8ayWTAL"
        "BgcqhkjOOAQDBQADLwAwLAIUAKYCp0d6z4QQdyN74JDfQ2WCyi8CFDUM4CaNB+ceVXdKtOrNTQcc0e+t"
    )
    ANDROID_SALT_B64 = (
        "PkTwKSZqUfAUyR0rPQ8hYJ0wNsQQ3dW1+3SCnyTXIfEAxxS75FwkDf47wNv/c8pP3p0GXKR6OOQmhyERwx74fw1RYSU1"
        "0I4r1gyBVDbRJ40pidjM41G1I1oN"
    )
    ANDROID_PRECALCULATED_KEY_B64 = (
        "eQV5aq/Cg63Gsq1sshN9T3gh+UUp0wIw0xgHYT1bnCjEqOJQKCRrWxdAe2yvsDeCJL+Y4G3PRD2HUF7oUgiGo8vGlNJO"
        "aux26k+A2F3hj8A="
    )

    @classmethod
    def generate_ios_token(cls, phone_number_without_cc: str,
                           wa_string: str = None,
                           package_md5: str = None) -> str:
        """
        Generate iOS registration token.
        Formula: md5(waString + md5(app package) + phone_number)
        """
        ws = wa_string or cls.IOS_WA_STRING
        pkg = package_md5 or cls.IOS_PACKAGE_MD5
        token_input = f"{ws}{pkg}{phone_number_without_cc}"
        return hashlib.md5(token_input.encode("utf-8")).hexdigest()

    @classmethod
    def generate_android_token(cls, phone_number: str,
                                classes_md5_b64: str = "",
                                use_precalculated_key: bool = False) -> str:
        """
        Generate Android registration token menggunakan PBKDF2 + HMAC-SHA1.
        Meniru RE-WA Android token generation dengan image-based key derivation.
        """
        wa_prefix = base64.b64decode(cls.ANDROID_WA_PREFIX_B64)
        salt = base64.b64decode(cls.ANDROID_SALT_B64)
        signature = base64.b64decode(cls.ANDROID_SIGNATURE_B64)

        # For demo: use wa_prefix sebagai password base
        # Production: derive dari about_logo.png + wa_prefix
        password = wa_prefix + b"mock_image_bytes"  # Placeholder untuk image

        if use_precalculated_key:
            key = base64.b64decode(cls.ANDROID_PRECALCULATED_KEY_B64)
        else:
            key = WhatsAppEncryptionEngine.pbkdf2_derive_key(password, salt, iterations=128, keylen=80)
            key = base64.b64decode(key)  # decode hasil PBKDF2

        cls_decoded = base64.b64decode(classes_md5_b64) if classes_md5_b64 else b""
        data = signature + cls_decoded + phone_number.encode()

        token = WhatsAppEncryptionEngine.generate_hmac_sha1_token(key[:64], data)
        return token.decode()

    @classmethod
    def decrypt_ios_recovery_token(cls, rc_dat_hex: str) -> str:
        """
        Decrypt iOS recovery token dari rc.dat.
        iOS: tidak di-encrypt, hanya URL-encoded hex string.
        """
        # Parse hex string → ASCII
        raw = rc_dat_hex.replace("%", "")
        try:
            decoded = bytes.fromhex(raw).decode("ascii", errors="replace")
            return urllib.parse.unquote(decoded)
        except Exception:
            return urllib.parse.unquote(rc_dat_hex)

    @classmethod
    def decrypt_android_recovery_token(cls, rc2_data: bytes,
                                        phone_number: str,
                                        google_play_email: str = "") -> str:
        """
        Decrypt Android recovery token dari rc2 file.
        Steps: PBKDF2 key derivation → AES-128-OFB decryption.
        """
        # RC_SECRET (decrypted dari XOR cipher)
        rc_secret = cls._decode_rc_secret()
        recovery_jid = cls._get_recovery_jid(phone_number)
        secret = (rc_secret + recovery_jid + google_play_email).encode("utf-8")

        # Parse rc2 data structure
        # Format: header(2) + salt(4) + iv(16) + encrypted_data(20)
        if len(rc2_data) < 42:
            raise ValueError("rc2 data too short")

        header = rc2_data[:2]
        if header != b"\x00\x02":
            raise ValueError(f"Unexpected header: {header.hex()}")

        salt = rc2_data[2:6]
        iv = rc2_data[6:22]
        encrypted = rc2_data[22:42]

        key = WhatsAppEncryptionEngine.pbkdf2_derive_key(secret, salt, iterations=16, keylen=16)
        decrypted = WhatsAppEncryptionEngine.aes128_ofb_decrypt(encrypted, key, iv)
        return urllib.parse.quote_plus(decrypted.decode("latin-1"))

    @staticmethod
    def _decode_rc_secret() -> str:
        """Decode RC_SECRET dari XOR cipher."""
        encoded = "A\x04\x1d@\x11\x18V\x91\x02\x90\x88\x9f\x9eT(3{;ES"
        xor_key = "\x12"
        return "".join(chr(ord(c) ^ ord(xor_key)) for c in encoded)

    @staticmethod
    def _get_recovery_jid(phone_number: str) -> str:
        """Extract recovery JID dari phone number."""
        pattern = re.compile(
            r"^([17]|2[07]|3[0123469]|4[013456789]|5[12345678]|6[0123456]|8[1246]|9[0123458]|\d{3})\d*?(\d{4,6})$"
        )
        match = pattern.match(phone_number)
        if match:
            return match.group(1) + match.group(2)
        return phone_number


# ─────────────────────────────────────────────────────────────────────────────
# 4. PROTOCOL ENDPOINT DOCUMENTATION — v.whatsapp.net API
# ─────────────────────────────────────────────────────────────────────────────


class WhatsAppProtocolEndpoints:
    """
    Dokumentasi dan builder untuk WhatsApp protocol endpoints.
    Meniru RE-WA endpoint documentation.
    """

    BASE_URL = "https://v.whatsapp.net/v2"

    ENDPOINTS = {
        "exist": {
            "url": "{base}/exist",
            "method": "GET",
            "params": ["ENC"],  # Base64 encoded encrypted data
            "description": "Check if number was already registered",
        },
        "code": {
            "url": "{base}/code",
            "method": "GET",
            "params": ["ENC", "rc"],  # rc: 0=release, 1=beta, 2=alpha, 3=debug
            "description": "Request registration code via SMS/voice",
        },
        "register": {
            "url": "{base}/register",
            "method": "GET",
            "params": [
                "ENC", "cc", "in", "lg", "lc",
                "authkey", "e_regid", "e_keytype", "e_ident",
                "e_skey_id", "e_skey_val", "e_skey_sig",
                "id", "code", "entered"
            ],
            "description": "Complete registration with received code",
        },
    }

    @classmethod
    def build_exist_request(cls, encrypted_data_b64: str) -> str:
        """Build exist request URL."""
        return f"{cls.BASE_URL}/exist?ENC={urllib.parse.quote(encrypted_data_b64)}"

    @classmethod
    def build_code_request(cls, encrypted_data_b64: str,
                           release_channel: int = 0) -> str:
        """Build code request URL."""
        return f"{cls.BASE_URL}/code?ENC={urllib.parse.quote(encrypted_data_b64)}&rc={release_channel}"

    @classmethod
    def build_register_request(cls, params: Dict[str, str]) -> str:
        """Build register request URL."""
        query = urllib.parse.urlencode(params)
        return f"{cls.BASE_URL}/register?{query}"

    @classmethod
    def get_endpoint_docs(cls) -> Dict[str, Any]:
        return cls.ENDPOINTS

    @classmethod
    def encrypt_exist_payload(cls, user_public_key: bytes,
                              phone_number: str,
                              country_code: str) -> bytes:
        """
        Encrypt exist payload: <user_public_key> + <encrypted_data>.
        Meniru RE-WA exist endpoint encryption.
        """
        # Build plaintext: phone number data
        plaintext = f"{country_code}{phone_number}".encode()

        # Derive key dari user public key (simplified)
        key = hashlib.sha256(user_public_key).digest()[:32]

        # Encrypt dengan AES-256-GCM
        encrypted = WhatsAppEncryptionEngine.aes256_gcm_encrypt(plaintext, key)
        return user_public_key + encrypted


# ─────────────────────────────────────────────────────────────────────────────
# 5. PROTOBUF MESSAGE PARSER — WhatsApp Web Protocol
# ─────────────────────────────────────────────────────────────────────────────


class WhatsAppProtobufParser:
    """
    Parser untuk WhatsApp Web protobuf messages.
    Meniru multi-device protocol message structure.
    """

    MESSAGE_TYPES = {
        0: "heartbeat",
        1: "pairing_request",
        2: "pairing_response",
        3: "message_ack",
        4: "message",
        5: "presence",
        6: "status",
        7: "receipt",
        8: "notification",
    }

    @staticmethod
    def parse_binary_message(raw: bytes) -> Dict[str, Any]:
        """
        Parse raw binary message dari WhatsApp Web WebSocket.
        Format: [tag][message_type_byte][protobuf_payload]
        """
        if len(raw) < 3:
            return {"error": "message too short"}

        tag_len = raw[0]
        tag = raw[1:1 + tag_len].decode("utf-8", errors="replace")
        msg_type = raw[1 + tag_len]
        payload = raw[2 + tag_len:]

        return {
            "tag": tag,
            "message_type": WhatsAppProtobufParser.MESSAGE_TYPES.get(msg_type, f"unknown_{msg_type}"),
            "message_type_id": msg_type,
            "payload_length": len(payload),
            "payload_hash": hashlib.sha256(payload).hexdigest()[:16],
            "raw_length": len(raw),
        }

    @staticmethod
    def build_heartbeat(tag: str = "") -> bytes:
        """Build heartbeat message."""
        tag_bytes = tag.encode() if tag else b"HB"
        return bytes([len(tag_bytes)]) + tag_bytes + b"\x00"

    @staticmethod
    def build_message_ack(tag: str, message_id: str) -> bytes:
        """Build message acknowledgement."""
        tag_bytes = tag.encode()
        payload = message_id.encode()
        return bytes([len(tag_bytes)]) + tag_bytes + b"\x03" + payload

    @staticmethod
    def decode_node_buffer(data: bytes) -> Dict[str, Any]:
        """
        Decode WhatsApp binary node buffer.
        Format: [list_size][attribute_count][children_count][tag][attrs][children]
        """
        if len(data) < 4:
            return {"error": "buffer too short"}

        list_size = data[0]
        attr_count = data[1]
        child_count = data[2]
        tag_len = data[3]
        tag = data[4:4 + tag_len].decode("utf-8", errors="replace")

        return {
            "list_size": list_size,
            "attribute_count": attr_count,
            "child_count": child_count,
            "tag": tag,
            "remaining_bytes": len(data) - (4 + tag_len),
        }


# ─────────────────────────────────────────────────────────────────────────────
# 6. NETWORK TRAFFIC INSPECTOR — Metadata Extraction
# ─────────────────────────────────────────────────────────────────────────────


class NetworkTrafficInspector:
    """
    Inspector untuk analisis network traffic WhatsApp:
    • WebSocket frame analysis
    • TLS fingerprinting
    • DNS query logging
    • Endpoint reachability
    """

    def __init__(self) -> None:
        self.captured_frames: List[Dict[str, Any]] = []
        self.dns_queries: List[str] = []

    def inspect_websocket_frame(self, frame_data: bytes,
                                 direction: str = "inbound") -> Dict[str, Any]:
        """Inspect satu WebSocket frame."""
        parsed = WhatsAppProtobufParser.parse_binary_message(frame_data)
        record = {
            "timestamp": time.time(),
            "direction": direction,
            **parsed,
        }
        self.captured_frames.append(record)
        return record

    def analyze_tls_fingerprint(self, client_hello: bytes) -> Dict[str, Any]:
        """Extract TLS fingerprint dari Client Hello."""
        # Simplified: extract cipher suites dan extensions
        if len(client_hello) < 43:
            return {"error": "invalid client hello"}

        # Skip random (32 bytes) setelah version (2) + random (32)
        session_id_len = client_hello[34]
        offset = 35 + session_id_len

        cipher_suites_len = struct.unpack(">H", client_hello[offset:offset + 2])[0]
        cipher_suites = client_hello[offset + 2:offset + 2 + cipher_suites_len]

        # Parse cipher suite IDs (2 bytes each)
        suites = []
        for i in range(0, len(cipher_suites), 2):
            suites.append(struct.unpack(">H", cipher_suites[i:i + 2])[0])

        return {
            "cipher_suites": [f"0x{s:04x}" for s in suites],
            "cipher_suite_count": len(suites),
            "fingerprint": hashlib.sha256(cipher_suites).hexdigest()[:16],
        }

    def get_traffic_summary(self) -> Dict[str, Any]:
        by_type: Dict[str, int] = {}
        for frame in self.captured_frames:
            mt = frame.get("message_type", "unknown")
            by_type[mt] = by_type.get(mt, 0) + 1

        return {
            "total_frames": len(self.captured_frames),
            "by_message_type": by_type,
            "dns_queries": len(self.dns_queries),
        }


# ─────────────────────────────────────────────────────────────────────────────
# 7. CRYPTOGRAPHIC ANALYSIS TOOLS
# ─────────────────────────────────────────────────────────────────────────────


class CryptoAnalysisTools:
    """
    Tools untuk analisis kriptografik WhatsApp:
    • Entropy measurement
    • Key validation
    • Weak key detection
    • Randomness analysis
    """

    @staticmethod
    def measure_entropy(data: bytes) -> float:
        """Measure Shannon entropy dari byte sequence."""
        if not data:
            return 0.0
        entropy = 0.0
        for x in range(256):
            p_x = data.count(x) / len(data)
            if p_x > 0:
                entropy += -p_x * math.log2(p_x)
        return entropy

    @staticmethod
    def is_weak_key(key: bytes, threshold_entropy: float = 3.0) -> bool:
        """Check apakah key memiliki entropy rendah (weak)."""
        return CryptoAnalysisTools.measure_entropy(key) < threshold_entropy

    @staticmethod
    def analyze_key_strength(public_key: bytes) -> Dict[str, Any]:
        """Analyze strength dari public key."""
        entropy = CryptoAnalysisTools.measure_entropy(public_key)
        return {
            "key_length": len(public_key),
            "entropy_bits": round(entropy, 2),
            "max_entropy": 8.0,
            "strength": "strong" if entropy > 7.5 else "medium" if entropy > 5.0 else "weak",
            "is_curve25519": public_key.startswith(b"\x05"),
        }

    @staticmethod
    def detect_patterns(data: bytes) -> Dict[str, Any]:
        """Detect repeating patterns dalam data."""
        patterns = {}
        for length in [2, 4, 8, 16]:
            repeats = 0
            for i in range(0, len(data) - length, length):
                if data[i:i + length] == data[i + length:i + 2 * length]:
                    repeats += 1
            patterns[f"repeat_{length}bytes"] = repeats
        return patterns


# ─────────────────────────────────────────────────────────────────────────────
# 8. SHARED DATA ANALYZER — iOS & Android Storage
# ─────────────────────────────────────────────────────────────────────────────


class SharedDataAnalyzer:
    """
    Analyzer untuk WhatsApp shared data storage:
    • iOS NSUserDefaults: AES-128-CBC encrypted
    • Android rc2: AES-128-OFB encrypted recovery token
    • Keychain/Keystore analysis
    """

    @staticmethod
    def analyze_ios_nsuserdefaults(encrypted_b64: str,
                                    country_code: str) -> Dict[str, Any]:
        """
        Analyze iOS NSUserDefaults encrypted entry.
        Key: md5("s.whatsapp.net")[:16]
        IV: 16 zero bytes
        """
        wa_string = "s.whatsapp.net"
        key = hashlib.md5(wa_string.encode()).hexdigest()[:16].encode()
        iv = b"\x00" * 16

        encrypted = base64.b64decode(encrypted_b64)
        try:
            decrypted = WhatsAppEncryptionEngine.aes128_cbc_decrypt(encrypted, key)
            return {
                "platform": "iOS",
                "source": "NSUserDefaults",
                "decrypted": decrypted.decode("utf-8", errors="replace"),
                "key_derivation": f"md5('{wa_string}')[:16]",
                "iv": "16 x 0x00",
            }
        except Exception as e:
            return {
                "platform": "iOS",
                "source": "NSUserDefaults",
                "error": str(e),
                "entropy": CryptoAnalysisTools.measure_entropy(encrypted),
            }

    @staticmethod
    def analyze_android_rc2(rc2_file_path: Path,
                           phone_number: str,
                           google_email: str = "") -> Dict[str, Any]:
        """Analyze Android rc2 recovery token file."""
        try:
            rc2_data = rc2_file_path.read_bytes()
            token = WhatsAppTokenGenerator.decrypt_android_recovery_token(
                rc2_data, phone_number, google_email
            )
            return {
                "platform": "Android",
                "source": "rc2",
                "recovery_token": token,
                "file_size": len(rc2_data),
                "decryption": "PBKDF2-SHA1 + AES-128-OFB",
            }
        except Exception as e:
            return {
                "platform": "Android",
                "source": "rc2",
                "error": str(e),
                "file_size": rc2_file_path.stat().st_size if rc2_file_path.exists() else 0,
            }


# ─────────────────────────────────────────────────────────────────────────────
# 9. UNIFIED RE-WA ENGINE — Entry Point
# ─────────────────────────────────────────────────────────────────────────────


class REWAEngine:
    """
    Unified engine untuk WhatsApp reverse engineering & protocol analysis.
    Entry point bagi MAGNATRIX security agents.
    """

    def __init__(self) -> None:
        self.signal = SignalProtocolEngine()
        self.encryption = WhatsAppEncryptionEngine()
        self.tokens = WhatsAppTokenGenerator()
        self.endpoints = WhatsAppProtocolEndpoints()
        self.protobuf = WhatsAppProtobufParser()
        self.network = NetworkTrafficInspector()
        self.crypto = CryptoAnalysisTools()
        self.storage = SharedDataAnalyzer()

    # ── Initialization ────────────────────────────────────────────────────

    def initialize_signal_client(self) -> Dict[str, Any]:
        """Initialize Signal Protocol client untuk WhatsApp registration."""
        return self.signal.initialize()

    # ── Token Generation ──────────────────────────────────────────────────

    def generate_ios_token(self, phone: str) -> str:
        return self.tokens.generate_ios_token(phone)

    def generate_android_token(self, phone: str, classes_md5: str = "") -> str:
        return self.tokens.generate_android_token(phone, classes_md5)

    def decrypt_recovery_token(self, platform: str, data: bytes,
                                phone: str, email: str = "") -> Dict[str, Any]:
        """Decrypt recovery token untuk platform yang ditentukan."""
        if platform.lower() == "ios":
            token = self.tokens.decrypt_ios_recovery_token(data.hex() if isinstance(data, bytes) else data.decode())
            return {"platform": "iOS", "token": token, "method": "url_decode"}
        elif platform.lower() == "android":
            token = self.tokens.decrypt_android_recovery_token(data, phone, email)
            return {"platform": "Android", "token": token, "method": "PBKDF2+AES-128-OFB"}
        return {"error": "unsupported platform"}

    # ── Protocol Analysis ─────────────────────────────────────────────────

    def analyze_endpoint(self, endpoint_name: str) -> Optional[Dict[str, Any]]:
        docs = self.endpoints.get_endpoint_docs()
        return docs.get(endpoint_name)

    def parse_websocket_message(self, raw: bytes) -> Dict[str, Any]:
        return self.protobuf.parse_binary_message(raw)

    def inspect_traffic(self, frame: bytes, direction: str = "inbound") -> Dict[str, Any]:
        return self.network.inspect_websocket_frame(frame, direction)

    # ── Cryptographic Analysis ──────────────────────────────────────────────

    def analyze_key(self, public_key: bytes) -> Dict[str, Any]:
        return self.crypto.analyze_key_strength(public_key)

    def measure_data_entropy(self, data: bytes) -> float:
        return self.crypto.measure_entropy(data)

    # ── Storage Analysis ──────────────────────────────────────────────────

    def analyze_ios_storage(self, encrypted_b64: str, country_code: str) -> Dict[str, Any]:
        return self.storage.analyze_ios_nsuserdefaults(encrypted_b64, country_code)

    def analyze_android_storage(self, rc2_path: Path, phone: str, email: str = "") -> Dict[str, Any]:
        return self.storage.analyze_android_rc2(rc2_path, phone, email)

    # ── Batch Analysis ────────────────────────────────────────────────────

    def full_analysis_report(self, phone_number: str,
                             country_code: str,
                             platform: str = "android") -> Dict[str, Any]:
        """Generate comprehensive analysis report."""
        self.initialize_signal_client()
        session = self.signal.establish_session(
            remote_registration_id=12345,
            remote_identity_key=secrets.token_bytes(33),
            remote_prekey=secrets.token_bytes(33),
            remote_prekey_id=1,
            remote_signed_prekey=secrets.token_bytes(33),
            remote_signed_prekey_signature=secrets.token_bytes(64),
        )

        return {
            "phone_number": phone_number,
            "country_code": country_code,
            "platform": platform,
            "signal_initialized": True,
            "session_id": session.session_id,
            "ios_token_sample": self.generate_ios_token(phone_number),
            "entropy_sample": self.measure_data_entropy(secrets.token_bytes(256)),
            "endpoints_available": list(self.endpoints.get_endpoint_docs().keys()),
            "generated_at": _now_iso(),
        }


def main():
    import sys
    print("═══════════════════════════════════════════════════════════════")
    print("  MAGNATRIX-OS — RE-WA Native Signal/WhatsApp Analyzer")
    print("  AMATI-PELAJARI-TIRU dari technocode/RE-WA")
    print("═══════════════════════════════════════════════════════════════")
    print()

    engine = REWAEngine()

    # Demo 1: Signal Protocol initialization
    print("[1] Signal Protocol Initialization:")
    signal_state = engine.initialize_signal_client()
    print(f"  Registration ID: {signal_state['registration_id']}")
    print(f"  Identity Key: {signal_state['identity_public_key'][:32]}...")
    print(f"  Prekeys: {signal_state['prekeys_count']}")
    print()

    # Demo 2: Token generation
    print("[2] Token Generation:")
    ios_token = engine.generate_ios_token("123456789")
    print(f"  iOS Token: {ios_token}")
    android_token = engine.generate_android_token("34123456789", "")
    print(f"  Android Token: {android_token[:50]}...")
    print()

    # Demo 3: Session establishment
    print("[3] Signal Session:")
    session = engine.signal.establish_session(
        remote_registration_id=99999,
        remote_identity_key=b"\x05" + secrets.token_bytes(32),
        remote_prekey=b"\x05" + secrets.token_bytes(32),
        remote_prekey_id=42,
        remote_signed_prekey=b"\x05" + secrets.token_bytes(32),
        remote_signed_prekey_signature=secrets.token_bytes(64),
    )
    print(f"  Session ID: {session.session_id}")
    print(f"  Root Key Hash: {hashlib.sha256(session.root_key).hexdigest()[:16]}")
    print()

    # Demo 4: Encrypt/decrypt
    print("[4] Message Encryption:")
    plaintext = b"Hello, MAGNATRIX!"
    encrypted = engine.signal.encrypt_message(session.session_id, plaintext)
    print(f"  Ciphertext: {encrypted['ciphertext'][:40]}...")
    decrypted = engine.signal.decrypt_message(
        session.session_id,
        _hex_to_bytes(encrypted["ciphertext"]),
        _hex_to_bytes(encrypted["iv"]),
    )
    print(f"  Decrypted: {decrypted.decode()}")
    print()

    # Demo 5: Protocol message parsing
    print("[5] Protobuf Message Parsing:")
    heartbeat = engine.protobuf.build_heartbeat("test-tag")
    parsed = engine.parse_websocket_message(heartbeat)
    print(f"  Tag: {parsed['tag']}")
    print(f"  Type: {parsed['message_type']}")
    print()

    # Demo 6: Endpoint documentation
    print("[6] Protocol Endpoints:")
    for name, doc in engine.endpoints.get_endpoint_docs().items():
        print(f"  • {name}: {doc['description']}")
    print()

    # Demo 7: Crypto analysis
    print("[7] Cryptographic Analysis:")
    test_key = b"\x05" + secrets.token_bytes(32)
    analysis = engine.analyze_key(test_key)
    print(f"  Key Length: {analysis['key_length']}")
    print(f"  Entropy: {analysis['entropy_bits']}/8.0 bits")
    print(f"  Strength: {analysis['strength']}")
    print(f"  Curve25519: {analysis['is_curve25519']}")
    print()

    # Demo 8: Full report
    print("[8] Full Analysis Report:")
    report = engine.full_analysis_report("34123456789", "34")
    print(json.dumps(report, indent=2))
    print()
    print("Done.")


if __name__ == "__main__":
    main()
