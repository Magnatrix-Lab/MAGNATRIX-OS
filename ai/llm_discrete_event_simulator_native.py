#!/usr/bin/env python3
"""MAGNATRIX-OS :: Discrete Event Simulator Native Module
Simulates systems where state changes occur at discrete points in time using an event queue.
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Callable, Any


class EventType(Enum):
    ARRIVAL = auto()
    DEPARTURE = auto()
    SERVICE_START = auto()
    SERVICE_END = auto()
    TIMEOUT = auto()
    CUSTOM = auto()


@dataclass
class Event:
    time: float
    event_type: EventType
    entity_id: int
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0

    def __lt__(self, other: "Event") -> bool:
        if self.time == other.time:
            return self.priority < other.priority
        return self.time < other.time


@dataclass
class Entity:
    id: int
    state: str = "idle"
    arrival_time: float = 0.0
    departure_time: float = 0.0
    service_time: float = 0.0


@dataclass
class SimulationMetrics:
    total_events: int
    max_queue_length: int
    avg_waiting_time: float
    throughput: float
    utilization: float
    final_time: float

    def to_dict(self) -> Dict:
        return {
            "total_events": self.total_events,
            "max_queue": self.max_queue_length,
            "avg_wait": round(self.avg_waiting_time, 3),
            "throughput": round(self.throughput, 3),
            "utilization": round(self.utilization, 3),
            "final_time": round(self.final_time, 3),
        }


class DiscreteEventSimulator:
    """Event-driven simulation using a priority queue."""

    def __init__(self):
        self.event_queue: List[Event] = []
        self.current_time = 0.0
        self.entities: Dict[int, Entity] = {}
        self.event_log: List[Event] = []
        self.queue_length = 0
        self.max_queue = 0
        self.total_wait = 0.0
        self.entities_processed = 0
        self.busy_time = 0.0
        self.last_busy_start = 0.0
        self.is_busy = False
        self.event_handlers: Dict[EventType, Callable[[Event], List[Event]]] = {}

    def register_handler(self, event_type: EventType, handler: Callable[[Event], List[Event]]) -> None:
        self.event_handlers[event_type] = handler

    def schedule(self, event: Event) -> None:
        heapq.heappush(self.event_queue, event)

    def run(self, until_time: float = float("inf"), max_events: int = 10000) -> SimulationMetrics:
        event_count = 0
        while self.event_queue and self.current_time < until_time and event_count < max_events:
            event = heapq.heappop(self.event_queue)
            self.current_time = event.time
            self.event_log.append(event)
            event_count += 1
            handler = self.event_handlers.get(event.event_type)
            if handler:
                new_events = handler(event)
                for ne in new_events:
                    heapq.heappush(self.event_queue, ne)
        if self.is_busy:
            self.busy_time += self.current_time - self.last_busy_start
        total_time = self.current_time if self.current_time > 0 else 1.0
        avg_wait = self.total_wait / self.entities_processed if self.entities_processed > 0 else 0.0
        return SimulationMetrics(
            total_events=event_count,
            max_queue_length=self.max_queue,
            avg_waiting_time=avg_wait,
            throughput=self.entities_processed / total_time,
            utilization=self.busy_time / total_time,
            final_time=self.current_time,
        )

    def stats(self) -> Dict[str, int]:
        return {
            "entities": len(self.entities),
            "logged_events": len(self.event_log),
            "handlers": len(self.event_handlers),
        }


def run() -> None:
    sim = DiscreteEventSimulator()
    sim.register_handler(EventType.ARRIVAL, lambda e: [
        Event(e.time + 2.0, EventType.SERVICE_START, e.entity_id, {"queue_pos": sim.queue_length}),
    ])
    sim.register_handler(EventType.SERVICE_START, lambda e: [
        Event(e.time + 1.5, EventType.SERVICE_END, e.entity_id),
    ])
    sim.register_handler(EventType.SERVICE_END, lambda e: [
        Event(e.time + 0.5, EventType.DEPARTURE, e.entity_id),
    ])

    for i in range(10):
        sim.schedule(Event(i * 1.0, EventType.ARRIVAL, i))
        sim.entities[i] = Entity(id=i)

    metrics = sim.run(until_time=100.0)
    print(f"Discrete Event Simulator Demo:")
    print(f"  Events processed: {metrics.total_events}")
    print(f"  Throughput: {metrics.throughput:.3f} entities/time")
    print(f"  Avg wait: {metrics.avg_waiting_time:.3f}, Max queue: {metrics.max_queue_length}")
    print(f"  Stats: {sim.stats()}")


if __name__ == "__main__":
    run()
