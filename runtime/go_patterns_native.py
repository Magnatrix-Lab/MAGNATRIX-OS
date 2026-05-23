#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAGNATRIX-OS — Go-Patterns Native Integration (Python Design Patterns Library)
═══════════════════════════════════════════════════════════════════════════════
AMATI-PELAJARI-TIRU dari tmrts/go-patterns

Pola yang ditiru:
• Creational Patterns — Singleton, Factory Method, Builder, Prototype, Abstract Factory
• Structural Patterns — Adapter, Bridge, Composite, Decorator, Facade, Flyweight, Proxy
• Behavioral Patterns — Observer, Strategy, Template Method, Iterator, State, Command,
  Chain of Responsibility, Mediator, Memento, Visitor
• Concurrency Patterns — Worker Pool, Pipeline, Fan-out/Fan-in, Futures/Promises,
  Semaphore, Barrier, Broadcast, Mutex/Atomic
• Functional Options — Builder pattern variant untuk configurasi API
• Object Pool — Resource pooling untuk high-throughput operations

Semua pattern diimplementasikan dalam Python-native idiomatic code.
Meniru Go implementation style: explicit interfaces, composition over inheritance,
minimal magic, clear separation of concerns.

Layer: Runtime (3) — Design Patterns & Concurrency Primitives Library
Versi: Phase 5 — Go-Patterns Native Python Library
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from pathlib import Path
from queue import Queue, Empty
from typing import Any, Callable, Dict, Generic, Iterator, List, Optional, Protocol, Set, Tuple, TypeVar, Union
from concurrent.futures import ThreadPoolExecutor, Future as ConcurrentFuture


# ═════════════════════════════════════════════════════════════════════════════
# 0. UTILITAS
# ═════════════════════════════════════════════════════════════════════════════

def _now() -> str:
    from datetime import datetime
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


# ═════════════════════════════════════════════════════════════════════════════
# 1. CREATIONAL PATTERNS
# ═════════════════════════════════════════════════════════════════════════════

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")

# ── Singleton ───────────────────────────────────────────────────────────

class SingletonMeta(type):
    """Thread-safe Singleton metaclass."""
    _instances: Dict[type, Any] = {}
    _locks: Dict[type, threading.Lock] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in SingletonMeta._locks:
            SingletonMeta._locks[cls] = threading.Lock()
        with SingletonMeta._locks[cls]:
            if cls not in SingletonMeta._instances:
                SingletonMeta._instances[cls] = super().__call__(*args, **kwargs)
        return SingletonMeta._instances[cls]

class DatabaseConnection(metaclass=SingletonMeta):
    """Example singleton: database connection."""
    def __init__(self) -> None:
        self.id = id(self)
        self.connected = False
    def connect(self) -> None:
        self.connected = True

# ── Factory Method ──────────────────────────────────────────────────────

class Product(ABC):
    @abstractmethod
    def use(self) -> str: ...

class ConcreteProductA(Product):
    def use(self) -> str: return "Using Product A"

class ConcreteProductB(Product):
    def use(self) -> str: return "Using Product B"

class Creator(ABC):
    @abstractmethod
    def factory_method(self) -> Product: ...
    def operation(self) -> str:
        product = self.factory_method()
        return f"Creator: {product.use()}"

class CreatorA(Creator):
    def factory_method(self) -> Product:
        return ConcreteProductA()

class CreatorB(Creator):
    def factory_method(self) -> Product:
        return ConcreteProductB()

# ── Abstract Factory ────────────────────────────────────────────────────

class Button(ABC):
    @abstractmethod
    def render(self) -> str: ...

class Checkbox(ABC):
    @abstractmethod
    def check(self) -> str: ...

class WinButton(Button):
    def render(self) -> str: return "Windows Button"

class WinCheckbox(Checkbox):
    def check(self) -> str: return "Windows Checkbox"

class MacButton(Button):
    def render(self) -> str: return "Mac Button"

class MacCheckbox(Checkbox):
    def check(self) -> str: return "Mac Checkbox"

class GUIFactory(ABC):
    @abstractmethod
    def create_button(self) -> Button: ...
    @abstractmethod
    def create_checkbox(self) -> Checkbox: ...

class WinFactory(GUIFactory):
    def create_button(self) -> Button: return WinButton()
    def create_checkbox(self) -> Checkbox: return WinCheckbox()

class MacFactory(GUIFactory):
    def create_button(self) -> Button: return MacButton()
    def create_checkbox(self) -> Checkbox: return MacCheckbox()

# ── Builder ─────────────────────────────────────────────────────────────

@dataclass
class House:
    walls: int = 0
    doors: int = 0
    windows: int = 0
    roof: str = ""
    garage: bool = False
    pool: bool = False

class HouseBuilder:
    """Fluent builder untuk House."""
    def __init__(self) -> None:
        self._house = House()
    def set_walls(self, n: int) -> HouseBuilder:
        self._house.walls = n; return self
    def set_doors(self, n: int) -> HouseBuilder:
        self._house.doors = n; return self
    def set_windows(self, n: int) -> HouseBuilder:
        self._house.windows = n; return self
    def set_roof(self, roof: str) -> HouseBuilder:
        self._house.roof = roof; return self
    def add_garage(self) -> HouseBuilder:
        self._house.garage = True; return self
    def add_pool(self) -> HouseBuilder:
        self._house.pool = True; return self
    def build(self) -> House:
        return self._house

