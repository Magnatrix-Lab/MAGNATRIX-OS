#!/usr/bin/env python3
"""
protocol/protocol_stack_native.py — MAGNATRIX-OS Native Protocol Stack
Pure stdlib. No external dependencies.

Features:
  • MessageFramer — length-prefix, delimiter, fixed-size framing
  • Serializer — JSON, msgpack-like binary, custom TLV binary
  • Compressor — zlib (gzip/deflate), pass-through, size-aware adaptive
  • EncryptionWrapper — ChaCha20-like stream cipher (XOR-based), key handshake
  • HandshakeProtocol — version negotiation, cipher suite selection
  • ProtocolStack — composes all layers with encode/decode pipeline

Naming convention: Native<ClassName>
"""

from __future__ import annotations

import json
import os
import struct
import zlib
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# NativeMessageFramer
# ---------------------------------------------------------------------------

class NativeMessageFramer:
    """Frame raw bytes with length-prefix, delimiter, or fixed-size."""

    LENGTH_PREFIX = "length_prefix"
    DELIMITER = "delimiter"
    FIXED_SIZE = "fixed_size"

    def __init__(self, mode: str = LENGTH_PREFIX, delimiter: bytes = b"\r\n", fixed_size: int = 1024) -> None:
        self.mode = mode
        self.delimiter = delimiter
        self.fixed_size = fixed_size

    def frame(self, payload: bytes) -> bytes:
        if self.mode == self.LENGTH_PREFIX:
            length = len(payload)
            return struct.pack(">I", length) + payload
        elif self.mode == self.DELIMITER:
            return payload + self.delimiter
        elif self.mode == self.FIXED_SIZE:
            if len(payload) > self.fixed_size:
                raise ValueError(f"payload exceeds fixed size {self.fixed_size}")
            return payload.ljust(self.fixed_size, b"\x00")
        else:
            raise ValueError(f"unknown framing mode: {self.mode}")

    def unframe(self, data: bytes) -> Tuple[bytes, bytes]:
        """Return (message, remaining_buffer). Incomplete => message empty."""
        if self.mode == self.LENGTH_PREFIX:
            if len(data) < 4:
                return b"", data
            length = struct.unpack(">I", data[:4])[0]
            if len(data) < 4 + length:
                return b"", data
            return data[4:4 + length], data[4 + length:]
        elif self.mode == self.DELIMITER:
            idx = data.find(self.delimiter)
            if idx == -1:
                return b"", data
            return data[:idx], data[idx + len(self.delimiter):]
        elif self.mode == self.FIXED_SIZE:
            if len(data) < self.fixed_size:
                return b"", data
            msg = data[:self.fixed_size].rstrip(b"\x00")
            return msg, data[self.fixed_size:]
        else:
            raise ValueError(f"unknown framing mode: {self.mode}")


# ---------------------------------------------------------------------------
# NativeSerializer
# ---------------------------------------------------------------------------

