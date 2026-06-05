"""Packet Analyzer — protocol parsing, flow tracking, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum, auto
import time

class ProtocolType(Enum):
    HTTP = auto()
    TCP = auto()
    UDP = auto()
    DNS = auto()
    ARP = auto()
    UNKNOWN = auto()

@dataclass
class PacketRecord:
    packet_id: str
    timestamp: float
    src: str
    dst: str
    protocol: ProtocolType
    size: int
    payload: Optional[str] = None

class PacketAnalyzer:
    def __init__(self):
        self.packets: List[PacketRecord] = []
        self.flows: Dict[str, List[PacketRecord]] = {}
        self.stats_data = {"total": 0, "by_protocol": {}, "total_bytes": 0}

    def ingest(self, packet: PacketRecord):
        self.packets.append(packet)
        self.stats_data["total"] += 1
        self.stats_data["by_protocol"][packet.protocol.name] = self.stats_data["by_protocol"].get(packet.protocol.name, 0) + 1
        self.stats_data["total_bytes"] += packet.size
        flow_key = tuple(sorted([packet.src, packet.dst]))
        flow_id = f"{flow_key[0]}-{flow_key[1]}"
        if flow_id not in self.flows:
            self.flows[flow_id] = []
        self.flows[flow_id].append(packet)

    def detect_protocol(self, payload: str) -> ProtocolType:
        if payload.startswith("HTTP") or "GET " in payload or "POST " in payload:
            return ProtocolType.HTTP
        if payload.startswith("DNS") or "QUERY" in payload:
            return ProtocolType.DNS
        if payload.startswith("ARP"):
            return ProtocolType.ARP
        return ProtocolType.UNKNOWN

    def get_flow_stats(self, flow_id: str) -> Dict:
        flow = self.flows.get(flow_id, [])
        if not flow:
            return {}
        return {"packets": len(flow), "bytes": sum(p.size for p in flow), "duration": flow[-1].timestamp - flow[0].timestamp if len(flow) > 1 else 0}

    def top_talkers(self, n: int = 5) -> List[Tuple[str, int]]:
        talkers = {}
        for p in self.packets:
            talkers[p.src] = talkers.get(p.src, 0) + p.size
        return sorted(talkers.items(), key=lambda x: x[1], reverse=True)[:n]

    def stats(self) -> Dict:
        return {"packets": len(self.packets), "flows": len(self.flows), **self.stats_data}

def run():
    analyzer = PacketAnalyzer()
    for i in range(10):
        p = PacketRecord(f"p{i}", time.time(), f"10.0.0.{i%3}", f"10.0.0.{(i+1)%3}", ProtocolType.TCP, 100 + i * 10, f"payload_{i}")
        analyzer.ingest(p)
    print(analyzer.top_talkers(3))
    print(analyzer.stats())

if __name__ == "__main__":
    run()