# ── Prototype ───────────────────────────────────────────────────────────

import copy

class Prototype(ABC):
    @abstractmethod
    def clone(self) -> Prototype: ...

class ConcretePrototype(Prototype):
    def __init__(self, field: str, items: List[str]) -> None:
        self.field = field
        self.items = items
    def clone(self) -> ConcretePrototype:
        return copy.deepcopy(self)
    def __repr__(self) -> str:
        return f"ConcretePrototype(field={self.field}, items={self.items})"

# ── Functional Options ──────────────────────────────────────────────────

@dataclass
class ServerConfig:
    host: str = "localhost"
    port: int = 8080
    timeout: float = 30.0
    max_conns: int = 100
    tls_enabled: bool = False

ServerOption = Callable[[ServerConfig], None]

def WithHost(host: str) -> ServerOption:
    return lambda c: setattr(c, "host", host)

def WithPort(port: int) -> ServerOption:
    return lambda c: setattr(c, "port", port)

def WithTimeout(timeout: float) -> ServerOption:
    return lambda c: setattr(c, "timeout", timeout)

def WithTLS(enabled: bool = True) -> ServerOption:
    return lambda c: setattr(c, "tls_enabled", enabled)

def NewServer(opts: List[ServerOption]) -> ServerConfig:
    cfg = ServerConfig()
    for opt in opts:
        opt(cfg)
    return cfg

# ── Object Pool ─────────────────────────────────────────────────────────

