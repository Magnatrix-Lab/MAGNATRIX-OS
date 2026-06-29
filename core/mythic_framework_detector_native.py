
"""
mythic_framework_detector_native.py
MAGNATRIX-OS — Mythic Framework Detector

Detect artifacts and indicators of the Mythic C2 framework
and its agents (including Proteus, Apollo, Poseidon, etc.).

Pure Python standard library.
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MythicIndicator:
    agent_type: str
    indicator_type: str
    value: str
    confidence: float
    description: str


class MythicFrameworkDetector:
    """Detect Mythic C2 framework and agent indicators."""

    # Known Mythic agent types and their signatures
    MYTHIC_AGENTS = {
        "proteus": {
            "strings": ["proteus", "proteus-agent", "prx_obf", "Proteus.bin"],
            "apis": ["WinHttpOpen", "WinHttpConnect", "WinHttpSendRequest"],
            "patterns": ["_start", "Instance", "initialize", "no_std"],
        },
        "apollo": {
            "strings": ["apollo", "Apollo"],
            "apis": ["CreateRemoteThread", "VirtualAllocEx", "WriteProcessMemory"],
            "patterns": ["rpc", "mythic"],
        },
        "poseidon": {
            "strings": ["poseidon", "Poseidon"],
            "apis": ["http", "websocket"],
            "patterns": ["callback", "tasking"],
        },
        "athena": {
            "strings": ["athena", "Athena"],
            "apis": ["grpc", "http"],
            "patterns": ["mythic"],
        },
        "hermes": {
            "strings": ["hermes", "Hermes"],
            "apis": ["http", "tcp"],
            "patterns": ["callback"],
        },
    }

    # Mythic server-side indicators
    MYTHIC_SERVER_INDICATORS = [
        r"/api/v[0-9.]+/agent_message",
        r"/api/v[0-9.]+/tasking",
        r"/api/v[0-9.]+/response",
        r"/api/v[0-9.]+/files/download",
        r"/api/v[0-9.]+/files/upload",
        r"/api/v[0-9.]+/crypto",
        r"/api/v[0-9.]+/payload_types",
        r"/api/v[0-9.]+/callbacks",
        r"/api/v[0-9.]+/operators",
        r"/new/websocket",
        r"/mythic/",
    ]

    # Mythic Payload Type indicators
    PAYLOAD_TYPE_INDICATORS = [
        b"PayloadType",
        b"mythic_container",
        b"MythicContainer",
        b"agent_functions",
        b"CommandBase",
        b"builder.py",
        b"PayloadType_",
    ]

    def __init__(self):
        self.indicators: List[MythicIndicator] = []
        self.scanned_files: Set[str] = set()

    def scan_binary(self, filepath: str) -> List[MythicIndicator]:
        """Scan a binary for Mythic agent indicators."""
        indicators = []
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            text = data.decode("latin-1", errors="ignore")
            text_lower = text.lower()

            for agent_name, signatures in self.MYTHIC_AGENTS.items():
                score = 0.0
                matched = []
                # Check strings
                for s in signatures["strings"]:
                    if s.lower() in text_lower:
                        score += 0.3
                        matched.append(f"string:{s}")
                # Check APIs
                for api in signatures["apis"]:
                    if api.encode() in data:
                        score += 0.2
                        matched.append(f"api:{api}")
                # Check patterns
                for pat in signatures["patterns"]:
                    if pat.lower() in text_lower:
                        score += 0.15
                        matched.append(f"pattern:{pat}")

                if score >= 0.5:
                    indicators.append(MythicIndicator(
                        agent_type=agent_name,
                        indicator_type="binary_signature",
                        value="; ".join(matched[:5]),
                        confidence=min(1.0, score),
                        description=f"Mythic {agent_name} agent indicators detected",
                    ))

            # Check for Payload Type indicators
            for pat in self.PAYLOAD_TYPE_INDICATORS:
                if pat in data:
                    indicators.append(MythicIndicator(
                        agent_type="unknown",
                        indicator_type="payload_type",
                        value=pat.decode("latin-1", errors="ignore"),
                        confidence=0.8,
                        description="Mythic Payload Type indicator found",
                    ))

        except Exception:
            pass

        self.indicators.extend(indicators)
        self.scanned_files.add(filepath)
        return indicators

    def scan_network_url(self, url: str) -> List[MythicIndicator]:
        """Scan a URL for Mythic server indicators."""
        indicators = []
        for pattern in self.MYTHIC_SERVER_INDICATORS:
            if re.search(pattern, url, re.IGNORECASE):
                indicators.append(MythicIndicator(
                    agent_type="server",
                    indicator_type="mythic_api_endpoint",
                    value=url,
                    confidence=0.9,
                    description=f"Mythic API endpoint pattern matched: {pattern}",
                ))
        return indicators

    def scan_directory(self, directory: str) -> List[MythicIndicator]:
        """Scan a directory for Mythic Payload Type files."""
        indicators = []
        path = Path(directory)
        mythic_files = [
            "config.json", "Payload_Type", "agent_functions", "mythic",
            "builder.py", "__init__.py", "Dockerfile", "requirements.txt",
        ]
        for file_path in path.rglob("*"):
            if file_path.is_file():
                for mf in mythic_files:
                    if mf in str(file_path):
                        try:
                            content = file_path.read_text(errors="ignore")
                            if "mythic" in content.lower() or "PayloadType" in content:
                                indicators.append(MythicIndicator(
                                    agent_type="payload_dev",
                                    indicator_type="mythic_source_file",
                                    value=str(file_path),
                                    confidence=0.85,
                                    description="Mythic Payload Type development file detected",
                                ))
                        except Exception:
                            pass
        self.indicators.extend(indicators)
        return indicators

    def get_agent_breakdown(self) -> Dict[str, int]:
        """Get count of indicators by agent type."""
        counts = {}
        for ind in self.indicators:
            counts[ind.agent_type] = counts.get(ind.agent_type, 0) + 1
        return counts

    def get_confidence_score(self) -> float:
        """Get overall confidence that Mythic is present."""
        if not self.indicators:
            return 0.0
        max_conf = max(ind.confidence for ind in self.indicators)
        count_bonus = min(0.3, len(self.indicators) * 0.05)
        return min(1.0, max_conf + count_bonus)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_indicators": len(self.indicators),
            "files_scanned": len(self.scanned_files),
            "confidence_score": self.get_confidence_score(),
            "agent_breakdown": self.get_agent_breakdown(),
            "indicator_types": list(set(i.indicator_type for i in self.indicators)),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["MythicFrameworkDetector", "MythicIndicator"]
