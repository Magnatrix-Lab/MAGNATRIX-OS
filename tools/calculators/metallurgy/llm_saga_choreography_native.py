"""Saga Choreography — event-driven saga coordination, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Any, Optional
from enum import Enum, auto
import time
import uuid

class ChoreographyEvent(Enum):
    ORDER_CREATED = auto()
    INVENTORY_RESERVED = auto()
    PAYMENT_PROCESSED = auto()
    SHIPMENT_INITIATED = auto()
    INVENTORY_FAILED = auto()
    PAYMENT_FAILED = auto()
    COMPENSATION_REQUIRED = auto()

@dataclass
class SagaMessage:
    msg_id: str
    saga_id: str
    event: ChoreographyEvent
    payload: Dict
    timestamp: float = field(default_factory=time.time)

class SagaChoreography:
    def __init__(self, saga_id: str):
        self.saga_id = saga_id
        self.handlers: Dict[ChoreographyEvent, List[Callable]] = {}
        self.messages: List[SagaMessage] = []
        self.state: Dict[str, Any] = {}

    def on(self, event: ChoreographyEvent, handler: Callable[[SagaMessage], Optional[List[SagaMessage]]]):
        if event not in self.handlers:
            self.handlers[event] = []
        self.handlers[event].append(handler)

    def emit(self, event: ChoreographyEvent, payload: Dict) -> SagaMessage:
        msg_id = str(uuid.uuid4())[:8]
        msg = SagaMessage(msg_id, self.saga_id, event, payload)
        self.messages.append(msg)
        for handler in self.handlers.get(event, []):
            try:
                new_msgs = handler(msg)
                if new_msgs:
                    for m in new_msgs:
                        self.messages.append(m)
            except:
                pass
        return msg

    def get_messages(self, event: Optional[ChoreographyEvent] = None) -> List[SagaMessage]:
        if event:
            return [m for m in self.messages if m.event == event]
        return self.messages

    def stats(self) -> Dict:
        return {"saga_id": self.saga_id, "messages": len(self.messages), "events": len(set(m.event for m in self.messages)), "handlers": len(self.handlers)}

def run():
    saga = SagaChoreography("order")
    def on_order_created(msg):
        if msg.payload.get("valid"):
            return [SagaMessage("", msg.saga_id, ChoreographyEvent.INVENTORY_RESERVED, {"order_id": msg.payload["id"]})]
        return [SagaMessage("", msg.saga_id, ChoreographyEvent.COMPENSATION_REQUIRED, {})]
    def on_inventory_reserved(msg):
        return [SagaMessage("", msg.saga_id, ChoreographyEvent.PAYMENT_PROCESSED, {"order_id": msg.payload["order_id"]})]
    saga.on(ChoreographyEvent.ORDER_CREATED, on_order_created)
    saga.on(ChoreographyEvent.INVENTORY_RESERVED, on_inventory_reserved)
    saga.emit(ChoreographyEvent.ORDER_CREATED, {"id": 1, "valid": True})
    print([m.event.name for m in saga.messages])
    print(saga.stats())

if __name__ == "__main__":
    run()
