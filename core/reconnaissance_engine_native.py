"""
reconnaissance_engine_native.py
MAGNATRIX-OS — Reconnaissance Engine

Inspired by AbyssSec offensive security research:
Network and web reconnaissance with service fingerprinting and asset discovery. Pure stdlib.
"""

import json
import socket
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class ReconTarget:
    target_id: str
    host: str
    ports: List[int] = field(default_factory=list)
    services: Dict[int, str] = field(default_factory=dict)
    banners: Dict[int, str] = field(default_factory=dict)
    web_assets: List[str] = field(default_factory=list)
    discovered_at: str = ""

    def __post_init__(self):
        if not self.discovered_at:
            self.discovered_at = datetime.now().isoformat()


class ReconnaissanceEngine:
    """Network and web reconnaissance with service fingerprinting."""

    COMMON_PORTS = [21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995, 1723, 3306, 3389, 5432, 5900, 8080, 8443, 9200, 27017]

    SERVICE_SIGNATURES = {
        21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS", 80: "HTTP",
        110: "POP3", 111: "RPC", 135: "MSRPC", 139: "NetBIOS", 143: "IMAP",
        443: "HTTPS", 445: "SMB", 993: "IMAPS", 995: "POP3S", 1723: "PPTP",
        3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL", 5900: "VNC", 8080: "HTTP-Proxy", 8443: "HTTPS-Alt", 9200: "Elasticsearch", 27017: "MongoDB",
    }

    def __init__(self, recon_dir: str = "./recon"):
        self.recon_dir = Path(recon_dir)
        self.recon_dir.mkdir(exist_ok=True)
        self.targets: Dict[str, ReconTarget] = {}
        self._load()

    def _load(self) -> None:
        file = self.recon_dir / "targets.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for tid, td in data.items():
                        self.targets[tid] = ReconTarget(**td)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.recon_dir / "targets.json", "w", encoding="utf-8") as f:
            json.dump({tid: asdict(t) for tid, t in self.targets.items()}, f, indent=2)

    def add_target(self, target_id: str, host: str) -> ReconTarget:
        target = ReconTarget(target_id=target_id, host=host)
        self.targets[target_id] = target
        self._save()
        return target

    def scan_ports(self, target_id: str, ports: Optional[List[int]] = None, timeout: float = 0.5) -> ReconTarget:
        target = self.targets.get(target_id)
        if not target:
            return None
        scan_ports = ports or self.COMMON_PORTS
        open_ports = []
        for port in scan_ports:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(timeout)
                    result = s.connect_ex((target.host, port))
                    if result == 0:
                        open_ports.append(port)
                        target.services[port] = self.SERVICE_SIGNATURES.get(port, "Unknown")
                        try:
                            banner = s.recv(1024).decode('utf-8', errors='ignore').strip()
                            if banner:
                                target.banners[port] = banner[:200]
                        except:
                            pass
            except Exception:
                pass
        target.ports = open_ports
        self._save()
        return target

    def enumerate_web(self, target_id: str, paths: Optional[List[str]] = None) -> ReconTarget:
        target = self.targets.get(target_id)
        if not target:
            return None
        common_paths = paths or ["/", "/admin", "/api", "/login", "/robots.txt", "/.env", "/config", "/wp-admin", "/phpmyadmin"]
        found = []
        for path in common_paths:
            found.append(f"http://{target.host}{path}")
        target.web_assets = found
        self._save()
        return target

    def get_target(self, target_id: str) -> Optional[ReconTarget]:
        return self.targets.get(target_id)

    def list_targets(self) -> List[ReconTarget]:
        return list(self.targets.values())

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.targets)
        total_ports = sum(len(t.ports) for t in self.targets.values())
        return {"targets": total, "open_ports_found": total_ports}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["ReconnaissanceEngine", "ReconTarget"]