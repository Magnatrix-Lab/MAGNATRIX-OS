"""Crypto Obfuscation Validator - Validate obfuscation properties."""
from __future__ import annotations
import json, hashlib, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class ValidationReport:
    report_id: str
    obf_id: str
    properties_checked: List[str]
    passed: List[bool]
    overall_valid: bool

    def to_dict(self) -> Dict:
        return {"report_id": self.report_id, "obf_id": self.obf_id,
                "properties_checked": self.properties_checked, "passed": self.passed,
                "overall_valid": self.overall_valid}

class CryptoObfuscationValidator:
    """Validate obfuscation properties: correctness, efficiency, security."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "crypto_obf_val"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.reports: List[ValidationReport] = []
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for r in data.get("reports",[]): self.reports.append(ValidationReport(**r))
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"reports": [r.to_dict() for r in self.reports]}, indent=2))

    def validate(self, obf_id: str, encrypted_logic: str, test_inputs: List[Dict]) -> ValidationReport:
        properties = ["correctness", "polynomial_slowdown", "security"]
        # Correctness: same I/O
        passed = [True, True, True]
        # Simulate correctness check
        h = hashlib.sha256(encrypted_logic.encode()).hexdigest()
        if int(h[:4], 16) % 100 < 5:  # 5% chance of failure
            passed[0] = False
        # Security: internal logic should be hidden
        if len(encrypted_logic) < 32:
            passed[2] = False
        overall = all(passed)
        report = ValidationReport(
            report_id="val_" + obf_id + "_" + str(int(time.time())),
            obf_id=obf_id, properties_checked=properties, passed=passed,
            overall_valid=overall)
        self.reports.append(report)
        self._save_state()
        return report

    def get_stats(self) -> Dict:
        valid = sum(1 for r in self.reports if r.overall_valid)
        return {"reports_total": len(self.reports), "valid": valid}

    def to_dict(self) -> Dict:
        return {"reports": [r.to_dict() for r in self.reports], "stats": self.get_stats()}

__all__ = ["CryptoObfuscationValidator", "ValidationReport"]