class ObjectPool(Generic[T]):
    """Generic object pool untuk reusable resources."""
    def __init__(self, factory: Callable[[], T], max_size: int = 10) -> None:
        self._factory = factory
        self._max_size = max_size
        self._pool: Queue[T] = Queue(maxsize=max_size)
        self._in_use: Set[T] = set()
        self._lock = threading.Lock()
        # Pre-warm
        for _ in range(max_size // 2):
            self._pool.put(factory())

    def acquire(self) -> T:
        with self._lock:
            try:
                obj = self._pool.get_nowait()
                self._in_use.add(obj)
                return obj
            except Empty:
                obj = self._factory()
                self._in_use.add(obj)
                return obj

    def release(self, obj: T) -> None:
        with self._lock:
            self._in_use.discard(obj)
            if self._pool.qsize() < self._max_size:
                self._pool.put(obj)

    def stats(self) -> Dict[str, int]:
        return {"available": self._pool.qsize(), "in_use": len(self._in_use), "max": self._max_size}


# ═════════════════════════════════════════════════════════════════════════════
# 2. STRUCTURAL PATTERNS
# ═════════════════════════════════════════════════════════════════════════════

# ── Adapter ─────────────────────────────────────────────────────────────

class Target(ABC):
    @abstractmethod
    def request(self) -> str: ...

class Adaptee:
    """Existing class dengan interface yang tidak compatible."""
    def specific_request(self) -> str:
        return "Specific request from Adaptee"

class Adapter(Target):
    def __init__(self, adaptee: Adaptee) -> None:
        self._adaptee = adaptee
    def request(self) -> str:
        return f"Adapter wrapping: {self._adaptee.specific_request()}"

# ── Bridge ──────────────────────────────────────────────────────────────

class Implementation(ABC):
    @abstractmethod
    def operation_impl(self) -> str: ...

class ConcreteImplementationA(Implementation):
    def operation_impl(self) -> str: return "ConcreteImplementationA"

class ConcreteImplementationB(Implementation):
    def operation_impl(self) -> str: return "ConcreteImplementationB"

class Abstraction:
    def __init__(self, impl: Implementation) -> None:
        self._impl = impl
    def operation(self) -> str:
        return f"Abstraction → {self._impl.operation_impl()}"

class RefinedAbstraction(Abstraction):
    def operation(self) -> str:
        return f"RefinedAbstraction → {self._impl.operation_impl()}"

# ── Composite ────────────────────────────────────────────────────────────

class Component(ABC):
    @abstractmethod
    def operation(self) -> str: ...
    @abstractmethod
    def get_price(self) -> float: ...

class Leaf(Component):
    def __init__(self, name: str, price: float) -> None:
        self.name = name
        self._price = price
    def operation(self) -> str:
        return f"Leaf: {self.name}"
    def get_price(self) -> float:
        return self._price

class Composite(Component):
    def __init__(self, name: str) -> None:
        self.name = name
        self._children: List[Component] = []
    def add(self, component: Component) -> None:
        self._children.append(component)
    def remove(self, component: Component) -> None:
        self._children.remove(component)
    def operation(self) -> str:
        results = [c.operation() for c in self._children]
        return f"Composite({self.name}): [{', '.join(results)}]"
    def get_price(self) -> float:
        return sum(c.get_price() for c in self._children)

# ── Decorator ──────────────────────────────────────────────────────────

class Coffee(ABC):
    @abstractmethod
    def cost(self) -> float: ...
    @abstractmethod
    def description(self) -> str: ...

class SimpleCoffee(Coffee):
    def cost(self) -> float: return 10.0
    def description(self) -> str: return "Simple coffee"

class CoffeeDecorator(Coffee, ABC):
    def __init__(self, coffee: Coffee) -> None:
        self._coffee = coffee
    def cost(self) -> float:
        return self._coffee.cost()
    def description(self) -> str:
        return self._coffee.description()

class MilkDecorator(CoffeeDecorator):
    def cost(self) -> float:
        return self._coffee.cost() + 2.0
    def description(self) -> str:
        return f"{self._coffee.description()}, milk"

class SugarDecorator(CoffeeDecorator):
    def cost(self) -> float:
        return self._coffee.cost() + 1.0
    def description(self) -> str:
        return f"{self._coffee.description()}, sugar"

# ── Facade ──────────────────────────────────────────────────────────────

class SubsystemA:
    def operation_a(self) -> str: return "SubsystemA: Ready"

class SubsystemB:
    def operation_b(self) -> str: return "SubsystemB: Go"

class SubsystemC:
    def operation_c(self) -> str: return "SubsystemC: Fire"

class Facade:
    """Simplified interface ke complex subsystem."""
    def __init__(self) -> None:
        self._a = SubsystemA()
        self._b = SubsystemB()
        self._c = SubsystemC()
    def operation(self) -> str:
        return " | ".join([
            self._a.operation_a(),
            self._b.operation_b(),
            self._c.operation_c(),
        ])

# ── Flyweight ──────────────────────────────────────────────────────────

class Flyweight:
    """Intrinsic state yang dapat dishare."""
    def __init__(self, shared_state: str) -> None:
        self._shared = shared_state
    def operation(self, extrinsic_state: str) -> str:
        return f"Flyweight[{self._shared}] processing {extrinsic_state}"

class FlyweightFactory:
    def __init__(self) -> None:
        self._flyweights: Dict[str, Flyweight] = {}
    def get_flyweight(self, key: str) -> Flyweight:
        if key not in self._flyweights:
            self._flyweights[key] = Flyweight(key)
        return self._flyweights[key]
    def count(self) -> int:
        return len(self._flyweights)

# ── Proxy ──────────────────────────────────────────────────────────────

class RealSubject:
    def request(self) -> str:
        return "RealSubject: Handling request"

class Proxy:
    """Virtual proxy dengan lazy initialization & access control."""
    def __init__(self) -> None:
        self._real: Optional[RealSubject] = None
        self._access_log: List[str] = []
    def request(self) -> str:
        if self._real is None:
            self._real = RealSubject()
        self._access_log.append(_now())
        return f"Proxy: {self._real.request()}"
    def get_access_count(self) -> int:
        return len(self._access_log)


# ═════════════════════════════════════════════════════════════════════════════
# 3. BEHAVIORAL PATTERNS
# ═════════════════════════════════════════════════════════════════════════════

# ── Observer ───────────────────────────────────────────────────────────

class Observer(ABC):
    @abstractmethod
    def update(self, subject: Subject) -> None: ...

class Subject:
    def __init__(self) -> None:
        self._observers: List[Observer] = []
        self._state: Any = None
    def attach(self, observer: Observer) -> None:
        self._observers.append(observer)
    def detach(self, observer: Observer) -> None:
        self._observers.remove(observer)
    def notify(self) -> None:
        for observer in self._observers:
            observer.update(self)
    def set_state(self, state: Any) -> None:
        self._state = state
        self.notify()
    def get_state(self) -> Any:
        return self._state

class ConcreteObserverA(Observer):
    def __init__(self) -> None:
        self.received_state: Any = None
    def update(self, subject: Subject) -> None:
        self.received_state = subject.get_state()

class ConcreteObserverB(Observer):
    def __init__(self) -> None:
        self.count = 0
    def update(self, subject: Subject) -> None:
        self.count += 1

# ── Strategy ──────────────────────────────────────────────────────────

class Strategy(ABC):
    @abstractmethod
    def execute(self, a: float, b: float) -> float: ...

class AddStrategy(Strategy):
    def execute(self, a: float, b: float) -> float:
        return a + b

class MultiplyStrategy(Strategy):
    def execute(self, a: float, b: float) -> float:
        return a * b

class Context:
    def __init__(self, strategy: Strategy) -> None:
        self._strategy = strategy
    def set_strategy(self, strategy: Strategy) -> None:
        self._strategy = strategy
    def execute(self, a: float, b: float) -> float:
        return self._strategy.execute(a, b)

# ── Template Method ─────────────────────────────────────────────────────

class AbstractClass(ABC):
    """Template method defines skeleton, subclasses override steps."""
    def template_method(self) -> str:
        return " | ".join([
            self.base_operation(),
            self.required_operation1(),
            self.required_operation2(),
            self.hook(),
        ])
    def base_operation(self) -> str:
        return "AbstractClass: base"
    @abstractmethod
    def required_operation1(self) -> str: ...
    @abstractmethod
    def required_operation2(self) -> str: ...
    def hook(self) -> str:
        return "AbstractClass: default hook"

class ConcreteClass1(AbstractClass):
    def required_operation1(self) -> str: return "ConcreteClass1: op1"
    def required_operation2(self) -> str: return "ConcreteClass1: op2"

class ConcreteClass2(AbstractClass):
    def required_operation1(self) -> str: return "ConcreteClass2: op1"
    def required_operation2(self) -> str: return "ConcreteClass2: op2"
    def hook(self) -> str: return "ConcreteClass2: overridden hook"

# ── Iterator ──────────────────────────────────────────────────────────────

class BookCollection:
    def __init__(self) -> None:
        self._books: List[str] = []
    def add(self, book: str) -> None:
        self._books.append(book)
    def __iter__(self) -> Iterator[str]:
        return iter(self._books)
    def reverse_iterator(self) -> Iterator[str]:
        return iter(reversed(self._books))

# ── State ───────────────────────────────────────────────────────────────

class State(ABC):
    @abstractmethod
    def handle(self, context: ContextState) -> str: ...

class ConcreteStateA(State):
    def handle(self, context: ContextState) -> str:
        context.transition_to(ConcreteStateB())
        return "State A → B"

class ConcreteStateB(State):
    def handle(self, context: ContextState) -> str:
        context.transition_to(ConcreteStateA())
        return "State B → A"

class ContextState:
    def __init__(self, state: State) -> None:
        self._state = state
    def transition_to(self, state: State) -> None:
        self._state = state
    def request(self) -> str:
        return self._state.handle(self)

# ── Command ─────────────────────────────────────────────────────────────

class Command(ABC):
    @abstractmethod
    def execute(self) -> str: ...
    @abstractmethod
    def undo(self) -> str: ...

class Light:
    def __init__(self) -> None:
        self.is_on = False
    def on(self) -> str:
        self.is_on = True
        return "Light is ON"
    def off(self) -> str:
        self.is_on = False
        return "Light is OFF"

class LightOnCommand(Command):
    def __init__(self, light: Light) -> None:
        self._light = light
    def execute(self) -> str:
        return self._light.on()
    def undo(self) -> str:
        return self._light.off()

class RemoteControl:
    def __init__(self) -> None:
        self._commands: Dict[str, Command] = {}
        self._history: List[Command] = []
    def set_command(self, slot: str, command: Command) -> None:
        self._commands[slot] = command
    def press_button(self, slot: str) -> str:
        cmd = self._commands.get(slot)
        if cmd:
            self._history.append(cmd)
            return cmd.execute()
        return "No command"
    def press_undo(self) -> str:
        if self._history:
            return self._history.pop().undo()
        return "Nothing to undo"

# ── Chain of Responsibility ─────────────────────────────────────────────

class Handler(ABC):
    def __init__(self) -> None:
        self._next: Optional[Handler] = None
    def set_next(self, handler: Handler) -> Handler:
        self._next = handler
        return handler
    def handle(self, request: str) -> Optional[str]:
        if self._next:
            return self._next.handle(request)
        return None

class MonkeyHandler(Handler):
    def handle(self, request: str) -> Optional[str]:
        if request == "Banana":
            return f"Monkey: I'll eat the {request}"
        return super().handle(request)

class SquirrelHandler(Handler):
    def handle(self, request: str) -> Optional[str]:
        if request == "Nut":
            return f"Squirrel: I'll eat the {request}"
        return super().handle(request)

class DogHandler(Handler):
    def handle(self, request: str) -> Optional[str]:
        if request == "MeatBall":
            return f"Dog: I'll eat the {request}"
        return super().handle(request)

# ── Mediator ────────────────────────────────────────────────────────────

class Mediator(ABC):
    @abstractmethod
    def notify(self, sender: ComponentMediator, event: str) -> None: ...

class ConcreteMediator(Mediator):
    def __init__(self) -> None:
        self._component_a: Optional[ComponentA] = None
        self._component_b: Optional[ComponentB] = None
    def set_components(self, a: ComponentA, b: ComponentB) -> None:
        self._component_a = a
        self._component_b = b
    def notify(self, sender: ComponentMediator, event: str) -> None:
        if event == "A":
            if self._component_b:
                self._component_b.do_b()
        elif event == "B":
            if self._component_a:
                self._component_a.do_a()

class ComponentMediator(ABC):
    def __init__(self, mediator: Mediator) -> None:
        self._mediator = mediator

class ComponentA(ComponentMediator):
    def do_a(self) -> str:
        return "ComponentA does A"
    def trigger_a(self) -> None:
        self._mediator.notify(self, "A")

class ComponentB(ComponentMediator):
    def do_b(self) -> str:
        return "ComponentB does B"
    def trigger_b(self) -> None:
        self._mediator.notify(self, "B")

# ── Memento ───────────────────────────────────────────────────────────────

class Memento:
    def __init__(self, state: str) -> None:
        self._state = state
        self._date = _now()
    def get_state(self) -> str:
        return self._state
    def get_date(self) -> str:
        return self._date

class Originator:
    def __init__(self, state: str) -> None:
        self._state = state
    def set_state(self, state: str) -> None:
        self._state = state
    def get_state(self) -> str:
        return self._state
    def save(self) -> Memento:
        return Memento(self._state)
    def restore(self, memento: Memento) -> None:
        self._state = memento.get_state()

class Caretaker:
    def __init__(self, originator: Originator) -> None:
        self._originator = originator
        self._history: List[Memento] = []
    def backup(self) -> None:
        self._history.append(self._originator.save())
    def undo(self) -> Optional[str]:
        if not self._history:
            return None
        memento = self._history.pop()
        self._originator.restore(memento)
        return f"Restored to: {memento.get_state()}"

# ── Visitor ───────────────────────────────────────────────────────────────

class Visitor(ABC):
    @abstractmethod
    def visit_concrete_component_a(self, element: ConcreteComponentA) -> str: ...
    @abstractmethod
    def visit_concrete_component_b(self, element: ConcreteComponentB) -> str: ...

class ConcreteVisitor1(Visitor):
    def visit_concrete_component_a(self, element: ConcreteComponentA) -> str:
        return f"Visitor1 → {element.special_method_a()}"
    def visit_concrete_component_b(self, element: ConcreteComponentB) -> str:
        return f"Visitor1 → {element.special_method_b()}"

class ConcreteVisitor2(Visitor):
    def visit_concrete_component_a(self, element: ConcreteComponentA) -> str:
        return f"Visitor2 → {element.special_method_a()}"
    def visit_concrete_component_b(self, element: ConcreteComponentB) -> str:
        return f"Visitor2 → {element.special_method_b()}"

class Visitable(ABC):
    @abstractmethod
    def accept(self, visitor: Visitor) -> str: ...

class ConcreteComponentA(Visitable):
    def accept(self, visitor: Visitor) -> str:
        return visitor.visit_concrete_component_a(self)
    def special_method_a(self) -> str:
        return "ComponentA"

class ConcreteComponentB(Visitable):
    def accept(self, visitor: Visitor) -> str:
        return visitor.visit_concrete_component_b(self)
    def special_method_b(self) -> str:
        return "ComponentB"


# ═════════════════════════════════════════════════════════════════════════════
# 4. CONCURRENCY PATTERNS
# ═════════════════════════════════════════════════════════════════════════════

# ── Worker Pool ───────────────────────────────────────────────────────────

class WorkerPool:
    """Fixed-size worker pool untuk task processing."""
    def __init__(self, num_workers: int = 4) -> None:
        self._executor = ThreadPoolExecutor(max_workers=num_workers)
        self._tasks: List[ConcurrentFuture[Any]] = []

    def submit(self, fn: Callable[..., T], *args, **kwargs) -> ConcurrentFuture[T]:
        future = self._executor.submit(fn, *args, **kwargs)
        self._tasks.append(future)
        return future

    def map(self, fn: Callable[[T], V], items: List[T]) -> List[V]:
        return list(self._executor.map(fn, items))

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True)

    def active_count(self) -> int:
        return sum(1 for f in self._tasks if not f.done())

