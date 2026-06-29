"""
target_reconnaissance_native.py
MAGNATRIX-OS — Target Reconnaissance

Identify target software versions and configurations. Pure stdlib.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class ReconResult:
    result_id: str
    target: str
    open_ports: List[int]
    services: Dict[str, str]
    software_versions: Dict[str, str]
    os_guess: str
    confidence: float


class TargetReconnaissance:
    """Identify target software versions and configurations."""

    def __init__(self, cache_dir: str = "./recon_results"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.results: Dict[str, ReconResult] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "results.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for rid, rd in data.items():
                        self.results[rid] = ReconResult(**rd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "results.json", "w", encoding="utf-8") as f:
            json.dump({rid: asdict(r) for rid, r in self.results.items()}, f, indent=2)

    def recon(self, result_id: str, target: str, banners: List[str]) -> ReconResult:
        """Reconnaissance from collected banners."""
        services = {}
        versions = {}
        ports = []
        os_guess = "unknown"
        confidence = 0.0

        for banner in banners:
            # Port extraction
            port_match = re.search(r":(\d+)", banner)
            if port_match:
                ports.append(int(port_match.group(1)))

            # Service detection
            for service, pattern in {
                "ssh": r"SSH", "http": r"HTTP", "ftp": r"FTP", "smtp": r"SMTP",
                "docker": r"Docker", "nginx": r"nginx", "apache": r"Apache",
            }.items():
                if re.search(pattern, banner, re.IGNORECASE):
                    services[service] = banner[:100]

            # Version extraction
            ver_match = re.search(r"(\d+\.\d+(?:\.\d+)?)", banner)
            if ver_match:
                for svc in services:
                    versions[svc] = ver_match.group(1)

            # OS detection
            if "Windows" in banner:
                os_guess = "Windows"
                confidence = 0.8
            elif "Linux" in banner:
                os_guess = "Linux"
                confidence = 0.8

        result = ReconResult(
            result_id=result_id, target=target, open_ports=list(set(ports)),
            services=services, software_versions=versions, os_guess=os_guess,
            confidence=confidence,
        )
        self.results[result_id] = result
        self._save()
        return result

    def get_result(self, result_id: str) -> Optional[ReconResult]:
        return self.results.get(result_id)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.results)
        avg_ports = sum(len(r.open_ports) for r in self.results.values()) / max(1, total)
        return {"total_targets": total, "avg_ports": round(avg_ports, 2)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["TargetReconnaissance", "ReconResult"]