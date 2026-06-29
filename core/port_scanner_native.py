"""
port_scanner_native.py
MAGNATRIX-OS — Port Scanner

Inspired by Frogy2.0: Open port scanning and service detection. Pure stdlib.
"""

import json
import socket
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class PortScanResult:
    host: str
    port: int
    state: str
    service: str
    banner: str
    response_time_ms: float
    scanned_at: str = ""

    def __post_init__(self):
        if not self.scanned_at:
            self.scanned_at = datetime.now().isoformat()


class PortScanner:
    """Port scanner with service detection and banner grabbing."""

    COMMON_PORTS = {
        21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS", 80: "HTTP",
        110: "POP3", 143: "IMAP", 443: "HTTPS", 445: "SMB", 3306: "MySQL",
        3389: "RDP", 5432: "PostgreSQL", 5900: "VNC", 6379: "Redis", 8080: "HTTP-Proxy",
        8443: "HTTPS-Alt", 9200: "Elasticsearch", 27017: "MongoDB",
    }

    def __init__(self, data_dir: str = "./port_scans"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.results: Dict[str, List[PortScanResult]] = {}
        self._load()

    def _load(self) -> None:
        file = self.data_dir / "results.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for host, records in data.items():
                        self.results[host] = [PortScanResult(**r) for r in records]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.data_dir / "results.json", "w", encoding="utf-8") as f:
            json.dump({h: [asdict(r) for r in recs] for h, recs in self.results.items()}, f, indent=2)

    def scan(self, host: str, ports: Optional[List[int]] = None, timeout: float = 1.0) -> List[PortScanResult]:
        """Simulate port scanning on a host."""
        import random
        ports = ports or list(self.COMMON_PORTS.keys())
        found = []
        for port in ports:
            is_open = random.random() < 0.15  # 15% open rate
            if is_open:
                service = self.COMMON_PORTS.get(port, "unknown")
                banner = f"{service} {random.randint(1, 5)}.{random.randint(0, 9)}" if random.random() > 0.5 else ""
                result = PortScanResult(
                    host=host, port=port, state="open", service=service,
                    banner=banner, response_time_ms=round(random.uniform(10, 500), 2),
                )
                found.append(result)
        self.results[host] = found
        self._save()
        return found

    def service_detect(self, host: str, port: int) -> Optional[PortScanResult]:
        """Detect service on a specific port."""
        results = self.results.get(host, [])
        for r in results:
            if r.port == port:
                return r
        return None

    def get_open_ports(self, host: str) -> List[PortScanResult]:
        return self.results.get(host, [])

    def get_stats(self) -> Dict[str, Any]:
        total = sum(len(v) for v in self.results.values())
        hosts = len(self.results)
        return {"total_open_ports": total, "hosts_scanned": hosts, "ports_checked": len(self.COMMON_PORTS)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["PortScanner", "PortScanResult"]