# ── Pipeline ───────────────────────────────────────────────────────────────

class PipelineStage(Generic[T, V]):
    """Satu stage dalam pipeline."""
    def __init__(self, fn: Callable[[T], V]) -> None:
        self._fn = fn
        self._input: Queue[T] = Queue()
        self._output: Queue[V] = Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while True:
            try:
                item = self._input.get(timeout=1.0)
                result = self._fn(item)
                self._output.put(result)
            except Empty:
                continue

    def send(self, item: T) -> None:
        self._input.put(item)

    def receive(self, timeout: float = 1.0) -> Optional[V]:
        try:
            return self._output.get(timeout=timeout)
        except Empty:
            return None

class Pipeline(Generic[T, V]):
    """Multi-stage pipeline."""
    def __init__(self, stages: List[Callable[[Any], Any]]) -> None:
        self._stages: List[PipelineStage[Any, Any]] = []
        for fn in stages:
            self._stages.append(PipelineStage(fn))
        # Chain stages
        for i in range(len(self._stages) - 1):
            self._chain(self._stages[i], self._stages[i + 1])

    def _chain(self, upstream: PipelineStage[Any, Any], downstream: PipelineStage[Any, Any]) -> None:
        def relay() -> None:
            while True:
                result = upstream.receive(timeout=0.5)
                if result is not None:
                    downstream.send(result)
        threading.Thread(target=relay, daemon=True).start()

    def send(self, item: T) -> None:
        if self._stages:
            self._stages[0].send(item)

    def receive(self, timeout: float = 2.0) -> Optional[V]:
        if self._stages:
            return self._stages[-1].receive(timeout=timeout)
        return None

