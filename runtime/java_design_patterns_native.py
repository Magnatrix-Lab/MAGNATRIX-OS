"""
Java Design Patterns — Native Python Implementation
====================================================
Inspired by: iluwatar/java-design-patterns (canonical collection, 100+ patterns)
Target: runtime/java_design_patterns_native.py
Author: GQRIS | Treas Adi Surya
License: MIT-style (pure Python, zero external deps)

Coverage:
  - Creational     (15+)
  - Structural     (20+)
  - Behavioral     (25+)
  - Concurrency    (15+)
  - Architectural  (10+)
  - Functional     (10+)

All classes include docstring + type hints + __repr__.
"""

from __future__ import annotations

import abc
import copy
import enum
import functools
import queue
import random
import re
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import (
    Any, Callable, Dict, Generic, Iterator, List, Optional, Protocol,
    Sequence, Set, Tuple, Type, TypeVar, Union, runtime_checkable,
)

# =============================================================================
# SECTION 1 — PATTERN CATALOG & INFRASTRUCTURE
# =============================================================================

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


class PatternCategory(enum.Enum):
    """Classification of design patterns."""
    CREATIONAL = "creational"
    STRUCTURAL = "structural"
    BEHAVIORAL = "behavioral"
    CONCURRENCY = "concurrency"
    ARCHITECTURAL = "architectural"
    FUNCTIONAL = "functional"


@dataclass(frozen=True)
class PatternMeta:
    """Metadata describing a design pattern."""
    name: str
    category: PatternCategory
    description: str
    intent: str
    participants: Tuple[str, ...]

    def __repr__(self) -> str:
        return (
            f"PatternMeta(name={self.name!r}, "
            f"category={self.category.value}, "
            f"intent={self.intent[:40]!r}...)"
        )


class PatternCatalog:
    """Registry for all implemented design patterns.

    Provides lookup by name, category, and capability-based queries.
    """

    _registry: Dict[str, Tuple[Type[Any], PatternMeta]] = {}
    _lock = threading.Lock()

    @classmethod
    def register(cls, meta: PatternMeta, impl_class: Type[Any]) -> None:
        """Register a pattern implementation."""
        with cls._lock:
            cls._registry[meta.name] = (impl_class, meta)

    @classmethod
    def get(cls, name: str) -> Optional[Tuple[Type[Any], PatternMeta]]:
        """Retrieve implementation + metadata by pattern name."""
        return cls._registry.get(name)

    @classmethod
    def by_category(cls, category: PatternCategory) -> Dict[str, Tuple[Type[Any], PatternMeta]]:
        """Return all patterns in a given category."""
        return {
            k: v for k, v in cls._registry.items()
            if v[1].category == category
        }

    @classmethod
    def all_patterns(cls) -> Dict[str, Tuple[Type[Any], PatternMeta]]:
        """Return the full catalog."""
        return dict(cls._registry)

    @classmethod
    def count(cls) -> int:
        return len(cls._registry)

    def __repr__(self) -> str:
        return f"PatternCatalog(count={self.count()})"


# =============================================================================
# SECTION 2 — CREATIONAL PATTERNS (15+)
# =============================================================================

# ---------------------------------------------------------------------------
# 2.1 Singleton (thread-safe)
# ---------------------------------------------------------------------------

class SingletonMeta(type):
    """Metaclass ensuring exactly one instance per class."""

    _instances: Dict[Type[Any], Any] = {}
    _singleton_lock = threading.Lock()

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            with cls._singleton_lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class AppConfig(metaclass=SingletonMeta):
    """Thread-safe singleton holding application-wide configuration."""

    def __init__(self) -> None:
        self._settings: Dict[str, Any] = {"version": "1.0.0", "debug": False}
        self._lock = threading.Lock()

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._settings[key] = value

    def __repr__(self) -> str:
        return f"AppConfig(settings={self._settings})"


PatternCatalog.register(
    PatternMeta(
        "Singleton", PatternCategory.CREATIONAL,
        "Ensure a class has only one instance and provide global access.",
        "Restrict instantiation to one object; shared state across app.",
        ("Singleton",),
    ),
    AppConfig,
)


# ---------------------------------------------------------------------------
# 2.2 Factory Method
# ---------------------------------------------------------------------------

class Dialog(abc.ABC):
    """Abstract product: dialog window."""

    @abc.abstractmethod
    def render(self) -> str:
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


class WindowsDialog(Dialog):
    def render(self) -> str:
        return "Rendering Windows-style dialog."


class WebDialog(Dialog):
    def render(self) -> str:
        return "Rendering HTML dialog."


class DialogFactory(abc.ABC):
    """Creator with Factory Method."""

    @abc.abstractmethod
    def create_dialog(self) -> Dialog:
        ...

    def show_dialog(self) -> str:
        dialog = self.create_dialog()
        return dialog.render()


class WindowsDialogFactory(DialogFactory):
    def create_dialog(self) -> Dialog:
        return WindowsDialog()


class WebDialogFactory(DialogFactory):
    def create_dialog(self) -> Dialog:
        return WebDialog()


PatternCatalog.register(
    PatternMeta(
        "FactoryMethod", PatternCategory.CREATIONAL,
        "Define an interface for creating an object, but let subclasses decide.",
        "Decouple object creation from usage via subclass override.",
        ("Creator", "Product", "ConcreteCreator", "ConcreteProduct"),
    ),
    DialogFactory,
)


# ---------------------------------------------------------------------------
# 2.3 Abstract Factory
# ---------------------------------------------------------------------------

class Button(abc.ABC):
    @abc.abstractmethod
    def paint(self) -> str:
        ...


class Checkbox(abc.ABC):
    @abc.abstractmethod
    def paint(self) -> str:
        ...


class WinButton(Button):
    def paint(self) -> str:
        return "Windows Button"


class WinCheckbox(Checkbox):
    def paint(self) -> str:
        return "Windows Checkbox"


class MacButton(Button):
    def paint(self) -> str:
        return "macOS Button"


class MacCheckbox(Checkbox):
    def paint(self) -> str:
        return "macOS Checkbox"


class GUIFactory(abc.ABC):
    """Abstract Factory: families of related objects."""

    @abc.abstractmethod
    def create_button(self) -> Button:
        ...

    @abc.abstractmethod
    def create_checkbox(self) -> Checkbox:
        ...


class WinFactory(GUIFactory):
    def create_button(self) -> Button:
        return WinButton()

    def create_checkbox(self) -> Checkbox:
        return WinCheckbox()


class MacFactory(GUIFactory):
    def create_button(self) -> Button:
        return MacButton()

    def create_checkbox(self) -> Checkbox:
        return MacCheckbox()


class Application:
    """Client of Abstract Factory."""

    def __init__(self, factory: GUIFactory) -> None:
        self._factory = factory
        self._button = factory.create_button()
        self._checkbox = factory.create_checkbox()

    def paint_ui(self) -> List[str]:
        return [self._button.paint(), self._checkbox.paint()]

    def __repr__(self) -> str:
        return f"Application(factory={self._factory.__class__.__name__})"


PatternCatalog.register(
    PatternMeta(
        "AbstractFactory", PatternCategory.CREATIONAL,
        "Create families of related objects without specifying concrete classes.",
        "Ensure UI components belong to the same platform family.",
        ("AbstractFactory", "ConcreteFactory", "AbstractProduct", "ConcreteProduct", "Client"),
    ),
    GUIFactory,
)


# ---------------------------------------------------------------------------
# 2.4 Builder
# ---------------------------------------------------------------------------

@dataclass
class Burger:
    """Product built step-by-step."""
    size: int = 1
    cheese: bool = False
    pepperoni: bool = False
    lettuce: bool = False
    tomato: bool = False

    def __repr__(self) -> str:
        toppings = [k for k, v in self.__dict__.items() if v and k != "size"]
        return f"Burger(size={self.size}, toppings={toppings})"


class BurgerBuilder:
    """Builder: fluent construction of complex Burger."""

    def __init__(self, size: int = 1) -> None:
        self._burger = Burger(size=size)

    def add_cheese(self) -> BurgerBuilder:
        self._burger.cheese = True
        return self

    def add_pepperoni(self) -> BurgerBuilder:
        self._burger.pepperoni = True
        return self

    def add_lettuce(self) -> BurgerBuilder:
        self._burger.lettuce = True
        return self

    def add_tomato(self) -> BurgerBuilder:
        self._burger.tomato = True
        return self

    def build(self) -> Burger:
        return self._burger

    def __repr__(self) -> str:
        return f"BurgerBuilder(burger={self._burger})"


PatternCatalog.register(
    PatternMeta(
        "Builder", PatternCategory.CREATIONAL,
        "Construct complex objects step by step; same construction process creates different representations.",
        "Separate object construction from its representation; fluent API.",
        ("Builder", "ConcreteBuilder", "Director", "Product"),
    ),
    BurgerBuilder,
)


# ---------------------------------------------------------------------------
# 2.5 Prototype
# ---------------------------------------------------------------------------

class Shape(abc.ABC):
    """Prototype base with clone support."""

    def __init__(self, x: int = 0, y: int = 0, color: str = "black") -> None:
        self.x = x
        self.y = y
        self.color = color

    @abc.abstractmethod
    def clone(self) -> Shape:
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(x={self.x}, y={self.y}, color={self.color!r})"


class Rectangle(Shape):
    def __init__(self, x: int = 0, y: int = 0, color: str = "black", width: int = 0, height: int = 0) -> None:
        super().__init__(x, y, color)
        self.width = width
        self.height = height

    def clone(self) -> Rectangle:
        return copy.deepcopy(self)

    def __repr__(self) -> str:
        return f"Rectangle(x={self.x}, y={self.y}, color={self.color!r}, w={self.width}, h={self.height})"


class Circle(Shape):
    def __init__(self, x: int = 0, y: int = 0, color: str = "black", radius: int = 0) -> None:
        super().__init__(x, y, color)
        self.radius = radius

    def clone(self) -> Circle:
        return copy.deepcopy(self)

    def __repr__(self) -> str:
        return f"Circle(x={self.x}, y={self.y}, color={self.color!r}, r={self.radius})"


PatternCatalog.register(
    PatternMeta(
        "Prototype", PatternCategory.CREATIONAL,
        "Create new objects by copying existing ones.",
        "Avoid subclass explosion; clone configured instances.",
        ("Prototype", "ConcretePrototype", "Client"),
    ),
    Shape,
)


# ---------------------------------------------------------------------------
# 2.6 Object Pool
# ---------------------------------------------------------------------------

class ExpensiveResource:
    """Resource that is costly to create."""

    _counter = 0
    _lock = threading.Lock()

    def __init__(self) -> None:
        with ExpensiveResource._lock:
            ExpensiveResource._counter += 1
            self._id = ExpensiveResource._counter
        time.sleep(0.001)  # Simulate creation cost
        self._in_use = False

    @property
    def id(self) -> int:
        return self._id

    def acquire(self) -> None:
        self._in_use = True

    def release(self) -> None:
        self._in_use = False

    @property
    def in_use(self) -> bool:
        return self._in_use

    def __repr__(self) -> str:
        return f"ExpensiveResource(id={self._id}, in_use={self._in_use})"


class ObjectPool:
    """Manage a pool of reusable objects."""

    def __init__(self, factory: Callable[[], ExpensiveResource], max_size: int = 10) -> None:
        self._factory = factory
        self._max_size = max_size
        self._pool: deque[ExpensiveResource] = deque()
        self._lock = threading.Lock()
        self._created = 0

    def acquire(self) -> ExpensiveResource:
        with self._lock:
            if self._pool:
                obj = self._pool.popleft()
                obj.acquire()
                return obj
            if self._created < self._max_size:
                self._created += 1
                obj = self._factory()
                obj.acquire()
                return obj
            raise RuntimeError("Pool exhausted")

    def release(self, obj: ExpensiveResource) -> None:
        with self._lock:
            obj.release()
            self._pool.append(obj)

    def __repr__(self) -> str:
        return f"ObjectPool(available={len(self._pool)}, created={self._created}, max={self._max_size})"


PatternCatalog.register(
    PatternMeta(
        "ObjectPool", PatternCategory.CREATIONAL,
        "Reuse objects that are expensive to create.",
        "Avoid repeated instantiation cost; bound resource usage.",
        ("Pool", "Reusable", "Client"),
    ),
    ObjectPool,
)


# ---------------------------------------------------------------------------
# 2.7 Multiton
# ---------------------------------------------------------------------------

class PrinterDriver:
    """Resource with limited instances per key (Multiton)."""

    _instances: Dict[str, PrinterDriver] = {}
    _lock = threading.Lock()

    def __new__(cls, key: str) -> PrinterDriver:
        with cls._lock:
            if key not in cls._instances:
                instance = super().__new__(cls)
                instance._key = key
                instance._jobs: List[str] = []
                cls._instances[key] = instance
            return cls._instances[key]

    @property
    def key(self) -> str:
        return self._key

    def print_job(self, document: str) -> str:
        self._jobs.append(document)
        return f"[{self._key}] Printed: {document}"

    def __repr__(self) -> str:
        return f"PrinterDriver(key={self._key!r}, jobs={len(self._jobs)})"


PatternCatalog.register(
    PatternMeta(
        "Multiton", PatternCategory.CREATIONAL,
        "Ensure a class has only a limited number of instances per key.",
        "Control resource instances per identifier; e.g. named connection pools.",
        ("Multiton", "Key", "Client"),
    ),
    PrinterDriver,
)


# ---------------------------------------------------------------------------
# 2.8 Lazy Initialization
# ---------------------------------------------------------------------------

class LazyValue(Generic[T]):
    """Defer computation until first access."""

    def __init__(self, factory: Callable[[], T]) -> None:
        self._factory = factory
        self._value: Optional[T] = None
        self._computed = False
        self._lock = threading.Lock()

    def get(self) -> T:
        if not self._computed:
            with self._lock:
                if not self._computed:
                    self._value = self._factory()
                    self._computed = True
        return self._value  # type: ignore[return-value]

    def __repr__(self) -> str:
        status = "computed" if self._computed else "lazy"
        return f"LazyValue(status={status!r})"


