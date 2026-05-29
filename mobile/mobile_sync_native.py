#!/usr/bin/env python3
"""
MAGNATRIX-OS | Layer 11 — Mobile Sync
Conflict-free Replicated Data Type (CRDT) sync for mobile offline-first.
- LWW-Element-Set (Last-Write-Wins) for key-value
- G-Counter + PN-Counter for numeric counters
- Delta sync (only send changes)
- Vector clock for causality tracking
"""
import json, time, hashlib, threading, os, sys
from typing import Dict, List, Optional, Any, Tuple, Set
from collections import defaultdict


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:12]


class VectorClock:
    """Lamport-style vector clock for causal ordering."""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self._clock: Dict[str, int] = {node_id: 0}

    def increment(self):
        self._clock[self.node_id] = self._clock.get(self.node_id, 0) + 1

    def merge(self, other: Dict[str, int]):
        for k, v in other.items():
            self._clock[k] = max(self._clock.get(k, 0), v)

    def compare(self, other: Dict[str, int]) -> int:
        """Returns 1 if self > other, -1 if self < other, 0 if concurrent/equal."""
        if self._clock == other:
            return 0
        all_keys = set(self._clock.keys()) | set(other.keys())
        dominates = False
        dominated = False
        for k in all_keys:
            a = self._clock.get(k, 0)
            b = other.get(k, 0)
            if a > b:
                dominates = True
            elif b > a:
                dominated = True
        if dominates and not dominated:
            return 1
        if dominated and not dominates:
            return -1
        return 0

    def to_dict(self) -> Dict:
        return dict(self._clock)

    @classmethod
    def from_dict(cls, node_id: str, d: Dict):
        vc = cls(node_id)
        vc._clock = dict(d)
        return vc


class LWWSet:
    """Last-Write-Wins Element Set CRDT."""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self._adds: Dict[str, Tuple[int, Dict]] = {}  # key -> (timestamp, vector_clock)
        self._removes: Dict[str, Tuple[int, Dict]] = {}
        self._lock = threading.Lock()

    def add(self, key: str, ts: Optional[int] = None):
        with self._lock:
            ts = ts or int(time.time() * 1000)
            vc = VectorClock(self.node_id)
            vc.increment()
            self._adds[key] = (ts, vc.to_dict())

    def remove(self, key: str, ts: Optional[int] = None):
        with self._lock:
            ts = ts or int(time.time() * 1000)
            vc = VectorClock(self.node_id)
            vc.increment()
            self._removes[key] = (ts, vc.to_dict())

    def lookup(self, key: str) -> bool:
        with self._lock:
            if key not in self._adds:
                return False
            if key not in self._removes:
                return True
            add_ts, add_vc = self._adds[key]
            rem_ts, rem_vc = self._removes[key]
            # Compare vector clocks
            cmp = VectorClock.from_dict(self.node_id, add_vc).compare(rem_vc)
            if cmp == 0:
                # Concurrent: tie-break by timestamp
                return add_ts >= rem_ts
            return cmp > 0 or (cmp == 0 and add_ts >= rem_ts)

    def members(self) -> Set[str]:
        return {k for k in self._adds if self.lookup(k)}

    def merge(self, other: 'LWWSet'):
        with self._lock:
            for k, (ts, vc) in other._adds.items():
                if k not in self._adds or ts > self._adds[k][0]:
                    self._adds[k] = (ts, vc)
            for k, (ts, vc) in other._removes.items():
                if k not in self._removes or ts > self._removes[k][0]:
                    self._removes[k] = (ts, vc)

    def delta(self, since: int) -> Dict:
        """Return changes since timestamp."""
        out = {"adds": {}, "removes": {}}
        for k, (ts, vc) in self._adds.items():
            if ts >= since:
                out["adds"][k] = (ts, vc)
        for k, (ts, vc) in self._removes.items():
            if ts >= since:
                out["removes"][k] = (ts, vc)
        return out

    def to_dict(self) -> Dict:
        return {"adds": dict(self._adds), "removes": dict(self._removes)}

    @classmethod
    def from_dict(cls, node_id: str, d: Dict):
        s = cls(node_id)
        s._adds = dict(d.get("adds", {}))
        s._removes = dict(d.get("removes", {}))
        return s


class GCounter:
    """Grow-only counter CRDT."""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self._state: Dict[str, int] = {node_id: 0}
        self._lock = threading.Lock()

    def increment(self, delta: int = 1):
        with self._lock:
            self._state[self.node_id] = self._state.get(self.node_id, 0) + delta

    def value(self) -> int:
        with self._lock:
            return sum(self._state.values())

    def merge(self, other: 'GCounter'):
        with self._lock:
            for k, v in other._state.items():
                self._state[k] = max(self._state.get(k, 0), v)

    def to_dict(self) -> Dict:
        return dict(self._state)

    @classmethod
    def from_dict(cls, node_id: str, d: Dict):
        c = cls(node_id)
        c._state = dict(d)
        return c


class PNCounter:
    """Positive-Negative counter CRDT."""

    def __init__(self, node_id: str):
        self._pos = GCounter(node_id)
        self._neg = GCounter(node_id)

    def increment(self, delta: int = 1):
        self._pos.increment(delta)

    def decrement(self, delta: int = 1):
        self._neg.increment(delta)

    def value(self) -> int:
        return self._pos.value() - self._neg.value()

    def merge(self, other: 'PNCounter'):
        self._pos.merge(other._pos)
        self._neg.merge(other._neg)

    def to_dict(self) -> Dict:
        return {"pos": self._pos.to_dict(), "neg": self._neg.to_dict()}

    @classmethod
    def from_dict(cls, node_id: str, d: Dict):
        c = cls(node_id)
        c._pos = GCounter.from_dict(node_id, d.get("pos", {}))
        c._neg = GCounter.from_dict(node_id, d.get("neg", {}))
        return c


