
"""
byovd_threat_intel_native.py
MAGNATRIX-OS — BYOVD Threat Intel Cross-Reference

Cross-reference driver hashes/names against known BYOVD databases:
LOLDrivers, Microsoft Vulnerable Driver Blocklist, KDU (Kernel Driver Utility).
Inspired by DriverScope.

Pure Python standard library.
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ThreatIntelMatch:
    database: str
    driver_name: str
    driver_hash: str
    threat_category: str
    description: str
    mitigation: str
    first_seen: str
    severity: str


class BYOVDThreatIntel:
    """Cross-reference drivers against known BYOVD threat databases."""

    # Known BYOVD driver signatures (simplified - in production would load from DB)
    KNOWN_BYOVD_DRIVERS: Dict[str, Dict[str, Any]] = {
        "dbutil_2_3.sys": {
            "database": "LOLDrivers",
            "category": "Dell BIOS Driver",
            "description": "Dell BIOS utility driver with arbitrary read/write primitives",
            "mitigation": "Block via WDAC or vulnerable driver blocklist",
            "severity": "CRITICAL",
        },
        "gdrv.sys": {
            "database": "LOLDrivers",
            "category": "Gigabyte Driver",
            "description": "Gigabyte driver with physical memory read/write",
            "mitigation": "Block via WDAC or vulnerable driver blocklist",
            "severity": "CRITICAL",
        },
        "rtcore64.sys": {
            "database": "LOLDrivers",
            "category": "Micro-Star Driver",
            "description": "MSI Afterburner driver with kernel memory access",
            "mitigation": "Block via WDAC or vulnerable driver blocklist",
            "severity": "CRITICAL",
        },
        "aswarpot.sys": {
            "database": "MS Blocklist",
            "category": "ASUS Driver",
            "description": "ASUS driver with arbitrary kernel memory access",
            "mitigation": "Block via vulnerable driver blocklist",
            "severity": "CRITICAL",
        },
        "ene.sys": {
            "database": "LOLDrivers",
            "category": "Energy Driver",
            "description": "Driver with kernel read/write primitives",
            "mitigation": "Block via WDAC or vulnerable driver blocklist",
            "severity": "CRITICAL",
        },
        "atszio.sys": {
            "database": "KDU",
            "category": "ASUS Driver",
            "description": "ASUS ATKEX driver used in KDU toolkit",
            "mitigation": "Block via WDAC or vulnerable driver blocklist",
            "severity": "CRITICAL",
        },
        "phymem64.sys": {
            "database": "KDU",
            "category": "Physical Memory Driver",
            "description": "Direct physical memory access driver",
            "mitigation": "Block via WDAC or vulnerable driver blocklist",
            "severity": "CRITICAL",
        },
    }

    def __init__(self, database_dir: str = "./byovd_db"):
        self.database_dir = Path(database_dir)
        self.database_dir.mkdir(exist_ok=True)
        self.matches: List[ThreatIntelMatch] = []
        self._load_databases()

    def _load_databases(self) -> None:
        """Load threat intelligence databases from local files."""
        # Load LOLDrivers database
        loldrivers_file = self.database_dir / "loldrivers.json"
        if loldrivers_file.exists():
            try:
                with open(loldrivers_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for entry in data:
                        name = entry.get("driver_name", "").lower()
                        if name:
                            self.KNOWN_BYOVD_DRIVERS[name] = {
                                "database": "LOLDrivers",
                                "category": entry.get("category", "Unknown"),
                                "description": entry.get("description", ""),
                                "mitigation": entry.get("mitigation", "Block driver"),
                                "severity": entry.get("severity", "HIGH"),
                            }
            except Exception:
                pass

    def cross_reference(self, driver_name: str, driver_hash: Optional[str] = None) -> List[ThreatIntelMatch]:
        """Cross-reference a driver against known BYOVD databases."""
        matches = []
        name_lower = driver_name.lower()
        for known_name, info in self.KNOWN_BYOVD_DRIVERS.items():
            if known_name in name_lower or name_lower in known_name:
                matches.append(ThreatIntelMatch(
                    database=info["database"],
                    driver_name=driver_name,
                    driver_hash=driver_hash or "unknown",
                    threat_category=info["category"],
                    description=info["description"],
                    mitigation=info["mitigation"],
                    first_seen=datetime.now().isoformat(),
                    severity=info["severity"],
                ))
        self.matches.extend(matches)
        return matches

    def calculate_hash(self, filepath: str) -> str:
        """Calculate SHA256 hash of a driver file."""
        try:
            sha256 = hashlib.sha256()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception:
            return ""

    def is_known_byovd(self, driver_name: str) -> bool:
        """Quick check if driver is known BYOVD."""
        name_lower = driver_name.lower()
        return any(known in name_lower or name_lower in known for known in self.KNOWN_BYOVD_DRIVERS.keys())

    def get_novel_candidates(self, drivers: List[str]) -> List[str]:
        """Identify drivers not in any known database (potential zero-days)."""
        novel = []
        for driver in drivers:
            if not self.is_known_byovd(driver):
                novel.append(driver)
        return novel

    def get_stats(self) -> Dict[str, Any]:
        db_counts = {}
        for m in self.matches:
            db_counts[m.database] = db_counts.get(m.database, 0) + 1
        return {
            "total_matches": len(self.matches),
            "database_breakdown": db_counts,
            "known_signatures": len(self.KNOWN_BYOVD_DRIVERS),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["BYOVDThreatIntel", "ThreatIntelMatch"]