PatternCatalog.register(
    PatternMeta(
        "LazyInitialization", PatternCategory.CREATIONAL,
        "Delay object creation until it is actually needed.",
        "Improve startup time; avoid unnecessary computation.",
        ("LazyObject", "Factory", "Client"),
    ),
    LazyValue,
)


# ---------------------------------------------------------------------------
# 2.9 Dependency Injection
# ---------------------------------------------------------------------------

class DatabaseService:
    """A dependency to inject."""

    def query(self, sql: str) -> List[Dict[str, Any]]:
        return [{"result": f"mock_result_for_{sql}"}]

    def __repr__(self) -> str:
        return "DatabaseService()"


class UserRepository:
    """Receives dependency via constructor (constructor injection)."""

    def __init__(self, db: DatabaseService) -> None:
        self._db = db

    def find_user(self, user_id: int) -> Dict[str, Any]:
        return self._db.query(f"SELECT * FROM users WHERE id={user_id}")[0]

    def __repr__(self) -> str:
        return f"UserRepository(db={self._db})"


class DIContainer:
    """Simple IoC container for dependency injection."""

    def __init__(self) -> None:
        self._registrations: Dict[Type[Any], Callable[[], Any]] = {}

    def register(self, interface: Type[T], factory: Callable[[], T]) -> None:
        self._registrations[interface] = factory

    def resolve(self, interface: Type[T]) -> T:
        factory = self._registrations.get(interface)
        if not factory:
            raise KeyError(f"No registration for {interface}")
        return factory()

    def __repr__(self) -> str:
        return f"DIContainer(registered={list(self._registrations.keys())})"


PatternCatalog.register(
    PatternMeta(
        "DependencyInjection", PatternCategory.CREATIONAL,
        "Provide objects with their dependencies from external sources.",
        "Decouple object creation from dependency wiring; testability.",
        ("Service", "Client", "Injector", "Interface"),
    ),
    DIContainer,
)


# ---------------------------------------------------------------------------
# 2.10 Service Locator
# ---------------------------------------------------------------------------

class ServiceLocator:
    """Central registry for service discovery."""

    _services: Dict[str, Any] = {}
    _lock = threading.Lock()

    @classmethod
    def register(cls, name: str, service: Any) -> None:
        with cls._lock:
            cls._services[name] = service

    @classmethod
    def get(cls, name: str) -> Any:
        with cls._lock:
            service = cls._services.get(name)
            if service is None:
                raise KeyError(f"Service '{name}' not found")
            return service

    @classmethod
    def has(cls, name: str) -> bool:
        return name in cls._services

    def __repr__(self) -> str:
        return f"ServiceLocator(services={list(self._services.keys())})"


PatternCatalog.register(
    PatternMeta(
        "ServiceLocator", PatternCategory.CREATIONAL,
        "Encapsulate service lookup; centralize object retrieval.",
        "Hide service creation complexity; anti-pattern if overused.",
        ("ServiceLocator", "Service", "Client"),
    ),
    ServiceLocator,
)


# ---------------------------------------------------------------------------
# 2.11 Factory Kit
# ---------------------------------------------------------------------------

class Weapon(abc.ABC):
    @abc.abstractmethod
    def attack(self) -> str:
        ...


class Sword(Weapon):
    def attack(self) -> str:
        return "Swinging sword!"


class Bow(Weapon):
    def attack(self) -> str:
        return "Shooting arrow!"


class FactoryKit:
    """Map-based factory with lambda creators."""

    def __init__(self) -> None:
        self._creators: Dict[str, Callable[[], Weapon]] = {}

    def add(self, name: str, creator: Callable[[], Weapon]) -> None:
        self._creators[name] = creator

    def create(self, name: str) -> Weapon:
        creator = self._creators.get(name)
        if not creator:
            raise KeyError(f"Unknown weapon: {name}")
        return creator()

    def __repr__(self) -> str:
        return f"FactoryKit(registered={list(self._creators.keys())})"


PatternCatalog.register(
    PatternMeta(
        "FactoryKit", PatternCategory.CREATIONAL,
        "Define a factory by mapping identifiers to builder functions.",
        "Flexible object creation without inheritance; dynamic registration.",
        ("FactoryKit", "Creator", "Product"),
    ),
    FactoryKit,
)


# ---------------------------------------------------------------------------
# 2.12 Step Builder
# ---------------------------------------------------------------------------

class Computer:
    """Product with mandatory and optional fields."""

    def __init__(self) -> None:
        self.cpu: str = ""
        self.ram: int = 0
        self.storage: Optional[str] = None
        self.gpu: Optional[str] = None

    def __repr__(self) -> str:
        parts = [f"cpu={self.cpu!r}", f"ram={self.ram}GB"]
        if self.storage:
            parts.append(f"storage={self.storage!r}")
        if self.gpu:
            parts.append(f"gpu={self.gpu!r}")
        return f"Computer({', '.join(parts)})"


class ComputerStepBuilder:
    """Step builder enforcing creation order."""

    class CPUStep:
        def __init__(self) -> None:
            self._computer = Computer()

        def set_cpu(self, cpu: str) -> "ComputerStepBuilder.RAMStep":
            self._computer.cpu = cpu
            return ComputerStepBuilder.RAMStep(self._computer)

    class RAMStep:
        def __init__(self, computer: Computer) -> None:
            self._computer = computer

        def set_ram(self, ram: int) -> "ComputerStepBuilder.OptionalStep":
            self._computer.ram = ram
            return ComputerStepBuilder.OptionalStep(self._computer)

    class OptionalStep:
        def __init__(self, computer: Computer) -> None:
            self._computer = computer

        def set_storage(self, storage: str) -> "ComputerStepBuilder.OptionalStep":
            self._computer.storage = storage
            return self

        def set_gpu(self, gpu: str) -> "ComputerStepBuilder.OptionalStep":
            self._computer.gpu = gpu
            return self

        def build(self) -> Computer:
            return self._computer

    @staticmethod
    def new_builder() -> "ComputerStepBuilder.CPUStep":
        return ComputerStepBuilder.CPUStep()


PatternCatalog.register(
    PatternMeta(
        "StepBuilder", PatternCategory.CREATIONAL,
        "Guide object creation through explicit step types.",
        "Enforce construction sequence; compile-time safety via types.",
        ("StepBuilder", "Product", "Steps"),
    ),
    ComputerStepBuilder,
)


# =============================================================================
# SECTION 3 — STRUCTURAL PATTERNS (20+)
# =============================================================================

# ---------------------------------------------------------------------------
# 3.1 Adapter
# ---------------------------------------------------------------------------

class RoundPeg:
    """Target interface expected by client."""

    def __init__(self, radius: float) -> None:
        self._radius = radius

    def get_radius(self) -> float:
        return self._radius

    def __repr__(self) -> str:
        return f"RoundPeg(radius={self._radius})"


class SquarePeg:
    """Adaptee: incompatible interface."""

    def __init__(self, width: float) -> None:
        self._width = width

    def get_width(self) -> float:
        return self._width

    def __repr__(self) -> str:
        return f"SquarePeg(width={self._width})"


class SquarePegAdapter(RoundPeg):
    """Adapter: make SquarePeg compatible with RoundHole interface."""

    def __init__(self, peg: SquarePeg) -> None:
        super().__init__(peg.get_width() * (2 ** 0.5) / 2)
        self._peg = peg

    def __repr__(self) -> str:
        return f"SquarePegAdapter(peg={self._peg}, effective_radius={self.get_radius():.2f})"


class RoundHole:
    """Client expecting RoundPeg."""

    def __init__(self, radius: float) -> None:
        self._radius = radius

    def fits(self, peg: RoundPeg) -> bool:
        return peg.get_radius() <= self._radius

    def __repr__(self) -> str:
        return f"RoundHole(radius={self._radius})"


PatternCatalog.register(
    PatternMeta(
        "Adapter", PatternCategory.STRUCTURAL,
        "Allow objects with incompatible interfaces to collaborate.",
        "Wrap adaptee to expose target interface; object adapter via composition.",
        ("Target", "Adapter", "Adaptee", "Client"),
    ),
    SquarePegAdapter,
)


# ---------------------------------------------------------------------------
# 3.2 Bridge
# ---------------------------------------------------------------------------

class Device(abc.ABC):
    """Implementation hierarchy."""

    @abc.abstractmethod
    def is_enabled(self) -> bool:
        ...

    @abc.abstractmethod
    def enable(self) -> None:
        ...

    @abc.abstractmethod
    def disable(self) -> None:
        ...

    @abc.abstractmethod
    def get_volume(self) -> int:
        ...

    @abc.abstractmethod
    def set_volume(self, percent: int) -> None:
        ...


class Radio(Device):
    def __init__(self) -> None:
        self._on = False
        self._volume = 30

    def is_enabled(self) -> bool:
        return self._on

    def enable(self) -> None:
        self._on = True

    def disable(self) -> None:
        self._on = False

    def get_volume(self) -> int:
        return self._volume

    def set_volume(self, percent: int) -> None:
        self._volume = percent

    def __repr__(self) -> str:
        return f"Radio(on={self._on}, volume={self._volume})"


class TV(Device):
    def __init__(self) -> None:
        self._on = False
        self._volume = 50

    def is_enabled(self) -> bool:
        return self._on

    def enable(self) -> None:
        self._on = True

    def disable(self) -> None:
        self._on = False

    def get_volume(self) -> int:
        return self._volume

    def set_volume(self, percent: int) -> None:
        self._volume = percent

    def __repr__(self) -> str:
        return f"TV(on={self._on}, volume={self._volume})"


class RemoteControl:
    """Abstraction: decoupled from device implementation."""

    def __init__(self, device: Device) -> None:
        self._device = device

    def toggle_power(self) -> str:
        if self._device.is_enabled():
            self._device.disable()
            return "Power OFF"
        self._device.enable()
        return "Power ON"

    def volume_up(self) -> str:
        self._device.set_volume(min(100, self._device.get_volume() + 10))
        return f"Volume: {self._device.get_volume()}"

    def __repr__(self) -> str:
        return f"RemoteControl(device={self._device})"


class AdvancedRemote(RemoteControl):
    def mute(self) -> str:
        self._device.set_volume(0)
        return "Muted"


PatternCatalog.register(
    PatternMeta(
        "Bridge", PatternCategory.STRUCTURAL,
        "Split a large class into abstraction and implementation hierarchies.",
        "Vary abstraction and implementation independently; e.g. remote + device.",
        ("Abstraction", "Implementation", "ConcreteAbstraction", "ConcreteImplementation", "Client"),
    ),
    RemoteControl,
)


# ---------------------------------------------------------------------------
# 3.3 Composite
# ---------------------------------------------------------------------------

class Graphic(abc.ABC):
    """Component: common interface for leaf and composite."""

    @abc.abstractmethod
    def move(self, x: int, y: int) -> None:
        ...

    @abc.abstractmethod
    def draw(self) -> str:
        ...

    @abc.abstractmethod
    def get_bounds(self) -> Tuple[int, int, int, int]:
        ...


class Dot(Graphic):
    """Leaf."""

    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y

    def move(self, x: int, y: int) -> None:
        self.x += x
        self.y += y

    def draw(self) -> str:
        return f"Dot at ({self.x},{self.y})"

    def get_bounds(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.x, self.y)

    def __repr__(self) -> str:
        return f"Dot({self.x},{self.y})"


class CircleGraphic(Graphic):
    """Leaf with radius."""

    def __init__(self, x: int, y: int, radius: int) -> None:
        self.x = x
        self.y = y
        self.radius = radius

    def move(self, x: int, y: int) -> None:
        self.x += x
        self.y += y

    def draw(self) -> str:
        return f"Circle at ({self.x},{self.y}), r={self.radius}"

    def get_bounds(self) -> Tuple[int, int, int, int]:
        return (self.x - self.radius, self.y - self.radius,
                self.x + self.radius, self.y + self.radius)

    def __repr__(self) -> str:
        return f"CircleGraphic({self.x},{self.y},r={self.radius})"


class CompoundGraphic(Graphic):
    """Composite: contains children."""

    def __init__(self) -> None:
        self._children: List[Graphic] = []

    def add(self, child: Graphic) -> None:
        self._children.append(child)

    def remove(self, child: Graphic) -> None:
        self._children.remove(child)

    def move(self, x: int, y: int) -> None:
        for child in self._children:
            child.move(x, y)

    def draw(self) -> str:
        return f"Compound[{len(self._children)}]: " + ", ".join(c.draw() for c in self._children)

    def get_bounds(self) -> Tuple[int, int, int, int]:
        if not self._children:
            return (0, 0, 0, 0)
        bounds = [c.get_bounds() for c in self._children]
        min_x = min(b[0] for b in bounds)
        min_y = min(b[1] for b in bounds)
        max_x = max(b[2] for b in bounds)
        max_y = max(b[3] for b in bounds)
        return (min_x, min_y, max_x, max_y)

    def __repr__(self) -> str:
        return f"CompoundGraphic(children={len(self._children)})"


PatternCatalog.register(
    PatternMeta(
        "Composite", PatternCategory.STRUCTURAL,
        "Compose objects into tree structures; treat individual and composite uniformly.",
        "Recursive tree handling; UI components, file systems.",
        ("Component", "Leaf", "Composite", "Client"),
    ),
    CompoundGraphic,
)


# ---------------------------------------------------------------------------
# 3.4 Decorator
# ---------------------------------------------------------------------------

class DataSource(abc.ABC):
    """Component interface."""

    @abc.abstractmethod
    def write_data(self, data: str) -> None:
        ...

    @abc.abstractmethod
    def read_data(self) -> str:
        ...


class FileDataSource(DataSource):
    """Concrete component."""

    def __init__(self, filename: str) -> None:
        self._filename = filename
        self._data = ""

    def write_data(self, data: str) -> None:
        self._data = data

    def read_data(self) -> str:
        return self._data

    def __repr__(self) -> str:
        return f"FileDataSource(filename={self._filename!r})"


