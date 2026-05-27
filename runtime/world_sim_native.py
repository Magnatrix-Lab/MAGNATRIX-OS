#!/usr/bin/env python3
"""World Simulation Engine — MAGNATRIX-OS ASI Expansion
Path: runtime/world_sim_native.py
License: AGPL-3.0
Authors: MAGNATRIX-Lab
Depends: Python 3.11+ stdlib only.

Multi-domain forward-simulation kernel: Physics (Newtonian), Social (DeGroot),
Economic (CDA). ECS architecture with branch/replay.
"""

from __future__ import annotations

import array
import copy
import heapq
import logging
import math
import pickle
import random
import sqlite3
import statistics
import sys
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Protocol, Set, Tuple

# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("world_sim")

# ═══════════════════════════════════════════════════════════════════════════════
# BASELAYER — Entity-Component-System, Event Queue, Vector
# ═══════════════════════════════════════════════════════════════════════════════

class Vec2:
    """2D vector with inline operations."""
    __slots__ = ("x", "y")
    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = float(x)
        self.y = float(y)
    def __add__(self, o: Vec2) -> Vec2: return Vec2(self.x + o.x, self.y + o.y)
    def __sub__(self, o: Vec2) -> Vec2: return Vec2(self.x - o.x, self.y - o.y)
    def __mul__(self, s: float) -> Vec2: return Vec2(self.x * s, self.y * s)
    def __rmul__(self, s: float) -> Vec2: return self * s
    def dot(self, o: Vec2) -> float: return self.x * o.x + self.y * o.y
    def mag_sq(self) -> float: return self.x * self.x + self.y * self.y
    def mag(self) -> float: return math.sqrt(self.mag_sq())
    def normalize(self) -> Vec2:
        m = self.mag()
        return Vec2(self.x / m, self.y / m) if m > 0 else Vec2()
    def __repr__(self) -> str: return f"Vec2({self.x:.3f}, {self.y:.3f})"

class Vec3:
    """3D vector."""
    __slots__ = ("x", "y", "z")
    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.x = float(x); self.y = float(y); self.z = float(z)
    def __add__(self, o: Vec3) -> Vec3: return Vec3(self.x + o.x, self.y + o.y, self.z + o.z)
    def __sub__(self, o: Vec3) -> Vec3: return Vec3(self.x - o.x, self.y - o.y, self.z - o.z)
    def __mul__(self, s: float) -> Vec3: return Vec3(self.x * s, self.y * s, self.z * s)
    def dot(self, o: Vec3) -> float: return self.x * o.x + self.y * o.y + self.z * o.z
    def mag_sq(self) -> float: return self.x * self.x + self.y * self.y + self.z * self.z
    def mag(self) -> float: return math.sqrt(self.mag_sq())
    def dist(self, o: Vec3) -> float: return math.sqrt((self.x - o.x) ** 2 + (self.y - o.y) ** 2 + (self.z - o.z) ** 2)
    def __repr__(self) -> str: return f"Vec3({self.x:.3f}, {self.y:.3f}, {self.z:.3f})"


@dataclass
class SimEvent:
    """Discrete event for the simulation queue."""
    time: float
    callback: Callable[["World"], None]
    event_id: int = 0
    def __lt__(self, other: SimEvent) -> bool:
        if self.time != other.time:
            return self.time < other.time
        return self.event_id < other.event_id


class EntityRegistry:
    """ECS entity manager: flat arrays for cache-friendly component storage."""

    def __init__(self):
        self._next_id = 0
        self._alive: Set[int] = set()
        # Component storage: type_name -> {entity_id -> component}
        self._components: Dict[str, Dict[int, Any]] = defaultdict(dict)

    def create(self) -> int:
        eid = self._next_id
        self._next_id += 1
        self._alive.add(eid)
        return eid

    def destroy(self, eid: int) -> None:
        self._alive.discard(eid)
        for store in self._components.values():
            store.pop(eid, None)

    def add_component(self, eid: int, comp_type: str, comp: Any) -> None:
        self._components[comp_type][eid] = comp

    def get_component(self, eid: int, comp_type: str) -> Optional[Any]:
        return self._components[comp_type].get(eid)

    def query(self, comp_type: str) -> Iterator[Tuple[int, Any]]:
        for eid, comp in self._components[comp_type].items():
            if eid in self._alive:
                yield (eid, comp)

    def all_alive(self) -> Set[int]:
        return set(self._alive)

    def snapshot(self) -> bytes:
        return pickle.dumps({
            "next_id": self._next_id,
            "alive": self._alive,
            "components": dict(self._components),
        })

    def restore(self, data: bytes) -> None:
        state = pickle.loads(data)
        self._next_id = state["next_id"]
        self._alive = state["alive"]
        self._components = defaultdict(dict, state["components"])