# ── Fan-out / Fan-in ───────────────────────────────────────────────────

class FanOutFanIn:
    """Fan-out tasks ke multiple workers, fan-in results."""
    def __init__(self, num_workers: int = 4) -> None:
        self._num_workers = num_workers
        self._executor = ThreadPoolExecutor(max_workers=num_workers)

    def process(self, items: List[T],
                worker_fn: Callable[[T], V]) -> List[V]:
        """Fan out items, fan in results."""
        futures = [self._executor.submit(worker_fn, item) for item in items]
        return [f.result() for f in futures]

    def shutdown(self) -> None:
        self._executor.shutdown()

# ── Semaphore ────────────────────────────────────────────────────────────

class Semaphore:
    """Counting semaphore untuk limiting concurrent access."""
    def __init__(self, max_concurrent: int) -> None:
        self._semaphore = threading.Semaphore(max_concurrent)

    def acquire(self) -> bool:
        return self._semaphore.acquire(blocking=False)

    def release(self) -> None:
        self._semaphore.release()

    def with_limit(self, fn: Callable[..., T], *args, **kwargs) -> Optional[T]:
        """Execute function dengan semaphore limit."""
        if self.acquire():
            try:
                return fn(*args, **kwargs)
            finally:
                self.release()
        return None

# ── Barrier ──────────────────────────────────────────────────────────────

