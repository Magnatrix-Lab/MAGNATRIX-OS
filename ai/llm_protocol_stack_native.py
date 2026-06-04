"""Protocol Stack - Layered protocol for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Callable
from enum import Enum, auto

class LayerType(Enum):
    PHYSICAL = auto(); DATA_LINK = auto(); NETWORK = auto(); TRANSPORT = auto(); APPLICATION = auto()

@dataclass
class ProtocolStack:
    layers: Dict[LayerType, List[Callable]] = field(default_factory=dict)

    def register(self, layer: LayerType, handler: Callable) -> None:
        if layer not in self.layers: self.layers[layer] = []
        self.layers[layer].append(handler)

    def transmit(self, data: str) -> str:
        for layer in [LayerType.APPLICATION, LayerType.TRANSPORT, LayerType.NETWORK, LayerType.DATA_LINK, LayerType.PHYSICAL]:
            for handler in self.layers.get(layer, []): data = handler(data)
        return data

    def receive(self, data: str) -> str:
        for layer in [LayerType.PHYSICAL, LayerType.DATA_LINK, LayerType.NETWORK, LayerType.TRANSPORT, LayerType.APPLICATION]:
            for handler in self.layers.get(layer, []): data = handler(data)
        return data

    def stats(self) -> dict:
        return {"layers": len(self.layers), "handlers": sum(len(h) for h in self.layers.values())}

def run():
    ps = ProtocolStack()
    ps.register(LayerType.APPLICATION, lambda d: f"APP({d})")
    ps.register(LayerType.TRANSPORT, lambda d: f"TCP({d})")
    print("Transmit:", ps.transmit("hello"))
    print("Stats:", ps.stats())

if __name__ == "__main__": run()