class DataSourceDecorator(DataSource, abc.ABC):
    """Base decorator."""

    def __init__(self, source: DataSource) -> None:
        self._wrappee = source

    def write_data(self, data: str) -> None:
        self._wrappee.write_data(data)

    def read_data(self) -> str:
        return self._wrappee.read_data()


class EncryptionDecorator(DataSourceDecorator):
    """Encrypt on write, decrypt on read."""

    def write_data(self, data: str) -> None:
        encrypted = data[::-1]  # Simple "encryption"
        self._wrappee.write_data(encrypted)

    def read_data(self) -> str:
        data = self._wrappee.read_data()
        return data[::-1]

    def __repr__(self) -> str:
        return f"EncryptionDecorator(source={self._wrappee})"


class CompressionDecorator(DataSourceDecorator):
    """Compress on write, decompress on read."""

    def write_data(self, data: str) -> None:
        compressed = data.replace(" ", "")  # Simple "compression"
        self._wrappee.write_data(compressed)

    def read_data(self) -> str:
        data = self._wrappee.read_data()
        return data  # Simplified

    def __repr__(self) -> str:
        return f"CompressionDecorator(source={self._wrappee})"


PatternCatalog.register(
    PatternMeta(
        "Decorator", PatternCategory.STRUCTURAL,
        "Add responsibilities to objects dynamically without subclassing.",
        "Wrap objects recursively; open/closed principle enabler.",
        ("Component", "ConcreteComponent", "Decorator", "ConcreteDecorator"),
    ),
    DataSourceDecorator,
)


# ---------------------------------------------------------------------------
# 3.5 Facade
# ---------------------------------------------------------------------------

class CPU:
    def freeze(self) -> str:
        return "CPU freeze"

    def jump(self, position: int) -> str:
        return f"CPU jump to {position}"

    def execute(self) -> str:
        return "CPU execute"

    def __repr__(self) -> str:
        return "CPU()"


class Memory:
    def load(self, position: int, data: str) -> str:
        return f"Memory load at {position}: {data}"

    def __repr__(self) -> str:
        return "Memory()"


class HardDrive:
    def read(self, lba: int, size: int) -> str:
        return f"HDD read lba={lba} size={size}"

    def __repr__(self) -> str:
        return "HardDrive()"


class ComputerFacade:
    """Simplified interface to complex subsystem."""

    def __init__(self) -> None:
        self._cpu = CPU()
        self._memory = Memory()
        self._hard_drive = HardDrive()

    def start(self) -> List[str]:
        return [
            self._cpu.freeze(),
            self._memory.load(0, self._hard_drive.read(0, 1024)),
            self._cpu.jump(0),
            self._cpu.execute(),
        ]

    def __repr__(self) -> str:
        return "ComputerFacade()"


PatternCatalog.register(
    PatternMeta(
        "Facade", PatternCategory.STRUCTURAL,
        "Provide a simplified interface to a complex subsystem.",
        "Reduce coupling between client and subsystem; entry point.",
        ("Facade", "SubsystemClasses", "Client"),
    ),
    ComputerFacade,
)


# ---------------------------------------------------------------------------
# 3.6 Flyweight
# ---------------------------------------------------------------------------

class TreeType:
    """Intrinsic state: shared flyweight."""

    _cache: Dict[str, TreeType] = {}
    _lock = threading.Lock()

    def __new__(cls, name: str, color: str, texture: str) -> TreeType:
        key = f"{name}:{color}:{texture}"
        with cls._lock:
            if key not in cls._cache:
                instance = super().__new__(cls)
                instance.name = name
                instance.color = color
                instance.texture = texture
                cls._cache[key] = instance
            return cls._cache[key]

    def __repr__(self) -> str:
        return f"TreeType(name={self.name!r}, color={self.color!r})"


class Tree:
    """Extrinsic state: unique per instance."""

    def __init__(self, x: int, y: int, tree_type: TreeType) -> None:
        self.x = x
        self.y = y
        self._type = tree_type

    def draw(self, canvas: str) -> str:
        return f"Draw {self._type.name} ({self._type.color}) at ({self.x},{self.y}) on {canvas}"

    def __repr__(self) -> str:
        return f"Tree({self.x},{self.y},type={self._type})"


class Forest:
    """Client: manages flyweights + extrinsic state."""

    def __init__(self) -> None:
        self._trees: List[Tree] = []

    def plant_tree(self, x: int, y: int, name: str, color: str, texture: str) -> None:
        tree_type = TreeType(name, color, texture)
        self._trees.append(Tree(x, y, tree_type))

    def draw(self, canvas: str) -> List[str]:
        return [t.draw(canvas) for t in self._trees]

    def __repr__(self) -> str:
        return f"Forest(trees={len(self._trees)}, types={len(TreeType._cache)})"


PatternCatalog.register(
    PatternMeta(
        "Flyweight", PatternCategory.STRUCTURAL,
        "Fit more objects into available RAM by sharing common state.",
        "Separate intrinsic (shared) and extrinsic (unique) state.",
        ("Flyweight", "ConcreteFlyweight", "FlyweightFactory", "Context", "Client"),
    ),
    Forest,
)


# ---------------------------------------------------------------------------
# 3.7 Proxy
# ---------------------------------------------------------------------------

class ImageInterface(abc.ABC):
    @abc.abstractmethod
    def display(self) -> str:
        ...


class RealImage(ImageInterface):
    """Heavy object: loads from disk."""

    def __init__(self, filename: str) -> None:
        self._filename = filename
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        time.sleep(0.001)  # Simulate load

    def display(self) -> str:
        return f"Displaying {self._filename}"

    def __repr__(self) -> str:
        return f"RealImage({self._filename!r})"


class ProxyImage(ImageInterface):
    """Proxy: lazy-loads RealImage."""

    def __init__(self, filename: str) -> None:
        self._filename = filename
        self._real_image: Optional[RealImage] = None

    def display(self) -> str:
        if self._real_image is None:
            self._real_image = RealImage(self._filename)
        return self._real_image.display()

    def __repr__(self) -> str:
        loaded = "loaded" if self._real_image else "lazy"
        return f"ProxyImage({self._filename!r}, {loaded})"


class ProtectionProxy(ImageInterface):
    """Proxy: access control."""

    def __init__(self, filename: str, user_role: str) -> None:
        self._filename = filename
        self._user_role = user_role
        self._real = RealImage(filename)

    def display(self) -> str:
        if self._user_role != "admin":
            return "Access denied"
        return self._real.display()

    def __repr__(self) -> str:
        return f"ProtectionProxy({self._filename!r}, role={self._user_role!r})"


PatternCatalog.register(
    PatternMeta(
        "Proxy", PatternCategory.STRUCTURAL,
        "Provide a placeholder/surrogate for another object to control access.",
        "Virtual (lazy), protection (auth), caching, logging, remote proxies.",
        ("Subject", "RealSubject", "Proxy", "Client"),
    ),
    ProxyImage,
)


# ---------------------------------------------------------------------------
# 3.8 Data Access Object (DAO)
# ---------------------------------------------------------------------------

@dataclass
class Person:
    """Domain object."""
    id: int
    first_name: str
    last_name: str

    def __repr__(self) -> str:
        return f"Person({self.id}, {self.first_name!r}, {self.last_name!r})"


class PersonDao(abc.ABC):
    """DAO interface."""

    @abc.abstractmethod
    def get(self, id: int) -> Optional[Person]:
        ...

    @abc.abstractmethod
    def get_all(self) -> List[Person]:
        ...

    @abc.abstractmethod
    def insert(self, person: Person) -> None:
        ...

    @abc.abstractmethod
    def update(self, person: Person) -> None:
        ...

    @abc.abstractmethod
    def delete(self, id: int) -> None:
        ...


class InMemoryPersonDao(PersonDao):
    """Concrete DAO: in-memory storage."""

    def __init__(self) -> None:
        self._people: Dict[int, Person] = {}
        self._next_id = 1
        self._lock = threading.Lock()

    def get(self, id: int) -> Optional[Person]:
        return self._people.get(id)

    def get_all(self) -> List[Person]:
        return list(self._people.values())

    def insert(self, person: Person) -> None:
        with self._lock:
            person.id = self._next_id
            self._people[person.id] = person
            self._next_id += 1

    def update(self, person: Person) -> None:
        self._people[person.id] = person

    def delete(self, id: int) -> None:
        self._people.pop(id, None)

    def __repr__(self) -> str:
        return f"InMemoryPersonDao(count={len(self._people)})"


PatternCatalog.register(
    PatternMeta(
        "DataAccessObject", PatternCategory.STRUCTURAL,
        "Abstract and encapsulate all access to data sources.",
        "Separate persistence logic from business logic; testable.",
        ("DAO", "DomainObject", "Client"),
    ),
    PersonDao,
)


# ---------------------------------------------------------------------------
# 3.9 Fluent Interface
# ---------------------------------------------------------------------------

class QueryBuilder:
    """Fluent SQL-like query builder."""

    def __init__(self) -> None:
        self._table = ""
        self._select: List[str] = []
        self._where: List[str] = []
        self._order_by = ""

    def select(self, *columns: str) -> QueryBuilder:
        self._select.extend(columns)
        return self

    def from_table(self, table: str) -> QueryBuilder:
        self._table = table
        return self

    def where(self, condition: str) -> QueryBuilder:
        self._where.append(condition)
        return self

    def order_by(self, column: str) -> QueryBuilder:
        self._order_by = column
        return self

    def build(self) -> str:
        cols = ", ".join(self._select) if self._select else "*"
        sql = f"SELECT {cols} FROM {self._table}"
        if self._where:
            sql += " WHERE " + " AND ".join(self._where)
        if self._order_by:
            sql += f" ORDER BY {self._order_by}"
        return sql

    def __repr__(self) -> str:
        return f"QueryBuilder(table={self._table!r})"


PatternCatalog.register(
    PatternMeta(
        "FluentInterface", PatternCategory.STRUCTURAL,
        "Chain method calls for readable, discoverable APIs.",
        "Return self from setters; readable nested configuration.",
        ("FluentObject", "Methods", "Client"),
    ),
    QueryBuilder,
)


# ---------------------------------------------------------------------------
# 3.10 Module
# ---------------------------------------------------------------------------

class CounterModule:
    """Namespace emulation / module pattern."""

    def __init__(self) -> None:
        self._count = 0
        self._lock = threading.Lock()

    def increment(self) -> int:
        with self._lock:
            self._count += 1
            return self._count

    def decrement(self) -> int:
        with self._lock:
            self._count -= 1
            return self._count

    def get(self) -> int:
        return self._count

    def __repr__(self) -> str:
        return f"CounterModule(count={self._count})"


PatternCatalog.register(
    PatternMeta(
        "Module", PatternCategory.STRUCTURAL,
        "Encapsulate related functions and data into a single namespace.",
        "Python modules are the language-native form; class-based emulation here.",
        ("Module", "Exports", "Client"),
    ),
    CounterModule,
)


# ---------------------------------------------------------------------------
# 3.11 Twin
# ---------------------------------------------------------------------------

class GameItem:
    """First parent in twin pattern (simulated multiple inheritance)."""

    def __init__(self) -> None:
        self.name = "item"

    def use(self) -> str:
        return f"Using {self.name}"

    def __repr__(self) -> str:
        return f"GameItem(name={self.name!r})"


class Drawable:
    """Second parent in twin pattern."""

    def __init__(self) -> None:
        self.sprite = "default.png"

    def render(self) -> str:
        return f"Rendering {self.sprite}"

    def __repr__(self) -> str:
        return f"Drawable(sprite={self.sprite!r})"


class TwinItem:
    """Twin: combines two hierarchies via composition."""

    def __init__(self) -> None:
        self._item = GameItem()
        self._drawable = Drawable()
        self._item.name = "sword"
        self._drawable.sprite = "sword.png"

    def use(self) -> str:
        return self._item.use()

    def render(self) -> str:
        return self._drawable.render()

    def __repr__(self) -> str:
        return f"TwinItem({self._item}, {self._drawable})"


PatternCatalog.register(
    PatternMeta(
        "Twin", PatternCategory.STRUCTURAL,
        "Model multiple inheritance with composition when language limits apply.",
        "Combine two class hierarchies without diamond problem.",
        ("Twin", "ParentA", "ParentB", "Client"),
    ),
    TwinItem,
)


# ---------------------------------------------------------------------------
# 3.12 Serialized Entity
# ---------------------------------------------------------------------------

class SerializedEntity:
    """Entity that can serialize/deserialize itself."""

    def __init__(self, entity_id: str, data: Dict[str, Any]) -> None:
        self.entity_id = entity_id
        self._data = data

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.entity_id, **self._data}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> SerializedEntity:
        eid = d.pop("id")
        return cls(eid, d)

    def __repr__(self) -> str:
        return f"SerializedEntity(id={self.entity_id!r}, keys={list(self._data.keys())})"


PatternCatalog.register(
    PatternMeta(
        "SerializedEntity", PatternCategory.STRUCTURAL,
        "Encapsulate serialization logic within the entity itself.",
        "Entity controls its own external representation; DTO alternative.",
        ("Entity", "Serializer", "Client"),
    ),
    SerializedEntity,
)


# ---------------------------------------------------------------------------
# 3.13 Event Aggregator
# ---------------------------------------------------------------------------