class Barrier:
    """Barrier untuk synchronizing multiple threads."""
    def __init__(self, count: int) -> None:
        self._barrier = threading.Barrier(count)

    def wait(self, timeout: Optional[float] = None) -> int:
        return self._barrier.wait(timeout)

# ── Broadcast ────────────────────────────────────────────────────────────

class Broadcast:
    """Broadcast message ke multiple subscribers."""
    def __init__(self) -> None:
        self._subscribers: List[Callable[[Any], None]] = []
        self._lock = threading.Lock()

    def subscribe(self, callback: Callable[[Any], None]) -> None:
        with self._lock:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[Any], None]) -> None:
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def publish(self, message: Any) -> None:
        with self._lock:
            subs = list(self._subscribers)
        for sub in subs:
            sub(message)

# ── Futures / Promises ─────────────────────────────────────────────────

class Promise(Generic[T]):
    """Promise/Future untuk async result."""
    def __init__(self) -> None:
        self._value: Optional[T] = None
        self._resolved = threading.Event()
        self._callbacks: List[Callable[[T], None]] = []

    def resolve(self, value: T) -> None:
        self._value = value
        self._resolved.set()
        for cb in self._callbacks:
            cb(value)

    def get(self, timeout: Optional[float] = None) -> Optional[T]:
        if self._resolved.wait(timeout):
            return self._value
        return None

    def then(self, callback: Callable[[T], None]) -> None:
        if self._resolved.is_set():
            callback(self._value)
        else:
            self._callbacks.append(callback)

# ── Mutex / Atomic ───────────────────────────────────────────────────────

class Mutex:
    """Simple mutex wrapper."""
    def __init__(self) -> None:
        self._lock = threading.Lock()

    def lock(self) -> None:
        self._lock.acquire()

    def unlock(self) -> None:
        self._lock.release()

    def with_lock(self, fn: Callable[..., T], *args, **kwargs) -> T:
        with self._lock:
            return fn(*args, **kwargs)

class AtomicInt:
    """Thread-safe atomic integer."""
    def __init__(self, value: int = 0) -> None:
        self._value = value
        self._lock = threading.Lock()

    def get(self) -> int:
        with self._lock:
            return self._value

    def add(self, delta: int) -> int:
        with self._lock:
            self._value += delta
            return self._value

    def compare_and_swap(self, expected: int, new: int) -> bool:
        with self._lock:
            if self._value == expected:
                self._value = new
                return True
            return False


# ═════════════════════════════════════════════════════════════════════════════
# 5. PATTERN CATALOG & DISCOVERY
# ═════════════════════════════════════════════════════════════════════════════

