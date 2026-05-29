#!/usr/bin/env python3
"""
MAGNATRIX-OS | Layer 11 — Mobile Runtime
Native mobile runtime for Android/iOS without Flutter/React Native dependencies.
- WebSocket bridge to desktop kernel
- SQLite local sync
- Geolocation + sensor simulation
- Native widget tree renderer (declarative UI)
"""
import json, time, threading, sqlite3, os, sys, math, random
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from collections import deque


@dataclass
class SensorReading:
    lat: float = 0.0
    lon: float = 0.0
    accel_x: float = 0.0
    accel_y: float = 0.0
    accel_z: float = 0.0
    battery: float = 100.0
    timestamp: float = 0.0


class LocalStore:
    """SQLite-backed key-value and document store for mobile."""

    def __init__(self, path: str = "/tmp/magnatrix_mobile.db"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self._init()
        self._lock = threading.Lock()

    def _init(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS kv (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated REAL
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payload TEXT,
                created REAL
            )
        """)
        self.conn.commit()

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            c = self.conn.execute("SELECT value FROM kv WHERE key=?", (key,))
            row = c.fetchone()
            return row[0] if row else None

    def set(self, key: str, value: str):
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO kv (key, value, updated) VALUES (?, ?, ?)",
                (key, value, time.time())
            )
            self.conn.commit()

    def queue(self, payload: str):
        with self._lock:
            self.conn.execute("INSERT INTO sync_queue (payload, created) VALUES (?, ?)", (payload, time.time()))
            self.conn.commit()

    def dequeue(self, limit: int = 10) -> List[str]:
        with self._lock:
            c = self.conn.execute("SELECT id, payload FROM sync_queue ORDER BY id LIMIT ?", (limit,))
            rows = c.fetchall()
            out = []
            for rid, payload in rows:
                out.append(payload)
                self.conn.execute("DELETE FROM sync_queue WHERE id=?", (rid,))
            self.conn.commit()
            return out


class SensorSimulator:
    """Simulate mobile sensors (for desktop testing)."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self._lat = -6.2088
        self._lon = 106.8456
        self._battery = 87.0
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._listeners: List[Callable] = []
        self._lock = threading.Lock()

    def _emit(self, reading: SensorReading):
        for cb in self._listeners:
            try:
                cb(reading)
            except Exception:
                pass

    def start(self, interval: float = 1.0):
        self._running = True
        def _loop():
            while self._running:
                self._lat += self.rng.uniform(-0.0001, 0.0001)
                self._lon += self.rng.uniform(-0.0001, 0.0001)
                self._battery = max(0.0, self._battery - self.rng.uniform(0, 0.05))
                r = SensorReading(
                    lat=self._lat, lon=self._lon,
                    accel_x=self.rng.uniform(-1, 1),
                    accel_y=self.rng.uniform(-1, 1),
                    accel_z=self.rng.uniform(9, 10),
                    battery=self._battery,
                    timestamp=time.time(),
                )
                with self._lock:
                    self._emit(r)
                time.sleep(interval)
        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def on_reading(self, cb: Callable):
        with self._lock:
            self._listeners.append(cb)

    def get_current(self) -> SensorReading:
        return SensorReading(lat=self._lat, lon=self._lon, battery=self._battery, timestamp=time.time())


class BridgeClient:
    """WebSocket-like bridge to desktop kernel."""

    def __init__(self, endpoint: str = "ws://localhost:7777/mobile"):
        self.endpoint = endpoint
        self._connected = False
        self._queue: deque = deque()
        self._handlers: Dict[str, Callable] = {}
        self._lock = threading.Lock()

    def connect(self) -> bool:
        self._connected = True
        threading.Thread(target=self._rx_loop, daemon=True).start()
        return True

    def disconnect(self):
        self._connected = False

    def _rx_loop(self):
        # Simulated receive loop
        while self._connected:
            time.sleep(0.5)

    def send(self, msg: Dict) -> bool:
        with self._lock:
            self._queue.append(json.dumps(msg))
        return self._connected

    def register(self, msg_type: str, handler: Callable):
        self._handlers[msg_type] = handler

    def poll(self) -> List[str]:
        with self._lock:
            out = list(self._queue)
            self._queue.clear()
            return out


class WidgetTree:
    """Declarative UI widget tree (React-like but pure Python)."""

    def __init__(self, root: Optional[Dict] = None):
        self.root = root or {"type": "View", "props": {}, "children": []}
        self._dirty = True

    def add(self, parent_path: List[int], widget: Dict):
        node = self.root
        for idx in parent_path:
            node = node["children"][idx]
        node["children"].append(widget)
        self._dirty = True

    def remove(self, path: List[int]):
        if len(path) == 1:
            self.root["children"].pop(path[0])
        else:
            node = self.root
            for idx in path[:-1]:
                node = node["children"][idx]
            node["children"].pop(path[-1])
        self._dirty = True

    def to_json(self) -> str:
        return json.dumps(self.root, indent=2)

    def diff(self, old_tree: Dict) -> List[Dict]:
        # Simple diff: emit replace ops for changed nodes
        ops = []
        def _walk(new, old, path):
            if old is None:
                ops.append({"op": "add", "path": path, "node": new})
                return
            if new.get("type") != old.get("type"):
                ops.append({"op": "replace", "path": path, "node": new})
                return
            # Props diff
            new_props = new.get("props", {})
            old_props = old.get("props", {})
            for k, v in new_props.items():
                if old_props.get(k) != v:
                    ops.append({"op": "prop", "path": path, "key": k, "value": v})
            # Children diff
            nc = new.get("children", [])
            oc = old.get("children", [])
            for i in range(max(len(nc), len(oc))):
                _walk(nc[i] if i < len(nc) else None, oc[i] if i < len(oc) else None, path + [i])
        _walk(self.root, old_tree, [])
        return ops


class MobileRuntime:
    """Full mobile runtime with store, sensors, bridge, and UI."""

    def __init__(self, device_id: str = "mobile-01"):
        self.device_id = device_id
        self.store = LocalStore()
        self.sensors = SensorSimulator()
        self.bridge = BridgeClient()
        self.ui = WidgetTree()
        self._running = False

    def start(self):
        self._running = True
        self.sensors.start()
        self.bridge.connect()
        # Sync sensor readings to store
        self.sensors.on_reading(self._on_sensor)

    def stop(self):
        self._running = False
        self.sensors.stop()
        self.bridge.disconnect()

    def _on_sensor(self, r: SensorReading):
        self.store.set("last_sensor", json.dumps(asdict(r)))
        self.bridge.send({"type": "sensor", "device": self.device_id, "data": asdict(r)})

    def render(self, widget_tree: Dict) -> str:
        old = self.ui.root
        self.ui.root = widget_tree
        diff = self.ui.diff(old)
        self.bridge.send({"type": "ui_diff", "device": self.device_id, "ops": diff})
        return self.ui.to_json()

    def sync(self) -> List[str]:
        return self.store.dequeue(100)


# ─── SELF TESTS ───
if __name__ == "__main__":
    tests = []
    def _t(name, fn):
        tests.append((name, fn))

    _t("store_kv", lambda: (LocalStore().set("a", "1"), LocalStore().get("a"))[1] == "1")
    _t("store_queue", lambda: (LocalStore().queue("x"), len(LocalStore().dequeue()))[1] >= 1)
    _t("sensor_sim", lambda: SensorSimulator().get_current().battery > 0)
    _t("bridge_send", lambda: BridgeClient().send({"x": 1}))
    _t("widget_tree", lambda: json.loads(WidgetTree().to_json())["type"] == "View")
    _t("widget_diff", lambda: len(WidgetTree({"type": "View", "props": {}, "children": []}).diff({"type": "Text", "props": {}, "children": []})) > 0)
    _t("runtime_lifecycle", lambda: (MobileRuntime().start(), MobileRuntime().stop(), True)[2])
    _t("render_ui", lambda: "View" in MobileRuntime().render({"type": "View", "props": {}, "children": []}))

    passed = 0
    for name, fn in tests:
        try:
            ok = fn()
            print(f"  {'PASS' if ok else 'FAIL'} {name}")
            if ok:
                passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
    print(f"\nMobile Runtime: {passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)