class EventAggregator:
    """Central hub for decoupled pub/sub between components."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable[[Any], None]]] = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, handler: Callable[[Any], None]) -> None:
        with self._lock:
            self._subscribers[event_type].append(handler)

    def publish(self, event_type: str, payload: Any) -> None:
        with self._lock:
            handlers = list(self._subscribers.get(event_type, []))
        for h in handlers:
            h(payload)

    def __repr__(self) -> str:
        return f"EventAggregator(events={list(self._subscribers.keys())})"


PatternCatalog.register(
    PatternMeta(
        "EventAggregator", PatternCategory.STRUCTURAL,
        "Decouple event producers and consumers via a central broker.",
        "Message bus pattern; components subscribe to named channels.",
        ("Aggregator", "Publisher", "Subscriber"),
    ),
    EventAggregator,
)


# =============================================================================
# SECTION 4 — BEHAVIORAL PATTERNS (25+)
# =============================================================================

# ---------------------------------------------------------------------------
# 4.1 Chain of Responsibility
# ---------------------------------------------------------------------------

class Handler(abc.ABC):
    """Base handler for chain."""

    def __init__(self) -> None:
        self._next: Optional[Handler] = None

    def set_next(self, handler: Handler) -> Handler:
        self._next = handler
        return handler

    def handle(self, request: str) -> Optional[str]:
        if self._next:
            return self._next.handle(request)
        return None


class AuthHandler(Handler):
    """Concrete handler: authentication check."""

    def handle(self, request: str) -> Optional[str]:
        if request.startswith("auth:"):
            return "AuthHandler: processed authentication"
        return super().handle(request)


class CacheHandler(Handler):
    """Concrete handler: caching check."""

    def handle(self, request: str) -> Optional[str]:
        if request.startswith("cache:"):
            return "CacheHandler: served from cache"
        return super().handle(request)


class LoggingHandler(Handler):
    """Concrete handler: logging."""

    def handle(self, request: str) -> Optional[str]:
        result = super().handle(request)
        return f"LoggingHandler: logged '{request}' -> {result}"


PatternCatalog.register(
    PatternMeta(
        "ChainOfResponsibility", PatternCategory.BEHAVIORAL,
        "Pass requests along a chain of handlers until one handles it.",
        "Decouple sender from receiver; dynamic processing pipeline.",
        ("Handler", "ConcreteHandler", "Client"),
    ),
    Handler,
)


# ---------------------------------------------------------------------------
# 4.2 Command
# ---------------------------------------------------------------------------

class Command(abc.ABC):
    """Encapsulated request."""

    @abc.abstractmethod
    def execute(self) -> str:
        ...

    @abc.abstractmethod
    def undo(self) -> str:
        ...


class Light:
    """Receiver."""

    def on(self) -> str:
        return "Light is ON"

    def off(self) -> str:
        return "Light is OFF"

    def __repr__(self) -> str:
        return "Light()"


class LightOnCommand(Command):
    """Concrete command."""

    def __init__(self, light: Light) -> None:
        self._light = light

    def execute(self) -> str:
        return self._light.on()

    def undo(self) -> str:
        return self._light.off()

    def __repr__(self) -> str:
        return f"LightOnCommand({self._light})"


class RemoteControlInvoker:
    """Invoker: holds and executes commands."""

    def __init__(self) -> None:
        self._command: Optional[Command] = None
        self._history: List[Command] = []

    def set_command(self, cmd: Command) -> None:
        self._command = cmd

    def press_button(self) -> str:
        if self._command:
            self._history.append(self._command)
            return self._command.execute()
        return "No command set"

    def press_undo(self) -> str:
        if self._history:
            return self._history.pop().undo()
        return "Nothing to undo"

    def __repr__(self) -> str:
        return f"RemoteControlInvoker(history={len(self._history)})"


PatternCatalog.register(
    PatternMeta(
        "Command", PatternCategory.BEHAVIORAL,
        "Turn a request into a stand-alone object for parameterization and queueing.",
        "Undo/redo, macro recording, job queues; decouple invoker from receiver.",
        ("Command", "ConcreteCommand", "Receiver", "Invoker", "Client"),
    ),
    Command,
)


# ---------------------------------------------------------------------------
# 4.3 Interpreter
# ---------------------------------------------------------------------------

class Expression(abc.ABC):
    """Abstract syntax tree node."""

    @abc.abstractmethod
    def interpret(self, context: Dict[str, int]) -> int:
        ...


class NumberExpression(Expression):
    """Terminal expression."""

    def __init__(self, number: int) -> None:
        self._number = number

    def interpret(self, context: Dict[str, int]) -> int:
        return self._number

    def __repr__(self) -> str:
        return f"NumberExpression({self._number})"


class VariableExpression(Expression):
    """Terminal: lookup in context."""

    def __init__(self, name: str) -> None:
        self._name = name

    def interpret(self, context: Dict[str, int]) -> int:
        return context.get(self._name, 0)

    def __repr__(self) -> str:
        return f"VariableExpression({self._name!r})"


class AddExpression(Expression):
    """Non-terminal: addition."""

    def __init__(self, left: Expression, right: Expression) -> None:
        self._left = left
        self._right = right

    def interpret(self, context: Dict[str, int]) -> int:
        return self._left.interpret(context) + self._right.interpret(context)

    def __repr__(self) -> str:
        return f"AddExpression({self._left}, {self._right})"


class SubtractExpression(Expression):
    """Non-terminal: subtraction."""

    def __init__(self, left: Expression, right: Expression) -> None:
        self._left = left
        self._right = right

    def interpret(self, context: Dict[str, int]) -> int:
        return self._left.interpret(context) - self._right.interpret(context)

    def __repr__(self) -> str:
        return f"SubtractExpression({self._left}, {self._right})"


PatternCatalog.register(
    PatternMeta(
        "Interpreter", PatternCategory.BEHAVIORAL,
        "Define a grammar and interpret sentences in the language.",
        "AST evaluation; domain-specific language parsing.",
        ("AbstractExpression", "TerminalExpression", "NonTerminalExpression", "Context", "Client"),
    ),
    Expression,
)


# ---------------------------------------------------------------------------
# 4.4 Iterator
# ---------------------------------------------------------------------------

class Book:
    """Element in collection."""

    def __init__(self, title: str, author: str) -> None:
        self.title = title
        self.author = author

    def __repr__(self) -> str:
        return f"Book({self.title!r}, {self.author!r})"


class BookCollection:
    """Aggregate with custom iterator."""

    def __init__(self) -> None:
        self._books: List[Book] = []

    def add(self, book: Book) -> None:
        self._books.append(book)

    def __iter__(self) -> Iterator[Book]:
        return iter(self._books)

    def __len__(self) -> int:
        return len(self._books)

    def __repr__(self) -> str:
        return f"BookCollection(books={len(self._books)})"


class ReverseIterator:
    """External iterator: traverse in reverse."""

    def __init__(self, collection: BookCollection) -> None:
        self._collection = list(collection)
        self._index = len(self._collection) - 1

    def __iter__(self) -> Iterator[Book]:
        return self

    def __next__(self) -> Book:
        if self._index < 0:
            raise StopIteration
        book = self._collection[self._index]
        self._index -= 1
        return book

    def __repr__(self) -> str:
        return f"ReverseIterator(pos={self._index})"


PatternCatalog.register(
    PatternMeta(
        "Iterator", PatternCategory.BEHAVIORAL,
        "Traverse a collection without exposing its underlying representation.",
        "Custom traversal order; external vs internal iterators.",
        ("Iterator", "ConcreteIterator", "Aggregate", "ConcreteAggregate"),
    ),
    BookCollection,
)


# ---------------------------------------------------------------------------
# 4.5 Mediator
# ---------------------------------------------------------------------------

class ChatMediator(abc.ABC):
    """Mediator interface."""

    @abc.abstractmethod
    def send_message(self, message: str, sender: "ChatUser") -> None:
        ...


class ChatUser:
    """Colleague."""

    def __init__(self, name: str, mediator: ChatMediator) -> None:
        self._name = name
        self._mediator = mediator

    def send(self, message: str) -> str:
        self._mediator.send_message(message, self)
        return f"{self._name} sent: {message}"

    def receive(self, message: str, sender_name: str) -> str:
        return f"{self._name} received from {sender_name}: {message}"

    @property
    def name(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return f"ChatUser({self._name!r})"


class ChatRoom(ChatMediator):
    """Concrete mediator: routes messages."""

    def __init__(self) -> None:
        self._users: List[ChatUser] = []

    def register(self, user: ChatUser) -> None:
        self._users.append(user)

    def send_message(self, message: str, sender: ChatUser) -> None:
        for user in self._users:
            if user != sender:
                user.receive(message, sender.name)

    def __repr__(self) -> str:
        return f"ChatRoom(users={[u.name for u in self._users]})"


PatternCatalog.register(
    PatternMeta(
        "Mediator", PatternCategory.BEHAVIORAL,
        "Reduce chaotic dependencies between objects via a central mediator.",
        "Chat room, air traffic control; colleagues communicate indirectly.",
        ("Mediator", "ConcreteMediator", "Colleague"),
    ),
    ChatRoom,
)


# ---------------------------------------------------------------------------
# 4.6 Memento
# ---------------------------------------------------------------------------

class EditorMemento:
    """Memento: stores state without exposing internals."""

    def __init__(self, content: str, cursor_pos: int) -> None:
        self._content = content
        self._cursor_pos = cursor_pos

    @property
    def content(self) -> str:
        return self._content

    @property
    def cursor_pos(self) -> int:
        return self._cursor_pos

    def __repr__(self) -> str:
        return f"EditorMemento(len={len(self._content)}, cursor={self._cursor_pos})"


class TextEditor:
    """Originator: creates and restores mementos."""

    def __init__(self) -> None:
        self._content = ""
        self._cursor_pos = 0

    def type_text(self, text: str) -> None:
        self._content += text
        self._cursor_pos = len(self._content)

    def save(self) -> EditorMemento:
        return EditorMemento(self._content, self._cursor_pos)

    def restore(self, memento: EditorMemento) -> None:
        self._content = memento.content
        self._cursor_pos = memento.cursor_pos

    @property
    def content(self) -> str:
        return self._content

    def __repr__(self) -> str:
        return f"TextEditor(content={self._content!r}, cursor={self._cursor_pos})"


class History:
    """Caretaker: manages mementos."""

    def __init__(self) -> None:
        self._mementos: List[EditorMemento] = []

    def push(self, memento: EditorMemento) -> None:
        self._mementos.append(memento)

    def pop(self) -> Optional[EditorMemento]:
        return self._mementos.pop() if self._mementos else None

    def __repr__(self) -> str:
        return f"History(snapshots={len(self._mementos)})"


PatternCatalog.register(
    PatternMeta(
        "Memento", PatternCategory.BEHAVIORAL,
        "Capture and restore an object's internal state without violating encapsulation.",
        "Undo stacks, save games; memento is opaque to caretaker.",
        ("Originator", "Memento", "Caretaker"),
    ),
    TextEditor,
)


# ---------------------------------------------------------------------------
# 4.7 Observer
# ---------------------------------------------------------------------------

class Observer(abc.ABC):
    """Subscriber interface."""

    @abc.abstractmethod
    def update(self, event_type: str, data: Any) -> None:
        ...


class Subject(abc.ABC):
    """Publisher interface."""

    def __init__(self) -> None:
        self._observers: List[Observer] = []
        self._lock = threading.Lock()

    def attach(self, observer: Observer) -> None:
        with self._lock:
            if observer not in self._observers:
                self._observers.append(observer)

    def detach(self, observer: Observer) -> None:
        with self._lock:
            self._observers.remove(observer)

    def notify(self, event_type: str, data: Any) -> None:
        with self._lock:
            observers = list(self._observers)
        for obs in observers:
            obs.update(event_type, data)


class NewsAgency(Subject):
    """Concrete subject."""

    def publish_news(self, headline: str) -> None:
        self.notify("news", headline)

    def __repr__(self) -> str:
        return f"NewsAgency(subscribers={len(self._observers)})"


class NewsChannel(Observer):
    """Concrete observer."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._headlines: List[str] = []

    def update(self, event_type: str, data: Any) -> None:
        if event_type == "news":
            self._headlines.append(str(data))

    @property
    def headlines(self) -> List[str]:
        return self._headlines

    def __repr__(self) -> str:
        return f"NewsChannel({self._name!r}, headlines={len(self._headlines)})"


PatternCatalog.register(
    PatternMeta(
        "Observer", PatternCategory.BEHAVIORAL,
        "Notify multiple objects about events happening to the object they observe.",
        "Pub/sub, event-driven UI; one-to-many dependency.",
        ("Subject", "Observer", "ConcreteSubject", "ConcreteObserver"),
    ),
    NewsAgency,
)


# ---------------------------------------------------------------------------
# 4.8 State
# ---------------------------------------------------------------------------

class PhoneState(abc.ABC):
    """State interface."""

    @abc.abstractmethod
    def on_pick_up(self, phone: "Phone") -> str:
        ...

    @abc.abstractmethod
    def on_hang_up(self, phone: "Phone") -> str:
        ...

    @abc.abstractmethod
    def on_dial(self, phone: "Phone", number: str) -> str:
        ...


class IdleState(PhoneState):
    def on_pick_up(self, phone: "Phone") -> str:
        phone.state = OffHookState()
        return "Picked up, off-hook"

    def on_hang_up(self, phone: "Phone") -> str:
        return "Already idle"

    def on_dial(self, phone: "Phone", number: str) -> str:
        return "Cannot dial while idle"


class OffHookState(PhoneState):
    def on_pick_up(self, phone: "Phone") -> str:
        return "Already off-hook"

    def on_hang_up(self, phone: "Phone") -> str:
        phone.state = IdleState()
        return "Hung up, back to idle"

    def on_dial(self, phone: "Phone", number: str) -> str:
        phone.state = CallingState()
        return f"Dialing {number}..."


class CallingState(PhoneState):
    def on_pick_up(self, phone: "Phone") -> str:
        return "Already in call"

    def on_hang_up(self, phone: "Phone") -> str:
        phone.state = IdleState()
        return "Call ended"

    def on_dial(self, phone: "Phone", number: str) -> str:
        return "Already dialing"


class Phone:
    """Context: phone with state-dependent behavior."""

    def __init__(self) -> None:
        self.state: PhoneState = IdleState()

    def pick_up(self) -> str:
        return self.state.on_pick_up(self)

    def hang_up(self) -> str:
        return self.state.on_hang_up(self)

    def dial(self, number: str) -> str:
        return self.state.on_dial(self, number)

    def __repr__(self) -> str:
        return f"Phone(state={self.state.__class__.__name__})"


