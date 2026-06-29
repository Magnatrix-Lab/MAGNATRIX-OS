"""Blockchain Smart Contract VM -- EVM-lite execution environment."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class Contract:
    contract_id: str = ""
    bytecode: str = ""
    storage: dict = None
    balance: float = 0.0
    creator: str = ""
    created_at: float = 0.0

    def __post_init__(self):
        if self.storage is None:
            self.storage = {}

class BlockchainSmartContractVM:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._contracts: dict[str, Contract] = {}
        self._calls: list[dict] = []
        self._persist_path = self.root / "blockchain_vm.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._contracts = {k: Contract(**v) for k, v in data.get("contracts", {}).items()}
            self._calls = data.get("calls", [])

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "contracts": {k: v.__dict__ for k, v in self._contracts.items()},
            "calls": self._calls
        }, indent=2))

    def deploy(self, contract_id: str, bytecode: str, creator: str, initial_storage: dict = None) -> Contract:
        import time
        contract = Contract(
            contract_id=contract_id, bytecode=bytecode, creator=creator,
            storage=initial_storage or {}, created_at=time.time()
        )
        self._contracts[contract_id] = contract
        self._save()
        return contract

    def call(self, contract_id: str, caller: str, function: str, args: list, value: float = 0.0) -> dict:
        contract = self._contracts.get(contract_id)
        if not contract:
            return {"error": "Contract not found"}

        # Simulated execution: update storage based on function name
        result = {"function": function, "args": args, "caller": caller, "value": value}
        if function == "set":
            if len(args) >= 2:
                contract.storage[str(args[0])] = args[1]
                result["stored"] = True
        elif function == "get":
            if args:
                result["value"] = contract.storage.get(str(args[0]), None)
        elif function == "transfer":
            if contract.balance >= value:
                contract.balance -= value
                result["transferred"] = value
            else:
                result["error"] = "Insufficient balance"
        elif function == "deposit":
            contract.balance += value
            result["deposited"] = value

        self._calls.append(result)
        self._save()
        return result

    def get_storage(self, contract_id: str, key: str) -> any:
        contract = self._contracts.get(contract_id)
        return contract.storage.get(key) if contract else None

    def get_balance(self, contract_id: str) -> float:
        contract = self._contracts.get(contract_id)
        return contract.balance if contract else 0.0

    def to_dict(self) -> dict:
        return {"contract_count": len(self._contracts), "calls": len(self._calls)}

    def get_stats(self) -> dict:
        by_function = {}
        for c in self._calls:
            fn = c.get("function", "unknown")
            by_function[fn] = by_function.get(fn, 0) + 1
        total_storage = sum(len(c.storage) for c in self._contracts.values())
        return {"contracts": len(self._contracts), "calls": len(self._calls), "by_function": by_function, "total_storage": total_storage}

__all__ = ["BlockchainSmartContractVM", "Contract"]
