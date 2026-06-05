"""VPN Tunnel — encapsulation, encryption, key rotation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Callable
from enum import Enum, auto
import hashlib
import time
import random

class VPNState(Enum):
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    ERROR = auto()

@dataclass
class VPNPacket:
    original_src: str
    original_dst: str
    payload: str
    encrypted: bool = False

class VPNTunnel:
    def __init__(self, tunnel_id: str):
        self.tunnel_id = tunnel_id
        self.state = VPNState.DISCONNECTED
        self.key = ""
        self.key_created = 0.0
        self.key_lifetime = 3600.0
        self.packets_in = 0
        self.packets_out = 0
        self.bytes_in = 0
        self.bytes_out = 0

    def connect(self, shared_secret: str):
        self.key = hashlib.sha256(shared_secret.encode()).hexdigest()[:16]
        self.key_created = time.time()
        self.state = VPNState.CONNECTED

    def _rotate_key(self):
        if time.time() - self.key_created > self.key_lifetime:
            self.key = hashlib.sha256((self.key + str(time.time())).encode()).hexdigest()[:16]
            self.key_created = time.time()

    def _encrypt(self, data: str) -> str:
        self._rotate_key()
        key_bytes = [ord(c) for c in self.key]
        encrypted = ""
        for i, c in enumerate(data):
            encrypted += chr(ord(c) ^ key_bytes[i % len(key_bytes)])
        return encrypted

    def _decrypt(self, data: str) -> str:
        return self._encrypt(data)

    def encapsulate(self, packet: VPNPacket) -> str:
        if self.state != VPNState.CONNECTED:
            raise Exception("Tunnel not connected")
        encrypted = self._encrypt(packet.payload)
        self.packets_out += 1
        self.bytes_out += len(packet.payload)
        return f"TUNNEL:{self.tunnel_id}:{encrypted}"

    def decapsulate(self, tunneled_data: str) -> VPNPacket:
        if self.state != VPNState.CONNECTED:
            raise Exception("Tunnel not connected")
        parts = tunneled_data.split(":", 2)
        if len(parts) < 3:
            raise ValueError("Invalid packet")
        payload = self._decrypt(parts[2])
        self.packets_in += 1
        self.bytes_in += len(payload)
        return VPNPacket("unknown", "unknown", payload, True)

    def disconnect(self):
        self.state = VPNState.DISCONNECTED
        self.key = ""

    def stats(self) -> Dict:
        return {"tunnel_id": self.tunnel_id, "state": self.state.name, "packets_in": self.packets_in, "packets_out": self.packets_out, "bytes_in": self.bytes_in, "bytes_out": self.bytes_out}

def run():
    tunnel = VPNTunnel("t1")
    tunnel.connect("secret123")
    p = VPNPacket("10.0.0.1", "10.0.0.2", "Hello World!")
    enc = tunnel.encapsulate(p)
    print(enc)
    dec = tunnel.decapsulate(enc)
    print(dec.payload)
    print(tunnel.stats())

if __name__ == "__main__":
    run()