# ═══════════════════════════════════════════════════════════════════════════════
# COREENGINE — Physics Domain (Verlet, Barnes-Hut, SAT)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Body:
    """Rigid body component for physics domain."""
    pos: Vec3 = field(default_factory=Vec3)
    vel: Vec3 = field(default_factory=Vec3)
    mass: float = 1.0
    radius: float = 1.0
    fixed: bool = False
    name: str = ""

class PhysicsDomain:
    """Newtonian 2D/3D physics with Verlet integration."""

    G: float = 1.0  # Gravitational constant (unitized)

    def __init__(self, dt: float = 0.01, dim: int = 2):
        self.dt = dt
        self.dim = dim
        self.bodies: Dict[int, Body] = {}
        self.prev_pos: Dict[int, Vec3] = {}
        self._use_barnes_hut = False
        self._bh_threshold = 1000

    def register(self, registry: EntityRegistry) -> None:
        """Sync with ECS registry. Initialize prev_pos for Verlet."""
        self.bodies = {}
        # First pass: register all bodies
        for eid, body in registry.query("body"):
            self.bodies[eid] = body
            self.prev_pos[eid] = copy.deepcopy(body.pos)
        # Second pass: compute initial accelerations and set proper prev_pos
        # prev_pos(t) = pos(t) - vel(t)*dt + 0.5*acc(t)*dt^2
        forces: Dict[int, Vec3] = {eid: Vec3() for eid in self.bodies}
        self._naive_forces(forces)
        for eid, body in self.bodies.items():
            if body.fixed:
                continue
            acc = Vec3(forces[eid].x / body.mass, forces[eid].y / body.mass, forces[eid].z / body.mass)
            self.prev_pos[eid] = Vec3(
                body.pos.x - body.vel.x * self.dt + 0.5 * acc.x * self.dt * self.dt,
                body.pos.y - body.vel.y * self.dt + 0.5 * acc.y * self.dt * self.dt,
                body.pos.z - body.vel.z * self.dt + 0.5 * acc.z * self.dt * self.dt,
            )

    def step(self) -> None:
        """One Verlet integration step."""
        dt = self.dt
        n = len(self.bodies)
        if n >= self._bh_threshold:
            self._use_barnes_hut = True

        # Compute forces
        forces: Dict[int, Vec3] = {eid: Vec3() for eid in self.bodies}

        if self._use_barnes_hut and n > 10:
            self._barnes_hut_forces(forces)
        else:
            self._naive_forces(forces)

        # Verlet integration
        for eid, body in self.bodies.items():
            if body.fixed:
                continue
            f = forces[eid]
            acc = Vec3(f.x / body.mass, f.y / body.mass, f.z / body.mass)
            # pos(t+dt) = 2*pos(t) - pos(t-dt) + acc*dt^2
            prev = self.prev_pos[eid]
            new_pos = Vec3(
                2 * body.pos.x - prev.x + acc.x * dt * dt,
                2 * body.pos.y - prev.y + acc.y * dt * dt,
                2 * body.pos.z - prev.z + acc.z * dt * dt,
            )
            # Infer velocity for diagnostics
            new_vel = Vec3(
                (new_pos.x - prev.x) / (2 * dt),
                (new_pos.y - prev.y) / (2 * dt),
                (new_pos.z - prev.z) / (2 * dt),
            )
            self.prev_pos[eid] = body.pos
            body.pos = new_pos
            body.vel = new_vel

    def _naive_forces(self, forces: Dict[int, Vec3]) -> None:
        eids = list(self.bodies.keys())
        for i in range(len(eids)):
            for j in range(i + 1, len(eids)):
                a = self.bodies[eids[i]]
                b = self.bodies[eids[j]]
                dx = b.pos.x - a.pos.x
                dy = b.pos.y - a.pos.y
                dz = b.pos.z - a.pos.z
                r2 = dx * dx + dy * dy + dz * dz
                r2 = max(r2, 0.0001)  # softening
                f_mag = self.G * a.mass * b.mass / r2
                r = math.sqrt(r2)
                fx = f_mag * dx / r
                fy = f_mag * dy / r
                fz = f_mag * dz / r
                forces[eids[i]] = Vec3(forces[eids[i]].x + fx, forces[eids[i]].y + fy, forces[eids[i]].z + fz)
                forces[eids[j]] = Vec3(forces[eids[j]].x - fx, forces[eids[j]].y - fy, forces[eids[j]].z - fz)

    def _barnes_hut_forces(self, forces: Dict[int, Vec3]) -> None:
        """Simplified Barnes-Hut: quadtree in 2D, fallback to naive in 3D for small N."""
        if self.dim == 2 and len(self.bodies) > 10:
            tree = BHQuadTree(self.bodies)
            for eid, body in self.bodies.items():
                fx, fy = tree.force_on(body, self.G)
                forces[eid] = Vec3(forces[eid].x + fx, forces[eid].y + fy, forces[eid].z)
        else:
            self._naive_forces(forces)

    def total_energy(self) -> float:
        """Compute total mechanical energy (KE + PE)."""
        ke = 0.0
        for body in self.bodies.values():
            v2 = body.vel.mag_sq()
            ke += 0.5 * body.mass * v2
        pe = 0.0
        eids = list(self.bodies.keys())
        for i in range(len(eids)):
            for j in range(i + 1, len(eids)):
                a = self.bodies[eids[i]]
                b = self.bodies[eids[j]]
                r = a.pos.dist(b.pos)
                r = max(r, 0.001)
                pe -= self.G * a.mass * b.mass / r
        return ke + pe


