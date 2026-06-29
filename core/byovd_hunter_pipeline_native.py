
"""
byovd_hunter_pipeline_native.py
MAGNATRIX-OS — BYOVD Hunter Pipeline

End-to-end BYOVD hunting pipeline combining import scanning,
IOCTL extraction, threat intel cross-reference, emulation, and
blocklist management. Inspired by DriverScope.

Pure Python standard library.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class BYOVDHuntResult:
    driver_name: str
    driver_path: str
    sha256: str
    threat_level: str
    findings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class BYOVDHunterPipeline:
    """End-to-end BYOVD hunting pipeline."""

    def __init__(self, output_dir: str = "./byovd_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results: List[BYOVDHuntResult] = []

    def hunt(self, driver_path: str) -> BYOVDHuntResult:
        """Run full BYOVD hunting pipeline on a driver."""
        driver_name = Path(driver_path).name
        findings = []
        recommendations = []
        threat_level = "LOW"

        # Step 1: Import scanning
        from .driver_import_scanner_native import DriverImportScanner
        import_scanner = DriverImportScanner()
        import_findings = import_scanner.scan_pe_imports(driver_path)
        for f in import_findings:
            if f.severity in ["HIGH", "CRITICAL"]:
                findings.append(f"[{f.severity}] Dangerous import: {f.dll_name}!{f.func_name} - {f.description}")
                if f.severity == "CRITICAL":
                    threat_level = "CRITICAL"
                elif threat_level != "CRITICAL":
                    threat_level = "HIGH"

        # Step 2: IOCTL extraction
        from .ioctl_dispatch_extractor_native import IOCTLDispatchExtractor
        ioctl_extractor = IOCTLDispatchExtractor()
        ioctl_handlers = ioctl_extractor.extract_from_binary(driver_path)
        if ioctl_handlers:
            surface = ioctl_extractor.get_attack_surface()
            findings.append(f"IOCTL surface: {surface['total_ioctl_codes']} codes, {surface.get('high_risk_methods', 0)} METHOD_NEITHER")
            if surface.get("high_risk_methods", 0) > 0:
                if threat_level == "LOW":
                    threat_level = "MEDIUM"

        # Step 3: Threat intel cross-reference
        from .byovd_threat_intel_native import BYOVDThreatIntel
        threat_intel = BYOVDThreatIntel()
        matches = threat_intel.cross_reference(driver_name)
        if matches:
            for m in matches:
                findings.append(f"[KNOWN BYOVD] Found in {m.database}: {m.description}")
            threat_level = "CRITICAL"
            recommendations.append("Immediately block this driver via WDAC or vulnerable driver blocklist")

        # Step 4: Driver emulation
        from .driver_emulation_engine_native import DriverEmulationEngine
        emulator = DriverEmulationEngine()
        emu_result = emulator.emulate_driver(driver_path)
        primitives = emulator.get_exploitable_primitives(driver_name)
        if primitives:
            for p in primitives:
                findings.append(f"[EMULATION] {p}")
            if threat_level == "LOW":
                threat_level = "MEDIUM"

        # Step 5: Blocklist check
        from .vulnerable_driver_blocklist_native import VulnerableDriverBlocklistManager
        blocklist = VulnerableDriverBlocklistManager()
        block_entry = blocklist.check_driver(driver_path)
        if block_entry:
            findings.append(f"[BLOCKLIST] Driver is already blocked: {block_entry.block_reason}")
            threat_level = "CRITICAL"
        else:
            recommendations.append("Consider adding to vulnerable driver blocklist if threat level is HIGH/CRITICAL")

        # Calculate hash
        from .byovd_threat_intel_native import BYOVDThreatIntel
        ti = BYOVDThreatIntel()
        sha256 = ti.calculate_hash(driver_path)

        result = BYOVDHuntResult(
            driver_name=driver_name, driver_path=driver_path,
            sha256=sha256, threat_level=threat_level,
            findings=findings, recommendations=recommendations,
        )
        self.results.append(result)
        self._save_report(result)
        return result

    def _save_report(self, result: BYOVDHuntResult) -> None:
        filename = f"byovd_{result.driver_name.replace('.', '_')}_{int(datetime.now().timestamp())}.json"
        path = self.output_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(result), f, indent=2)

    def batch_hunt(self, driver_paths: List[str]) -> List[BYOVDHuntResult]:
        return [self.hunt(p) for p in driver_paths]

    def get_summary(self) -> Dict[str, Any]:
        total = len(self.results)
        critical = sum(1 for r in self.results if r.threat_level == "CRITICAL")
        high = sum(1 for r in self.results if r.threat_level == "HIGH")
        medium = sum(1 for r in self.results if r.threat_level == "MEDIUM")
        return {
            "total_scanned": total,
            "critical": critical, "high": high, "medium": medium, "low": total - critical - high - medium,
            "total_findings": sum(len(r.findings) for r in self.results),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_summary()


__all__ = ["BYOVDHunterPipeline", "BYOVDHuntResult"]
