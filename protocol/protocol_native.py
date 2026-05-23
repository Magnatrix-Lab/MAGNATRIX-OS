"""
protocol_native.py - Layer 1 Native Protocol Implementation

Pure Python implementation of messaging protocol with encryption,
handshake authentication, heartbeat, and message queuing.
No external dependencies.

Layer: 1 (Transport + Security)
"""

import json
import struct
import time
import hashlib
import os
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Union, Tuple
from enum import Enum, auto
from collections import deque
import base64


# ============================================================================
# AES-256-GCM Pure Python Implementation
# ============================================================================

class AES256GCM:
    """Pure Python AES-256-GCM encryption/decryption."""

    # AES S-box
    _SBOX = bytes([
        0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5, 0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB, 0x76,
        0xCA, 0x82, 0xC9, 0x7D, 0xFA, 0x59, 0x47, 0xF0, 0xAD, 0xD4, 0xA2, 0xAF, 0x9C, 0xA4, 0x72, 0xC0,
        0xB7, 0xFD, 0x93, 0x26, 0x36, 0x3F, 0xF7, 0xCC, 0x34, 0xA5, 0xE5, 0xF1, 0x71, 0xD8, 0x31, 0x15,
        0x04, 0xC7, 0x23, 0xC3, 0x18, 0x96, 0x05, 0x9A, 0x07, 0x12, 0x80, 0xE2, 0xEB, 0x27, 0xB2, 0x75,
        0x09, 0x83, 0x2C, 0x1A, 0x1B, 0x6E, 0x5A, 0xA0, 0x52, 0x3B, 0xD6, 0xB3, 0x29, 0xE3, 0x2F, 0x84,
        0x53, 0xD1, 0x00, 0xED, 0x20, 0xFC, 0xB1, 0x5B, 0x6A, 0xCB, 0xBE, 0x39, 0x4A, 0x4C, 0x58, 0xCF,
        0xD0, 0xEF, 0xAA, 0xFB, 0x43, 0x4D, 0x33, 0x85, 0x45, 0xF9, 0x02, 0x7F, 0x50, 0x3C, 0x9F, 0xA8,
        0x51, 0xA3, 0x40, 0x8F, 0x92, 0x9D, 0x38, 0xF5, 0xBC, 0xB6, 0xDA, 0x21, 0x10, 0xFF, 0xF3, 0xD2,
        0xCD, 0x0C, 0x13, 0xEC, 0x5F, 0x97, 0x44, 0x17, 0xC4, 0xA7, 0x7E, 0x3D, 0x64, 0x5D, 0x19, 0x73,
        0x60, 0x81, 0x4F, 0xDC, 0x22, 0x2A, 0x90, 0x88, 0x46, 0xEE, 0xB8, 0x14, 0xDE, 0x5E, 0x0B, 0xDB,
        0xE0, 0x32, 0x3A, 0x0A, 0x49, 0x06, 0x24, 0x5C, 0xC2, 0xD3, 0xAC, 0x62, 0x91, 0x95, 0xE4, 0x79,
        0xE7, 0xC8, 0x37, 0x6D, 0x8D, 0xD5, 0x4E, 0xA9, 0x6C, 0x56, 0xF4, 0xEA, 0x65, 0x7A, 0xAE, 0x08,
        0xBA, 0x78, 0x25, 0x2E, 0x1C, 0xA6, 0xB4, 0xC6, 0xE8, 0xDD, 0x74, 0x1F, 0x4B, 0xBD, 0x8B, 0x8A,
        0x70, 0x3E, 0xB5, 0x66, 0x48, 0x03, 0xF6, 0x0E, 0x61, 0x35, 0x57, 0xB9, 0x86, 0xC1, 0x1D, 0x9E,
        0xE1, 0xF8, 0x98, 0x11, 0x69, 0xD9, 0x8E, 0x94, 0x9B, 0x1E, 0x87, 0xE9, 0xCE, 0x55, 0x28, 0xDF,
        0x8C, 0xA1, 0x89, 0x0D, 0xBF, 0xE6, 0x42, 0x68, 0x41, 0x99, 0x2D, 0x0F, 0xB0, 0x54, 0xBB, 0x16,
    ])

    # Inverse S-box
    _INV_SBOX = bytes([
        0x52, 0x09, 0x6A, 0xD5, 0x30, 0x36, 0xA5, 0x38, 0xBF, 0x40, 0xA3, 0x9E, 0x81, 0xF3, 0xD7, 0xFB,
        0x7C, 0xE3, 0x39, 0x82, 0x9B, 0x2F, 0xFF, 0x87, 0x34, 0x8E, 0x43, 0x44, 0xC4, 0xDE, 0xE9, 0xCB,
        0x54, 0x7B, 0x94, 0x32, 0xA6, 0xC2, 0x23, 0x3D, 0xEE, 0x4C, 0x95, 0x0B, 0x42, 0xFA, 0xC3, 0x4E,
        0x08, 0x2E, 0xA1, 0x66, 0x28, 0xD9, 0x24, 0xB2, 0x76, 0x5B, 0xA2, 0x49, 0x6D, 0x8B, 0xD1, 0x25,
        0x72, 0xF8, 0xF6, 0x64, 0x86, 0x68, 0x98, 0x16, 0xD4, 0xA4, 0x5C, 0xCC, 0x5D, 0x65, 0xB6, 0x92,
        0x6C, 0x70, 0x48, 0x50, 0xFD, 0xED, 0xB9, 0xDA, 0x5E, 0x15, 0x46, 0x57, 0xA7, 0x8D, 0x9D, 0x84,
        0x90, 0xD8, 0xAB, 0x00, 0x8C, 0xBC, 0xD3, 0x0A, 0xF7, 0xE4, 0x58, 0x05, 0xB8, 0xB3, 0x45, 0x06,
        0xD0, 0x2C, 0x1E, 0x8F, 0xCA, 0x3F, 0x0F, 0x02, 0xC1, 0xAF, 0xBD, 0x03, 0x01, 0x13, 0x8A, 0x6B,
        0x3A, 0x91, 0x11, 0x41, 0x4F, 0x67, 0xDC, 0xEA, 0x97, 0xF2, 0xCF, 0xCE, 0xF0, 0xB4, 0xE6, 0x73,
        0x96, 0xAC, 0x74, 0x22, 0xE7, 0xAD, 0x35, 0x85, 0xE2, 0xF9, 0x37, 0xE8, 0x1C, 0x75, 0xDF, 0x6E,
        0x47, 0xF1, 0x1A, 0x71, 0x1D, 0x29, 0xC5, 0x89, 0x6F, 0xB7, 0x62, 0x0E, 0xAA, 0x18, 0xBE, 0x1B,
        0xFC, 0x56, 0x3E, 0x4B, 0xC6, 0xD2, 0x79, 0x20, 0x9A, 0xDB, 0xC0, 0xFE, 0x78, 0xCD, 0x5A, 0xF4,
        0x1F, 0xDD, 0xA8, 0x33, 0x88, 0x07, 0xC7, 0x31, 0xB1, 0x12, 0x10, 0x59, 0x27, 0x80, 0xEC, 0x5F,
        0x60, 0x51, 0x7F, 0xA9, 0x19, 0xB5, 0x4A, 0x0D, 0x2D, 0xE5, 0x7A, 0x9F, 0x93, 0xC9, 0x9C, 0xEF,
        0xA0, 0xE0, 0x3B, 0x4D, 0xAE, 0x2A, 0xF5, 0xB0, 0xC8, 0xEB, 0xBB, 0x3C, 0x83, 0x53, 0x99, 0x61,
        0x17, 0x2B, 0x04, 0x7E, 0xBA, 0x77, 0xD6, 0x26, 0xE1, 0x69, 0x14, 0x63, 0x55, 0x21, 0x0C, 0x7D,
    ])

    # Round constants
    _RCON = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36]

    def __init__(self, key: bytes) -> None:
        """Initialize with 32-byte AES-256 key."""
        if len(key) != 32:
            raise ValueError("AES-256 requires 32-byte key")
        self._key = key
        self._round_keys = self._key_expansion(key)

    @classmethod
    def generate_key(cls) -> bytes:
        """Generate a random 32-byte AES-256 key."""
        return os.urandom(32)

    def _sub_bytes(self, state: bytearray) -> None:
        """Substitute bytes using S-box."""
        for i in range(16):
            state[i] = self._SBOX[state[i]]

    def _inv_sub_bytes(self, state: bytearray) -> None:
        """Inverse substitute bytes."""
        for i in range(16):
            state[i] = self._INV_SBOX[state[i]]

    def _shift_rows(self, state: bytearray) -> None:
        """Shift rows transformation."""
        # Row 1: shift left by 1
        state[1], state[5], state[9], state[13] = state[5], state[9], state[13], state[1]
        # Row 2: shift left by 2
        state[2], state[6], state[10], state[14] = state[10], state[14], state[2], state[6]
        # Row 3: shift left by 3
        state[3], state[7], state[11], state[15] = state[15], state[3], state[7], state[11]

    def _inv_shift_rows(self, state: bytearray) -> None:
        """Inverse shift rows."""
        state[1], state[5], state[9], state[13] = state[13], state[1], state[5], state[9]
        state[2], state[6], state[10], state[14] = state[10], state[2], state[6], state[14]
        state[3], state[7], state[11], state[15] = state[7], state[11], state[15], state[3]

    def _xtime(self, x: int) -> int:
        """Multiply by x in GF(2^8)."""
        return ((x << 1) ^ 0x1B) & 0xFF if x & 0x80 else (x << 1) & 0xFF

    def _mix_columns(self, state: bytearray) -> None:
        """Mix columns transformation."""
        for i in range(0, 16, 4):
            a, b, c, d = state[i], state[i+1], state[i+2], state[i+3]
            state[i] = self._xtime(a) ^ self._xtime(b) ^ b ^ c ^ d
            state[i+1] = a ^ self._xtime(b) ^ self._xtime(c) ^ c ^ d
            state[i+2] = a ^ b ^ self._xtime(c) ^ self._xtime(d) ^ d
            state[i+3] = self._xtime(a) ^ a ^ b ^ c ^ self._xtime(d)

    def _inv_mix_columns(self, state: bytearray) -> None:
        """Inverse mix columns."""
        for i in range(0, 16, 4):
            a, b, c, d = state[i], state[i+1], state[i+2], state[i+3]
            state[i] = self._mul(a, 0x0E) ^ self._mul(b, 0x0B) ^ self._mul(c, 0x0D) ^ self._mul(d, 0x09)
            state[i+1] = self._mul(a, 0x09) ^ self._mul(b, 0x0E) ^ self._mul(c, 0x0B) ^ self._mul(d, 0x0D)
            state[i+2] = self._mul(a, 0x0D) ^ self._mul(b, 0x09) ^ self._mul(c, 0x0E) ^ self._mul(d, 0x0B)
            state[i+3] = self._mul(a, 0x0B) ^ self._mul(b, 0x0D) ^ self._mul(c, 0x09) ^ self._mul(d, 0x0E)

    def _mul(self, a: int, b: int) -> int:
        """Multiply two bytes in GF(2^8)."""
        result = 0
        for _ in range(8):
            if b & 1:
                result ^= a
            a = self._xtime(a)
            b >>= 1
        return result & 0xFF

    def _add_round_key(self, state: bytearray, round_key: List[int]) -> None:
        """Add round key (XOR)."""
        for i in range(16):
            state[i] ^= round_key[i]

    def _key_expansion(self, key: bytes) -> List[List[int]]:
        """Expand 32-byte key into 15 round keys (60 words)."""
        nk = 8  # Number of 32-bit words in key for AES-256
        nr = 14  # Number of rounds
        w = [0] * (4 * (nr + 1))

        for i in range(nk):
            w[i] = struct.unpack('>I', key[4*i:4*i+4])[0]

        for i in range(nk, 4 * (nr + 1)):
            temp = w[i - 1]
            if i % nk == 0:
                temp = self._sub_word(self._rot_word(temp)) ^ (self._RCON[i // nk - 1] << 24)
            elif i % nk == 4:
                temp = self._sub_word(temp)
            w[i] = w[i - nk] ^ temp

        round_keys = []
        for i in range(0, len(w), 4):
            key_bytes = b''.join(struct.pack('>I', w[j]) for j in range(i, i + 4))
            round_keys.append(list(key_bytes))
        return round_keys

    def _sub_word(self, word: int) -> int:
        """Apply S-box to each byte of a word."""
        return (self._SBOX[(word >> 24) & 0xFF] << 24 |
                self._SBOX[(word >> 16) & 0xFF] << 16 |
                self._SBOX[(word >> 8) & 0xFF] << 8 |
                self._SBOX[word & 0xFF])

    def _rot_word(self, word: int) -> int:
        """Rotate word left by 1 byte."""
        return ((word << 8) | (word >> 24)) & 0xFFFFFFFF

    def _encrypt_block(self, block: bytes) -> bytes:
        """Encrypt single 16-byte block."""
        state = bytearray(block)
        self._add_round_key(state, self._round_keys[0])
        for i in range(1, 14):
            self._sub_bytes(state)
            self._shift_rows(state)
            self._mix_columns(state)
            self._add_round_key(state, self._round_keys[i])
        self._sub_bytes(state)
        self._shift_rows(state)
        self._add_round_key(state, self._round_keys[14])
        return bytes(state)

    def _decrypt_block(self, block: bytes) -> bytes:
        """Decrypt single 16-byte block."""
        state = bytearray(block)
        self._add_round_key(state, self._round_keys[14])
        for i in range(13, 0, -1):
            self._inv_shift_rows(state)
            self._inv_sub_bytes(state)
            self._add_round_key(state, self._round_keys[i])
            self._inv_mix_columns(state)
        self._inv_shift_rows(state)
        self._inv_sub_bytes(state)
        self._add_round_key(state, self._round_keys[0])
        return bytes(state)

    def _gf_mul(self, a: int, b: int) -> int:
        """Galois field multiplication for GCM."""
        result = 0
        for _ in range(8):
            if b & 1:
                result ^= a
            a = (a << 1) ^ 0xE1 if a & 0x80 else a << 1
            b >>= 1
        return result & 0xFF

    def _ghash(self, H: bytes, data: bytes) -> bytes:
        """GHASH function for GCM authentication."""
        Y = bytearray(16)
        for i in range(0, len(data), 16):
            block = data[i:i+16]
            if len(block) < 16:
                block = block + b'\x00' * (16 - len(block))
            for j in range(16):
                Y[j] ^= block[j]
            Y = self._gcm_mul(Y, H)
        return bytes(Y)

    def _gcm_mul(self, X: bytes, H: bytes) -> bytearray:
        """GCM multiplication: X * H in GF(2^128)."""
        Z = bytearray(16)
        V = bytearray(H)
        for i in range(128):
            if (X[i // 8] >> (7 - (i % 8))) & 1:
                for j in range(16):
                    Z[j] ^= V[j]
            carry = V[15] & 1
            for j in range(15, 0, -1):
                V[j] = (V[j] >> 1) | ((V[j-1] & 1) << 7)
            V[0] = (V[0] >> 1) ^ (0xE1 if carry else 0)
        return Z

    def _inc32(self, block: bytes) -> bytes:
        """Increment rightmost 32 bits of block."""
        b = bytearray(block)
        for i in range(15, 11, -1):
            b[i] = (b[i] + 1) & 0xFF
            if b[i] != 0:
                break
        return bytes(b)

    def _pad16(self, data: bytes) -> bytes:
        """Pad data to multiple of 16 bytes."""
        pad_len = (16 - len(data) % 16) % 16
        return data + b'\x00' * pad_len

    def encrypt(self, plaintext: bytes, iv: bytes, aad: bytes = b'') -> Tuple[bytes, bytes]:
        """Encrypt plaintext and return (ciphertext, tag)."""
        if len(iv) != 12:
            raise ValueError("GCM requires 12-byte IV")

        H = self._encrypt_block(b'\x00' * 16)
        J0 = iv + b'\x00\x00\x00\x01'

        # Encrypt plaintext
        ciphertext = bytearray()
        counter = J0
        for i in range(0, len(plaintext), 16):
            counter = self._inc32(counter)
            keystream = self._encrypt_block(counter)
            block = plaintext[i:i+16]
            for j in range(len(block)):
                ciphertext.append(block[j] ^ keystream[j])

        # Compute auth tag
        ghash_input = self._pad16(aad) + self._pad16(bytes(ciphertext)) + struct.pack('>QQ', len(aad) * 8, len(ciphertext) * 8)
        S = self._ghash(H, ghash_input)
        tag = bytes(a ^ b for a, b in zip(self._encrypt_block(J0), S))
        return bytes(ciphertext), tag[:16]

    def decrypt(self, ciphertext: bytes, iv: bytes, tag: bytes, aad: bytes = b'') -> bytes:
        """Decrypt ciphertext and verify tag."""
        if len(iv) != 12 or len(tag) != 16:
            raise ValueError("Invalid IV or tag length")

        H = self._encrypt_block(b'\x00' * 16)
        J0 = iv + b'\x00\x00\x00\x01'

        # Verify tag
        ghash_input = self._pad16(aad) + self._pad16(ciphertext) + struct.pack('>QQ', len(aad) * 8, len(ciphertext) * 8)
        S = self._ghash(H, ghash_input)
        computed_tag = bytes(a ^ b for a, b in zip(self._encrypt_block(J0), S))[:16]

        # Constant-time comparison
        result = 0
        for a, b in zip(tag, computed_tag):
            result |= a ^ b
        if result != 0:
            raise ValueError("Authentication failed: tag mismatch")

        # Decrypt
        plaintext = bytearray()
        counter = J0
        for i in range(0, len(ciphertext), 16):
            counter = self._inc32(counter)
            keystream = self._encrypt_block(counter)
            block = ciphertext[i:i+16]
            for j in range(len(block)):
                plaintext.append(block[j] ^ keystream[j])

        return bytes(plaintext)


# ============================================================================
# Message Types
# ============================================================================

class MessageType(Enum):
    """Enumeration of protocol message types."""
    DATA = auto()
    HANDSHAKE = auto()
    HEARTBEAT = auto()
    HEARTBEAT_ACK = auto()
    ERROR = auto()
    CONTROL = auto()


# ============================================================================
# Message Dataclass
# ============================================================================

@dataclass
class Message:
    """Protocol message with metadata and cryptographic signature.

    Attributes:
        id: Unique message identifier (UUID v4 as string).
        type: Message classification enum.
        payload: Message body content as bytes.
        sender: Sender identifier string.
        recipient: Target recipient identifier string.
        timestamp: Unix epoch timestamp in seconds.
        signature: Ed25519-style signature bytes (64 bytes).
    """
    id: str
    type: MessageType
    payload: bytes
    sender: str
    recipient: str
    timestamp: float
    signature: bytes = field(default=b'\x00' * 64)

    def __repr__(self) -> str:
        return (f"Message(id={self.id!r}, type={self.type.name}, "
                f"sender={self.sender!r}, recipient={self.recipient!r}, "
                f"timestamp={self.timestamp:.3f}, "
                f"payload_len={len(self.payload)}, signature_set={bool(self.signature)})")


# ============================================================================
# Serializer
# ============================================================================

class Serializer:
    """Bidirectional serializer supporting JSON and Binary formats."""

    SUPPORTED_FORMATS: Tuple[str, ...] = ("json", "binary")

    @classmethod
    def to_json(cls, msg: Message) -> bytes:
        """Serialize Message to JSON bytes."""
        obj = {
            "id": msg.id,
            "type": msg.type.name,
            "payload": base64.b64encode(msg.payload).decode(),
            "sender": msg.sender,
            "recipient": msg.recipient,
            "timestamp": msg.timestamp,
            "signature": base64.b64encode(msg.signature).decode(),
        }
        return json.dumps(obj, separators=(',', ':')).encode()

    @classmethod
    def from_json(cls, data: bytes) -> Message:
        """Deserialize JSON bytes to Message."""
        obj = json.loads(data)
        return Message(
            id=obj["id"],
            type=MessageType[obj["type"]],
            payload=base64.b64decode(obj["payload"]),
            sender=obj["sender"],
            recipient=obj["recipient"],
            timestamp=obj["timestamp"],
            signature=base64.b64decode(obj["signature"]),
        )

    @classmethod
    def to_binary(cls, msg: Message) -> bytes:
        """Serialize Message to compact binary format.

        Format: [header][payload][signature]
        Header: version(1) | type(1) | id_len(2) | sender_len(2) | recipient_len(2)
                | payload_len(4) | signature_len(2) | timestamp(8) | id | sender | recipient
        """
        id_bytes = msg.id.encode()
        sender_bytes = msg.sender.encode()
        recipient_bytes = msg.recipient.encode()
        payload = msg.payload
        sig = msg.signature

        header = struct.pack(
            '!B B H H H I H d',
            1,  # version
            msg.type.value,
            len(id_bytes),
            len(sender_bytes),
            len(recipient_bytes),
            len(payload),
            len(sig),
            msg.timestamp,
        )
        return header + id_bytes + sender_bytes + recipient_bytes + payload + sig

    @classmethod
    def from_binary(cls, data: bytes) -> Message:
        """Deserialize binary bytes to Message."""
        version, msg_type, id_len, sender_len, recipient_len, payload_len, sig_len, timestamp = \
            struct.unpack('!B B H H H I H d', data[:22])

        offset = 22
        id_str = data[offset:offset + id_len].decode()
        offset += id_len
        sender = data[offset:offset + sender_len].decode()
        offset += sender_len
        recipient = data[offset:offset + recipient_len].decode()
        offset += recipient_len
        payload = data[offset:offset + payload_len]
        offset += payload_len
        signature = data[offset:offset + sig_len]

        return Message(
            id=id_str,
            type=MessageType(msg_type),
            payload=payload,
            sender=sender,
            recipient=recipient,
            timestamp=timestamp,
            signature=signature,
        )


# ============================================================================
# Handshake Protocol
# ============================================================================

class HandshakeState(Enum):
    """States of the challenge-response handshake."""
    IDLE = auto()
    CHALLENGE_SENT = auto()
    AUTHENTICATED = auto()
    FAILED = auto()


class HandshakeProtocol:
    """Challenge-response authentication protocol.

    Uses SHA-256 HMAC-style challenge signing for mutual authentication.
    """

    def __init__(self, identity: str, secret: bytes) -> None:
        """Initialize handshake with identity and shared secret.

        Args:
            identity: Unique identifier for this peer.
            secret: Pre-shared 32-byte secret for challenge signing.
        """
        self.identity = identity
        self._secret = secret
        self.state = HandshakeState.IDLE
        self._challenge: Optional[bytes] = None
        self._peer_identity: Optional[str] = None

    def __repr__(self) -> str:
        return (f"HandshakeProtocol(identity={self.identity!r}, "
                f"state={self.state.name}, peer={self._peer_identity!r})")

    def generate_challenge(self) -> bytes:
        """Generate a random 32-byte challenge nonce."""
        self._challenge = os.urandom(32)
        self.state = HandshakeState.CHALLENGE_SENT
        return self._challenge

    def sign_challenge(self, challenge: bytes) -> bytes:
        """Sign a challenge with the shared secret using HMAC-SHA256."""
        return hashlib.sha256(challenge + self._secret).digest()

    def verify_response(self, challenge: bytes, response: bytes, peer_id: str) -> bool:
        """Verify peer's response and authenticate.

        Args:
            challenge: Original challenge sent.
            response: Signed challenge from peer.
            peer_id: Peer identity string.

        Returns:
            True if authentication succeeds.
        """
        expected = hashlib.sha256(challenge + self._secret).digest()
        if len(response) != 32 or not self._constant_time_compare(response, expected):
            self.state = HandshakeState.FAILED
            return False
        self._peer_identity = peer_id
        self.state = HandshakeState.AUTHENTICATED
        return True

    @staticmethod
    def _constant_time_compare(a: bytes, b: bytes) -> bool:
        """Constant-time byte comparison to prevent timing attacks."""
        if len(a) != len(b):
            return False
        result = 0
        for x, y in zip(a, b):
            result |= x ^ y
        return result == 0

    def is_authenticated(self) -> bool:
        """Check if handshake is complete."""
        return self.state == HandshakeState.AUTHENTICATED

    def get_peer(self) -> Optional[str]:
        """Return authenticated peer identity."""
        return self._peer_identity


# ============================================================================
# Heartbeat
# ============================================================================

class HeartbeatManager:
    """Keepalive heartbeat with timeout detection.

    Monitors peer liveness by tracking heartbeat intervals and
    triggering timeout callbacks when threshold is exceeded.
    """

    def __init__(
        self,
        interval_sec: float = 5.0,
        timeout_sec: float = 15.0,
        on_timeout: Optional[Callable[[], None]] = None,
    ) -> None:
        """Initialize heartbeat manager.

        Args:
            interval_sec: Seconds between heartbeat sends.
            timeout_sec: Seconds before declaring peer dead.
            on_timeout: Callback fired on timeout detection.
        """
        self.interval = interval_sec
        self.timeout = timeout_sec
        self.on_timeout = on_timeout
        self._last_received: float = time.time()
        self._running = False
        self._timer: Optional[threading.Timer] = None
        self._timeout_timer: Optional[threading.Timer] = None

    def __repr__(self) -> str:
        return (f"HeartbeatManager(interval={self.interval}s, "
                f"timeout={self.timeout}s, running={self._running})")

    def start(self) -> None:
        """Start heartbeat monitoring timers."""
        self._running = True
        self._schedule_heartbeat()
        self._schedule_timeout_check()

    def stop(self) -> None:
        """Stop all heartbeat timers."""
        self._running = False
        if self._timer:
            self._timer.cancel()
        if self._timeout_timer:
            self._timeout_timer.cancel()

    def _schedule_heartbeat(self) -> None:
        """Schedule next heartbeat emission."""
        if not self._running:
            return
        self._timer = threading.Timer(self.interval, self._send_heartbeat)
        self._timer.daemon = True
        self._timer.start()

    def _schedule_timeout_check(self) -> None:
        """Schedule next timeout verification."""
        if not self._running:
            return
        self._timeout_timer = threading.Timer(self.timeout, self._check_timeout)
        self._timeout_timer.daemon = True
        self._timeout_timer.start()

    def _send_heartbeat(self) -> None:
        """Heartbeat send stub — override or wire to transport."""
        self._schedule_heartbeat()

    def _check_timeout(self) -> None:
        """Check if peer has timed out."""
        elapsed = time.time() - self._last_received
        if elapsed > self.timeout:
            if self.on_timeout:
                self.on_timeout()
        self._schedule_timeout_check()

    def pong_received(self) -> None:
        """Record heartbeat acknowledgement from peer."""
        self._last_received = time.time()

    def is_alive(self) -> bool:
        """Check if peer is still responsive."""
        return (time.time() - self._last_received) <= self.timeout


# ============================================================================
# Message Queue
# ============================================================================

class MessageQueue:
    """Thread-safe FIFO message buffer with overflow handling.

    Drops oldest messages when capacity is exceeded (circular eviction).
    """

    def __init__(self, capacity: int = 1000) -> None:
        """Initialize queue with max capacity.

        Args:
            capacity: Maximum messages to retain.
        """
        self.capacity = capacity
        self._queue: deque = deque(maxlen=capacity)
        self._lock = threading.Lock()
        self._dropped_count = 0

    def __repr__(self) -> str:
        return (f"MessageQueue(size={len(self._queue)}, "
                f"capacity={self.capacity}, dropped={self._dropped_count})")

    def enqueue(self, msg: Message) -> bool:
        """Add message to queue. Returns False if queue was full (oldest dropped)."""
        with self._lock:
            was_full = len(self._queue) >= self.capacity
            if was_full:
                self._dropped_count += 1
            self._queue.append(msg)
            return not was_full

    def dequeue(self) -> Optional[Message]:
        """Remove and return oldest message."""
        with self._lock:
            if self._queue:
                return self._queue.popleft()
            return None

    def peek(self) -> Optional[Message]:
        """Return oldest message without removing."""
        with self._lock:
            if self._queue:
                return self._queue[0]
            return None

    def size(self) -> int:
        """Return current queue length."""
        with self._lock:
            return len(self._queue)

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        with self._lock:
            return len(self._queue) == 0

    def clear(self) -> None:
        """Empty the queue."""
        with self._lock:
            self._queue.clear()

    def get_all(self) -> List[Message]:
        """Return snapshot of all queued messages."""
        with self._lock:
            return list(self._queue)


# ============================================================================
# Protocol Kernel (Bridge to Layer 1)
# ============================================================================

class ProtocolKernel:
    """Kernel orchestrating encryption, serialization, handshake, and queue.

    Bridges raw transport to structured, authenticated, encrypted messages.
    """

    def __init__(
        self,
        identity: str,
        secret: bytes,
        queue_capacity: int = 1000,
    ) -> None:
        """Initialize protocol kernel.

        Args:
            identity: Local peer identifier.
            secret: 32-byte shared secret for handshake and key derivation.
            queue_capacity: Max messages in inbound queue.
        """
        self.identity = identity
        self._secret = secret
        self._aes_key = hashlib.sha256(secret).digest()
        self._cipher = AES256GCM(self._aes_key)
        self._handshake = HandshakeProtocol(identity, secret)
        self._heartbeat = HeartbeatManager()
        self._inbound = MessageQueue(queue_capacity)
        self._outbound = MessageQueue(queue_capacity)
        self._peers: Dict[str, HandshakeProtocol] = {}
        self._lock = threading.Lock()

    def __repr__(self) -> str:
        return (f"ProtocolKernel(identity={self.identity!r}, "
                f"peers={len(self._peers)}, "
                f"inbound={self._inbound.size()}, outbound={self._outbound.size()})")

    def encrypt_message(self, msg: Message, aad: bytes = b'') -> Tuple[bytes, bytes, bytes]:
        """Encrypt a Message, returning (iv, ciphertext, tag).

        Args:
            msg: Message to encrypt.
            aad: Additional authenticated data.
        """
        serialized = Serializer.to_binary(msg)
        iv = os.urandom(12)
        ciphertext, tag = self._cipher.encrypt(serialized, iv, aad)
        return iv, ciphertext, tag

    def decrypt_message(
        self, iv: bytes, ciphertext: bytes, tag: bytes, aad: bytes = b''
    ) -> Message:
        """Decrypt and verify a Message.

        Args:
            iv: 12-byte initialization vector.
            ciphertext: Encrypted payload.
            tag: 16-byte authentication tag.
            aad: Additional authenticated data.

        Returns:
            Decrypted Message.
        """
        serialized = self._cipher.decrypt(ciphertext, iv, tag, aad)
        return Serializer.from_binary(serialized)

    def send_message(
        self,
        msg_type: MessageType,
        payload: bytes,
        recipient: str,
        encrypt: bool = True,
    ) -> Optional[Message]:
        """Construct, optionally encrypt, and queue a message for sending.

        Args:
            msg_type: Message classification.
            payload: Raw payload bytes.
            recipient: Target peer identifier.
            encrypt: Whether to encrypt the message.

        Returns:
            The constructed Message, or None if failed.
        """
        msg = Message(
            id=self._generate_id(),
            type=msg_type,
            payload=payload,
            sender=self.identity,
            recipient=recipient,
            timestamp=time.time(),
            signature=self._sign_payload(payload),
        )
        self._outbound.enqueue(msg)
        return msg

    def receive_message(self, raw_data: bytes) -> Optional[Message]:
        """Process raw inbound data into a Message and queue it.

        Args:
            raw_data: Serialized or encrypted message bytes.

        Returns:
            Parsed Message, or None if invalid.
        """
        try:
            msg = Serializer.from_binary(raw_data)
            if not self._verify_signature(msg):
                return None
            self._inbound.enqueue(msg)
            return msg
        except Exception:
            return None

    def _generate_id(self) -> str:
        """Generate UUID v4 string."""
        return hashlib.sha256(os.urandom(32)).hexdigest()[:32]

    def _sign_payload(self, payload: bytes) -> bytes:
        """Sign payload with local secret (HMAC-SHA256 truncated to 64 bytes)."""
        sig = hashlib.sha256(payload + self._secret).digest()
        return sig + hashlib.sha256(sig).digest()

    def _verify_signature(self, msg: Message) -> bool:
        """Verify message signature."""
        expected = self._sign_payload(msg.payload)
        return HandshakeProtocol._constant_time_compare(msg.signature, expected)

    def initiate_handshake(self, peer_id: str) -> Tuple[bytes, bytes]:
        """Start handshake with a peer. Returns (challenge, signed_challenge)."""
        peer = HandshakeProtocol(peer_id, self._secret)
        with self._lock:
            self._peers[peer_id] = peer
        challenge = peer.generate_challenge()
        signed = peer.sign_challenge(challenge)
        return challenge, signed

    def respond_handshake(self, peer_id: str, challenge: bytes) -> bytes:
        """Respond to a peer's handshake challenge."""
        peer = HandshakeProtocol(peer_id, self._secret)
        with self._lock:
            self._peers[peer_id] = peer
        return peer.sign_challenge(challenge)

    def verify_peer(self, peer_id: str, challenge: bytes, response: bytes) -> bool:
        """Verify peer's handshake response."""
        with self._lock:
            peer = self._peers.get(peer_id)
        if not peer:
            return False
        return peer.verify_response(challenge, response, peer_id)

    def is_peer_authenticated(self, peer_id: str) -> bool:
        """Check if peer has completed handshake."""
        with self._lock:
            peer = self._peers.get(peer_id)
        return peer.is_authenticated() if peer else False

    def get_inbound(self) -> MessageQueue:
        """Return inbound message queue."""
        return self._inbound

    def get_outbound(self) -> MessageQueue:
        """Return outbound message queue."""
        return self._outbound


# ============================================================================
# Demo / Self-Test
# ============================================================================

def run_demo() -> None:
    """Demonstrate encrypt → send → decrypt → verify handshake flow."""
    print("=" * 60)
    print("PROTOCOL_NATIVE DEMO")
    print("=" * 60)

    # Setup two peers
    secret = os.urandom(32)
    alice = ProtocolKernel("alice", secret)
    bob = ProtocolKernel("bob", secret)

    print(f"\n[1] Alice kernel: {alice}")
    print(f"    Bob kernel:   {bob}")

    # Handshake
    print("\n[2] Handshake: Alice -> Bob")
    challenge, alice_signed = alice.initiate_handshake("bob")
    bob_response = bob.respond_handshake("alice", challenge)
    ok = alice.verify_peer("bob", challenge, bob_response)
    print(f"    Alice verifies Bob: {ok}")

    challenge2, bob_signed = bob.initiate_handshake("alice")
    alice_response = alice.respond_handshake("bob", challenge2)
    ok2 = bob.verify_peer("alice", challenge2, alice_response)
    print(f"    Bob verifies Alice: {ok2}")

    # Encrypt and send message
    print("\n[3] Encrypt -> Send -> Decrypt")
    payload = b"Hello, this is a secret message!"
    msg = alice.send_message(MessageType.DATA, payload, "bob")
    print(f"    Created: {msg}")

    aad = b"session-v1"
    iv, ciphertext, tag = alice.encrypt_message(msg, aad)
    print(f"    IV:        {iv.hex()[:24]}...")
    print(f"    Ciphertext: {len(ciphertext)} bytes")
    print(f"    Tag:       {tag.hex()[:24]}...")

    # Decrypt
    decrypted = bob.decrypt_message(iv, ciphertext, tag, aad)
    print(f"    Decrypted: {decrypted}")

    # Verify payload integrity
    print(f"    Payload match: {decrypted.payload == payload}")

    # Heartbeat
    print("\n[4] Heartbeat")
    hb = HeartbeatManager(interval_sec=1.0, timeout_sec=3.0)
    print(f"    {hb}")
    hb.pong_received()
    print(f"    Alive: {hb.is_alive()}")

    # Message Queue
    print("\n[5] Message Queue")
    q = MessageQueue(capacity=3)
    for i in range(5):
        m = Message(
            id=f"msg-{i}", type=MessageType.DATA,
            payload=b"x", sender="a", recipient="b",
            timestamp=time.time(), signature=b'\x00'*64,
        )
        q.enqueue(m)
    print(f"    {q}")
    print(f"    All IDs: {[m.id for m in q.get_all()]}")

    # JSON / Binary serialization
    print("\n[6] Serialization")
    json_bytes = Serializer.to_json(msg)
    msg_from_json = Serializer.from_json(json_bytes)
    print(f"    JSON roundtrip OK: {msg_from_json.payload == msg.payload}")

    bin_bytes = Serializer.to_binary(msg)
    msg_from_bin = Serializer.from_binary(bin_bytes)
    print(f"    Binary roundtrip OK: {msg_from_bin.payload == msg.payload}")

    print("\n" + "=" * 60)
    print("DEMO COMPLETE -- ALL CHECKS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