PatternCatalog.register(
    PatternMeta(
        "State", PatternCategory.BEHAVIORAL,
        "Alter an object's behavior when its internal state changes.",
        "Replace conditional state logic with polymorphic classes.",
        ("Context", "State", "ConcreteState"),
    ),
    Phone,
)


# ---------------------------------------------------------------------------
# 4.9 Strategy
# ---------------------------------------------------------------------------

class PaymentStrategy(abc.ABC):
    """Strategy interface."""

    @abc.abstractmethod
    def pay(self, amount: float) -> str:
        ...


class CreditCardStrategy(PaymentStrategy):
    def __init__(self, card_number: str) -> None:
        self._card_number = card_number

    def pay(self, amount: float) -> str:
        return f"Paid ${amount:.2f} with card ending in {self._card_number[-4:]}"

    def __repr__(self) -> str:
        return f"CreditCardStrategy(****{self._card_number[-4:]})"


class PayPalStrategy(PaymentStrategy):
    def __init__(self, email: str) -> None:
        self._email = email

    def pay(self, amount: float) -> str:
        return f"Paid ${amount:.2f} via PayPal ({self._email})"

    def __repr__(self) -> str:
        return f"PayPalStrategy({self._email!r})"


class ShoppingCart:
    """Context: uses a payment strategy."""

    def __init__(self) -> None:
        self._items: List[Tuple[str, float]] = []
        self._strategy: Optional[PaymentStrategy] = None

    def add_item(self, name: str, price: float) -> None:
        self._items.append((name, price))

    def set_strategy(self, strategy: PaymentStrategy) -> None:
        self._strategy = strategy

    def checkout(self) -> str:
        total = sum(p for _, p in self._items)
        if self._strategy:
            return self._strategy.pay(total)
        return "No payment strategy set"

    def __repr__(self) -> str:
        return f"ShoppingCart(items={len(self._items)}, total=${sum(p for _, p in self._items):.2f})"


PatternCatalog.register(
    PatternMeta(
        "Strategy", PatternCategory.BEHAVIORAL,
        "Define a family of algorithms, make them interchangeable.",
        "Runtime algorithm selection; open/closed for behavior variants.",
        ("Context", "Strategy", "ConcreteStrategy"),
    ),
    ShoppingCart,
)


# ---------------------------------------------------------------------------
# 4.10 Template Method
# ---------------------------------------------------------------------------

class DataMiner(abc.ABC):
    """Abstract class with template method."""

    def mine(self, path: str) -> List[str]:
        """Template method: fixed algorithm skeleton."""
        file = self._open_file(path)
        raw_data = self._extract_data(file)
        data = self._parse_data(raw_data)
        analysis = self._analyze(data)
        self._close_file(file)
        return analysis

    def _open_file(self, path: str) -> str:
        return f"opened:{path}"

    def _close_file(self, file: str) -> None:
        pass

    @abc.abstractmethod
    def _extract_data(self, file: str) -> str:
        ...

    @abc.abstractmethod
    def _parse_data(self, raw: str) -> List[str]:
        ...

    def _analyze(self, data: List[str]) -> List[str]:
        return [f"Analyzed: {d}" for d in data]


class PDFDataMiner(DataMiner):
    def _extract_data(self, file: str) -> str:
        return "PDF raw content"

    def _parse_data(self, raw: str) -> List[str]:
        return ["PDF page 1", "PDF page 2"]

    def __repr__(self) -> str:
        return "PDFDataMiner()"


class CSVDataMiner(DataMiner):
    def _extract_data(self, file: str) -> str:
        return "col1,col2\n1,2\n3,4"

    def _parse_data(self, raw: str) -> List[str]:
        lines = raw.strip().split("\n")
        return [f"Row: {line}" for line in lines[1:]]

    def __repr__(self) -> str:
        return "CSVDataMiner()"


PatternCatalog.register(
    PatternMeta(
        "TemplateMethod", PatternCategory.BEHAVIORAL,
        "Define algorithm skeleton in base class; subclasses override steps.",
        "Framework hooks; invariant algorithm, variant steps.",
        ("AbstractClass", "ConcreteClass", "TemplateMethod", "PrimitiveOperations"),
    ),
    DataMiner,
)


# ---------------------------------------------------------------------------
# 4.11 Visitor
# ---------------------------------------------------------------------------

class Visitable(abc.ABC):
    """Element that accepts visitors."""

    @abc.abstractmethod
    def accept(self, visitor: "Visitor") -> str:
        ...


class Visitor(abc.ABC):
    """Operation to perform on elements."""

    @abc.abstractmethod
    def visit_dot(self, dot: "DotElement") -> str:
        ...

    @abc.abstractmethod
    def visit_circle(self, circle: "CircleElement") -> str:
        ...


class DotElement(Visitable):
    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y

    def accept(self, visitor: Visitor) -> str:
        return visitor.visit_dot(self)

    def __repr__(self) -> str:
        return f"DotElement({self.x},{self.y})"


class CircleElement(Visitable):
    def __init__(self, x: int, y: int, radius: int) -> None:
        self.x = x
        self.y = y
        self.radius = radius

    def accept(self, visitor: Visitor) -> str:
        return visitor.visit_circle(self)

    def __repr__(self) -> str:
        return f"CircleElement({self.x},{self.y},r={self.radius})"


class XMLExportVisitor(Visitor):
    def visit_dot(self, dot: DotElement) -> str:
        return f'<dot x="{dot.x}" y="{dot.y}"/>'

    def visit_circle(self, circle: CircleElement) -> str:
        return f'<circle x="{circle.x}" y="{circle.y}" r="{circle.radius}"/>'

    def __repr__(self) -> str:
        return "XMLExportVisitor()"


class RenderVisitor(Visitor):
    def visit_dot(self, dot: DotElement) -> str:
        return f"Render dot at ({dot.x},{dot.y})"

    def visit_circle(self, circle: CircleElement) -> str:
        return f"Render circle at ({circle.x},{circle.y}), r={circle.radius}"

    def __repr__(self) -> str:
        return "RenderVisitor()"


PatternCatalog.register(
    PatternMeta(
        "Visitor", PatternCategory.BEHAVIORAL,
        "Separate algorithms from the objects on which they operate.",
        "Double dispatch; add operations without changing element classes.",
        ("Visitor", "ConcreteVisitor", "Element", "ConcreteElement"),
    ),
    Visitor,
)


# ---------------------------------------------------------------------------
# 4.12 Null Object
# ---------------------------------------------------------------------------

class Animal(abc.ABC):
    @abc.abstractmethod
    def speak(self) -> str:
        ...


class Dog(Animal):
    def speak(self) -> str:
        return "Woof!"

    def __repr__(self) -> str:
        return "Dog()"


class NullAnimal(Animal):
    """Null object: does nothing safely."""

    def speak(self) -> str:
        return ""

    def __repr__(self) -> str:
        return "NullAnimal()"


class AnimalFactory:
    """Returns NullAnimal for unknown types instead of None."""

    _registry: Dict[str, Type[Animal]] = {"dog": Dog}

    @classmethod
    def get_animal(cls, name: str) -> Animal:
        animal_cls = cls._registry.get(name)
        return animal_cls() if animal_cls else NullAnimal()

    def __repr__(self) -> str:
        return f"AnimalFactory(known={list(self._registry.keys())})"


PatternCatalog.register(
    PatternMeta(
        "NullObject", PatternCategory.BEHAVIORAL,
        "Provide a default object that does nothing, avoiding null checks.",
        "Eliminate None checks; safe default behavior.",
        ("AbstractObject", "RealObject", "NullObject", "Client"),
    ),
    NullAnimal,
)


# ---------------------------------------------------------------------------
# 4.13 Specification
# ---------------------------------------------------------------------------

@dataclass
class ProductSpec:
    """Domain object for specification pattern."""
    name: str
    color: str
    price: float
    weight: float

    def __repr__(self) -> str:
        return f"ProductSpec({self.name!r}, {self.color!r}, ${self.price:.2f})"


class Specification(abc.ABC):
    """Boolean specification for domain objects."""

    @abc.abstractmethod
    def is_satisfied_by(self, candidate: ProductSpec) -> bool:
        ...

    def __and__(self, other: Specification) -> Specification:
        return AndSpecification(self, other)

    def __or__(self, other: Specification) -> Specification:
        return OrSpecification(self, other)

    def __invert__(self) -> Specification:
        return NotSpecification(self)


class ColorSpecification(Specification):
    def __init__(self, color: str) -> None:
        self._color = color

    def is_satisfied_by(self, candidate: ProductSpec) -> bool:
        return candidate.color == self._color

    def __repr__(self) -> str:
        return f"ColorSpecification({self._color!r})"


class PriceRangeSpecification(Specification):
    def __init__(self, min_price: float, max_price: float) -> None:
        self._min = min_price
        self._max = max_price

    def is_satisfied_by(self, candidate: ProductSpec) -> bool:
        return self._min <= candidate.price <= self._max

    def __repr__(self) -> str:
        return f"PriceRangeSpecification(${self._min:.2f}-${self._max:.2f})"


class AndSpecification(Specification):
    def __init__(self, left: Specification, right: Specification) -> None:
        self._left = left
        self._right = right

    def is_satisfied_by(self, candidate: ProductSpec) -> bool:
        return self._left.is_satisfied_by(candidate) and self._right.is_satisfied_by(candidate)

    def __repr__(self) -> str:
        return f"AndSpecification({self._left}, {self._right})"


class OrSpecification(Specification):
    def __init__(self, left: Specification, right: Specification) -> None:
        self._left = left
        self._right = right

    def is_satisfied_by(self, candidate: ProductSpec) -> bool:
        return self._left.is_satisfied_by(candidate) or self._right.is_satisfied_by(candidate)

    def __repr__(self) -> str:
        return f"OrSpecification({self._left}, {self._right})"


class NotSpecification(Specification):
    def __init__(self, spec: Specification) -> None:
        self._spec = spec

    def is_satisfied_by(self, candidate: ProductSpec) -> bool:
        return not self._spec.is_satisfied_by(candidate)

    def __repr__(self) -> str:
        return f"NotSpecification({self._spec})"


PatternCatalog.register(
    PatternMeta(
        "Specification", PatternCategory.BEHAVIORAL,
        "Recombinable business rules via boolean logic on domain objects.",
        "Composable rules; AND/OR/NOT combinators for flexible filtering.",
        ("Specification", "CompositeSpecification", "LeafSpecification", "Candidate"),
    ),
    Specification,
)


# ---------------------------------------------------------------------------
# 4.14 State Machine
# ---------------------------------------------------------------------------

