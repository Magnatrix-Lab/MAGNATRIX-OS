"""LLM Adapter Factory — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable, Type
from enum import Enum, auto

class AdapterType(Enum):
    INPUT = auto()
    OUTPUT = auto()
    FORMAT = auto()
    PROTOCOL = auto()
    MODEL = auto()

@dataclass
class Adapter:
    id: str
    adapter_type: AdapterType
    transform: Callable[[Any], Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

class AdapterFactory:
    def __init__(self) -> None:
        self._adapters: Dict[str, Adapter] = {}
        self._registry: Dict[str, List[str]] = {}

    def register(self, adapter: Adapter) -> None:
        self._adapters[adapter.id] = adapter
        if adapter.adapter_type.name not in self._registry:
            self._registry[adapter.adapter_type.name] = []
        self._registry[adapter.adapter_type.name].append(adapter.id)

    def get(self, adapter_id: str) -> Optional[Adapter]:
        return self._adapters.get(adapter_id)

    def create_chain(self, adapter_ids: List[str]) -> Callable[[Any], Any]:
        def chain_transform(data: Any) -> Any:
            result = data
            for aid in adapter_ids:
                adapter = self._adapters.get(aid)
                if adapter:
                    result = adapter.transform(result)
            return result
        return chain_transform

    def find_by_type(self, adapter_type: AdapterType) -> List[Adapter]:
        ids = self._registry.get(adapter_type.name, [])
        return [self._adapters[eid] for eid in ids if eid in self._adapters]

    def get_stats(self) -> Dict[str, Any]:
        return {"adapters": len(self._adapters), "by_type": {t: len(ids) for t, ids in self._registry.items()}}

def run() -> None:
    print("Adapter Factory test")
    e = AdapterFactory()
    e.register(Adapter("a1", AdapterType.INPUT, lambda x: x.strip().lower()))
    e.register(Adapter("a2", AdapterType.FORMAT, lambda x: {"text": x}))
    e.register(Adapter("a3", AdapterType.OUTPUT, lambda x: x.get("text", "").upper()))
    chain = e.create_chain(["a1", "a2", "a3"])
    result = chain("  Hello World  ")
    print("  Chain result: '" + result + "'")
    print("  Input adapters: " + str([a.id for a in e.find_by_type(AdapterType.INPUT)]))
    print("  Stats: " + str(e.get_stats()))
    print("Adapter Factory test complete.")

if __name__ == "__main__":
    run()
