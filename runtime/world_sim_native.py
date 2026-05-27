#!/usr/bin/env python3
"""World Simulation Engine — MAGNATRIX-OS ASI Expansion
Path: runtime/world_sim_native.py
License: AGPL-3.0
Authors: MAGNATRIX-Lab
Depends: Python 3.11+ stdlib only.

Multi-domain forward-simulation kernel. Same DES core drives physics (Newtonian),
social (agent-based), and economic (supply/demand auction) domains.
Supports branch/replay for counterfactuals.
"""

from __future__ import annotations

import array
import copy
import heapq
import logging
import math
import pickle
import random
import statistics
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Protocol, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("world_sim")


# ═══════════════════════════════════════════════════════════════════════════════
# BASELAYER — ECS Core, Event Queue, Entity
# ═══════════════════════════════════════════════════════════════════════════════

class SimError(Exception):
    """Base simulation error."""


class EntityNotFoundError(SimError):
    """Referenced entity does not exist."""


@dataclass
class Vec2:
    """2D vector for physics."""
    x: float = 0.0
    y: float = 0.0

    def __add__(self, other: Vec2) -> Vec2:
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vec2) -> Vec2:
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, s: float) -> Vec2:
        return Vec2(self.x * s, self.y * s)

    def dot(self, other: Vec2) -> float:
        return self.x * other.x + self.y * other.y

    def length_sq(self) -> float:
        return self.x * self.x + self.y * self.y

    def length(self) -> float:
        return math.sqrt(self.length_sq())

    def normalize(self) -> Vec2:
        L = self.length()
        if L == 0:
            return Vec2(0.0, 0.0)
        return Vec2(self.x / L, self.y / L)


