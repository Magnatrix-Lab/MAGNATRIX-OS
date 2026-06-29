"""Sandbox Network Restrictor — DNS block, IP filter."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class NetworkRule:
    rule_id: str = ""
    type: str = ""  # allow | block
    target: str = ""  # ip | domain | port
    value: str = ""

class SandboxNetworkRestrictor:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._rules: list[NetworkRule] = []
        self._default_policy: str = "block"
        self._log: list[dict] = []
        self._persist_path = self.root / "sandbox_network.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._rules = [NetworkRule(**r) for r in data.get("rules", [])]
            self._default_policy = data.get("default_policy", "block")
            self._log = data.get("log", [])

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "rules": [r.__dict__ for r in self._rules],
            "default_policy": self._default_policy,
            "log": self._log
        }, indent=2))

    def allow_domain(self, domain: str) -> None:
        self._rules.append(NetworkRule(rule_id=f"allow_domain_{domain}", type="allow", target="domain", value=domain))
        self._save()

    def block_domain(self, domain: str) -> None:
        self._rules.append(NetworkRule(rule_id=f"block_domain_{domain}", type="block", target="domain", value=domain))
        self._save()

    def allow_ip(self, ip: str) -> None:
        self._rules.append(NetworkRule(rule_id=f"allow_ip_{ip}", type="allow", target="ip", value=ip))
        self._save()

    def block_ip(self, ip: str) -> None:
        self._rules.append(NetworkRule(rule_id=f"block_ip_{ip}", type="block", target="ip", value=ip))
        self._save()

    def evaluate(self, domain: str = "", ip: str = "", port: int = 0) -> str:
        # Check explicit rules
        for rule in self._rules:
            if rule.type == "block":
                if rule.target == "domain" and domain.endswith(rule.value):
                    self._log.append({"domain": domain, "ip": ip, "action": "block", "reason": rule.rule_id})
                    self._save()
                    return "block"
                if rule.target == "ip" and ip == rule.value:
                    self._log.append({"domain": domain, "ip": ip, "action": "block", "reason": rule.rule_id})
                    self._save()
                    return "block"
            if rule.type == "allow":
                if rule.target == "domain" and domain.endswith(rule.value):
                    self._log.append({"domain": domain, "ip": ip, "action": "allow", "reason": rule.rule_id})
                    self._save()
                    return "allow"
                if rule.target == "ip" and ip == rule.value:
                    self._log.append({"domain": domain, "ip": ip, "action": "allow", "reason": rule.rule_id})
                    self._save()
                    return "allow"
        self._log.append({"domain": domain, "ip": ip, "action": self._default_policy})
        self._save()
        return self._default_policy

    def to_dict(self) -> dict:
        return {"rule_count": len(self._rules), "default_policy": self._default_policy, "log_entries": len(self._log)}

    def get_stats(self) -> dict:
        return {"rules": len(self._rules), "blocked": sum(1 for e in self._log if e.get("action") == "block"), "allowed": sum(1 for e in self._log if e.get("action") == "allow")}

__all__ = ["SandboxNetworkRestrictor", "NetworkRule"]
