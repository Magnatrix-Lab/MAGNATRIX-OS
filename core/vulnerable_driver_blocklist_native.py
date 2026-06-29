
"""
vulnerable_driver_blocklist_native.py
MAGNATRIX-OS — Vulnerable Driver Blocklist Manager

Manage and apply Windows vulnerable driver blocklists (WDAC, HVCI).
Block BYOVD drivers before they load.
Inspired by DriverScope.

Pure Python standard library.
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class BlocklistEntry:
    driver_name: str
    sha256_hash: str
    sha1_hash: str
    block_reason: str
    source: str
    added_date: str
    severity: str


class VulnerableDriverBlocklistManager:
    """Manage Windows vulnerable driver blocklists."""

    def __init__(self, blocklist_file: str = "./vulnerable_driver_blocklist.json"):
        self.blocklist_file = Path(blocklist_file)
        self.blocklist: Dict[str, BlocklistEntry] = {}
        self._load()

    def _load(self) -> None:
        if self.blocklist_file.exists():
            try:
                with open(self.blocklist_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for entry in data:
                        self.blocklist[entry["sha256_hash"]] = BlocklistEntry(**entry)
            except Exception:
                pass

    def _save(self) -> None:
        self.blocklist_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.blocklist_file, "w", encoding="utf-8") as f:
            json.dump([asdict(entry) for entry in self.blocklist.values()], f, indent=2)

    def add_entry(self, driver_name: str, filepath: str, block_reason: str,
                  source: str = "manual", severity: str = "HIGH") -> BlocklistEntry:
        """Add a driver to the blocklist."""
        sha256 = self._calculate_sha256(filepath)
        sha1 = self._calculate_sha1(filepath)
        entry = BlocklistEntry(
            driver_name=driver_name, sha256_hash=sha256, sha1_hash=sha1,
            block_reason=block_reason, source=source,
            added_date=datetime.now().isoformat(), severity=severity,
        )
        self.blocklist[sha256] = entry
        self._save()
        return entry

    def _calculate_sha256(self, filepath: str) -> str:
        try:
            h = hashlib.sha256()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return ""

    def _calculate_sha1(self, filepath: str) -> str:
        try:
            h = hashlib.sha1()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return ""

    def check_driver(self, filepath: str) -> Optional[BlocklistEntry]:
        """Check if a driver is on the blocklist."""
        sha256 = self._calculate_sha256(filepath)
        return self.blocklist.get(sha256)

    def check_by_hash(self, sha256_hash: str) -> Optional[BlocklistEntry]:
        return self.blocklist.get(sha256_hash)

    def remove_entry(self, sha256_hash: str) -> bool:
        if sha256_hash in self.blocklist:
            del self.blocklist[sha256_hash]
            self._save()
            return True
        return False

    def generate_wdac_policy(self) -> str:
        """Generate WDAC (Windows Defender Application Control) policy snippet."""
        lines = ['<SiPolicy xmlns="urn:schemas-microsoft-com:sipolicy">', '  <Rules>']
        for entry in self.blocklist.values():
            lines.append(f'    <FileRule Type="Deny" ID="ID_DENY_{entry.sha256_hash[:16]}" ')
            lines.append(f'             FriendlyName="{entry.driver_name}" ')
            lines.append(f'             Hash="{entry.sha256_hash}" />')
        lines.append('  </Rules>')
        lines.append('</SiPolicy>')
        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        severity_counts = {}
        for entry in self.blocklist.values():
            severity_counts[entry.severity] = severity_counts.get(entry.severity, 0) + 1
        return {
            "total_entries": len(self.blocklist),
            "severity_breakdown": severity_counts,
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["VulnerableDriverBlocklistManager", "BlocklistEntry"]