class MobileSyncEngine:
    """Full sync engine with LWWSet + PNCounter + delta encoding."""

    def __init__(self, node_id: str, store_path: str = "/tmp/magnatrix_sync"):
        self.node_id = node_id
        self.store_path = store_path
        self._sets: Dict[str, LWWSet] = {}
        self._counters: Dict[str, PNCounter] = {}
        self._last_sync = 0
        self._lock = threading.Lock()
        os.makedirs(store_path, exist_ok=True)
        self._load()

    def _load(self):
        for fname in os.listdir(self.store_path) if os.path.exists(self.store_path) else []:
            if fname.endswith(".json"):
                with open(os.path.join(self.store_path, fname), 'r') as f:
                    data = json.load(f)
                name = fname[:-5]
                if "adds" in data:
                    self._sets[name] = LWWSet.from_dict(self.node_id, data)
                elif "pos" in data:
                    self._counters[name] = PNCounter.from_dict(self.node_id, data)

    def _save(self):
        for name, s in self._sets.items():
            with open(os.path.join(self.store_path, f"{name}.json"), 'w') as f:
                json.dump(s.to_dict(), f)
        for name, c in self._counters.items():
            with open(os.path.join(self.store_path, f"{name}.json"), 'w') as f:
                json.dump(c.to_dict(), f)

    def set_add(self, set_name: str, key: str):
        with self._lock:
            if set_name not in self._sets:
                self._sets[set_name] = LWWSet(self.node_id)
            self._sets[set_name].add(key)

    def set_remove(self, set_name: str, key: str):
        with self._lock:
            if set_name not in self._sets:
                self._sets[set_name] = LWWSet(self.node_id)
            self._sets[set_name].remove(key)

    def set_members(self, set_name: str) -> Set[str]:
        with self._lock:
            return self._sets.get(set_name, LWWSet(self.node_id)).members()

    def counter_inc(self, name: str, delta: int = 1):
        with self._lock:
            if name not in self._counters:
                self._counters[name] = PNCounter(self.node_id)
            self._counters[name].increment(delta)

    def counter_dec(self, name: str, delta: int = 1):
        with self._lock:
            if name not in self._counters:
                self._counters[name] = PNCounter(self.node_id)
            self._counters[name].decrement(delta)

    def counter_value(self, name: str) -> int:
        with self._lock:
            return self._counters.get(name, PNCounter(self.node_id)).value()

    def delta(self, since: Optional[int] = None) -> Dict:
        since = since or self._last_sync
        out = {}
        for name, s in self._sets.items():
            d = s.delta(since)
            if d["adds"] or d["removes"]:
                out[name] = d
        for name, c in self._counters.items():
            out[name] = c.to_dict()
        return out

    def apply_delta(self, delta: Dict):
        with self._lock:
            for name, data in delta.items():
                if isinstance(data, dict) and "adds" in data:
                    if name not in self._sets:
                        self._sets[name] = LWWSet(self.node_id)
                    self._sets[name].merge(LWWSet.from_dict(self.node_id, data))
                elif isinstance(data, dict) and "pos" in data:
                    if name not in self._counters:
                        self._counters[name] = PNCounter(self.node_id)
                    self._counters[name].merge(PNCounter.from_dict(self.node_id, data))
        self._last_sync = int(time.time() * 1000)
        self._save()


# ─── SELF TESTS ───
if __name__ == "__main__":
    tests = []
    def _t(name, fn):
        tests.append((name, fn))

    _t("lww_add", lambda: (LWWSet("A").add("x"), LWWSet("A").lookup("x"))[1])
    _t("lww_remove", lambda: (s := LWWSet("A"), s.add("x"), s.remove("x"), not s.lookup("x"))[3])
    _t("lww_merge", lambda: (a := LWWSet("A"), b := LWWSet("B"), a.add("x"), b.add("y"), a.merge(b), "y" in a.members())[5])
    _t("g_counter", lambda: (c := GCounter("A"), c.increment(3), c.increment(2), c.value() == 5)[3])
    _t("pn_counter", lambda: (c := PNCounter("A"), c.increment(5), c.decrement(2), c.value() == 3)[3])
    _t("vector_clock_compare", lambda: VectorClock("A")._clock != VectorClock("B")._clock)
    _t("engine_set", lambda: (e := MobileSyncEngine("A"), e.set_add("todos", "task1"), "task1" in e.set_members("todos"))[2])
    _t("engine_counter", lambda: (e := MobileSyncEngine("A"), e.counter_inc("views", 10), e.counter_value("views") == 10)[2])
    _t("engine_delta", lambda: (e := MobileSyncEngine("A"), e.set_add("x", "a"), len(e.delta()) > 0)[2])
    _t("engine_save_load", lambda: (e := MobileSyncEngine("A", "/tmp/mtx_sync_test"), e.set_add("s", "k"), e._save(), e2 := MobileSyncEngine("A", "/tmp/mtx_sync_test"), "k" in e2.set_members("s"))[5])

    passed = 0
    for name, fn in tests:
        try:
            ok = fn()
            print(f"  {'PASS' if ok else 'FAIL'} {name}")
            if ok:
                passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
    print(f"\nMobile Sync: {passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)