class PatternCatalog:
    """
    Catalog dari semua available patterns — dokumentasi & discovery.
    """

    PATTERNS: Dict[str, Dict[str, Any]] = {
        # Creational
        "singleton": {"category": "creational", "class": DatabaseConnection, "description": "Ensure single instance globally"},
        "factory_method": {"category": "creational", "class": Creator, "description": "Delegate instantiation to subclasses"},
        "abstract_factory": {"category": "creational", "class": GUIFactory, "description": "Create families of related objects"},
        "builder": {"category": "creational", "class": HouseBuilder, "description": "Construct complex objects step by step"},
        "prototype": {"category": "creational", "class": Prototype, "description": "Clone existing objects"},
        "functional_options": {"category": "creational", "class": ServerConfig, "description": "Configure via variadic option functions"},
        "object_pool": {"category": "creational", "class": ObjectPool, "description": "Reuse expensive-to-create objects"},
        # Structural
        "adapter": {"category": "structural", "class": Adapter, "description": "Convert one interface to another"},
        "bridge": {"category": "structural", "class": Abstraction, "description": "Split abstraction from implementation"},
        "composite": {"category": "structural", "class": Composite, "description": "Tree structure of part-whole hierarchies"},
        "decorator": {"category": "structural", "class": CoffeeDecorator, "description": "Add behavior dynamically without subclassing"},
        "facade": {"category": "structural", "class": Facade, "description": "Simplified interface to complex subsystem"},
        "flyweight": {"category": "structural", "class": FlyweightFactory, "description": "Share data among similar objects"},
        "proxy": {"category": "structural", "class": Proxy, "description": "Placeholder controlling access to real object"},
        # Behavioral
        "observer": {"category": "behavioral", "class": Subject, "description": "Notify dependents automatically"},
        "strategy": {"category": "behavioral", "class": Context, "description": "Encapsulate interchangeable algorithms"},
        "template_method": {"category": "behavioral", "class": AbstractClass, "description": "Skeleton algorithm, subclasses override steps"},
        "iterator": {"category": "behavioral", "class": BookCollection, "description": "Sequential access without exposing representation"},
        "state": {"category": "behavioral", "class": ContextState, "description": "Alter behavior when internal state changes"},
        "command": {"category": "behavioral", "class": Command, "description": "Encapsulate request as object"},
        "chain_of_responsibility": {"category": "behavioral", "class": Handler, "description": "Pass request along chain of handlers"},
        "mediator": {"category": "behavioral", "class": Mediator, "description": "Define how objects interact via mediator"},
        "memento": {"category": "behavioral", "class": Caretaker, "description": "Capture and restore object state"},
        "visitor": {"category": "behavioral", "class": Visitor, "description": "Add operations without changing classes"},
        # Concurrency
        "worker_pool": {"category": "concurrency", "class": WorkerPool, "description": "Fixed pool of workers processing tasks"},
        "pipeline": {"category": "concurrency", "class": Pipeline, "description": "Multi-stage chained processing"},
        "fan_out_fan_in": {"category": "concurrency", "class": FanOutFanIn, "description": "Distribute and collect results"},
        "semaphore": {"category": "concurrency", "class": Semaphore, "description": "Limit concurrent resource access"},
        "barrier": {"category": "concurrency", "class": Barrier, "description": "Synchronize multiple threads at a point"},
        "broadcast": {"category": "concurrency", "class": Broadcast, "description": "Publish to multiple subscribers"},
        "promise": {"category": "concurrency", "class": Promise, "description": "Async result placeholder"},
        "atomic": {"category": "concurrency", "class": AtomicInt, "description": "Thread-safe atomic operations"},
    }

    @classmethod
    def list_patterns(cls, category: Optional[str] = None) -> List[Dict[str, Any]]:
        if category:
            return [
                {"name": k, **v}
                for k, v in cls.PATTERNS.items()
                if v["category"] == category
            ]
        return [{"name": k, **v} for k, v in cls.PATTERNS.items()]

    @classmethod
    def get_pattern(cls, name: str) -> Optional[Dict[str, Any]]:
        return cls.PATTERNS.get(name)

    @classmethod
    def get_stats(cls) -> Dict[str, int]:
        cats: Dict[str, int] = {}
        for p in cls.PATTERNS.values():
            cats[p["category"]] = cats.get(p["category"], 0) + 1
        return cats


# ═════════════════════════════════════════════════════════════════════════════
# 6. UNIFIED PATTERNS ENGINE — Entry Point
# ═════════════════════════════════════════════════════════════════════════════

