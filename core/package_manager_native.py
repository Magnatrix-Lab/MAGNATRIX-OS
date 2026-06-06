#!/usr/bin/env python3
"""
Package Manager for MAGNATRIX-OS
pip/conda wrapper, dependency resolution, lock file generation,
and package audit. Native stdlib only (subprocess for pip).

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclasses.dataclass
class PackageInfo:
    name: str
    version: str
    latest: Optional[str] = None
    outdated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "latest": self.latest,
            "outdated": self.outdated,
        }


class PackageManager:
    """Manages Python package dependencies."""

    def __init__(self, requirements_file: str = "requirements.txt") -> None:
        self.requirements_file = Path(requirements_file)
        self._pip_available = self._check_pip()

    def _check_pip(self) -> bool:
        try:
            result = subprocess.run(["pip", "--version"], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def _pip_cmd(self, args: List[str]) -> subprocess.CompletedProcess:
        if not self._pip_available:
            raise RuntimeError("pip not available")
        return subprocess.run(["python", "-m", "pip"] + args, capture_output=True, text=True, timeout=60)

    def is_available(self) -> bool:
        return self._pip_available

    # ------------------------------------------------------------------
    # Package operations
    # ------------------------------------------------------------------

    def list_installed(self) -> List[PackageInfo]:
        result = self._pip_cmd(["list", "--format=json"])
        try:
            data = json.loads(result.stdout)
            return [PackageInfo(d["name"], d["version"]) for d in data]
        except Exception:
            return []

    def list_outdated(self) -> List[PackageInfo]:
        result = self._pip_cmd(["list", "--outdated", "--format=json"])
        try:
            data = json.loads(result.stdout)
            return [PackageInfo(d["name"], d["version"], d.get("latest_version"), True) for d in data]
        except Exception:
            return []

    def install(self, package: str, upgrade: bool = False) -> bool:
        args = ["install"]
        if upgrade:
            args.append("--upgrade")
        args.append(package)
        result = self._pip_cmd(args)
        return result.returncode == 0

    def uninstall(self, package: str) -> bool:
        result = self._pip_cmd(["uninstall", "-y", package])
        return result.returncode == 0

    def show(self, package: str) -> Dict[str, Any]:
        result = self._pip_cmd(["show", package])
        info = {}
        for line in result.stdout.strip().split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                info[key.strip()] = value.strip()
        return info

    # ------------------------------------------------------------------
    # Requirements / Lock file
    # ------------------------------------------------------------------

    def freeze(self, output_path: Optional[str] = None) -> str:
        result = self._pip_cmd(["freeze"])
        content = result.stdout
        if output_path:
            Path(output_path).write_text(content, encoding="utf-8")
        return content

    def generate_lock(self, output_path: str = "requirements.lock") -> str:
        return self.freeze(output_path)

    def install_requirements(self, path: Optional[str] = None) -> bool:
        req = path or str(self.requirements_file)
        if not Path(req).exists():
            return False
        result = self._pip_cmd(["install", "-r", req])
        return result.returncode == 0

    def audit(self) -> List[Dict[str, Any]]:
        """Check for known vulnerabilities (via pip-audit if available)."""
        try:
            result = subprocess.run(["pip-audit", "--format=json"], capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                return json.loads(result.stdout).get("vulnerabilities", [])
        except Exception:
            pass
        return []

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        installed = self.list_installed()
        outdated = self.list_outdated()
        return {
            "pip_available": self._pip_available,
            "installed_packages": len(installed),
            "outdated_packages": len(outdated),
            "requirements_file": str(self.requirements_file),
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    pm = PackageManager()
    print("=== Package Manager Demo ===\n")
    print(f"pip available: {pm.is_available()}")
    if pm.is_available():
        installed = pm.list_installed()
        print(f"Installed packages: {len(installed)}")
        if installed:
            print(f"  First 5: {[p.name for p in installed[:5]]}")
        show = pm.show("pip")
        print(f"\npip info: {show.get('Version', 'N/A')}")
    print(f"Stats: {pm.stats()}")


if __name__ == "__main__":
    _demo()
