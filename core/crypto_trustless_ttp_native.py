"""Crypto Trustless TTP - Trustless trusted third party simulation using iO."""
from __future__ import annotations
import json, hashlib, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class ProtocolInstance:
    instance_id: str
    protocol_name: str
    participants: List[str]
    obfuscated_logic_id: str
    state: str = "pending"  # pending, active, completed
    result: str = ""

    def to_dict(self) -> Dict:
        return {"instance_id": self.instance_id, "protocol_name": self.protocol_name,
                "participants": self.participants, "obfuscated_logic_id": self.obfuscated_logic_id,
                "state": self.state, "result": self.result}

class CryptoTrustlessTTP:
    """Simulate trustless trusted third party using iO obfuscation."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "crypto_ttp"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.instances: Dict[str, ProtocolInstance] = {}
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for i in data.get("instances",[]): self.instances[i["instance_id"]] = ProtocolInstance(**i)
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"instances": [i.to_dict() for i in self.instances.values()]}, indent=2))

    def deploy_protocol(self, protocol_name: str, participants: List[str], obfuscated_logic_id: str) -> ProtocolInstance:
        instance = ProtocolInstance(
            instance_id="ttp_" + protocol_name + "_" + str(int(time.time())),
            protocol_name=protocol_name, participants=participants,
            obfuscated_logic_id=obfuscated_logic_id, state="active")
        self.instances[instance.instance_id] = instance
        self._save_state()
        return instance

    def execute(self, instance_id: str, inputs: Dict) -> Dict:
        """Execute protocol on inputs without revealing internal logic."""
        inst = self.instances.get(instance_id)
        if not inst: return {"error": "Instance not found"}
        h = hashlib.sha256((inst.obfuscated_logic_id + str(inputs)).encode()).hexdigest()
        result = "result_" + h[:16]
        inst.result = result
        inst.state = "completed"
        self._save_state()
        return {"instance_id": instance_id, "result": result, "participants": inst.participants}

    def get_capabilities(self) -> Dict:
        return {"encryption": True, "zero_knowledge": True, "multiparty": True,
                "stateful": False, "copiable": True, "blockchain_needed": False}

    def get_stats(self) -> Dict:
        active = sum(1 for i in self.instances.values() if i.state == "active")
        completed = sum(1 for i in self.instances.values() if i.state == "completed")
        return {"instances_total": len(self.instances), "active": active, "completed": completed}

    def to_dict(self) -> Dict:
        return {"instances": [i.to_dict() for i in self.instances.values()], "stats": self.get_stats()}

__all__ = ["CryptoTrustlessTTP", "ProtocolInstance"]