class PatternsEngine:
    """
    Unified engine untuk MAGNATRIX design patterns library.
    Entry point: pattern catalog, examples, demonstrations.
    """

    def __init__(self) -> None:
        self.catalog = PatternCatalog()

    def demonstrate_singleton(self) -> Dict[str, Any]:
        db1 = DatabaseConnection()
        db2 = DatabaseConnection()
        return {
            "pattern": "singleton",
            "same_instance": db1 is db2,
            "instance_id": db1.id,
        }

    def demonstrate_factory(self) -> Dict[str, Any]:
        c1 = CreatorA()
        c2 = CreatorB()
        return {
            "pattern": "factory_method",
            "creator_a": c1.operation(),
            "creator_b": c2.operation(),
        }

    def demonstrate_builder(self) -> Dict[str, Any]:
        house = HouseBuilder().set_walls(4).set_doors(2).set_windows(6).set_roof("tile").add_garage().build()
        return {
            "pattern": "builder",
            "house": {"walls": house.walls, "doors": house.doors, "windows": house.windows,
                     "roof": house.roof, "garage": house.garage, "pool": house.pool},
        }

    def demonstrate_decorator(self) -> Dict[str, Any]:
        coffee = SugarDecorator(MilkDecorator(SimpleCoffee()))
        return {
            "pattern": "decorator",
            "description": coffee.description(),
            "cost": coffee.cost(),
        }

    def demonstrate_observer(self) -> Dict[str, Any]:
        subject = Subject()
        obs1 = ConcreteObserverA()
        obs2 = ConcreteObserverB()
        subject.attach(obs1)
        subject.attach(obs2)
        subject.set_state("Hello Observers")
        return {
            "pattern": "observer",
            "obs1_state": obs1.received_state,
            "obs2_count": obs2.count,
        }

    def demonstrate_strategy(self) -> Dict[str, Any]:
        ctx = Context(AddStrategy())
        r1 = ctx.execute(5, 3)
        ctx.set_strategy(MultiplyStrategy())
        r2 = ctx.execute(5, 3)
        return {
            "pattern": "strategy",
            "add_result": r1,
            "multiply_result": r2,
        }

    def demonstrate_pipeline(self) -> Dict[str, Any]:
        pipe = Pipeline([
            lambda x: x * 2,
            lambda x: x + 10,
            lambda x: f"result={x}",
        ])
        pipe.send(5)
        import time
        time.sleep(0.3)
        result = pipe.receive(timeout=1.0)
        return {
            "pattern": "pipeline",
            "input": 5,
            "output": result,
        }

    def demonstrate_worker_pool(self) -> Dict[str, Any]:
        pool = WorkerPool(num_workers=2)
        def work(n: int) -> int:
            time.sleep(0.05)
            return n * n
        results = pool.map(work, [1, 2, 3, 4, 5])
        pool.shutdown()
        return {
            "pattern": "worker_pool",
            "inputs": [1, 2, 3, 4, 5],
            "outputs": results,
        }

    def demonstrate_command(self) -> Dict[str, Any]:
        light = Light()
        remote = RemoteControl()
        remote.set_command("on", LightOnCommand(light))
        on_result = remote.press_button("on")
        undo_result = remote.press_undo()
        return {
            "pattern": "command",
            "on": on_result,
            "undo": undo_result,
            "light_state": light.is_on,
        }

    def demonstrate_chain_of_responsibility(self) -> Dict[str, Any]:
        monkey = MonkeyHandler()
        squirrel = SquirrelHandler()
        dog = DogHandler()
        monkey.set_next(squirrel).set_next(dog)
        return {
            "pattern": "chain_of_responsibility",
            "banana": monkey.handle("Banana"),
            "nut": monkey.handle("Nut"),
            "meatball": monkey.handle("MeatBall"),
            "coffee": monkey.handle("Coffee"),
        }

    def demonstrate_flyweight(self) -> Dict[str, Any]:
        factory = FlyweightFactory()
        f1 = factory.get_flyweight("shared_state_A")
        f2 = factory.get_flyweight("shared_state_A")
        f3 = factory.get_flyweight("shared_state_B")
        return {
            "pattern": "flyweight",
            "same_instance_for_A": f1 is f2,
            "total_flyweights": factory.count(),
            "operation": f1.operation("extrinsic_X"),
        }

    def demonstrate_memento(self) -> Dict[str, Any]:
        originator = Originator("State-1")
        caretaker = Caretaker(originator)
        caretaker.backup()
        originator.set_state("State-2")
        caretaker.backup()
        originator.set_state("State-3")
        undo1 = caretaker.undo()
        undo2 = caretaker.undo()
        return {
            "pattern": "memento",
            "undo1": undo1,
            "undo2": undo2,
            "current_state": originator.get_state(),
        }

    def run_all_demos(self) -> Dict[str, Any]:
        demos = {
            "singleton": self.demonstrate_singleton,
            "factory_method": self.demonstrate_factory,
            "builder": self.demonstrate_builder,
            "decorator": self.demonstrate_decorator,
            "observer": self.demonstrate_observer,
            "strategy": self.demonstrate_strategy,
            "pipeline": self.demonstrate_pipeline,
            "worker_pool": self.demonstrate_worker_pool,
            "command": self.demonstrate_command,
            "chain_of_responsibility": self.demonstrate_chain_of_responsibility,
            "flyweight": self.demonstrate_flyweight,
            "memento": self.demonstrate_memento,
        }
        results = {}
        for name, fn in demos.items():
            try:
                results[name] = fn()
            except Exception as e:
                results[name] = {"error": str(e)}
        return results

    def get_catalog(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.catalog.list_patterns(category)

    def get_stats(self) -> Dict[str, int]:
        return self.catalog.get_stats()


def main():
    print("═══════════════════════════════════════════════════════════════")
    print("  MAGNATRIX-OS — Go-Patterns Native Python Library")
    print("  AMATI-PELAJARI-TIRU dari tmrts/go-patterns")
    print("═══════════════════════════════════════════════════════════════")
    print()

    engine = PatternsEngine()

    # Catalog
    print("[1] Pattern Catalog:")
    stats = engine.get_stats()
    for cat, count in stats.items():
        print(f"  {cat.title()}: {count} patterns")
    print()

    # Run all demos
    print("[2] Running All Pattern Demos:")
    results = engine.run_all_demos()
    for name, result in results.items():
        status = "✓" if "error" not in result else "✗"
        print(f"  {status} {name}: {str(result)[:80]}...")
    print()

    # Functional Options demo
    print("[3] Functional Options Pattern:")
    server = NewServer([
        WithHost("0.0.0.0"),
        WithPort(8443),
        WithTimeout(60.0),
        WithTLS(True),
    ])
    print(f"  Host: {server.host}, Port: {server.port}, TLS: {server.tls_enabled}")
    print()

    # Object Pool demo
    print("[4] Object Pool Pattern:")
    pool = ObjectPool(lambda: {"id": hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}, max_size=5)
    obj1 = pool.acquire()
    obj2 = pool.acquire()
    pool.release(obj1)
    print(f"  Stats: {pool.stats()}")
    print()

    print("Done.")


if __name__ == "__main__":
    main()