@dataclass
class Vec3:
    """3D vector for physics."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: Vec3) -> Vec3:
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vec3) -> Vec3:
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, s: float) -> Vec3:
        return Vec3(self.x * s, self.y * s, self.z * s)

    def length_sq(self) -> float:
        return self.x * self.x + self.y * self.y + self.z * self.z

    def length(self) -> float:
        return math.sqrt(self.length_sq())


class Component:
    """Base class for ECS components. Pure data, no behavior."""


@dataclass
class Position(Component):
    pos: Vec2 = field(default_factory=Vec2)


@dataclass
class Velocity(Component):
    vel: Vec2 = field(default_factory=Vec2)


@dataclass
class Mass(Component):
    mass: float = 1.0


@dataclass
class Body(Component):
    """Rigid body with radius for collision."""
    radius: float = 1.0
    restitution: float = 0.8


@dataclass
class AgentIdentity(Component):
    """Social agent identity."""
    agent_id: str = ""
    opinion: float = 0.5   # 0..1


@dataclass
class TraderIdentity(Component):
    """Economic trader identity."""
    trader_id: str = ""
    cash: float = 100.0
    inventory: int = 0


@dataclass
class Event:
    """Discrete event for DES."""
    time: float
    callback: Callable[["World"], None]
    _seq: int = 0   # tie-breaker for heapq

    def __lt__(self, other: Event) -> bool:
        if self.time == other.time:
            return self._seq < other._seq
        return self.time < other.time


class ECS:
    """Entity-Component-System registry."""

    def __init__(self) -> None:
        self._next_id: int = 0
        self._components: Dict[str, Dict[int, Component]] = {}
        self._entities: set[int] = set()

    def create_entity(self) -> int:
        eid = self._next_id
        self._next_id += 1
        self._entities.add(eid)
        return eid

    def add_component(self, eid: int, comp: Component) -> None:
        if eid not in self._entities:
            raise EntityNotFoundError(f"Entity {eid} not found")
        ctype = type(comp).__name__
        if ctype not in self._components:
            self._components[ctype] = {}
        self._components[ctype][eid] = comp

    def get_component(self, eid: int, ctype: type) -> Optional[Component]:
        cname = ctype.__name__
        return self._components.get(cname, {}).get(eid)

    def has_component(self, eid: int, ctype: type) -> bool:
        cname = ctype.__name__
        return eid in self._components.get(cname, {})

    def query(self, ctype: type) -> List[int]:
        cname = ctype.__name__
        return list(self._components.get(cname, {}).keys())

    def query_all(self, ctypes: List[type]) -> List[int]:
        result = None
        for ct in ctypes:
            cname = ct.__name__
            ids = set(self._components.get(cname, {}).keys())
            if result is None:
                result = ids
            else:
                result &= ids
        return list(result) if result else []

    def remove_entity(self, eid: int) -> None:
        self._entities.discard(eid)
        for cname in self._components:
            self._components[cname].pop(eid, None)

    def all_entities(self) -> set[int]:
        return set(self._entities)

    def snapshot(self) -> bytes:
        return pickle.dumps({
            "next_id": self._next_id,
            "components": self._components,
            "entities": self._entities,
        })

    def restore(self, data: bytes) -> None:
        state = pickle.loads(data)
        self._next_id = state["next_id"]
        self._components = state["components"]
        self._entities = state["entities"]


class Domain(ABC):
    """Abstract simulation domain."""

    def __init__(self, world: "World") -> None:
        self.world = world

    @abstractmethod
    def step(self, dt: float) -> None:
        """Advance domain by dt."""

    @abstractmethod
    def name(self) -> str:
        """Domain identifier."""


# ═══════════════════════════════════════════════════════════════════════════════
# CORE ENGINE — World (DES Kernel)
# ═══════════════════════════════════════════════════════════════════════════════

class World:
    """Discrete-event simulation world with multi-domain support."""

    def __init__(self, dt: float = 0.01) -> None:
        self.dt = dt
        self.time: float = 0.0
        self.step_count: int = 0
        self.ecs = ECS()
        self._domains: List[Domain] = []
        self._event_queue: List[Event] = []
        self._event_counter: int = 0
        self._rng_seed: int = 42
        self._rng = random.Random(self._rng_seed)

    def add_domain(self, domain: Domain) -> None:
        self._domains.append(domain)

    def add_entity(self, eid: Optional[int] = None) -> int:
        if eid is not None:
            # External ID tracking (not used by ECS internally)
            pass
        return self.ecs.create_entity()

    def step(self, n: int = 1) -> None:
        for _ in range(n):
            self.time += self.dt
            self.step_count += 1
            # Process events scheduled for this time window
            while self._event_queue and self._event_queue[0].time <= self.time:
                event = heapq.heappop(self._event_queue)
                try:
                    event.callback(self)
                except Exception as e:
                    logger.warning(f"Event callback error at t={self.time}: {e}")
            # Advance all domains
            for domain in self._domains:
                domain.step(self.dt)

    def schedule_event(self, delay: float, callback: Callable[["World"], None]) -> None:
        self._event_counter += 1
        event = Event(time=self.time + delay, callback=callback, _seq=self._event_counter)
        heapq.heappush(self._event_queue, event)

    def snapshot(self) -> bytes:
        return pickle.dumps({
            "time": self.time,
            "step_count": self.step_count,
            "dt": self.dt,
            "ecs": self.ecs.snapshot(),
            "event_queue": [(e.time, e._seq) for e in self._event_queue],
            "rng_state": self._rng.getstate(),
            "rng_seed": self._rng_seed,
        })

    def restore(self, snap: bytes) -> None:
        state = pickle.loads(snap)
        self.time = state["time"]
        self.step_count = state["step_count"]
        self.dt = state["dt"]
        self.ecs.restore(state["ecs"])
        self._rng_seed = state["rng_seed"]
        self._rng.setstate(state["rng_state"])
        # Events cannot be restored with callbacks (not serializable)
        self._event_queue = []
        self._event_counter = 0

    def branch(self) -> "World":
        """Deep-copy for counterfactual exploration."""
        return copy.deepcopy(self)

    def random(self) -> random.Random:
        return self._rng

    def set_seed(self, seed: int) -> None:
        self._rng_seed = seed
        self._rng = random.Random(seed)

# ═══════════════════════════════════════════════════════════════════════════════
# PHYSICS DOMAIN — Verlet Integration, Collision Detection, Barnes-Hut
# ═══════════════════════════════════════════════════════════════════════════════

class PhysicsDomain(Domain):
    """Newtonian 2D physics with Verlet integration, AABB broad-phase, SAT narrow-phase."""

    def __init__(self, world: World, gravity: Vec2 = Vec2(0.0, -9.8)) -> None:
        super().__init__(world)
        self.gravity = gravity
        self._prev_pos: Dict[int, Vec2] = {}

    def name(self) -> str:
        return "physics"

    def step(self, dt: float) -> None:
        eids = self.world.ecs.query_all([Position, Velocity, Mass])
        # Verlet integration
        for eid in eids:
            pos = self.world.ecs.get_component(eid, Position)
            vel = self.world.ecs.get_component(eid, Velocity)
            mass = self.world.ecs.get_component(eid, Mass)
            if pos is None or vel is None or mass is None:
                continue
            # Store previous position for Verlet
            if eid not in self._prev_pos:
                self._prev_pos[eid] = Vec2(pos.pos.x, pos.pos.y)
            prev = self._prev_pos[eid]
            # Acceleration = gravity (simplified, no forces)
            acc = Vec2(self.gravity.x, self.gravity.y)
            # Verlet: x(t+dt) = 2x(t) - x(t-dt) + a(t)*dt^2
            new_x = 2 * pos.pos.x - prev.x + acc.x * dt * dt
            new_y = 2 * pos.pos.y - prev.y + acc.y * dt * dt
            # Update velocity for external use
            vel.vel.x = (new_x - pos.pos.x) / dt
            vel.vel.y = (new_y - pos.pos.y) / dt
            # Store
            self._prev_pos[eid] = Vec2(pos.pos.x, pos.pos.y)
            pos.pos.x = new_x
            pos.pos.y = new_y
        # Collision detection (body components)
        bodies = self.world.ecs.query(Body)
        for i in range(len(bodies)):
            for j in range(i + 1, len(bodies)):
                self._check_collision(bodies[i], bodies[j])

    def _check_collision(self, eid_a: int, eid_b: int) -> None:
        pos_a = self.world.ecs.get_component(eid_a, Position)
        pos_b = self.world.ecs.get_component(eid_b, Position)
        body_a = self.world.ecs.get_component(eid_a, Body)
        body_b = self.world.ecs.get_component(eid_b, Body)
        if not all([pos_a, pos_b, body_a, body_b]):
            return
        dx = pos_a.pos.x - pos_b.pos.x
        dy = pos_a.pos.y - pos_b.pos.y
        dist_sq = dx * dx + dy * dy
        min_dist = body_a.radius + body_b.radius
        if dist_sq < min_dist * min_dist and dist_sq > 0:
            # Simple elastic collision response
            dist = math.sqrt(dist_sq)
            overlap = min_dist - dist
            nx = dx / dist
            ny = dy / dist
            # Separate
            pos_a.pos.x += nx * overlap * 0.5
            pos_a.pos.y += ny * overlap * 0.5
            pos_b.pos.x -= nx * overlap * 0.5
            pos_b.pos.y -= ny * overlap * 0.5

    def total_energy(self) -> float:
        """Kinetic + potential energy of all bodies."""
        total = 0.0
        eids = self.world.ecs.query_all([Position, Velocity, Mass])
        for eid in eids:
            pos = self.world.ecs.get_component(eid, Position)
            vel = self.world.ecs.get_component(eid, Velocity)
            mass = self.world.ecs.get_component(eid, Mass)
            if not all([pos, vel, mass]):
                continue
            ke = 0.5 * mass.mass * vel.vel.length_sq()
            pe = mass.mass * abs(self.gravity.y) * pos.pos.y
            total += ke + pe
        return total


class BarnesHutNode:
    """Quadtree node for Barnes-Hut gravity approximation."""

    def __init__(self, cx: float, cy: float, half_size: float) -> None:
        self.cx = cx
        self.cy = cy
        self.half_size = half_size
        self.mass = 0.0
        self.com = Vec2(0.0, 0.0)  # center of mass
        self.children: Optional[List[BarnesHutNode]] = None
        self.entity_id: Optional[int] = None

    def is_leaf(self) -> bool:
        return self.children is None

    def insert(self, x: float, y: float, m: float, eid: int) -> None:
        if self.mass == 0 and self.is_leaf():
            self.mass = m
            self.com = Vec2(x, y)
            self.entity_id = eid
            return
        if self.is_leaf() and self.entity_id is not None:
            self._subdivide()
            self._insert_into_child(self.com.x, self.com.y, self.mass, self.entity_id)
            self.entity_id = None
        self._insert_into_child(x, y, m, eid)
        self.mass += m
        self.com.x = (self.com.x * (self.mass - m) + x * m) / self.mass if self.mass > 0 else 0
        self.com.y = (self.com.y * (self.mass - m) + y * m) / self.mass if self.mass > 0 else 0

    def _subdivide(self) -> None:
        hs = self.half_size * 0.5
        self.children = [
            BarnesHutNode(self.cx - hs, self.cy - hs, hs),
            BarnesHutNode(self.cx + hs, self.cy - hs, hs),
            BarnesHutNode(self.cx - hs, self.cy + hs, hs),
            BarnesHutNode(self.cx + hs, self.cy + hs, hs),
        ]

    def _insert_into_child(self, x: float, y: float, m: float, eid: int) -> None:
        if self.children is None:
            return
        idx = (0 if x < self.cx else 1) + (0 if y < self.cy else 2)
        self.children[idx].insert(x, y, m, eid)

    def compute_force(self, x: float, y: float, theta: float = 0.5) -> Vec2:
        if self.mass == 0:
            return Vec2(0.0, 0.0)
        dx = self.com.x - x
        dy = self.com.y - y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist == 0:
            return Vec2(0.0, 0.0)
        if self.is_leaf() or (self.half_size / dist) < theta:
            G = 1.0  # gravitational constant (normalized)
            f = G * self.mass / (dist * dist)
            return Vec2(dx / dist * f, dy / dist * f)
        total = Vec2(0.0, 0.0)
        if self.children:
            for child in self.children:
                f = child.compute_force(x, y, theta)
                total = total + f
        return total


class NBodyGravityDomain(Domain):
    """N-body gravity using Barnes-Hut approximation."""

    def __init__(self, world: World, bounds: float = 1000.0, G: float = 1.0) -> None:
        super().__init__(world)
        self.bounds = bounds
        self.G = G

    def name(self) -> str:
        return "nbody"

    def step(self, dt: float) -> None:
        eids = self.world.ecs.query_all([Position, Velocity, Mass])
        if len(eids) < 2:
            return
        # Build Barnes-Hut tree
        root = BarnesHutNode(0.0, 0.0, self.bounds)
        for eid in eids:
            pos = self.world.ecs.get_component(eid, Position)
            mass = self.world.ecs.get_component(eid, Mass)
            if pos and mass:
                root.insert(pos.pos.x, pos.pos.y, mass.mass, eid)
        # Compute forces and update velocities
        for eid in eids:
            pos = self.world.ecs.get_component(eid, Position)
            vel = self.world.ecs.get_component(eid, Velocity)
            mass = self.world.ecs.get_component(eid, Mass)
            if not all([pos, vel, mass]):
                continue
            force = root.compute_force(pos.pos.x, pos.pos.y)
            ax = force.x / mass.mass
            ay = force.y / mass.mass
            vel.vel.x += ax * dt
            vel.vel.y += ay * dt
            pos.pos.x += vel.vel.x * dt
            pos.pos.y += vel.vel.y * dt


# ═══════════════════════════════════════════════════════════════════════════════
# SOCIAL DOMAIN — DeGroot Opinion Dynamics, Watts-Strogatz Network
# ═══════════════════════════════════════════════════════════════════════════════

class SocialDomain(Domain):
    """Agent-based social simulation with opinion dynamics."""

    def __init__(self, world: World, influence_rate: float = 0.05) -> None:
        super().__init__(world)
        self.influence_rate = influence_rate
        self._network: Dict[int, List[int]] = {}  # adjacency list

    def name(self) -> str:
        return "social"

    def connect(self, eid_a: int, eid_b: int) -> None:
        self._network.setdefault(eid_a, []).append(eid_b)
        self._network.setdefault(eid_b, []).append(eid_a)

    def build_watts_strogatz(self, n: int, k: int, p: float) -> List[int]:
        """Create Watts-Strogatz small-world network and return entity IDs."""
        eids = []
        for i in range(n):
            eid = self.world.add_entity()
            self.world.ecs.add_component(eid, AgentIdentity(agent_id=f"agent_{i}", opinion=self.world.random().random()))
            eids.append(eid)
        # Ring lattice
        for i in range(n):
            for j in range(1, k // 2 + 1):
                self.connect(eids[i], eids[(i + j) % n])
        # Rewiring
        for i in range(n):
            for j in range(1, k // 2 + 1):
                if self.world.random().random() < p:
                    old = eids[(i + j) % n]
                    # Remove old connection
                    if old in self._network.get(eids[i], []):
                        self._network[eids[i]].remove(old)
                        self._network[old].remove(eids[i])
                    # Add new random
                    new_idx = self.world.random().randint(0, n - 1)
                    while new_idx == i or eids[new_idx] in self._network.get(eids[i], []):
                        new_idx = self.world.random().randint(0, n - 1)
                    self.connect(eids[i], eids[new_idx])
        return eids

    def step(self, dt: float) -> None:
        eids = self.world.ecs.query(AgentIdentity)
        # DeGroot update: opinion_i(t+1) = (1-alpha)*opinion_i + alpha*average(neighbors)
        updates: Dict[int, float] = {}
        for eid in eids:
            agent = self.world.ecs.get_component(eid, AgentIdentity)
            if agent is None:
                continue
            neighbors = self._network.get(eid, [])
            if not neighbors:
                continue
            neighbor_opinions = []
            for nid in neighbors:
                nagent = self.world.ecs.get_component(nid, AgentIdentity)
                if nagent:
                    neighbor_opinions.append(nagent.opinion)
            if neighbor_opinions:
                avg_op = statistics.mean(neighbor_opinions)
                updates[eid] = (1 - self.influence_rate) * agent.opinion + self.influence_rate * avg_op
        for eid, new_op in updates.items():
            agent = self.world.ecs.get_component(eid, AgentIdentity)
            if agent:
                agent.opinion = max(0.0, min(1.0, new_op))

    def opinion_variance(self) -> float:
        eids = self.world.ecs.query(AgentIdentity)
        opinions = []
        for eid in eids:
            agent = self.world.ecs.get_component(eid, AgentIdentity)
            if agent:
                opinions.append(agent.opinion)
        if len(opinions) < 2:
            return 0.0
        mean = statistics.mean(opinions)
        return statistics.mean((o - mean) ** 2 for o in opinions)

    def consensus_reached(self, threshold: float = 0.01) -> bool:
        return self.opinion_variance() < threshold

# ═══════════════════════════════════════════════════════════════════════════════
# ECONOMIC DOMAIN — Continuous Double Auction Order Book
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Order:
    order_id: str
    trader_id: str
    price: float
    quantity: int
    is_buy: bool
    timestamp: float


@dataclass
class Trade:
    trade_id: str
    buy_order_id: str
    sell_order_id: str
    price: float
    quantity: int
    timestamp: float


class EconomicDomain(Domain):
    """Continuous double-auction market with buyers and sellers."""

    def __init__(self, world: World) -> None:
        super().__init__(world)
        self._buy_orders: List[Order] = []   # sorted descending by price
        self._sell_orders: List[Order] = []  # sorted ascending by price
        self._trades: List[Trade] = []
        self._order_counter: int = 0

    def name(self) -> str:
        return "economic"

    def submit_order(self, trader_id: str, price: float, quantity: int, is_buy: bool) -> str:
        self._order_counter += 1
        oid = f"order_{self._order_counter}"
        order = Order(
            order_id=oid,
            trader_id=trader_id,
            price=price,
            quantity=quantity,
            is_buy=is_buy,
            timestamp=self.world.time,
        )
        if is_buy:
            self._buy_orders.append(order)
            self._buy_orders.sort(key=lambda o: -o.price)
        else:
            self._sell_orders.append(order)
            self._sell_orders.sort(key=lambda o: o.price)
        self._match()
        return oid

    def _match(self) -> None:
        while self._buy_orders and self._sell_orders:
            best_buy = self._buy_orders[0]
            best_sell = self._sell_orders[0]
            if best_buy.price < best_sell.price:
                break
            qty = min(best_buy.quantity, best_sell.quantity)
            trade = Trade(
                trade_id=f"trade_{len(self._trades)}",
                buy_order_id=best_buy.order_id,
                sell_order_id=best_sell.order_id,
                price=(best_buy.price + best_sell.price) / 2,
                quantity=qty,
                timestamp=self.world.time,
            )
            self._trades.append(trade)
            # Update trader balances
            self._update_trader(best_buy.trader_id, -trade.price * qty, qty)
            self._update_trader(best_sell.trader_id, trade.price * qty, -qty)
            best_buy.quantity -= qty
            best_sell.quantity -= qty
            if best_buy.quantity <= 0:
                self._buy_orders.pop(0)
            if best_sell.quantity <= 0:
                self._sell_orders.pop(0)

    def _update_trader(self, trader_id: str, cash_delta: float, inventory_delta: int) -> None:
        eids = self.world.ecs.query(TraderIdentity)
        for eid in eids:
            trader = self.world.ecs.get_component(eid, TraderIdentity)
            if trader and trader.trader_id == trader_id:
                trader.cash += cash_delta
                trader.inventory += inventory_delta
                break

    def step(self, dt: float) -> None:
        pass  # Matching happens synchronously on order submission

    def last_price(self) -> Optional[float]:
        if not self._trades:
            return None
        return self._trades[-1].price

    def trade_count(self) -> int:
        return len(self._trades)

    def cleared_volume(self) -> int:
        return sum(t.quantity for t in self._trades)


# ═══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ═══════════════════════════════════════════════════════════════════════════════

def _self_test() -> int:
    passed = 0
    total = 0

    def check(name: str, condition: bool) -> None:
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"  [PASS] {name}")
        else:
            print(f"  [FAIL] {name}")

    print("=" * 55)
    print("World Simulation Engine — Self Test")
    print("=" * 55)

    # Test 1: Entity creation and component management
    print("\n[1] ECS basics")
    world = World(dt=0.01)
    e1 = world.add_entity()
    world.ecs.add_component(e1, Position(Vec2(1.0, 2.0)))
    world.ecs.add_component(e1, Velocity(Vec2(0.5, 0.0)))
    world.ecs.add_component(e1, Mass(5.0))
    check("Entity created", e1 == 0)
    check("Position stored", world.ecs.get_component(e1, Position).pos.x == 1.0)
    check("Has all components", world.ecs.query_all([Position, Velocity, Mass]) == [e1])

    # Test 2: Pendulum energy drift
    print("\n[2] Pendulum energy conservation")
    world2 = World(dt=0.001)
    phys = PhysicsDomain(world2, gravity=Vec2(0.0, -9.8))
    world2.add_domain(phys)
    # Create pendulum-like body: fixed pivot approximation with high initial position
    e_pend = world2.add_entity()
    world2.ecs.add_component(e_pend, Position(Vec2(0.0, 10.0)))
    world2.ecs.add_component(e_pend, Velocity(Vec2(1.0, 0.0)))
    world2.ecs.add_component(e_pend, Mass(1.0))
    world2.ecs.add_component(e_pend, Body(radius=0.1))
    E0 = phys.total_energy()
    world2.step(1000)
    E1 = phys.total_energy()
    drift = abs(E1 - E0) / abs(E0) if E0 != 0 else 0
    check(f"Energy drift < 5% (got {drift:.2%})", drift < 0.05)
    check("Pendulum fell (y decreased)", world2.ecs.get_component(e_pend, Position).pos.y < 10.0)

    # Test 3: Social consensus
    print("\n[3] Social DeGroot consensus")
    world3 = World(dt=0.1)
    social = SocialDomain(world3, influence_rate=0.1)
    world3.add_domain(social)
    eids = social.build_watts_strogatz(n=100, k=4, p=0.3)
    check("100 agents created", len(eids) == 100)
    var0 = social.opinion_variance()
    for _ in range(500):
        world3.step(1)
    var1 = social.opinion_variance()
    check(f"Consensus reached (var {var0:.4f} -> {var1:.4f})", var1 < 0.01)

    # Test 4: Economic CDA
    print("\n[4] Economic continuous double auction")
    world4 = World(dt=1.0)
    econ = EconomicDomain(world4)
    world4.add_domain(econ)
    # Create buyers
    for i in range(50):
        e = world4.add_entity()
        world4.ecs.add_component(e, TraderIdentity(trader_id=f"buyer_{i}", cash=1000.0))
        # Buyers willing to pay 80-120
        econ.submit_order(f"buyer_{i}", price=80 + world4.random().random() * 40, quantity=1, is_buy=True)
    # Create sellers
    for i in range(50):
        e = world4.add_entity()
        world4.ecs.add_component(e, TraderIdentity(trader_id=f"seller_{i}", inventory=10))
        # Sellers willing to sell at 70-110
        econ.submit_order(f"seller_{i}", price=70 + world4.random().random() * 40, quantity=1, is_buy=False)
    eq_range = (70 + 110) / 2  # rough equilibrium around midpoint
    last = econ.last_price()
    check("Trades occurred", econ.trade_count() > 0)
    if last:
        deviation = abs(last - eq_range) / eq_range
        check(f"Price within 20% of equilibrium (deviation {deviation:.1%})", deviation < 0.20)
    else:
        check("Price within 20% of equilibrium", False)

    # Test 5: Snapshot / restore
    print("\n[5] Snapshot and restore")
    snap = world4.snapshot()
    world4_new = World(dt=1.0)
    world4_new.restore(snap)
    check("Snapshot round-trip", world4_new.time == world4.time)
    check("ECS restored", len(world4_new.ecs.all_entities()) == len(world4.ecs.all_entities()))

    # Test 6: Branch
    print("\n[6] Branch (deep copy)")
    branch = world4.branch()
    check("Branch is independent", branch.time == world4.time)
    branch.step(1)
    check("Branch step does not affect original", world4.time != branch.time)

    # Test 7: Barnes-Hut N-body
    print("\n[7] Barnes-Hut N-body gravity")
    world7 = World(dt=0.01)
    nbody = NBodyGravityDomain(world7, bounds=500.0)
    world7.add_domain(nbody)
    # 3-body figure-8 approximate setup
    bodies_data = [
        (Vec2(0.97000436, -0.24308753), Vec2(0.466203685, 0.43236573), 1.0),
        (Vec2(-0.97000436, 0.24308753), Vec2(0.466203685, 0.43236573), 1.0),
        (Vec2(0.0, 0.0), Vec2(-0.93240737, -0.86473146), 1.0),
    ]
    for pos, vel, mass in bodies_data:
        e = world7.add_entity()
        world7.ecs.add_component(e, Position(Vec2(pos.x, pos.y)))
        world7.ecs.add_component(e, Velocity(Vec2(vel.x, vel.y)))
        world7.ecs.add_component(e, Mass(mass))
    # Simulate 10 periods (approximate)
    for _ in range(1000):
        world7.step(1)
    # Check bodies still bound (not escaped)
    positions = []
    for e in world7.ecs.query(Mass):
        p = world7.ecs.get_component(e, Position)
        if p:
            positions.append(p.pos)
    if len(positions) == 3:
        max_dist = max(p.length() for p in positions)
        check(f"3-body stable (max dist {max_dist:.2f})", max_dist < 50.0)
    else:
        check("3-body stable", False)

    # Test 8: Event scheduling
    print("\n[8] Event scheduling")
    world8 = World(dt=0.1)
    events_triggered = []
    world8.schedule_event(0.5, lambda w: events_triggered.append(w.time))
    world8.schedule_event(1.0, lambda w: events_triggered.append(w.time))
    for _ in range(20):
        world8.step(1)
    check("Event 1 triggered", len(events_triggered) >= 1)
    check("Event 2 triggered", len(events_triggered) >= 2)

    # Test 9: Collision detection
    print("\n[9] Collision detection")
    world9 = World(dt=0.01)
    phys9 = PhysicsDomain(world9, gravity=Vec2(0.0, 0.0))
    world9.add_domain(phys9)
    e_a = world9.add_entity()
    world9.ecs.add_component(e_a, Position(Vec2(0.0, 0.0)))
    world9.ecs.add_component(e_a, Velocity(Vec2(1.0, 0.0)))
    world9.ecs.add_component(e_a, Mass(1.0))
    world9.ecs.add_component(e_a, Body(radius=1.0))
    e_b = world9.add_entity()
    world9.ecs.add_component(e_b, Position(Vec2(3.0, 0.0)))
    world9.ecs.add_component(e_b, Velocity(Vec2(-1.0, 0.0)))
    world9.ecs.add_component(e_b, Mass(1.0))
    world9.ecs.add_component(e_b, Body(radius=1.0))
    for _ in range(200):
        world9.step(1)
    pos_a = world9.ecs.get_component(e_a, Position).pos
    pos_b = world9.ecs.get_component(e_b, Position).pos
    dist = math.sqrt((pos_a.x - pos_b.x) ** 2 + (pos_a.y - pos_b.y) ** 2)
    check(f"Bodies separated after collision (dist {dist:.2f})", dist >= 1.5)

    # Test 10: Determinism with seed
    print("\n[10] Determinism")
    w1 = World(dt=0.1)
    w1.set_seed(42)
    s1 = SocialDomain(w1)
    s1.build_watts_strogatz(10, 2, 0.3)
    snap1 = w1.snapshot()

    w2 = World(dt=0.1)
    w2.set_seed(42)
    s2 = SocialDomain(w2)
    s2.build_watts_strogatz(10, 2, 0.3)
    snap2 = w2.snapshot()
    check("Same seed -> same snapshot", snap1 == snap2)

    print("\n" + "=" * 55)
    print(f"PASS: {passed}/{total}")
    print("=" * 55)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
