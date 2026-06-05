"""Firewall Engine — packet filtering, stateful, rules, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import time

class Protocol(Enum):
    TCP = auto()
    UDP = auto()
    ICMP = auto()
    ANY = auto()

class Action(Enum):
    ALLOW = auto()
    DENY = auto()
    LOG = auto()

@dataclass
class Packet:
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: Protocol
    payload_size: int = 0

@dataclass
class FirewallRule:
    rule_id: str
    src_ip: Optional[str]
    dst_ip: Optional[str]
    src_port: Optional[int]
    dst_port: Optional[int]
    protocol: Protocol
    action: Action
    priority: int = 0

class FirewallEngine:
    def __init__(self):
        self.rules: List[FirewallRule] = []
        self.state_table: Dict[str, Dict] = {}
        self.logs: List[Dict] = []
        self.stats_data = {"allowed": 0, "denied": 0, "logged": 0}

    def add_rule(self, rule: FirewallRule):
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority)

    def _match_ip(self, ip: str, pattern: Optional[str]) -> bool:
        if pattern is None or pattern == "*":
            return True
        return ip == pattern

    def _match_port(self, port: int, pattern: Optional[int]) -> bool:
        if pattern is None or pattern == -1:
            return True
        return port == pattern

    def process(self, packet: Packet) -> Action:
        for rule in self.rules:
            if (self._match_ip(packet.src_ip, rule.src_ip) and
                self._match_ip(packet.dst_ip, rule.dst_ip) and
                self._match_port(packet.src_port, rule.src_port) and
                self._match_port(packet.dst_port, rule.dst_port) and
                (rule.protocol == Protocol.ANY or packet.protocol == rule.protocol)):
                self.logs.append({"packet": packet, "rule": rule.rule_id, "action": rule.action.name, "time": time.time()})
                if rule.action == Action.ALLOW:
                    self.stats_data["allowed"] += 1
                elif rule.action == Action.DENY:
                    self.stats_data["denied"] += 1
                elif rule.action == Action.LOG:
                    self.stats_data["logged"] += 1
                return rule.action
        self.stats_data["denied"] += 1
        return Action.DENY

    def stats(self) -> Dict:
        return {"rules": len(self.rules), **self.stats_data, "log_size": len(self.logs)}

def run():
    fw = FirewallEngine()
    fw.add_rule(FirewallRule("r1", None, "10.0.0.1", None, 80, Protocol.TCP, Action.ALLOW, 1))
    fw.add_rule(FirewallRule("r2", "192.168.1.1", None, None, None, Protocol.ANY, Action.DENY, 2))
    p1 = Packet("10.0.0.5", "10.0.0.1", 12345, 80, Protocol.TCP)
    p2 = Packet("192.168.1.1", "10.0.0.1", 12345, 80, Protocol.TCP)
    print(fw.process(p1).name)
    print(fw.process(p2).name)
    print(fw.stats())

if __name__ == "__main__":
    run()