class NativeSerializer:
    """JSON, msgpack-like binary, and custom TLV binary serializer."""

    JSON = "json"
    MSGPACK = "msgpack"
    TLV = "tlv"

    def __init__(self, mode: str = JSON) -> None:
        self.mode = mode

    def encode(self, obj: Any) -> bytes:
        if self.mode == self.JSON:
            return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        elif self.mode == self.MSGPACK:
            return self._encode_msgpack(obj)
        elif self.mode == self.TLV:
            return self._encode_tlv(obj)
        else:
            raise ValueError(f"unknown serializer mode: {self.mode}")

    def decode(self, data: bytes) -> Any:
        if self.mode == self.JSON:
            return json.loads(data.decode("utf-8"))
        elif self.mode == self.MSGPACK:
            return self._decode_msgpack(data)[0]
        elif self.mode == self.TLV:
            return self._decode_tlv(data)
        else:
            raise ValueError(f"unknown serializer mode: {self.mode}")

    # ---- msgpack-like (simplified) ----

    def _encode_msgpack(self, obj: Any) -> bytes:
        if obj is None:
            return b"\xc0"
        if obj is True:
            return b"\xc3"
        if obj is False:
            return b"\xc2"
        if isinstance(obj, int):
            if 0 <= obj <= 127:
                return struct.pack("b", obj)
            elif -32 <= obj < 0:
                return struct.pack("b", obj)
            elif -128 <= obj <= 127:
                return b"\xd0" + struct.pack("b", obj)
            elif -32768 <= obj <= 32767:
                return b"\xd1" + struct.pack(">h", obj)
            elif -2147483648 <= obj <= 2147483647:
                return b"\xd2" + struct.pack(">i", obj)
            else:
                return b"\xd3" + struct.pack(">q", obj)
        if isinstance(obj, float):
            return b"\xcb" + struct.pack(">d", obj)
        if isinstance(obj, str):
            data = obj.encode("utf-8")
            l = len(data)
            if l <= 31:
                return struct.pack("B", 0xA0 + l) + data
            elif l <= 255:
                return b"\xd9" + struct.pack("B", l) + data
            elif l <= 65535:
                return b"\xda" + struct.pack(">H", l) + data
            else:
                return b"\xdb" + struct.pack(">I", l) + data
        if isinstance(obj, bytes):
            l = len(obj)
            if l <= 255:
                return b"\xc4" + struct.pack("B", l) + obj
            elif l <= 65535:
                return b"\xc5" + struct.pack(">H", l) + obj
            else:
                return b"\xc6" + struct.pack(">I", l) + obj
        if isinstance(obj, list):
            l = len(obj)
            header = b"\xdd" + struct.pack(">I", l) if l > 15 else struct.pack("B", 0x90 + l)
            return header + b"".join(self._encode_msgpack(i) for i in obj)
        if isinstance(obj, dict):
            l = len(obj)
            header = b"\xdf" + struct.pack(">I", l) if l > 15 else struct.pack("B", 0x80 + l)
            return header + b"".join(
                self._encode_msgpack(k) + self._encode_msgpack(v) for k, v in obj.items()
            )
        raise TypeError(f"unsupported type: {type(obj)}")

    def _decode_msgpack(self, data: bytes, offset: int = 0) -> Tuple[Any, int]:
        if offset >= len(data):
            raise ValueError("unexpected end")
        tag = data[offset]
        offset += 1

        if tag == 0xC0:
            return None, offset
        if tag == 0xC3:
            return True, offset
        if tag == 0xC2:
            return False, offset

        if tag & 0x80 == 0:
            return tag, offset
        if tag & 0xE0 == 0xE0:
            return struct.unpack("b", bytes([tag]))[0], offset

        if tag == 0xD0:
            return struct.unpack("b", data[offset:offset + 1])[0], offset + 1
        if tag == 0xD1:
            return struct.unpack(">h", data[offset:offset + 2])[0], offset + 2
        if tag == 0xD2:
            return struct.unpack(">i", data[offset:offset + 4])[0], offset + 4
        if tag == 0xD3:
            return struct.unpack(">q", data[offset:offset + 8])[0], offset + 8
        if tag == 0xCB:
            return struct.unpack(">d", data[offset:offset + 8])[0], offset + 8

        if tag & 0xE0 == 0xA0:
            l = tag & 0x1F
            return data[offset:offset + l].decode("utf-8"), offset + l
        if tag == 0xD9:
            l = data[offset]
            offset += 1
            return data[offset:offset + l].decode("utf-8"), offset + l
        if tag == 0xDA:
            l = struct.unpack(">H", data[offset:offset + 2])[0]
            offset += 2
            return data[offset:offset + l].decode("utf-8"), offset + l
        if tag == 0xDB:
            l = struct.unpack(">I", data[offset:offset + 4])[0]
            offset += 4
            return data[offset:offset + l].decode("utf-8"), offset + l

        if tag == 0xC4:
            l = data[offset]
            offset += 1
            return data[offset:offset + l], offset + l
        if tag == 0xC5:
            l = struct.unpack(">H", data[offset:offset + 2])[0]
            offset += 2
            return data[offset:offset + l], offset + l
        if tag == 0xC6:
            l = struct.unpack(">I", data[offset:offset + 4])[0]
            offset += 4
            return data[offset:offset + l], offset + l

        if tag & 0xF0 == 0x90:
            l = tag & 0x0F
            arr = []
            for _ in range(l):
                v, offset = self._decode_msgpack(data, offset)
                arr.append(v)
            return arr, offset
        if tag == 0xDD:
            l = struct.unpack(">I", data[offset:offset + 4])[0]
            offset += 4
            arr = []
            for _ in range(l):
                v, offset = self._decode_msgpack(data, offset)
                arr.append(v)
            return arr, offset

        if tag & 0xF0 == 0x80:
            l = tag & 0x0F
            d = {}
            for _ in range(l):
                k, offset = self._decode_msgpack(data, offset)
                v, offset = self._decode_msgpack(data, offset)
                d[k] = v
            return d, offset
        if tag == 0xDF:
            l = struct.unpack(">I", data[offset:offset + 4])[0]
            offset += 4
            d = {}
            for _ in range(l):
                k, offset = self._decode_msgpack(data, offset)
                v, offset = self._decode_msgpack(data, offset)
                d[k] = v
            return d, offset

        raise ValueError(f"unknown msgpack tag: 0x{tag:02X}")

    # ---- custom TLV (type-length-value) ----

    def _encode_tlv(self, obj: Any) -> bytes:
        if not isinstance(obj, dict):
            raise TypeError("TLV mode only supports dict at top level")
        parts = []
        for key, value in obj.items():
            key_b = key.encode("utf-8")
            val_b = json.dumps(value, separators=(",", ":")).encode("utf-8")
            parts.append(struct.pack(">B", 0x01))  # type: string key
            parts.append(struct.pack(">H", len(key_b)))
            parts.append(key_b)
            parts.append(struct.pack(">B", 0x02))  # type: JSON value
            parts.append(struct.pack(">I", len(val_b)))
            parts.append(val_b)
        return b"".join(parts)

    def _decode_tlv(self, data: bytes) -> Dict[str, Any]:
        result = {}
        offset = 0
        while offset < len(data):
            if offset + 3 > len(data):
                break
            _ = data[offset]  # key type
            offset += 1
            kl = struct.unpack(">H", data[offset:offset + 2])[0]
            offset += 2
            key = data[offset:offset + kl].decode("utf-8")
            offset += kl
            _ = data[offset]  # val type
            offset += 1
            vl = struct.unpack(">I", data[offset:offset + 4])[0]
            offset += 4
            val = json.loads(data[offset:offset + vl].decode("utf-8"))
            offset += vl
            result[key] = val
        return result


