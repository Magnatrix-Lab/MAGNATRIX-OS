"""Adapter Pattern Engine — protocol translation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Callable, Any, Optional, List
from enum import Enum, auto

class ProtocolType(Enum):
    REST = auto()
    GRPC = auto()
    SOAP = auto()
    MESSAGE = auto()
    CUSTOM = auto()

@dataclass
class AdapterMapping:
    source_protocol: ProtocolType
    target_protocol: ProtocolType
    transform: Callable[[Any], Any]

class AdapterEngine:
    def __init__(self):
        self.adapters: Dict[str, AdapterMapping] = {}
        self.requests: List[Dict] = []
        self.responses: List[Dict] = []

    def register(self, adapter_id: str, source: ProtocolType, target: ProtocolType, transform: Callable):
        self.adapters[adapter_id] = AdapterMapping(source, target, transform)

    def translate(self, adapter_id: str, payload: Any) -> Any:
        adapter = self.adapters.get(adapter_id)
        if not adapter:
            raise ValueError(f"Adapter {adapter_id} not found")
        self.requests.append({"adapter": adapter_id, "payload": payload})
        result = adapter.transform(payload)
        self.responses.append({"adapter": adapter_id, "result": result})
        return result

    def list_adapters(self) -> List[Dict]:
        return [{"id": k, "source": v.source_protocol.name, "target": v.target_protocol.name} for k, v in self.adapters.items()]

    def stats(self) -> Dict:
        return {"adapters": len(self.adapters), "requests": len(self.requests), "responses": len(self.responses)}

def run():
    engine = AdapterEngine()
    def rest_to_grpc(payload):
        return {"method": payload.get("method"), "body": payload.get("data"), "metadata": {}}
    engine.register("rest2grpc", ProtocolType.REST, ProtocolType.GRPC, rest_to_grpc)
    result = engine.translate("rest2grpc", {"method": "GET", "data": {"id": 1}})
    print(result)
    print(engine.list_adapters())
    print(engine.stats())

if __name__ == "__main__":
    run()