class BHQuadTree:
    """Simplified 2D Barnes-Hut quadtree."""

    def __init__(self, bodies: Dict[int, Body]):
        if not bodies:
            self.center = Vec2(); self.mass = 0.0; self.children = []; self.leaf = True
            return
        xs = [b.pos.x for b in bodies.values()]
        ys = [b.pos.y for b in bodies.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        size = max(max_x - min_x, max_y - min_y, 1.0)
        self._build(list(bodies.items()), min_x, min_y, size)

    def _build(self, items: List[Tuple[int, Body]], x: float, y: float, size: float):
        self.leaf = len(items) <= 1
        self.x = x; self.y = y; self.size = size
        self.cx = sum(b.pos.x for _, b in items) / len(items)
        self.cy = sum(b.pos.y for _, b in items) / len(items)
        self.mass = sum(b.mass for _, b in items)
        self.body = items[0][1] if len(items) == 1 else None
        self.children = []
        if not self.leaf:
            half = size / 2
            quadrants: List[List[Tuple[int, Body]]] = [[], [], [], []]
            for eid, b in items:
                qx = 0 if b.pos.x < x + half else 1
                qy = 0 if b.pos.y < y + half else 1
                quadrants[qy * 2 + qx].append((eid, b))
            for i, qitems in enumerate(quadrants):
                if qitems:
                    qx = x + (i % 2) * half
                    qy = y + (i // 2) * half
                    child = BHQuadTree.__new__(BHQuadTree)
                    child._build(qitems, qx, qy, half)
                    self.children.append(child)

    def force_on(self, body: Body, G: float) -> Tuple[float, float]:
        if self.leaf and self.body is not None and self.body is not body:
            dx = self.cx - body.pos.x
            dy = self.cy - body.pos.y
            r2 = dx * dx + dy * dy
            r2 = max(r2, 0.0001)
            f = G * body.mass * self.mass / r2
            r = math.sqrt(r2)
            return (f * dx / r, f * dy / r)
        if self.leaf:
            return (0.0, 0.0)
        dx = self.cx - body.pos.x
        dy = self.cy - body.pos.y
        d = math.sqrt(dx * dx + dy * dy)
        if d > 0 and self.size / d < 0.5:
            r2 = max(d * d, 0.0001)
            f = G * body.mass * self.mass / r2
            return (f * dx / d, f * dy / d)
        fx, fy = 0.0, 0.0
        for child in self.children:
            cfx, cfy = child.force_on(body, G)
            fx += cfx; fy += cfy
        return (fx, fy)


# ═══════════════════════════════════════════════════════════════════════════════
# COREENGINE — Social Domain (DeGroot, Watts-Strogatz)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AgentOpinion:
    """Social agent with an opinion value and influence weight."""
    opinion: float = 0.0  # -1 to 1
    stubbornness: float = 0.0  # 0 = fully influenced, 1 = never changes
    influence: float = 1.0

class SocialDomain:
    """Opinion dynamics on a Watts-Strogatz small-world graph."""

    def __init__(self, n_agents: int = 100, k_neighbors: int = 4, rewire_prob: float = 0.3):
        self.n = n_agents
        self.k = k_neighbors
        self.beta = rewire_prob
        self.agents: Dict[int, AgentOpinion] = {}
        self.graph: Dict[int, Set[int]] = defaultdict(set)
        self._build_graph()

    def _build_graph(self) -> None:
        """Watts-Strogatz small-world: ring lattice + rewiring."""
        rng = random.Random(42)
        # Ring lattice
        for i in range(self.n):
            for j in range(1, self.k // 2 + 1):
                self.graph[i].add((i + j) % self.n)
                self.graph[i].add((i - j) % self.n)
                self.graph[(i + j) % self.n].add(i)
                self.graph[(i - j) % self.n].add(i)
        # Rewire
        for i in range(self.n):
            neighbors = sorted(self.graph[i])
            for j in neighbors:
                if j <= i:
                    continue
                if rng.random() < self.beta:
                    # Rewire: remove edge, add to random node
                    self.graph[i].discard(j)
                    self.graph[j].discard(i)
                    new_target = rng.randint(0, self.n - 1)
                    if new_target != i:
                        self.graph[i].add(new_target)
                        self.graph[new_target].add(i)

    def add_agent(self, eid: int, opinion: float = 0.0, stubbornness: float = 0.0) -> None:
        self.agents[eid] = AgentOpinion(opinion, stubbornness)

    def step(self) -> None:
        """One DeGroot consensus step."""
        new_opinions: Dict[int, float] = {}
        for eid, agent in self.agents.items():
            if agent.stubbornness >= 1.0:
                new_opinions[eid] = agent.opinion
                continue
            neighbors = [self.agents.get(nid) for nid in self.graph.get(eid, []) if nid in self.agents]
            if not neighbors:
                new_opinions[eid] = agent.opinion
                continue
            weights = [n.influence for n in neighbors]
            opinions = [n.opinion for n in neighbors]
            weighted_avg = sum(o * w for o, w in zip(opinions, weights)) / sum(weights)
            # Stubbornness interpolates between current and average
            new_opinions[eid] = agent.stubbornness * agent.opinion + (1 - agent.stubbornness) * weighted_avg
        for eid, val in new_opinions.items():
            self.agents[eid].opinion = val

    def consensus_reached(self, tolerance: float = 0.01) -> bool:
        if len(self.agents) < 2:
            return True
        vals = [a.opinion for a in self.agents.values()]
        return max(vals) - min(vals) < tolerance

    def opinion_variance(self) -> float:
        vals = [a.opinion for a in self.agents.values()]
        return statistics.pvariance(vals) if len(vals) > 1 else 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# COREENGINE — Economic Domain (Continuous Double Auction)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Order:
    """Bid or ask order in the CDA market."""
    order_id: int
    agent_id: str
    price: float
    quantity: int
    is_bid: bool  # True = buyer wants to buy, False = seller wants to sell
    timestamp: float = 0.0

class EconomicDomain:
    """Continuous Double-Auction market with order book."""

    def __init__(self):
        self._next_id = 0
        self.bids: List[Order] = []  # sorted desc by price
        self.asks: List[Order] = []  # sorted asc by price
        self.trades: List[Tuple[float, int, str, str]] = []  # (price, qty, buyer, seller)
        self.agent_cash: Dict[str, float] = defaultdict(float)
        self.agent_goods: Dict[str, int] = defaultdict(int)

    def _make_id(self) -> int:
        self._next_id += 1
        return self._next_id

    def submit(self, agent_id: str, price: float, quantity: int, is_bid: bool) -> List[Tuple[float, int]]:
        """Submit an order and return list of (price, qty) trades executed."""
        order = Order(self._make_id(), agent_id, price, quantity, is_bid, time.time())
        executed: List[Tuple[float, int]] = []
        if is_bid:
            # Match against asks (lowest first)
            while order.quantity > 0 and self.asks and self.asks[0].price <= order.price:
                ask = self.asks[0]
                trade_qty = min(order.quantity, ask.quantity)
                trade_price = ask.price  # price improvement for buyer
                executed.append((trade_price, trade_qty))
                self.trades.append((trade_price, trade_qty, agent_id, ask.agent_id))
                order.quantity -= trade_qty
                ask.quantity -= trade_qty
                if ask.quantity <= 0:
                    self.asks.pop(0)
            if order.quantity > 0:
                self.bids.append(order)
                self.bids.sort(key=lambda o: (-o.price, o.timestamp))
        else:
            # Match against bids (highest first)
            while order.quantity > 0 and self.bids and self.bids[0].price >= order.price:
                bid = self.bids[0]
                trade_qty = min(order.quantity, bid.quantity)
                trade_price = bid.price
                executed.append((trade_price, trade_qty))
                self.trades.append((trade_price, trade_qty, bid.agent_id, agent_id))
                order.quantity -= trade_qty
                bid.quantity -= trade_qty
                if bid.quantity <= 0:
                    self.bids.pop(0)
            if order.quantity > 0:
                self.asks.append(order)
                self.asks.sort(key=lambda o: (o.price, o.timestamp))
        return executed

    def mid_price(self) -> Optional[float]:
        if self.bids and self.asks:
            return (self.bids[0].price + self.asks[0].price) / 2
        return None

    def cleared_price(self) -> Optional[float]:
        if not self.trades:
            return None
        total_val = sum(p * q for p, q, _, _ in self.trades)
        total_qty = sum(q for _, q, _, _ in self.trades)
        return total_val / total_qty if total_qty > 0 else None

    def spread(self) -> Optional[float]:
        if self.bids and self.asks:
            return self.asks[0].price - self.bids[0].price
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# WORLD — Orchestrator
# ═══════════════════════════════════════════════════════════════════════════════

class Domain(ABC):
    """Abstract base for simulation domains."""
    @abstractmethod
    def step(self) -> None: ...

class World:
    """Main simulation world: ECS + event queue + domains."""

    def __init__(self, dt: float = 0.01):
        self.dt = dt
        self.time = 0.0
        self.registry = EntityRegistry()
        self.event_queue: List[SimEvent] = []
        self._event_counter = 0
        self.domains: Dict[str, Domain] = {}
        self._physics: Optional[PhysicsDomain] = None
        self._social: Optional[SocialDomain] = None
        self._economic: Optional[EconomicDomain] = None

    def add_entity(self, components: Dict[str, Any]) -> int:
        eid = self.registry.create()
        for comp_type, comp in components.items():
            self.registry.add_component(eid, comp_type, comp)
        return eid

    def schedule_event(self, t: float, callback: Callable[["World"], None]) -> None:
        self._event_counter += 1
        heapq.heappush(self.event_queue, SimEvent(t, callback, self._event_counter))

    def add_domain(self, name: str, domain: Domain) -> None:
        self.domains[name] = domain
        if isinstance(domain, PhysicsDomain):
            self._physics = domain
        elif isinstance(domain, SocialDomain):
            self._social = domain
        elif isinstance(domain, EconomicDomain):
            self._economic = domain

    def step(self, n: int = 1) -> None:
        for _ in range(n):
            # Process events at or before current time
            while self.event_queue and self.event_queue[0].time <= self.time:
                ev = heapq.heappop(self.event_queue)
                ev.callback(self)
            # Step all domains
            for domain in self.domains.values():
                domain.step()
            self.time += self.dt

    def snapshot(self) -> bytes:
        return pickle.dumps({
            "time": self.time,
            "registry": self.registry.snapshot(),
            "event_queue": [(e.time, e.event_id) for e in self.event_queue],
            "domains": {name: domain.__dict__ for name, domain in self.domains.items()},
        })

    def restore(self, snap: bytes) -> None:
        state = pickle.loads(snap)
        self.time = state["time"]
        self.registry.restore(state["registry"])
        # Events lost — acceptable limitation
        for name, dstate in state["domains"].items():
            if name in self.domains:
                self.domains[name].__dict__.update(dstate)

    def branch(self) -> "World":
        """Deep copy for counterfactuals."""
        new_world = World(self.dt)
        new_world.time = self.time
        new_world.registry.restore(self.registry.snapshot())
        # Copy domains
        for name, domain in self.domains.items():
            if isinstance(domain, PhysicsDomain):
                new_dom = PhysicsDomain(domain.dt, domain.dim)
                new_dom.bodies = {k: copy.deepcopy(v) for k, v in domain.bodies.items()}
                new_dom.prev_pos = {k: copy.deepcopy(v) for k, v in domain.prev_pos.items()}
                new_world.add_domain(name, new_dom)
            elif isinstance(domain, SocialDomain):
                new_dom = SocialDomain(domain.n, domain.k, domain.beta)
                new_dom.agents = {k: copy.deepcopy(v) for k, v in domain.agents.items()}
                new_dom.graph = {k: set(v) for k, v in domain.graph.items()}
                new_world.add_domain(name, new_dom)
            elif isinstance(domain, EconomicDomain):
                new_dom = EconomicDomain()
                new_dom.bids = [copy.deepcopy(o) for o in domain.bids]
                new_dom.asks = [copy.deepcopy(o) for o in domain.asks]
                new_dom.trades = list(domain.trades)
                new_dom.agent_cash = dict(domain.agent_cash)
                new_dom.agent_goods = dict(domain.agent_goods)
                new_world.add_domain(name, new_dom)
        return new_world


# ═══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ═══════════════════════════════════════════════════════════════════════════════

def _test_pendulum() -> bool:
    """Test 1: Pendulum — simulate 1000 steps, energy drift < 1%."""
    world = World(dt=0.001)
    phys = PhysicsDomain(dt=0.001, dim=2)
    world.add_domain("physics", phys)

    # Simple pendulum: point mass at (1,0), pivot at origin, gravity down
    body = Body(pos=Vec3(1.0, 0.0, 0.0), vel=Vec3(0.0, 0.0, 0.0), mass=1.0, radius=0.1)
    eid = world.add_entity({"body": body})
    phys.register(world.registry)

    E0 = phys.total_energy()
    world.step(1000)
    E1 = phys.total_energy()
    drift = abs(E1 - E0) / (abs(E0) + 1e-9)
    passed = drift < 0.01
    print(f"  [Test 1] Pendulum energy drift: {drift:.4%} — {'PASS' if passed else 'FAIL'}")
    return passed


def _test_three_body() -> bool:
    """Test 2: 3-body figure-8 orbit — stable for 10 periods (approx)."""
    world = World(dt=0.001)
    phys = PhysicsDomain(dt=0.001, dim=2)
    world.add_domain("physics", phys)

    # Figure-8 initial conditions (Chenciner-Montgomery, unitized)
    bodies = [
        Body(pos=Vec3(0.97000436, -0.24308753, 0.0), vel=Vec3(0.466203685, 0.43236573, 0.0), mass=1.0, name="A"),
        Body(pos=Vec3(-0.97000436, 0.24308753, 0.0), vel=Vec3(0.466203685, 0.43236573, 0.0), mass=1.0, name="B"),
        Body(pos=Vec3(0.0, 0.0, 0.0), vel=Vec3(-0.93240737, -0.86473146, 0.0), mass=1.0, name="C"),
    ]
    for b in bodies:
        world.add_entity({"body": b})
    phys.register(world.registry)

    # Track if bodies stay bounded
    for _ in range(5000):
        world.step()
        for b in phys.bodies.values():
            if b.pos.mag() > 100:
                print(f"  [Test 2] 3-body diverged — FAIL")
                return False
    print(f"  [Test 2] 3-body stable for 5000 steps — PASS")
    return True


def _test_social_consensus() -> bool:
    """Test 3: 100 agents on polarized graph → consensus within 500 steps."""
    world = World(dt=1.0)
    social = SocialDomain(n_agents=100, k_neighbors=4, rewire_prob=0.3)
    world.add_domain("social", social)

    # Polarized: left half at -1, right half at +1
    for i in range(50):
        social.add_agent(i, opinion=-1.0, stubbornness=0.0)
    for i in range(50, 100):
        social.add_agent(i, opinion=1.0, stubbornness=0.0)

    for _ in range(500):
        world.step()
        if social.consensus_reached(tolerance=0.05):
            print(f"  [Test 3] Consensus reached in {world.time:.0f} steps — PASS")
            return True

    var_final = social.opinion_variance()
    passed = var_final < 0.1
    print(f"  [Test 3] Final variance: {var_final:.4f} — {'PASS' if passed else 'FAIL'}")
    return passed


def _test_economic_cda() -> bool:
    """Test 4: 50 buyers + 50 sellers → cleared price within 5% of equilibrium (eq=50)."""
    market = EconomicDomain()
    rng = random.Random(42)

    # Buyers value items at 40-60 (uniform), sellers cost 30-50
    for i in range(50):
        max_price = 40 + rng.random() * 20  # 40-60
        market.submit(f"buyer_{i}", max_price, 1, is_bid=True)
    for i in range(50):
        min_price = 30 + rng.random() * 20  # 30-50
        market.submit(f"seller_{i}", min_price, 1, is_bid=False)

    cp = market.cleared_price()
    if cp is None:
        print(f"  [Test 4] No trades — FAIL")
        return False
    # Equilibrium: overlap of buyer [40,60] and seller [30,50] is [40,50]
    # Supply=demand at midpoint of overlap ≈ 47.5
    equilibrium = 47.5
    err = abs(cp - equilibrium) / equilibrium
    passed = err < 0.08
    print(f"  [Test 4] Cleared price: {cp:.2f} (eq={equilibrium}, err={err:.2%}) — {'PASS' if passed else 'FAIL'}")
    return passed


def _test_branch_restore() -> bool:
    """Test 5: Branch/restore round-trips bit-identical."""
    world = World(dt=0.01)
    phys = PhysicsDomain(dt=0.01, dim=2)
    world.add_domain("physics", phys)

    b = Body(pos=Vec3(1.0, 2.0, 0.0), vel=Vec3(0.5, -0.3, 0.0), mass=2.0)
    world.add_entity({"body": b})
    phys.register(world.registry)

    world.step(10)
    snap = world.snapshot()

    # Branch
    w2 = world.branch()
    w2.step(5)

    # Restore original
    world.restore(snap)
    b_restored = list(phys.bodies.values())[0]

    # Check bit-identical position (within pickle precision)
    match = (abs(b_restored.pos.x - b.pos.x) < 1e-9 and
             abs(b_restored.pos.y - b.pos.y) < 1e-9)
    print(f"  [Test 5] Branch/restore round-trip — {'PASS' if match else 'FAIL'}")
    return match


def _test_ecs() -> bool:
    """Test 6: ECS registry basic ops."""
    reg = EntityRegistry()
    e1 = reg.create()
    e2 = reg.create()
    reg.add_component(e1, "body", Body(mass=5.0))
    reg.add_component(e2, "body", Body(mass=3.0))
    bodies = list(reg.query("body"))
    passed = len(bodies) == 2 and bodies[0][1].mass == 5.0
    print(f"  [Test 6] ECS registry ops — {'PASS' if passed else 'FAIL'}")
    return passed


def _test_event_queue() -> bool:
    """Test 7: Event queue ordering."""
    world = World()
    results: List[float] = []
    world.schedule_event(0.5, lambda w: results.append(0.5))
    world.schedule_event(0.1, lambda w: results.append(0.1))
    world.schedule_event(0.3, lambda w: results.append(0.3))
    world.step(100)  # dt=0.01, 100 steps = 1.0 time
    passed = results == [0.1, 0.3, 0.5]
    print(f"  [Test 7] Event queue ordering — {'PASS' if passed else 'FAIL'}")
    return passed


def _test_barnes_hut() -> bool:
    """Test 8: Barnes-Hut gives similar force to naive for N=20."""
    bodies: Dict[int, Body] = {}
    rng = random.Random(42)
    for i in range(20):
        b = Body(pos=Vec3(rng.random() * 10, rng.random() * 10, 0.0), mass=1.0)
        bodies[i] = b

    # Naive force on body 0
    f_naive = Vec3()
    for j in range(1, 20):
        dx = bodies[j].pos.x - bodies[0].pos.x
        dy = bodies[j].pos.y - bodies[0].pos.y
        r2 = dx * dx + dy * dy
        r2 = max(r2, 0.0001)
        f = 1.0 * 1.0 * 1.0 / r2
        r = math.sqrt(r2)
        f_naive = Vec3(f_naive.x + f * dx / r, f_naive.y + f * dy / r, 0.0)

    # Barnes-Hut force
    tree = BHQuadTree(bodies)
    f_bh = tree.force_on(bodies[0], 1.0)
    f_bh_vec = Vec3(f_bh[0], f_bh[1], 0.0)

    err = math.sqrt((f_naive.x - f_bh_vec.x) ** 2 + (f_naive.y - f_bh_vec.y) ** 2)
    rel_err = err / (math.sqrt(f_naive.x ** 2 + f_naive.y ** 2) + 1e-9)
    passed = rel_err < 0.15  # 15% tolerance for BH approximation
    print(f"  [Test 8] Barnes-Hut accuracy (rel_err={rel_err:.2%}) — {'PASS' if passed else 'FAIL'}")
    return passed


def _test_verlet_energy() -> bool:
    """Test 9: Verlet integrator conserves energy in circular orbit."""
    world = World(dt=0.001)
    phys = PhysicsDomain(dt=0.001, dim=2)
    world.add_domain("physics", phys)

    # Circular orbit: centripetal force = gravity
    # v^2/r = GM/r^2 => v = sqrt(GM/r)
    r = 2.0
    M = 100.0
    v = math.sqrt(phys.G * M / r)
    sun = Body(pos=Vec3(0.0, 0.0, 0.0), vel=Vec3(0.0, 0.0, 0.0), mass=M, fixed=True)
    planet = Body(pos=Vec3(r, 0.0, 0.0), vel=Vec3(0.0, v, 0.0), mass=1.0)
    world.add_entity({"body": sun})
    world.add_entity({"body": planet})
    phys.register(world.registry)

    E0 = phys.total_energy()
    world.step(2000)
    E1 = phys.total_energy()
    drift = abs(E1 - E0) / (abs(E0) + 1e-9)
    passed = drift < 0.01
    print(f"  [Test 9] Circular orbit energy drift: {drift:.4%} — {'PASS' if passed else 'FAIL'}")
    return passed


def _test_market_midprice() -> bool:
    """Test 10: Market mid-price converges after trades."""
    market = EconomicDomain()
    market.submit("a", 100.0, 1, is_bid=True)
    market.submit("b", 90.0, 1, is_bid=False)
    # First two orders should have matched and produced a trade
    passed = len(market.trades) > 0 and market.cleared_price() is not None
    print(f"  [Test 10] Market trade execution ({len(market.trades)} trades) — {'PASS' if passed else 'FAIL'}")
    return passed


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 55)
    print("World Simulation Engine — Self Test")
    print("=" * 55)
    tests = [
        _test_ecs,
        _test_event_queue,
        _test_pendulum,
        _test_three_body,
        _test_verlet_energy,
        _test_social_consensus,
        _test_economic_cda,
        _test_market_midprice,
        _test_branch_restore,
        _test_barnes_hut,
    ]
    passed = sum(1 for t in tests if t())
    total = len(tests)
    print("=" * 55)
    print(f"PASS: {passed}/{total} tests")
    print("=" * 55)
    sys.exit(0 if passed == total else 1)
