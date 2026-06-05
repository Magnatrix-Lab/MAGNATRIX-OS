"""Protocol Bridge — bidirectional translation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Callable, Any, Optional, List
from enum import Enum, auto

class Protocol(Enum):
    HTTP = auto()
    MQTT = auto()
    WS = auto()
    TCP = auto()
    UDP = auto()

@dataclass
class Bridge:
    bridge_id: str
    protocol_a: Protocol
    protocol_b: Protocol
    a_to_b: Callable[[Any], Any]
    b_to_a: Callable[[Any], Any]

class ProtocolBridge:
    def __init__(self):
        self.bridges: Dict[str, Bridge] = {}
        self.translations: List[Dict] = []

    def create_bridge(self, bridge_id: str, a: Protocol, b: Protocol, a_to_b: Callable, b_to_a: Callable):
        self.bridges[bridge_id] = Bridge(bridge_id, a, b, a_to_b, b_to_a)

    def translate(self, bridge_id: str, direction: str, payload: Any) -> Any:
        bridge = self.bridges.get(bridge_id)
        if not bridge:
            raise ValueError(f"Bridge {bridge_id} not found")
        if direction == "a_to_b":
            result = bridge.a_to_b(payload)
        elif direction == "b_to_a":
            result = bridge.b_to_a(payload)
        else:
            raise ValueError("Invalid direction")
        self.translations.append({"bridge": bridge_id, "direction": direction, "payload": payload, "result": result})
        return result

    def stats(self) -> Dict:
        return {"bridges": len(self.bridges), "translations": len(self.translations)}

def run():
    bridge = ProtocolBridge()
    def http_to_mqtt(p):
        return {"topic": f"api/{p.get('path')}", "payload": p.get("body")}
    def mqtt_to_http(p):
        return {"path": p.get("topic").replace("api/", ""), "body": p.get("payload")}
    bridge.create_bridge("http_mqtt", Protocol.HTTP, Protocol.MQTT, http_to_mqtt, mqtt_to_http)
    print(bridge.translate("http_mqtt", "a_to_b", {"path": "users", "body": {"id": 1}}))
    print(bridge.stats())

if __name__ == "__main__":
    run()