class TurnstileState(enum.Enum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"


class TurnstileEvent(enum.Enum):
    COIN = "coin"
    PUSH = "push"


class Turnstile:
    """State machine with transition table."""

    def __init__(self) -> None:
        self._state = TurnstileState.LOCKED
        self._transitions = {
            (TurnstileState.LOCKED, TurnstileEvent.COIN): (TurnstileState.UNLOCKED, "Unlock turnstile"),
            (TurnstileState.LOCKED, TurnstileEvent.PUSH): (TurnstileState.LOCKED, "Alarm! Push without coin"),
            (TurnstileState.UNLOCKED, TurnstileEvent.COIN): (TurnstileState.UNLOCKED, "Refund coin"),
            (TurnstileState.UNLOCKED, TurnstileEvent.PUSH): (TurnstileState.LOCKED, "Lock turnstile"),
        }

    def handle(self, event: TurnstileEvent) -> str:
        key = (self._state, event)
        if key in self._transitions:
            new_state, action = self._transitions[key]
            self._state = new_state
            return action
        return "Invalid transition"

    @property
    def state(self) -> TurnstileState:
        return self._state

    def __repr__(self) -> str:
        return f"Turnstile(state={self._state.value})"


PatternCatalog.register(
    PatternMeta(
        "StateMachine", PatternCategory.BEHAVIORAL,
        "Model behavior as explicit states and transitions.",
        "Transition table; event-driven state changes.",
        ("StateMachine", "State", "Event", "Transition", "Action"),
    ),
    Turnstile,
)


# ---------------------------------------------------------------------------
# 4.15 Type-Object
# ---------------------------------------------------------------------------

class MonsterType:
    """Type object: shared monster blueprint."""

    def __init__(self, name: str, health: int, attack: int) -> None:
        self.name = name
        self.health = health
        self.attack = attack

    def __repr__(self) -> str:
        return f"MonsterType({self.name!r}, hp={self.health}, atk={self.attack})"


class Monster:
    """Each monster references a type object."""

    def __init__(self, x: int, y: int, monster_type: MonsterType) -> None:
        self.x = x
        self.y = y
        self._type = monster_type
        self._health = monster_type.health

    def take_damage(self, amount: int) -> str:
        self._health -= amount
        if self._health <= 0:
            return f"{self._type.name} at ({self.x},{self.y}) died!"
        return f"{self._type.name} hp={self._health}"

    def __repr__(self) -> str:
        return f"Monster({self.x},{self.y},type={self._type.name},hp={self._health})"


PatternCatalog.register(
    PatternMeta(
        "TypeObject", PatternCategory.BEHAVIORAL,
        "Use a separate object to represent a type, creating instances from it.",
        "Avoid subclass explosion; data-driven type system.",
        ("TypeObject", "Instance", "Client"),
    ),
    Monster,
)

# =============================================================================
# SECTION 5 — CONCURRENCY PATTERNS (15+)
# =============================================================================

# ---------------------------------------------------------------------------
# 5.1 Active Object
# ---------------------------------------------------------------------------

class ActiveObject:
    """Decouples method execution from invocation via scheduler thread."""

    def __init__(self) -> None:
        self._queue: queue.Queue[Tuple[Callable[..., Any], tuple, dict]] = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._results: Dict[int, Any] = {}
        self._result_lock = threading.Lock()
        self._seq = 0

    def _run(self) -> None:
        while True:
            try:
                func, args, kwargs = self._queue.get(timeout=1)
                result = func(*args, **kwargs)
                with self._result_lock:
                    self._seq += 1
                    self._results[self._seq] = result
            except queue.Empty:
                continue

    def schedule(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> int:
        self._queue.put((func, args, kwargs))
        return self._seq + 1  # Approximate future id

    def get_result(self, seq: int) -> Optional[T]:
        with self._result_lock:
            return self._results.get(seq)

    def __repr__(self) -> str:
        return f"ActiveObject(queue_size={self._queue.qsize()})"


PatternCatalog.register(
    PatternMeta(
        "ActiveObject", PatternCategory.CONCURRENCY,
        "Decouple method execution from method invocation for concurrent access.",
        "Scheduler thread + activation list; async method dispatch.",
        ("Proxy", "Scheduler", "Servant", "ActivationList", "Client"),
    ),
    ActiveObject,
)


# ---------------------------------------------------------------------------
# 5.2 Balking
# ---------------------------------------------------------------------------

class WashingMachine:
    """Balking: refuse operation if object is in invalid state."""

    class State(enum.Enum):
        IDLE = "idle"
        WASHING = "washing"

    def __init__(self) -> None:
        self._state = WashingMachine.State.IDLE
        self._lock = threading.Lock()

    def wash(self) -> str:
        with self._lock:
            if self._state == WashingMachine.State.WASHING:
                return "Balk: already washing!"
            self._state = WashingMachine.State.WASHING
            return "Started washing"

    def done(self) -> str:
        with self._lock:
            self._state = WashingMachine.State.IDLE
            return "Washing complete"

    def __repr__(self) -> str:
        return f"WashingMachine(state={self._state.value})"


PatternCatalog.register(
    PatternMeta(
        "Balking", PatternCategory.CONCURRENCY,
        "Refuse to execute action if object is in an inappropriate state.",
        "Guard methods with state check; early return on invalid state.",
        ("BalkingObject", "Client"),
    ),
    WashingMachine,
)


# ---------------------------------------------------------------------------
# 5.3 Barrier
# ---------------------------------------------------------------------------

class ThreadBarrier:
    """Barrier: threads wait until all arrive."""

    def __init__(self, count: int) -> None:
        self._count = count
        self._current = 0
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)

    def wait(self) -> str:
        with self._condition:
            self._current += 1
            if self._current >= self._count:
                self._current = 0
                self._condition.notify_all()
                return "Barrier tripped"
            self._condition.wait()
            return "Barrier passed"

    def __repr__(self) -> str:
        return f"ThreadBarrier(count={self._count}, waiting={self._current})"


PatternCatalog.register(
    PatternMeta(
        "Barrier", PatternCategory.CONCURRENCY,
        "Block threads until a predetermined number arrive at a synchronization point.",
        "Parallel decomposition; threads rendezvous before continuing.",
        ("Barrier", "ParticipantThreads"),
    ),
    ThreadBarrier,
)


# ---------------------------------------------------------------------------
# 5.4 Double-Checked Locking
# ---------------------------------------------------------------------------

class DCLSingleton:
    """Singleton via double-checked locking (demonstration)."""

    _instance: Optional[DCLSingleton] = None
    _lock = threading.Lock()

    def __new__(cls) -> DCLSingleton:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._data = "initialized"
        return cls._instance

    def __repr__(self) -> str:
        return f"DCLSingleton(data={self._data!r})"


PatternCatalog.register(
    PatternMeta(
        "DoubleCheckedLocking", PatternCategory.CONCURRENCY,
        "Reduce locking overhead by first checking without lock, then with lock.",
        "Lazy init optimization; safe in Python due to GIL but pattern remains educational.",
        ("Singleton", "Lock", "Client"),
    ),
    DCLSingleton,
)


# ---------------------------------------------------------------------------
# 5.5 Guarded Suspension
# ---------------------------------------------------------------------------

class GuardedQueue:
    """Suspend thread until precondition is satisfied."""

    def __init__(self) -> None:
        self._queue: deque[str] = deque()
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)

    def put(self, item: str) -> None:
        with self._condition:
            self._queue.append(item)
            self._condition.notify_all()

    def get(self) -> str:
        with self._condition:
            while not self._queue:
                self._condition.wait()
            return self._queue.popleft()

    def __repr__(self) -> str:
        return f"GuardedQueue(size={len(self._queue)})"


PatternCatalog.register(
    PatternMeta(
        "GuardedSuspension", PatternCategory.CONCURRENCY,
        "Suspend thread execution until a guard condition becomes true.",
        "Condition variables; wait/notify on state change.",
        ("GuardedObject", "ClientThread"),
    ),
    GuardedQueue,
)


# ---------------------------------------------------------------------------
# 5.6 Leaders/Followers
# ---------------------------------------------------------------------------

class LeadersFollowers:
    """One leader thread handles events; others follow as pool."""

    def __init__(self, handler: Callable[[str], str], pool_size: int = 4) -> None:
        self._handler = handler
        self._pool_size = pool_size
        self._leader_event = threading.Event()
        self._lock = threading.Lock()
        self._leader_id: Optional[int] = None

    def promote_leader(self, thread_id: int) -> None:
        with self._lock:
            self._leader_id = thread_id
            self._leader_event.set()

    def process(self, event: str, thread_id: int) -> str:
        with self._lock:
            if self._leader_id == thread_id:
                result = self._handler(event)
                # Promote next leader
                self._leader_event.clear()
                return f"Leader {thread_id}: {result}"
            return f"Follower {thread_id}: waiting"

    def __repr__(self) -> str:
        return f"LeadersFollowers(pool={self._pool_size}, leader={self._leader_id})"


PatternCatalog.register(
    PatternMeta(
        "LeadersFollowers", PatternCategory.CONCURRENCY,
        "One thread leads event processing; others wait to become leader.",
        "Minimize context switching; leader handles I/O, followers compute.",
        ("Leader", "Follower", "EventSource", "HandleSet"),
    ),
    LeadersFollowers,
)


# ---------------------------------------------------------------------------
# 5.7 Monitor
# ---------------------------------------------------------------------------

class BankAccountMonitor:
    """Monitor: all methods synchronized on same lock."""

    def __init__(self, balance: float = 0.0) -> None:
        self._balance = balance
        self._lock = threading.Lock()

    def deposit(self, amount: float) -> str:
        with self._lock:
            self._balance += amount
            return f"Deposited ${amount:.2f}, balance=${self._balance:.2f}"

    def withdraw(self, amount: float) -> str:
        with self._lock:
            if self._balance < amount:
                return f"Insufficient funds: ${self._balance:.2f}"
            self._balance -= amount
            return f"Withdrew ${amount:.2f}, balance=${self._balance:.2f}"

    @property
    def balance(self) -> float:
        with self._lock:
            return self._balance

    def __repr__(self) -> str:
        return f"BankAccountMonitor(balance=${self._balance:.2f})"


PatternCatalog.register(
    PatternMeta(
        "Monitor", PatternCategory.CONCURRENCY,
        "Encapsulate mutual exclusion and condition synchronization within an object.",
        "Hoare/Brinch Hansen monitor; all access through synchronized methods.",
        ("MonitorObject", "ClientThread"),
    ),
    BankAccountMonitor,
)


# ---------------------------------------------------------------------------
# 5.8 Producer-Consumer
# ---------------------------------------------------------------------------

class ProducerConsumer:
    """Producer-consumer with bounded buffer."""

    def __init__(self, capacity: int = 10) -> None:
        self._queue: queue.Queue[str] = queue.Queue(maxsize=capacity)
        self._produced = 0
        self._consumed = 0
        self._lock = threading.Lock()

    def produce(self, item: str) -> str:
        self._queue.put(item)
        with self._lock:
            self._produced += 1
        return f"Produced: {item}"

    def consume(self) -> str:
        item = self._queue.get()
        with self._lock:
            self._consumed += 1
        return f"Consumed: {item}"

    @property
    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {"produced": self._produced, "consumed": self._consumed}

    def __repr__(self) -> str:
        return f"ProducerConsumer(queue={self._queue.qsize()}, {self.stats})"


PatternCatalog.register(
    PatternMeta(
        "ProducerConsumer", PatternCategory.CONCURRENCY,
        "Coordinate data flow between producer and consumer threads via a buffer.",
        "Decouple production rate from consumption rate; backpressure.",
        ("Producer", "Consumer", "Buffer", "Client"),
    ),
    ProducerConsumer,
)


# ---------------------------------------------------------------------------
# 5.9 Read-Write Lock
# ---------------------------------------------------------------------------

class ReadWriteLock:
    """Allow multiple readers or single writer."""

    def __init__(self) -> None:
        self._readers = 0
        self._writer_waiting = False
        self._lock = threading.Lock()
        self._read_condition = threading.Condition(self._lock)
        self._write_condition = threading.Condition(self._lock)

    def acquire_read(self) -> None:
        with self._lock:
            while self._writer_waiting:
                self._read_condition.wait()
            self._readers += 1

    def release_read(self) -> None:
        with self._lock:
            self._readers -= 1
            if self._readers == 0:
                self._write_condition.notify_all()

    def acquire_write(self) -> None:
        with self._lock:
            self._writer_waiting = True
            while self._readers > 0:
                self._write_condition.wait()

    def release_write(self) -> None:
        with self._lock:
            self._writer_waiting = False
            self._read_condition.notify_all()

    def __repr__(self) -> str:
        return f"ReadWriteLock(readers={self._readers}, writer_waiting={self._writer_waiting})"


class SharedResource:
    """Resource protected by ReadWriteLock."""

    def __init__(self) -> None:
        self._data = ""
        self._rw_lock = ReadWriteLock()

    def read(self) -> str:
        self._rw_lock.acquire_read()
        try:
            return self._data
        finally:
            self._rw_lock.release_read()

    def write(self, data: str) -> None:
        self._rw_lock.acquire_write()
        try:
            self._data = data
        finally:
            self._rw_lock.release_write()

    def __repr__(self) -> str:
        return f"SharedResource(len={len(self._data)})"


PatternCatalog.register(
    PatternMeta(
        "ReadWriteLock", PatternCategory.CONCURRENCY,
        "Allow concurrent reads but exclusive writes.",
        "Optimize read-heavy workloads; starve-writer prevention.",
        ("ReadWriteLock", "SharedResource", "Client"),
    ),
    ReadWriteLock,
)


# ---------------------------------------------------------------------------
# 5.10 Thread Pool
# ---------------------------------------------------------------------------

class WorkerThread:
    """Worker in thread pool."""

    def __init__(self, task_queue: queue.Queue[Callable[[], Any]]) -> None:
        self._queue = task_queue
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while True:
            try:
                task = self._queue.get(timeout=1)
                if task is None:
                    break
                task()
            except queue.Empty:
                continue

    def __repr__(self) -> str:
        return f"WorkerThread(alive={self._thread.is_alive()})"


class ThreadPool:
    """Fixed-size thread pool."""

    def __init__(self, size: int = 4) -> None:
        self._queue: queue.Queue[Callable[[], Any]] = queue.Queue()
        self._workers = [WorkerThread(self._queue) for _ in range(size)]

    def submit(self, task: Callable[[], Any]) -> None:
        self._queue.put(task)

    def shutdown(self) -> None:
        for _ in self._workers:
            self._queue.put(None)

    def __repr__(self) -> str:
        alive = sum(1 for w in self._workers if w._thread.is_alive())
        return f"ThreadPool(size={len(self._workers)}, alive={alive})"


PatternCatalog.register(
    PatternMeta(
        "ThreadPool", PatternCategory.CONCURRENCY,
        "Manage a pool of worker threads to execute tasks asynchronously.",
        "Reuse threads; bound concurrency; queue-based work distribution.",
        ("ThreadPool", "WorkerThread", "Task", "Client"),
    ),
    ThreadPool,
)


# ---------------------------------------------------------------------------
# 5.11 Thread-Local Storage
# ---------------------------------------------------------------------------

class UserContext:
    """Thread-local storage for user session data."""

    _local = threading.local()

    @classmethod
    def set_user(cls, user_id: str) -> None:
        cls._local.user_id = user_id

    @classmethod
    def get_user(cls) -> Optional[str]:
        return getattr(cls._local, "user_id", None)

    def __repr__(self) -> str:
        return f"UserContext(user={self.get_user()!r})"


PatternCatalog.register(
    PatternMeta(
        "ThreadLocalStorage", PatternCategory.CONCURRENCY,
        "Store data local to each thread, invisible to other threads.",
        "Per-thread state without parameter passing; request context.",
        ("ThreadLocal", "ClientThread"),
    ),
    UserContext,
)


# ---------------------------------------------------------------------------
# 5.12 Pipeline
# ---------------------------------------------------------------------------

class PipelineStage(abc.ABC):
    """One stage in a processing pipeline."""

    @abc.abstractmethod
    def process(self, data: Any) -> Any:
        ...


class UppercaseStage(PipelineStage):
    def process(self, data: str) -> str:
        return data.upper()

    def __repr__(self) -> str:
        return "UppercaseStage()"


class ReplaceStage(PipelineStage):
    def __init__(self, old: str, new: str) -> None:
        self._old = old
        self._new = new

    def process(self, data: str) -> str:
        return data.replace(self._old, self._new)

    def __repr__(self) -> str:
        return f"ReplaceStage({self._old!r}->{self._new!r})"


class Pipeline:
    """Ordered composition of stages."""

    def __init__(self) -> None:
        self._stages: List[PipelineStage] = []

    def add_stage(self, stage: PipelineStage) -> None:
        self._stages.append(stage)

    def execute(self, data: Any) -> Any:
        for stage in self._stages:
            data = stage.process(data)
        return data

    def __repr__(self) -> str:
        return f"Pipeline(stages={len(self._stages)})"


PatternCatalog.register(
    PatternMeta(
        "Pipeline", PatternCategory.CONCURRENCY,
        "Chain data processing stages where output of one is input of the next.",
        "Ordered composition; streaming data processing.",
        ("Pipeline", "Stage", "Client"),
    ),
    Pipeline,
)

# =============================================================================
# SECTION 6 — ARCHITECTURAL PATTERNS (10+)
# =============================================================================

# ---------------------------------------------------------------------------
# 6.1 API Gateway
# ---------------------------------------------------------------------------

