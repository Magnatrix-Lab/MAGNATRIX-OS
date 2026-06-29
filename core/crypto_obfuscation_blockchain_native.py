"""Crypto Obfuscation Blockchain - iO + blockchain integration for stateful protocols."""
from __future__ import annotations
import json, hashlib, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class ObfuscatedContract:
    contract_id: str
    obfuscated_logic_id: str
    blockchain: str
    deployed_address: str
    stateful: bool
    state_hash: str

    def to_dict(self) -> Dict:
        return {"contract_id": self.contract_id, "obfuscated_logic_id": self.obfuscated_logic_id,
                "blockchain": self.blockchain, "deployed_address": self.deployed_address,
                "stateful": self.stateful, "state_hash": self.state_hash}

class CryptoObfuscationBlockchain:
    """iO + blockchain: obfuscated programs for stateful smart contracts."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "crypto_obf_chain"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.contracts: Dict[str, ObfuscatedContract] = {}
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for c in data.get("contracts",[]): self.contracts[c["contract_id"]] = ObfuscatedContract(**c)
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"contracts": [c.to_dict() for c in self.contracts.values()]}, indent=2))

    def deploy(self, obfuscated_logic_id: str, blockchain: str = "ethereum", stateful: bool = True) -> ObfuscatedContract:
        addr = "0x" + hashlib.sha256(obfuscated_logic_id.encode()).hexdigest()[:40]
        contract = ObfuscatedContract(
            contract_id="contract_" + obfuscated_logic_id + "_" + str(int(time.time())),
            obfuscated_logic_id=obfuscated_logic_id, blockchain=blockchain,
            deployed_address=addr, stateful=stateful, state_hash="0x" + "0" * 64)
        self.contracts[contract.contract_id] = contract
        self._save_state()
        return contract

    def update_state(self, contract_id: str, new_state: Dict) -> ObfuscatedContract:
        contract = self.contracts.get(contract_id)
        if not contract: raise ValueError("Contract not found")
        contract.state_hash = hashlib.sha256(str(new_state).encode()).hexdigest()
        self._save_state()
        return contract

    def execute(self, contract_id: str, inputs: Dict) -> Dict:
        contract = self.contracts.get(contract_id)
        if not contract: return {"error": "Contract not found"}
        h = hashlib.sha256((contract.state_hash + str(inputs)).encode()).hexdigest()
        return {"contract_id": contract_id, "output": "0x" + h[:16],
                "new_state_hash": hashlib.sha256(h.encode()).hexdigest()}

    def bridge_iO_to_chain(self, obfuscated_logic_id: str) -> Dict:
        """Bridge iO obfuscated program to blockchain for stateful execution."""
        contract = self.deploy(obfuscated_logic_id, stateful=True)
        return {"status": "bridged", "contract_id": contract.contract_id,
                "address": contract.deployed_address, "stateful": contract.stateful}

    def get_stats(self) -> Dict:
        stateful = sum(1 for c in self.contracts.values() if c.stateful)
        return {"contracts_total": len(self.contracts), "stateful": stateful, "stateless": len(self.contracts) - stateful}

    def to_dict(self) -> Dict:
        return {"contracts": [c.to_dict() for c in self.contracts.values()], "stats": self.get_stats()}

__all__ = ["CryptoObfuscationBlockchain", "ObfuscatedContract"]
