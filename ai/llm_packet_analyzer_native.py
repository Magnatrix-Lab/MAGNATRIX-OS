"""Packet Analyzer - Network packet parser for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import struct

class ProtocolType(Enum):
    TCP = auto(); UDP = auto(); ICMP = auto()

@dataclass
class PacketAnalyzer:
    protocol: ProtocolType = ProtocolType.TCP
    
    def parse_tcp(self, raw: bytes) -> Dict:
        if len(raw) < 20: return {}
        src_port, dst_port = struct.unpack("!HH", raw[:4])
        seq, ack = struct.unpack("!II", raw[4:12])
        flags = raw[13]
        return {"src_port": src_port, "dst_port": dst_port, "seq": seq, "ack": ack, "flags": flags}
    
    def parse_udp(self, raw: bytes) -> Dict:
        if len(raw) < 8: return {}
        src_port, dst_port, length, checksum = struct.unpack("!HHHH", raw[:8])
        return {"src_port": src_port, "dst_port": dst_port, "length": length}
    
    def parse(self, raw: bytes) -> Dict:
        if self.protocol == ProtocolType.TCP: return self.parse_tcp(raw)
        if self.protocol == ProtocolType.UDP: return self.parse_udp(raw)
        return {}
    
    def stats(self, raw: bytes) -> dict:
        parsed = self.parse(raw)
        return {"protocol": self.protocol.name, "parsed": parsed}

def run():
    pa = PacketAnalyzer(ProtocolType.TCP)
    raw = bytes([0x00, 0x50, 0x00, 0x50, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x50, 0x02, 0x71, 0x10, 0x00, 0x00, 0x00, 0x00])
    print("Parsed:", pa.parse(raw))
    print("Stats:", pa.stats(raw))

if __name__ == "__main__": run()