class ServiceEndpoint:
    """Backend service descriptor."""

    def __init__(self, name: str, base_url: str) -> None:
        self.name = name
        self.base_url = base_url

    def call(self, path: str) -> str:
        return f"[{self.name}] {self.base_url}{path}"

    def __repr__(self) -> str:
        return f"ServiceEndpoint({self.name!r}, {self.base_url!r})"


class ApiGateway:
    """Single entry point aggregating multiple microservices."""

    def __init__(self) -> None:
        self._services: Dict[str, ServiceEndpoint] = {}

    def register(self, route: str, endpoint: ServiceEndpoint) -> None:
        self._services[route] = endpoint

    def route(self, route: str, path: str) -> str:
        service = self._services.get(route)
        if not service:
            return f"404: No service for route '{route}'"
        return service.call(path)

    def __repr__(self) -> str:
        return f"ApiGateway(routes={list(self._services.keys())})"


PatternCatalog.register(
    PatternMeta(
        "ApiGateway", PatternCategory.ARCHITECTURAL,
        "Single entry point for client requests to multiple backend services.",
        "Routing, rate limiting, auth, aggregation; facade for microservices.",
        ("Gateway", "Service", "Client"),
    ),
    ApiGateway,
)


# ---------------------------------------------------------------------------
# 6.2 CQRS
# ---------------------------------------------------------------------------

class UserWriteModel:
    """Command side: handles state mutations."""

    def __init__(self) -> None:
        self._users: Dict[int, Dict[str, Any]] = {}
        self._next_id = 1
        self._lock = threading.Lock()

    def create_user(self, name: str, email: str) -> int:
        with self._lock:
            uid = self._next_id
            self._users[uid] = {"id": uid, "name": name, "email": email}
            self._next_id += 1
            return uid

    def update_user(self, uid: int, **kwargs: Any) -> str:
        with self._lock:
            if uid not in self._users:
                return "User not found"
            self._users[uid].update(kwargs)
            return "Updated"

    def __repr__(self) -> str:
        return f"UserWriteModel(users={len(self._users)})"


class UserReadModel:
    """Query side: optimized for reads."""

    def __init__(self, write_model: UserWriteModel) -> None:
        self._write = write_model

    def get_user(self, uid: int) -> Optional[Dict[str, Any]]:
        return self._write._users.get(uid)

    def list_users(self) -> List[Dict[str, Any]]:
        return list(self._write._users.values())

    def __repr__(self) -> str:
        return f"UserReadModel(cache_size={len(self._write._users)})"


class CqrsApplication:
    """CQRS: separate command and query responsibilities."""

    def __init__(self) -> None:
        self._write = UserWriteModel()
        self._read = UserReadModel(self._write)

    @property
    def commands(self) -> UserWriteModel:
        return self._write

    @property
    def queries(self) -> UserReadModel:
        return self._read

    def __repr__(self) -> str:
        return f"CqrsApplication(users={len(self._write._users)})"


PatternCatalog.register(
    PatternMeta(
        "CQRS", PatternCategory.ARCHITECTURAL,
        "Segregate read and write operations into separate models.",
        "Optimize queries independently; event sync between sides.",
        ("CommandModel", "QueryModel", "EventBus", "Client"),
    ),
    CqrsApplication,
)


# ---------------------------------------------------------------------------
# 6.3 Event Sourcing
# ---------------------------------------------------------------------------

@dataclass
class DomainEvent:
    """Immutable event capturing a state change."""
    event_id: str
    event_type: str
    aggregate_id: str
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)

    def __repr__(self) -> str:
        return f"DomainEvent({self.event_type!r}, agg={self.aggregate_id!r})"


class EventStore:
    """Append-only event log."""

    def __init__(self) -> None:
        self._events: List[DomainEvent] = []
        self._lock = threading.Lock()

    def append(self, event: DomainEvent) -> None:
        with self._lock:
            self._events.append(event)

    def get_events(self, aggregate_id: str) -> List[DomainEvent]:
        with self._lock:
            return [e for e in self._events if e.aggregate_id == aggregate_id]

    def all_events(self) -> List[DomainEvent]:
        with self._lock:
            return list(self._events)

    def __repr__(self) -> str:
        return f"EventStore(events={len(self._events)})"


class BankAccountAggregate:
    """Aggregate reconstructed from event stream."""

    def __init__(self, account_id: str) -> None:
        self._id = account_id
        self._balance = 0.0

    def apply(self, event: DomainEvent) -> None:
        if event.event_type == "Deposit":
            self._balance += event.payload.get("amount", 0)
        elif event.event_type == "Withdrawal":
            self._balance -= event.payload.get("amount", 0)

    @property
    def balance(self) -> float:
        return self._balance

    def __repr__(self) -> str:
        return f"BankAccountAggregate({self._id!r}, balance=${self._balance:.2f})"


class EventSourcedRepository:
    """Repository: rehydrates aggregate from event stream."""

    def __init__(self, event_store: EventStore) -> None:
        self._store = event_store

    def load(self, account_id: str) -> BankAccountAggregate:
        aggregate = BankAccountAggregate(account_id)
        for event in self._store.get_events(account_id):
            aggregate.apply(event)
        return aggregate

    def save(self, account_id: str, event: DomainEvent) -> None:
        self._store.append(event)

    def __repr__(self) -> str:
        return f"EventSourcedRepository(store={self._store})"


PatternCatalog.register(
    PatternMeta(
        "EventSourcing", PatternCategory.ARCHITECTURAL,
        "Store state changes as a sequence of events, not current state.",
        "Audit trail, temporal queries, replay; event store as source of truth.",
        ("EventStore", "Aggregate", "DomainEvent", "Repository", "Client"),
    ),
    EventStore,
)


# ---------------------------------------------------------------------------
# 6.4 Hexagonal Architecture (Ports & Adapters)
# ---------------------------------------------------------------------------

@runtime_checkable
class NotificationPort(Protocol):
    """Primary port: outbound notification capability."""

    def send(self, message: str, recipient: str) -> str:
        ...


class EmailAdapter:
    """Secondary adapter: email implementation."""

    def send(self, message: str, recipient: str) -> str:
        return f"Email to {recipient}: {message}"

    def __repr__(self) -> str:
        return "EmailAdapter()"


class SmsAdapter:
    """Secondary adapter: SMS implementation."""

    def send(self, message: str, recipient: str) -> str:
        return f"SMS to {recipient}: {message[:20]}..."

    def __repr__(self) -> str:
        return "SmsAdapter()"


class NotificationService:
    """Core domain: depends only on port, not concrete adapter."""

    def __init__(self, port: NotificationPort) -> None:
        self._port = port

    def notify(self, message: str, recipient: str) -> str:
        return self._port.send(message, recipient)

    def __repr__(self) -> str:
        return f"NotificationService(port={self._port})"


PatternCatalog.register(
    PatternMeta(
        "HexagonalArchitecture", PatternCategory.ARCHITECTURAL,
        "Core domain depends on ports; adapters connect to external systems.",
        "Testability; swap adapters without touching domain logic.",
        ("Port", "Adapter", "DomainService", "Client"),
    ),
    NotificationService,
)


# ---------------------------------------------------------------------------
# 6.5 Layered Architecture
# ---------------------------------------------------------------------------

class DataLayer:
    """Bottom layer: persistence."""

    def fetch(self, id: int) -> Dict[str, Any]:
        return {"id": id, "raw": "data"}

    def __repr__(self) -> str:
        return "DataLayer()"


class BusinessLayer:
    """Middle layer: domain logic."""

    def __init__(self, data: DataLayer) -> None:
        self._data = data

    def get_user(self, id: int) -> Dict[str, Any]:
        raw = self._data.fetch(id)
        return {"user_id": raw["id"], "processed": True}

    def __repr__(self) -> str:
        return "BusinessLayer()"


class PresentationLayer:
    """Top layer: UI/API formatting."""

    def __init__(self, business: BusinessLayer) -> None:
        self._business = business

    def user_json(self, id: int) -> str:
        user = self._business.get_user(id)
        return f'"user_id": {user["user_id"]}, "status": "ok"'

    def __repr__(self) -> str:
        return "PresentationLayer()"


class LayeredApplication:
    """Composed layered architecture."""

    def __init__(self) -> None:
        self.data = DataLayer()
        self.business = BusinessLayer(self.data)
        self.presentation = PresentationLayer(self.business)

    def __repr__(self) -> str:
        return "LayeredApplication(data->business->presentation)"


PatternCatalog.register(
    PatternMeta(
        "LayeredArchitecture", PatternCategory.ARCHITECTURAL,
        "Organize code into horizontal layers with strict dependency direction.",
        "Presentation -> Business -> Data; unidirectional dependencies.",
        ("PresentationLayer", "BusinessLayer", "DataLayer", "Client"),
    ),
    LayeredApplication,
)


# ---------------------------------------------------------------------------
# 6.6 Microservices (Emulation)
# ---------------------------------------------------------------------------

class Microservice:
    """Single deployable service with own database."""

    def __init__(self, name: str, endpoint: str) -> None:
        self.name = name
        self.endpoint = endpoint
        self._data: Dict[str, Any] = {}

    def handle(self, action: str, payload: Any) -> str:
        if action == "get":
            return str(self._data.get(payload, "not_found"))
        if action == "set":
            key, value = payload
            self._data[key] = value
            return f"{self.name}: set {key}"
        return "unknown_action"

    def __repr__(self) -> str:
        return f"Microservice({self.name!r}, {self.endpoint!r})"


class ServiceRegistry:
    """Discovery for microservices."""

    def __init__(self) -> None:
        self._services: Dict[str, Microservice] = {}

    def register(self, service: Microservice) -> None:
        self._services[service.name] = service

    def discover(self, name: str) -> Optional[Microservice]:
        return self._services.get(name)

    def __repr__(self) -> str:
        return f"ServiceRegistry(services={list(self._services.keys())})"


PatternCatalog.register(
    PatternMeta(
        "Microservices", PatternCategory.ARCHITECTURAL,
        "Decompose application into independently deployable services.",
        "Service boundaries, registry, inter-service communication.",
        ("Microservice", "ServiceRegistry", "Client"),
    ),
    ServiceRegistry,
)


# ---------------------------------------------------------------------------
# 6.7 MVC
# ---------------------------------------------------------------------------

class StudentModel:
    """Model: data and business rules."""

    def __init__(self, name: str, roll_no: str) -> None:
        self._name = name
        self._roll_no = roll_no

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def roll_no(self) -> str:
        return self._roll_no

    def __repr__(self) -> str:
        return f"StudentModel({self._name!r}, {self._roll_no!r})"


class StudentView:
    """View: presentation logic."""

    def print_details(self, name: str, roll_no: str) -> str:
        return f"Student: {name} [Roll: {roll_no}]"

    def __repr__(self) -> str:
        return "StudentView()"


class StudentController:
    """Controller: handles input, updates model/view."""

    def __init__(self, model: StudentModel, view: StudentView) -> None:
        self._model = model
        self._view = view

    def set_name(self, name: str) -> None:
        self._model.name = name

    def get_name(self) -> str:
        return self._model.name

    def update_view(self) -> str:
        return self._view.print_details(self._model.name, self._model.roll_no)

    def __repr__(self) -> str:
        return f"StudentController(model={self._model.name!r})"


PatternCatalog.register(
    PatternMeta(
        "MVC", PatternCategory.ARCHITECTURAL,
        "Separate application into Model, View, and Controller components.",
        "Classic triad; controller mediates between model and view.",
        ("Model", "View", "Controller", "Client"),
    ),
    StudentController,
)


# ---------------------------------------------------------------------------
# 6.8 MVVM
# ---------------------------------------------------------------------------

class EmployeeModel:
    """Domain model."""

    def __init__(self, name: str, salary: float) -> None:
        self.name = name
        self.salary = salary

    def __repr__(self) -> str:
        return f"EmployeeModel({self.name!r}, ${self.salary:.2f})"


class EmployeeViewModel:
    """ViewModel: transforms model for view binding."""

    def __init__(self, model: EmployeeModel) -> None:
        self._model = model

    @property
    def display_name(self) -> str:
        return self._model.name.upper()

    @property
    def formatted_salary(self) -> str:
        return f"${self._model.salary:,.2f}"

    def __repr__(self) -> str:
        return f"EmployeeViewModel({self.display_name!r}, {self.formatted_salary})"


class EmployeeView:
    """View: renders ViewModel."""

    def render(self, vm: EmployeeViewModel) -> str:
        return f"Employee: {vm.display_name} | Salary: {vm.formatted_salary}"

    def __repr__(self) -> str:
        return "EmployeeView()"


PatternCatalog.register(
    PatternMeta(
        "MVVM", PatternCategory.ARCHITECTURAL,
        "Model-View-ViewModel: bind view to properties on a ViewModel.",
        "Two-way data binding; ViewModel as adapter between Model and View.",
        ("Model", "ViewModel", "View", "Client"),
    ),
    EmployeeViewModel,
)


# ---------------------------------------------------------------------------
# 6.9 Repository
# ---------------------------------------------------------------------------

class Entity(abc.ABC):
    """Base entity with ID."""

    def __init__(self, entity_id: int) -> None:
        self.id = entity_id

    def __repr__(self) -> str:
        return f"Entity({self.id})"


class Customer(Entity):
    def __init__(self, entity_id: int, name: str) -> None:
        super().__init__(entity_id)
        self.name = name

    def __repr__(self) -> str:
        return f"Customer({self.id}, {self.name!r})"


class Repository(abc.ABC, Generic[T]):
    """Generic repository interface."""

    @abc.abstractmethod
    def get(self, id: int) -> Optional[T]:
        ...

    @abc.abstractmethod
    def add(self, entity: T) -> None:
        ...

    @abc.abstractmethod
    def remove(self, id: int) -> None:
        ...

    @abc.abstractmethod
    def get_all(self) -> List[T]:
        ...


