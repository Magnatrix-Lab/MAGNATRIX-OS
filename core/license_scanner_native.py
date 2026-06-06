#!/usr/bin/env python3
"""
License Scanner for MAGNATRIX-OS
Scans all source files for license headers and compliance.
Generates license reports and detects missing headers.
Native stdlib only.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclasses.dataclass
class LicenseReport:
    file_path: str
    has_license: bool
    license_type: Optional[str]
    line_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file_path,
            "has_license": self.has_license,
            "license": self.license_type,
            "lines": self.line_count,
        }


class LicenseScanner:
    """Scans repository for license compliance."""

    def __init__(self, repo_root: str) -> None:
        self.root = Path(repo_root).resolve()
        self._known_licenses = {
            "MIT": ["MIT License", "Permission is hereby granted"],
            "Apache": ["Apache License", "Licensed under the Apache License"],
            "GPL": ["GNU General Public License", "GPL"],
            "BSD": ["BSD License", "Redistribution and use"],
            "Proprietary": ["All rights reserved", "Confidential"],
        }

    def scan(self, extensions: Optional[Set[str]] = None) -> List[LicenseReport]:
        ext = extensions or {".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".go", ".rs", ".md"}
        reports = []
        for path in self.root.rglob("*"):
            if path.suffix not in ext:
                continue
            if any(part in {"__pycache__", ".git", "venv", "node_modules"} for part in path.parts):
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            has_license, license_type = self._detect_license(content)
            reports.append(LicenseReport(
                file_path=str(path.relative_to(self.root)),
                has_license=has_license,
                license_type=license_type,
                line_count=content.count("\n") + 1,
            ))
        return reports

    def _detect_license(self, content: str) -> Tuple[bool, Optional[str]]:
        header = content[:1000].lower()
        for license_name, markers in self._known_licenses.items():
            for marker in markers:
                if marker.lower() in header:
                    return True, license_name
        # Check for SPDX identifier
        if "spdx-license-identifier" in header:
            for line in content[:500].split("\n"):
                if "spdx-license-identifier" in line.lower():
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        return True, parts[1].strip()
        return False, None

    def generate_report(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        reports = self.scan()
        total = len(reports)
        licensed = sum(1 for r in reports if r.has_license)
        by_license = {}
        for r in reports:
            if r.license_type:
                by_license[r.license_type] = by_license.get(r.license_type, 0) + 1
        missing = [r.file_path for r in reports if not r.has_license]
        result = {
            "total_files": total,
            "licensed": licensed,
            "unlicensed": total - licensed,
            "coverage": round(licensed / max(1, total) * 100, 2),
            "by_license": by_license,
            "missing_files": missing[:50],
            "reports": [r.to_dict() for r in reports[:100]],
        }
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
        return result

    def stats(self) -> Dict[str, Any]:
        return {
            "repo_root": str(self.root),
            "known_licenses": len(self._known_licenses),
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="magnatrix_license_"))
    # Create test files
    (tmp / "mit_file.py").write_text("# MIT License\nprint(1)\n")
    (tmp / "apache_file.py").write_text("# Licensed under the Apache License\nprint(2)\n")
    (tmp / "no_license.py").write_text("print(3)\n")
    (tmp / "spdx.rs").write_text("// SPDX-License-Identifier: GPL-3.0\nfn main() {}\n")
    scanner = LicenseScanner(str(tmp))
    print("=== License Scanner Demo ===\n")
    reports = scanner.scan()
    for r in reports:
        print(f"  {r.file_path}: {'OK' if r.has_license else 'MISSING'} ({r.license_type})")
    report = scanner.generate_report()
    print(f"\nCoverage: {report['coverage']}%")
    print(f"By license: {report['by_license']}")
    # Cleanup
    import shutil
    shutil.rmtree(tmp)


if __name__ == "__main__":
    _demo()
