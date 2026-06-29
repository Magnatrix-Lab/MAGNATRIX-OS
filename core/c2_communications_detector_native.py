
"""
c2_communications_detector_native.py
MAGNATRIX-OS — C2 Communications Detector

Detect C2 communication patterns including WinHTTP, Mythic framework
indicators, and polymorphic C2 beaconing.
Inspired by Proteus C2 agent for Mythic.

Pure Python standard library.
"""

import re
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
import urllib.request
import urllib.parse


class C2Protocol(Enum):
    HTTP = "http"
    HTTPS = "https"
    WINHTTP = "winhttp"
    WININET = "wininet"
    SOCKET = "socket"
    DNS = "dns"
    UNKNOWN = "unknown"


@dataclass
class C2Indicator:
    protocol: str
    indicator_type: str
    value: str
    confidence: float
    description: str


class C2CommunicationsDetector:
    """Detect C2 communication patterns in binaries and network traffic."""

    # Mythic framework indicators
    MYTHIC_INDICATORS = [
        b"/api/v1.4/agent_message",
        b"/api/v1.4/tasking",
        b"/api/v1.4/response",
        b"Mythic",
        b"mythic",
        b"agent_message",
        b"tasking",
        b"post_response",
        b"uuid",
    ]

    # WinHTTP API patterns
    WINHTTP_PATTERNS = [
        b"WinHttpOpen",
        b"WinHttpConnect",
        b"WinHttpOpenRequest",
        b"WinHttpSendRequest",
        b"WinHttpReceiveResponse",
        b"WinHttpReadData",
        b"WinHttpWriteData",
        b"WinHttpSetOption",
        b"WinHttpSetTimeouts",
    ]

    # WinInet API patterns
    WININET_PATTERNS = [
        b"InternetOpen",
        b"InternetConnect",
        b"HttpOpenRequest",
        b"HttpSendRequest",
        b"InternetReadFile",
        b"InternetWriteFile",
    ]

    # User-Agent patterns common in C2
    C2_USER_AGENTS = [
        b"Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        b"Mozilla/5.0 (compatible; Bot/",
        b"curl/",
        b"python-requests/",
    ]

    # URL patterns common in C2
    C2_URL_PATTERNS = [
        r"/api/v[0-9]+/",
        r"/agent/",
        r"/beacon",
        r"/checkin",
        r"/tasks",
        r"/results",
        r"/download",
        r"/upload",
    ]

    def __init__(self):
        self.indicators: List[C2Indicator] = []
        self.scanned_files: Set[str] = set()

    def scan_binary(self, filepath: str) -> List[C2Indicator]:
        """Scan a binary for C2 communication indicators."""
        indicators = []
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            text = data.decode("latin-1", errors="ignore")

            # Check for Mythic indicators
            for pattern in self.MYTHIC_INDICATORS:
                if pattern in data:
                    indicators.append(C2Indicator(
                        protocol=C2Protocol.HTTP.value,
                        indicator_type="mythic_framework",
                        value=pattern.decode("latin-1", errors="ignore"),
                        confidence=0.9,
                        description="Mythic C2 framework indicator found",
                    ))

            # Check for WinHTTP patterns
            for pattern in self.WINHTTP_PATTERNS:
                if pattern in data:
                    indicators.append(C2Indicator(
                        protocol=C2Protocol.WINHTTP.value,
                        indicator_type="winhttp_api",
                        value=pattern.decode("latin-1", errors="ignore"),
                        confidence=0.85,
                        description="WinHTTP API reference - C2 communication primitive",
                    ))

            # Check for WinInet patterns
            for pattern in self.WININET_PATTERNS:
                if pattern in data:
                    indicators.append(C2Indicator(
                        protocol=C2Protocol.WININET.value,
                        indicator_type="wininet_api",
                        value=pattern.decode("latin-1", errors="ignore"),
                        confidence=0.8,
                        description="WinInet API reference - C2 communication primitive",
                    ))

            # Check for C2 URL patterns
            for pattern in self.C2_URL_PATTERNS:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches[:3]:
                    indicators.append(C2Indicator(
                        protocol=C2Protocol.HTTP.value,
                        indicator_type="c2_url_pattern",
                        value=match,
                        confidence=0.75,
                        description="C2 URL pattern detected",
                    ))

            # Check for suspicious User-Agent patterns
            for pattern in self.C2_USER_AGENTS:
                if pattern in data:
                    indicators.append(C2Indicator(
                        protocol=C2Protocol.HTTP.value,
                        indicator_type="user_agent",
                        value=pattern.decode("latin-1", errors="ignore"),
                        confidence=0.6,
                        description="HTTP User-Agent string found",
                    ))

            # Check for hardcoded IP addresses / domains
            ip_pattern = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
            ip_matches = re.findall(ip_pattern, text)
            for ip in ip_matches[:5]:
                if not ip.startswith(("127.", "0.", "255.", "10.", "192.168.", "172.16.")):
                    indicators.append(C2Indicator(
                        protocol=C2Protocol.UNKNOWN.value,
                        indicator_type="external_ip",
                        value=ip,
                        confidence=0.7,
                        description="Hardcoded external IP address",
                    ))

        except Exception:
            pass

        self.indicators.extend(indicators)
        self.scanned_files.add(filepath)
        return indicators

    def analyze_network_traffic(self, urls: List[str]) -> List[C2Indicator]:
        """Analyze network traffic for C2 indicators."""
        indicators = []
        for url in urls:
            parsed = urllib.parse.urlparse(url)
            path = parsed.path.lower()
            # Check for C2 URL patterns
            for pattern in self.C2_URL_PATTERNS:
                if re.search(pattern, path):
                    indicators.append(C2Indicator(
                        protocol=parsed.scheme,
                        indicator_type="network_c2_url",
                        value=url,
                        confidence=0.8,
                        description="Network traffic matches C2 URL pattern",
                    ))
            # Check for Mythic API endpoints
            if "/api/v" in path and ("agent" in path or "task" in path):
                indicators.append(C2Indicator(
                    protocol=parsed.scheme,
                    indicator_type="network_mythic_api",
                    value=url,
                    confidence=0.85,
                    description="Network traffic matches Mythic API endpoint",
                ))
        return indicators

    def get_c2_score(self, indicators: Optional[List[C2Indicator]] = None) -> float:
        """Calculate C2 likelihood score (0.0-1.0)."""
        if indicators is None:
            indicators = self.indicators
        if not indicators:
            return 0.0
        score = 0.0
        for ind in indicators:
            if ind.indicator_type == "mythic_framework":
                score += 0.3
            elif ind.indicator_type == "winhttp_api":
                score += 0.2
            elif ind.indicator_type == "c2_url_pattern":
                score += 0.15
            elif ind.indicator_type == "network_mythic_api":
                score += 0.25
            elif ind.indicator_type == "external_ip":
                score += 0.1
        return min(1.0, score)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_indicators": len(self.indicators),
            "files_scanned": len(self.scanned_files),
            "c2_score": self.get_c2_score(),
            "protocols": list(set(i.protocol for i in self.indicators)),
            "indicator_types": list(set(i.indicator_type for i in self.indicators)),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["C2CommunicationsDetector", "C2Indicator", "C2Protocol"]