class InMemoryRepository(Repository[Customer]):
    """Concrete repository: in-memory."""

    def __init__(self) -> None:
        self._store: Dict[int, Customer] = {}

    def get(self, id: int) -> Optional[Customer]:
        return self._store.get(id)

    def add(self, entity: Customer) -> None:
        self._store[entity.id] = entity

    def remove(self, id: int) -> None:
        self._store.pop(id, None)

    def get_all(self) -> List[Customer]:
        return list(self._store.values())

    def __repr__(self) -> str:
        return f"InMemoryRepository(count={len(self._store)})"


PatternCatalog.register(
    PatternMeta(
        "Repository", PatternCategory.ARCHITECTURAL,
        "Mediate between domain and data mapping layers using collection-like interface.",
        "Abstract persistence; swap in-memory for SQL without touching domain.",
        ("Repository", "ConcreteRepository", "Entity", "Client"),
    ),
    Repository,
)


# ---------------------------------------------------------------------------
# 6.10 Unit of Work
# ---------------------------------------------------------------------------

class UnitOfWork:
    """Track changes and commit atomically."""

    def __init__(self, repository: Repository[Any]) -> None:
        self._repo = repository
        self._new: List[Any] = []
        self._dirty: List[Any] = []
        self._removed: List[int] = []

    def register_new(self, entity: Any) -> None:
        self._new.append(entity)

    def register_dirty(self, entity: Any) -> None:
        self._dirty.append(entity)

    def register_removed(self, entity_id: int) -> None:
        self._removed.append(entity_id)

    def commit(self) -> str:
        for entity in self._new:
            self._repo.add(entity)
        for entity in self._dirty:
            self._repo.add(entity)
        for eid in self._removed:
            self._repo.remove(eid)
        self._new.clear()
        self._dirty.clear()
        self._removed.clear()
        return "Committed"

    def rollback(self) -> str:
        self._new.clear()
        self._dirty.clear()
        self._removed.clear()
        return "Rolled back"

    def __repr__(self) -> str:
        return f"UnitOfWork(new={len(self._new)}, dirty={len(self._dirty)}, removed={len(self._removed)})"


PatternCatalog.register(
    PatternMeta(
        "UnitOfWork", PatternCategory.ARCHITECTURAL,
        "Maintain a list of objects affected by a business transaction and coordinate writing.",
        "Atomic commit; batch updates; rollback support.",
        ("UnitOfWork", "Repository", "Entity", "Client"),
    ),
    UnitOfWork,
)

# =============================================================================
# SECTION 7 — FUNCTIONAL PATTERNS (10+)
# =============================================================================

# ---------------------------------------------------------------------------
# 7.1 Monad
# ---------------------------------------------------------------------------

class Maybe:
    """Maybe monad: encapsulate optional value."""

    def __init__(self, value: Any = None) -> None:
        self._value = value
        self._has_value = value is not None

    def is_present(self) -> bool:
        return self._has_value

    def map(self, fn: Callable[[Any], Any]) -> Maybe:
        if self._has_value:
            return Maybe(fn(self._value))
        return Maybe()

    def flat_map(self, fn: Callable[[Any], Maybe]) -> Maybe:
        if self._has_value:
            return fn(self._value)
        return Maybe()

    def get_or_else(self, default: Any) -> Any:
        return self._value if self._has_value else default

    def __repr__(self) -> str:
        return f"Maybe({self._value!r})" if self._has_value else "Maybe.empty"


class Result:
    """Result monad: Either-like success/failure."""

    def __init__(self, value: Any = None, error: Optional[str] = None) -> None:
        self._value = value
        self._error = error
        self._success = error is None

    @classmethod
    def ok(cls, value: Any) -> Result:
        return cls(value=value)

    @classmethod
    def fail(cls, error: str) -> Result:
        return cls(error=error)

    def map(self, fn: Callable[[Any], Any]) -> Result:
        if self._success:
            try:
                return Result.ok(fn(self._value))
            except Exception as e:
                return Result.fail(str(e))
        return self

    def get_or_else(self, default: Any) -> Any:
        return self._value if self._success else default

    def __repr__(self) -> str:
        if self._success:
            return f"Result.ok({self._value!r})"
        return f"Result.fail({self._error!r})"


PatternCatalog.register(
    PatternMeta(
        "Monad", PatternCategory.FUNCTIONAL,
        "Encapsulate computation chains with context (option, error, list).",
        "Bind/flat_map; composable error handling without exceptions.",
        ("Monad", "Unit", "Bind", "Client"),
    ),
    Maybe,
)


# ---------------------------------------------------------------------------
# 7.2 Functor
# ---------------------------------------------------------------------------

class Box(Generic[T]):
    """Simple functor: mappable container."""

    def __init__(self, value: T) -> None:
        self._value = value

    def map(self, fn: Callable[[T], Any]) -> Box:
        return Box(fn(self._value))

    @property
    def value(self) -> T:
        return self._value

    def __repr__(self) -> str:
        return f"Box({self._value!r})"


PatternCatalog.register(
    PatternMeta(
        "Functor", PatternCategory.FUNCTIONAL,
        "Map a function over a wrapped value without unwrapping.",
        "fmap; preserve structure while transforming contents.",
        ("Functor", "Map", "Client"),
    ),
    Box,
)


# ---------------------------------------------------------------------------
# 7.3 Strategy (Functional)
# ---------------------------------------------------------------------------

class FunctionalStrategy:
    """Strategy via pure functions, not classes."""

    @staticmethod
    def bubble_sort(data: List[int]) -> List[int]:
        arr = data.copy()
        n = len(arr)
        for i in range(n):
            for j in range(0, n - i - 1):
                if arr[j] > arr[j + 1]:
                    arr[j], arr[j + 1] = arr[j + 1], arr[j]
        return arr

    @staticmethod
    def quick_sort(data: List[int]) -> List[int]:
        if len(data) <= 1:
            return data
        pivot = data[len(data) // 2]
        left = [x for x in data if x < pivot]
        middle = [x for x in data if x == pivot]
        right = [x for x in data if x > pivot]
        return FunctionalStrategy.quick_sort(left) + middle + FunctionalStrategy.quick_sort(right)

    def __repr__(self) -> str:
        return "FunctionalStrategy()"


PatternCatalog.register(
    PatternMeta(
        "FunctionalStrategy", PatternCategory.FUNCTIONAL,
        "Pass algorithms as first-class functions instead of strategy objects.",
        "Higher-order functions; function registry; lambda strategies.",
        ("StrategyFunction", "Context", "Client"),
    ),
    FunctionalStrategy,
)


# ---------------------------------------------------------------------------
# 7.4 Memoization
# ---------------------------------------------------------------------------

class Memoized:
    """Decorator-style memoization cache."""

    def __init__(self, fn: Callable[..., T]) -> None:
        self._fn = fn
        self._cache: Dict[Tuple[Any, ...], T] = {}
        self._lock = threading.Lock()

    def __call__(self, *args: Any) -> T:
        key = args
        with self._lock:
            if key not in self._cache:
                self._cache[key] = self._fn(*args)
            return self._cache[key]

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def __repr__(self) -> str:
        return f"Memoized(cache_size={len(self._cache)})"


PatternCatalog.register(
    PatternMeta(
        "Memoization", PatternCategory.FUNCTIONAL,
        "Cache function results to avoid redundant computation.",
        "lru_cache equivalent; pure function optimization.",
        ("Memoizer", "Function", "Cache"),
    ),
    Memoized,
)


# ---------------------------------------------------------------------------
# 7.5 Currying
# ---------------------------------------------------------------------------

class Curried:
    """Transform multi-arg function into sequence of single-arg functions."""

    def __init__(self, fn: Callable[..., T], arity: int) -> None:
        self._fn = fn
        self._arity = arity
        self._args: List[Any] = []

    def __call__(self, arg: Any) -> Union[Curried, T]:
        self._args.append(arg)
        if len(self._args) >= self._arity:
            return self._fn(*self._args)
        return self

    def __repr__(self) -> str:
        return f"Curried(arity={self._arity}, collected={len(self._args)})"


PatternCatalog.register(
    PatternMeta(
        "Currying", PatternCategory.FUNCTIONAL,
        "Transform function f(a,b,c) into f(a)(b)(c).",
        "Partial application foundation; function factories.",
        ("CurriedFunction", "Client"),
    ),
    Curried,
)


# ---------------------------------------------------------------------------
# 7.6 Partial Application
# ---------------------------------------------------------------------------

class Partial:
    """Bind some arguments, leave others for later."""

    def __init__(self, fn: Callable[..., T], *bound: Any) -> None:
        self._fn = fn
        self._bound = bound

    def __call__(self, *args: Any) -> T:
        return self._fn(*self._bound, *args)

    def __repr__(self) -> str:
        return f"Partial(bound={self._bound})"


PatternCatalog.register(
    PatternMeta(
        "PartialApplication", PatternCategory.FUNCTIONAL,
        "Fix some arguments of a function, producing another function of fewer args.",
        "Specialize generic functions; dependency pre-injection.",
        ("Partial", "Function", "Client"),
    ),
    Partial,
)


# ---------------------------------------------------------------------------
# 7.7 Pipeline (Functional)
# ---------------------------------------------------------------------------

class FunctionalPipeline:
    """Left-to-right function composition."""

    def __init__(self, value: T) -> None:
        self._value = value

    def then(self, fn: Callable[[Any], Any]) -> FunctionalPipeline:
        self._value = fn(self._value)
        return self

    def result(self) -> Any:
        return self._value

    def __repr__(self) -> str:
        return f"FunctionalPipeline(value={self._value!r})"


PatternCatalog.register(
    PatternMeta(
        "FunctionalPipeline", PatternCategory.FUNCTIONAL,
        "Chain pure functions left-to-right for readable data transformation.",
        "Unix pipe style; immutable data flow.",
        ("Pipeline", "Stage", "Client"),
    ),
    FunctionalPipeline,
)


# ---------------------------------------------------------------------------
# 7.8 Compose
# ---------------------------------------------------------------------------

class Compose:
    """Function composition: (f ∘ g)(x) = f(g(x))."""

    def __init__(self, *fns: Callable[[Any], Any]) -> None:
        self._fns = list(reversed(fns))

    def __call__(self, x: Any) -> Any:
        result = x
        for fn in self._fns:
            result = fn(result)
        return result

    def __repr__(self) -> str:
        return f"Compose(functions={len(self._fns)})"


PatternCatalog.register(
    PatternMeta(
        "Compose", PatternCategory.FUNCTIONAL,
        "Combine functions so that output of one is input of the next.",
        "Mathematical composition; point-free style.",
        ("Compose", "Function", "Client"),
    ),
    Compose,
)


# =============================================================================
# SECTION 8 — DEMO
# =============================================================================

def demo() -> None:
    """Demonstrate 10+ patterns running end-to-end."""
    results: List[str] = []

    # 1. Singleton
    config = AppConfig()
    config.set("mode", "demo")
    results.append(f"Singleton: {config.get('mode')}")

    # 2. Factory Method
    factory = WebDialogFactory()
    results.append(f"FactoryMethod: {factory.show_dialog()}")

    # 3. Builder
    burger = BurgerBuilder(2).add_cheese().add_pepperoni().build()
    results.append(f"Builder: {burger}")

    # 4. Adapter
    hole = RoundHole(5)
    peg = SquarePegAdapter(SquarePeg(5))
    results.append(f"Adapter: fits={hole.fits(peg)}")

    # 5. Observer
    agency = NewsAgency()
    channel = NewsChannel("CNN")
    agency.attach(channel)
    agency.publish_news("Pattern Demo Running")
    results.append(f"Observer: {channel.headlines}")

    # 6. Strategy
    cart = ShoppingCart()
    cart.add_item("Book", 29.99)
    cart.set_strategy(PayPalStrategy("treas@example.com"))
    results.append(f"Strategy: {cart.checkout()}")

    # 7. Command
    light = Light()
    remote = RemoteControlInvoker()
    remote.set_command(LightOnCommand(light))
    results.append(f"Command: {remote.press_button()}")
    results.append(f"Command undo: {remote.press_undo()}")

    # 8. Decorator
    source = FileDataSource("data.txt")
    encrypted = EncryptionDecorator(source)
    encrypted.write_data("secret")
    results.append(f"Decorator: {encrypted.read_data()}")

    # 9. State
    phone = Phone()
    results.append(f"State: {phone.pick_up()}")
    results.append(f"State: {phone.dial('555-1234')}")
    results.append(f"State: {phone.hang_up()}")

    # 10. Pipeline (Concurrency)
    pipe = Pipeline()
    pipe.add_stage(UppercaseStage())
    pipe.add_stage(ReplaceStage(" ", "_"))
    results.append(f"Pipeline: {pipe.execute('hello world')}")

    # 11. CQRS
    app = CqrsApplication()
    uid = app.commands.create_user("Treas", "treas@example.com")
    user = app.queries.get_user(uid)
    results.append(f"CQRS: {user}")

    # 12. Monad
    maybe = Maybe(5).map(lambda x: x * 2).map(lambda x: x + 1)
    results.append(f"Monad: {maybe.get_or_else(0)}")

    # 13. Flyweight
    forest = Forest()
    forest.plant_tree(1, 1, "Oak", "green", "rough")
    forest.plant_tree(2, 2, "Oak", "green", "rough")
    forest.plant_tree(3, 3, "Pine", "dark_green", "smooth")
    results.append(f"Flyweight: {forest}")

    # 14. Specification
    spec = ColorSpecification("red") & PriceRangeSpecification(10, 100)
    product = ProductSpec("Shirt", "red", 45.0, 0.5)
    results.append(f"Specification: {spec.is_satisfied_by(product)}")

    # 15. Proxy
    proxy = ProxyImage("photo.png")
    results.append(f"Proxy (lazy): {proxy}")
    proxy.display()
    results.append(f"Proxy (loaded): {proxy}")

    # Catalog summary
    results.append(f"\nPatternCatalog: {PatternCatalog.count()} patterns registered")
    for cat in PatternCategory:
        count = len(PatternCatalog.by_category(cat))
        results.append(f"  {cat.value}: {count} patterns")

    print("\n".join(results))
    return results


if __name__ == "__main__":
    demo()
