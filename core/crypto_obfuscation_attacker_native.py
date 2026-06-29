"""Crypto Obfuscation Attacker - Simulate attacks on obfuscation schemes."""
from __future__ import annotations
import json, hashlib, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class AttackResult:
    attack_id: str
    obf_id: str
    attack_type: str
    success: bool
    recovered_info: str
    effort: int  # computational effort

    def to_dict(self) -> Dict:
        return {"attack_id": self.attack_id, "obf_id": self.obf_id,
                "attack_type": self.attack_type, "success": self.success,
                "recovered_info": self.recovered_info, "effort": self.effort}

class CryptoObfuscationAttacker:
    """Simulate attacks on obfuscation: reverse engineering, side-channel, algebraic."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "crypto_obf_attack"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[AttackResult] = []
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for r in data.get("results",[]): self.results.append(AttackResult(**r))
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"results": [r.to_dict() for r in self.results]}, indent=2))

    def reverse_engineering(self, obf_id: str, encrypted_logic: str) -> AttackResult:
        effort = len(encrypted_logic) * 100
        success = len(encrypted_logic) < 64  # Only weak obfuscation can be reversed
        info = "partial_source" if success else "none"
        result = AttackResult(
            attack_id="atk_rev_" + obf_id + "_" + str(int(time.time())),
            obf_id=obf_id, attack_type="reverse_engineering", success=success,
            recovered_info=info, effort=effort)
        self.results.append(result)
        self._save_state()
        return result

    def side_channel(self, obf_id: str, timing_data: List[float]) -> AttackResult:
        effort = len(timing_data) * 10
        # If timing correlates with input, side-channel possible
        success = max(timing_data) - min(timing_data) > 100
        result = AttackResult(
            attack_id="atk_sc_" + obf_id + "_" + str(int(time.time())),
            obf_id=obf_id, attack_type="side_channel", success=success,
            recovered_info="branch_info" if success else "none", effort=effort)
        self.results.append(result)
        self._save_state()
        return result

    def algebraic_attack(self, obf_id: str, equations: List[str]) -> AttackResult:
        effort = len(equations) * 500
        success = len(equations) < 5  # Only small systems are solvable
        result = AttackResult(
            attack_id="atk_alg_" + obf_id + "_" + str(int(time.time())),
            obf_id=obf_id, attack_type="algebraic", success=success,
            recovered_info="circuit_structure" if success else "none", effort=effort)
        self.results.append(result)
        self._save_state()
        return result

    def get_stats(self) -> Dict:
        by_type = {}
        for r in self.results:
            by_type[r.attack_type] = by_type.get(r.attack_type, {"total":0,"success":0})
            by_type[r.attack_type]["total"] += 1
            if r.success: by_type[r.attack_type]["success"] += 1
        return {"attacks_total": len(self.results), "by_type": by_type}

    def to_dict(self) -> Dict:
        return {"results": [r.to_dict() for r in self.results], "stats": self.get_stats()}

__all__ = ["CryptoObfuscationAttacker", "AttackResult"]