# ---------------------------------------------------------------------------
# NativeCompressor
# ---------------------------------------------------------------------------

class NativeCompressor:
    """Adaptive compression: zlib gzip/deflate with size threshold."""

    NONE = "none"
    GZIP = "gzip"
    DEFLATE = "deflate"

    def __init__(self, mode: str = GZIP, threshold: int = 64) -> None:
        self.mode = mode
        self.threshold = threshold

    def compress(self, data: bytes) -> Tuple[bytes, str]:
        if self.mode == self.NONE or len(data) < self.threshold:
            return data, self.NONE
        if self.mode == self.GZIP:
            return zlib.compress(data, level=6), self.GZIP
        if self.mode == self.DEFLATE:
            return zlib.compress(data, level=6)[2:-4], self.DEFLATE
        return data, self.NONE

    def decompress(self, data: bytes, mode: str) -> bytes:
        if mode == self.NONE:
            return data
        if mode == self.GZIP:
            return zlib.decompress(data)
        if mode == self.DEFLATE:
            return zlib.decompress(data, -15)
        return data


# ---------------------------------------------------------------------------
# NativeEncryptionWrapper
# ---------------------------------------------------------------------------

class NativeEncryptionWrapper:
    """ChaCha20-like stream cipher using simple XOR with deterministic key stream."""

    def __init__(self, key: Optional[bytes] = None) -> None:
        self.key = key or os.urandom(32)

    def _keystream(self, nonce: bytes, length: int) -> bytes:
        """Generate pseudo-random keystream from key + nonce via SHA256 chaining."""
        stream = b""
        counter = 0
        chunk = self.key + nonce
        while len(stream) < length:
            chunk = __import__("hashlib").sha256(chunk + struct.pack(">Q", counter)).digest()
            stream += chunk
            counter += 1
        return stream[:length]

    def encrypt(self, plaintext: bytes, nonce: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        nonce = nonce or os.urandom(12)
        ks = self._keystream(nonce, len(plaintext))
        ciphertext = bytes(a ^ b for a, b in zip(plaintext, ks))
        return ciphertext, nonce

    def decrypt(self, ciphertext: bytes, nonce: bytes) -> bytes:
        ks = self._keystream(nonce, len(ciphertext))
        return bytes(a ^ b for a, b in zip(ciphertext, ks))


# ---------------------------------------------------------------------------
# NativeHandshakeProtocol
# ---------------------------------------------------------------------------

class NativeHandshakeProtocol:
    """Version + cipher suite negotiation."""

    VERSION = "1.0"
    CIPHERS = ["chacha20", "aes256"]

    def __init__(self) -> None:
        self.negotiated: Dict[str, Any] = {}

    def client_hello(self) -> Dict[str, Any]:
        return {"version": self.VERSION, "ciphers": self.CIPHERS, "role": "client"}

    def server_hello(self, client_hello: Dict[str, Any]) -> Dict[str, Any]:
        version = min(self.VERSION, client_hello.get("version", "1.0"))
        ciphers = [c for c in self.CIPHERS if c in client_hello.get("ciphers", [])]
        chosen = ciphers[0] if ciphers else "none"
        session_id = os.urandom(16).hex()
        self.negotiated = {"version": version, "cipher": chosen, "session_id": session_id}
        return {"version": version, "cipher": chosen, "session_id": session_id, "role": "server"}

    def is_complete(self) -> bool:
        return bool(self.negotiated)


# ---------------------------------------------------------------------------
# NativeProtocolStack
# ---------------------------------------------------------------------------

class NativeProtocolStack:
    """Composes framer → serializer → compressor → encryption pipeline."""

    def __init__(
        self,
        framer: Optional[NativeMessageFramer] = None,
        serializer: Optional[NativeSerializer] = None,
        compressor: Optional[NativeCompressor] = None,
        encryption: Optional[NativeEncryptionWrapper] = None,
        handshake: Optional[NativeHandshakeProtocol] = None,
    ) -> None:
        self.framer = framer or NativeMessageFramer()
        self.serializer = serializer or NativeSerializer()
        self.compressor = compressor or NativeCompressor()
        self.encryption = encryption or NativeEncryptionWrapper()
        self.handshake = handshake or NativeHandshakeProtocol()

    def encode(self, obj: Any, with_encryption: bool = True) -> bytes:
        """Serialize → compress → encrypt → frame."""
        payload = self.serializer.encode(obj)
        payload, comp_mode = self.compressor.compress(payload)
        meta = {"compression": comp_mode}
        if with_encryption:
            payload, nonce = self.encryption.encrypt(payload)
            meta["nonce"] = nonce.hex()
        envelope = {"meta": meta, "payload": payload.hex()}
        inner = self.serializer.encode(envelope)
        return self.framer.frame(inner)

    def decode(self, data: bytes, with_encryption: bool = True) -> Tuple[Any, bytes]:
        """Unframe → decrypt → decompress → deserialize. Return (object, remaining_buffer)."""
        inner, remaining = self.framer.unframe(data)
        if not inner:
            return None, remaining
        envelope = self.serializer.decode(inner)
        meta = envelope.get("meta", {})
        payload = bytes.fromhex(envelope["payload"])
        if with_encryption:
            nonce = bytes.fromhex(meta.get("nonce", "00" * 12))
            payload = self.encryption.decrypt(payload, nonce)
        payload = self.compressor.decompress(payload, meta.get("compression", "none"))
        obj = self.serializer.decode(payload)
        return obj, remaining


# ---------------------------------------------------------------------------
# Self-test demo
# ---------------------------------------------------------------------------

def run() -> None:
    print("=" * 60)
    print("NativeProtocolStack — self-test demo")
    print("=" * 60)

    # [1] Framer tests
    print("\n[1] MessageFramer (length-prefix)")
    framer = NativeMessageFramer(NativeMessageFramer.LENGTH_PREFIX)
    msg = b"hello, protocol world"
    framed = framer.frame(msg)
    print(f"    framed len={len(framed)} header={framed[:4].hex()}")
    unframed, rem = framer.unframe(framed + b"extra")
    print(f"    unframed={unframed!r} remaining={rem!r}")
    assert unframed == msg

    print("\n[2] MessageFramer (delimiter)")
    framer2 = NativeMessageFramer(NativeMessageFramer.DELIMITER, delimiter=b"\n")
    framed2 = framer2.frame(b"line1")
    print(f"    framed={framed2!r}")
    u2, r2 = framer2.unframe(framed2 + b"leftover")
    print(f"    unframed={u2!r} remaining={r2!r}")
    assert u2 == b"line1"

    print("\n[3] MessageFramer (fixed-size)")
    framer3 = NativeMessageFramer(NativeMessageFramer.FIXED_SIZE, fixed_size=32)
    framed3 = framer3.frame(b"short")
    print(f"    framed len={len(framed3)}")
    u3, r3 = framer3.unframe(framed3 + b"x")
    print(f"    unframed={u3!r} remaining={r3!r}")
    assert u3 == b"short"

    # [4] Serializer JSON
    print("\n[4] Serializer JSON")
    ser_json = NativeSerializer(NativeSerializer.JSON)
    obj = {"name": "test", "value": 42, "flag": True}
    enc = ser_json.encode(obj)
    print(f"    encoded={enc!r}")
    dec = ser_json.decode(enc)
    print(f"    decoded={dec}")
    assert dec == obj

    # [5] Serializer msgpack
    print("\n[5] Serializer msgpack")
    ser_mp = NativeSerializer(NativeSerializer.MSGPACK)
    obj_mp = {"id": 12345, "tags": ["a", "b", "c"], "ratio": 0.99}
    enc_mp = ser_mp.encode(obj_mp)
    print(f"    encoded bytes={len(enc_mp)} hex_start={enc_mp[:8].hex()}")
    dec_mp, _off = ser_mp._decode_msgpack(enc_mp)
    print(f"    decoded={dec_mp}")
    assert dec_mp == obj_mp

    # [6] Serializer TLV
    print("\n[6] Serializer TLV")
    ser_tlv = NativeSerializer(NativeSerializer.TLV)
    obj_tlv = {"cmd": "ping", "seq": 7}
    enc_tlv = ser_tlv.encode(obj_tlv)
    print(f"    encoded bytes={len(enc_tlv)} hex={enc_tlv.hex()}")
    dec_tlv = ser_tlv.decode(enc_tlv)
    print(f"    decoded={dec_tlv}")
    assert dec_tlv == obj_tlv

    # [7] Compressor
    print("\n[7] Compressor")
    comp = NativeCompressor(NativeCompressor.GZIP, threshold=16)
    raw = b"x" * 1000
    cdata, mode = comp.compress(raw)
    print(f"    original={len(raw)} compressed={len(cdata)} mode={mode}")
    ddata = comp.decompress(cdata, mode)
    assert ddata == raw

    # [8] Encryption
    print("\n[8] EncryptionWrapper")
    encw = NativeEncryptionWrapper(key=b"0" * 32)
    plain = b"secret message for magnatrix"
    ct, nonce = encw.encrypt(plain)
    print(f"    plaintext={len(plain)} ciphertext={len(ct)} nonce={nonce.hex()}")
    dec_plain = encw.decrypt(ct, nonce)
    assert dec_plain == plain
    print(f"    decrypted={dec_plain!r}")

    # [9] Handshake
    print("\n[9] HandshakeProtocol")
    hs_client = NativeHandshakeProtocol()
    hs_server = NativeHandshakeProtocol()
    ch = hs_client.client_hello()
    print(f"    client_hello={ch}")
    sh = hs_server.server_hello(ch)
    print(f"    server_hello={sh}")
    assert hs_server.is_complete()

    # [10] Full stack encode/decode
    print("\n[10] Full ProtocolStack round-trip")
    stack = NativeProtocolStack(
        framer=NativeMessageFramer(NativeMessageFramer.LENGTH_PREFIX),
        serializer=NativeSerializer(NativeSerializer.JSON),
        compressor=NativeCompressor(NativeCompressor.GZIP, threshold=8),
        encryption=NativeEncryptionWrapper(key=b"k" * 32),
    )
    original = {"action": "send", "payload": "magnatrix protocol v1", "timestamp": 1717000000}
    wire = stack.encode(original)
    print(f"    wire bytes={len(wire)}")
    decoded, rem = stack.decode(wire)
    print(f"    decoded={decoded}")
    assert decoded == original

    # [11] Stack without encryption
    print("\n[11] ProtocolStack without encryption")
    wire2 = stack.encode(original, with_encryption=False)
    decoded2, _ = stack.decode(wire2, with_encryption=False)
    assert decoded2 == original
    print(f"    decoded={decoded2}")

    # [12] Multi-message streaming decode
    print("\n[12] Streaming decode (2 messages in one buffer)")
    msg1 = stack.encode({"seq": 1}, with_encryption=False)
    msg2 = stack.encode({"seq": 2}, with_encryption=False)
    combined = msg1 + msg2
    results = []
    buf = combined
    while buf:
        obj, buf = stack.decode(buf, with_encryption=False)
        if obj is None:
            break
        results.append(obj)
    print(f"    decoded messages={results}")
    assert results == [{"seq": 1}, {"seq": 2}]

    print("\n✅ All protocol stack tests passed.")
    print("=" * 60)


if __name__ == "__main__":
    run()
