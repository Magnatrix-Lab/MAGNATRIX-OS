"""
cap_theorem_analyzer_native.py
MAGNATRIX-OS — CAP Theorem Analyzer

Inspired by donnemartin/system-design-primer CAP theorem:
Analyze distributed systems for Consistency, Availability, Partition tolerance trade-offs. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class SystemProfile:
    system_name: str
    consistency: str  # strong, eventual, causal, none
    availability: str  # high, medium, low
    partition_tolerance: str  # full, partial, none
    use_case: str
    tradeoffs: List[str] = field(default_factory=list)


class CAPTheoremAnalyzer:
    """Analyze distributed systems for CAP theorem trade-offs."""

    def __init__(self, data_dir: str = "./cap_analysis"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.profiles: Dict[str, SystemProfile] = {}
        self._load()

    def _load(self) -> None:
        file = self.data_dir / "profiles.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for name, pd in data.items():
                        self.profiles[name] = SystemProfile(**pd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.data_dir / "profiles.json", "w", encoding="utf-8") as f:
            json.dump({k: asdict(v) for k, v in self.profiles.items()}, f, indent=2)

    def profile(self, system_name: str, consistency: str, availability: str,
                partition_tolerance: str, use_case: str) -> SystemProfile:
        tradeoffs = self._compute_tradeoffs(consistency, availability, partition_tolerance)
        profile = SystemProfile(
            system_name=system_name, consistency=consistency,
            availability=availability, partition_tolerance=partition_tolerance,
            use_case=use_case, tradeoffs=tradeoffs,
        )
        self.profiles[system_name] = profile
        self._save()
        return profile

    def _compute_tradeoffs(self, c: str, a: str, pt: str) -> List[str]:
        tradeoffs = []
        if c == "strong" and a == "high":
            tradeoffs.append("Requires synchronous replication, increases latency")
        if c == "eventual" and a == "high":
            tradeoffs.append("May serve stale data during partitions")
        if pt == "none" and a == "high":
            tradeoffs.append("Cannot tolerate network partitions")
        if c == "strong" and pt == "full":
            tradeoffs.append("Availability may degrade during partitions")
        if c == "none":
            tradeoffs.append("No consistency guarantees, maximum availability")
        return tradeoffs

    def classify(self, system_name: str) -> str:
        p = self.profiles.get(system_name)
        if not p:
            return "unknown"
        c, a = p.consistency, p.availability
        if c == "strong" and a == "high":
            return "CP"  # Consistency + Partition tolerance
        if c == "eventual" and a == "high":
            return "AP"  # Availability + Partition tolerance
        if c == "strong" and a != "high":
            return "CP"
        return "AP" if a == "high" else "CP"

    def compare(self, system_a: str, system_b: str) -> Dict[str, Any]:
        a = self.profiles.get(system_a)
        b = self.profiles.get(system_b)
        if not a or not b:
            return {"error": "System not found"}
        return {
            "system_a": system_a, "system_b": system_b,
            "same_consistency": a.consistency == b.consistency,
            "same_availability": a.availability == b.availability,
            "same_partition_tolerance": a.partition_tolerance == b.partition_tolerance,
        }

    def get_stats(self) -> Dict[str, Any]:
        cp = sum(1 for p in self.profiles.values() if self.classify(p.system_name) == "CP")
        ap = sum(1 for p in self.profiles.values() if self.classify(p.system_name) == "AP")
        return {"total_profiles": len(self.profiles), "cp_systems": cp, "ap_systems": ap}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["CAPTheoremAnalyzer", "SystemProfile"]