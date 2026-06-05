"""Smart Contract Engine — execution, state, events, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any
from enum import Enum, auto
import time
import hashlib
import json

class ContractState(Enum):
    DEPLOYED = auto()
    RUNNING = auto()
    PAUSED = auto()
    DESTROYED = auto()

@dataclass
class ContractEvent:
    event_id: str
    name: str
    data: Dict
    timestamp: float

@dataclass
class ContractStorage:
    data: Dict[str, Any] = field(default_factory=dict)

class SmartContract:
    def __init__(self, contract_id: str, owner: str):
        self.contract_id = contract_id
        self.owner = owner
        self.state = ContractState.DEPLOYED
        self.storage = ContractStorage()
        self.events: List[ContractEvent] = []
        self.balance: float = 0.0
        self.functions: Dict[str, Callable] = {}

    def deploy(self):
        self.state = ContractState.RUNNING

    def register_function(self, name: str, func: Callable):
        self.functions[name] = func

    def call(self, function_name: str, caller: str, args: Dict) -> Any:
        if self.state != ContractState.RUNNING:
            raise Exception("Contract not running")
        func = self.functions.get(function_name)
        if not func:
            raise Exception("Function not found")
        return func(self, caller, args)

    def emit(self, event_name: str, data: Dict):
        event_id = hashlib.sha256(f"{event_name}:{time.time()}".encode()).hexdigest()[:8]
        self.events.append(ContractEvent(event_id, event_name, data, time.time()))

    def get_storage(self, key: str) -> Any:
        return self.storage.data.get(key)

    def set_storage(self, key: str, value: Any):
        self.storage.data[key] = value

    def stats(self) -> Dict:
        return {"contract_id": self.contract_id, "state": self.state.name, "events": len(self.events), "balance": self.balance, "functions": len(self.functions)}

def run():
    contract = SmartContract("token_1", "owner_1")
    def transfer(contract, caller, args):
        from_addr = args.get("from")
        to_addr = args.get("to")
        amount = args.get("amount", 0)
        balances = contract.storage.data.get("balances", {})
        if balances.get(from_addr, 0) >= amount:
            balances[from_addr] -= amount
            balances[to_addr] = balances.get(to_addr, 0) + amount
            contract.storage.data["balances"] = balances
            contract.emit("Transfer", {"from": from_addr, "to": to_addr, "amount": amount})
            return True
        return False
    contract.register_function("transfer", transfer)
    contract.deploy()
    contract.set_storage("balances", {"Alice": 100, "Bob": 50})
    contract.call("transfer", "Alice", {"from": "Alice", "to": "Bob", "amount": 30})
    print(contract.get_storage("balances"))
    print(contract.stats())

if __name__ == "__main__":
    run()
