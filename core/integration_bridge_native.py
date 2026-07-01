#!/usr/bin/env python3
"""integration_bridge_native.py -- MAGNATRIX-OS Integration Bridge

Middleware connecting all modules to messaging bus + task scheduler + gateway +
health aggregator. Pure stdlib.
"""
from __future__ import annotations
import json, threading, time, uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable

@dataclass
class BridgeRoute:
    source: str; target: str; method: str
    priority: int = 5; enabled: bool = True; fallback: Optional[str] = None
    transform: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BridgeEvent:
    id: str; source: str; target: str; event_type: str; payload: Any
    timestamp: float = field(default_factory=time.time); route_used: str = ""
    latency: float = 0.0; status: str = "pending"

class IntegrationBridgeNative:
    def __init__(self, workspace: str = "./integration_bridge") -> None:
        self.workspace = Path(workspace); self.workspace.mkdir(parents=True, exist_ok=True)
        self._routes: Dict[str, BridgeRoute] = {}
        self._event_log: List[BridgeEvent] = []
        self._subsystems: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._routes_path = self.workspace / "routes.json"
        self._events_path = self.workspace / "events.jsonl"
        self._load()

    def _load(self) -> None:
        if self._routes_path.exists():
            try:
                with open(self._routes_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for rid, rd in data.items(): self._routes[rid] = BridgeRoute(**rd)
            except Exception: pass

    def _save(self) -> None:
        with open(self._routes_path, "w", encoding="utf-8") as f:
            json.dump({rid: asdict(r) for rid, r in self._routes.items()}, f, indent=2, default=str)

    def register_subsystem(self, name: str, instance: Any) -> None:
        with self._lock: self._subsystems[name] = instance

    def add_route(self, source: str, target: str, method: str, priority: int = 5, fallback: Optional[str] = None, transform: Optional[str] = None) -> str:
        with self._lock:
            rid = f"route_{source}_{target}_{method}"
            self._routes[rid] = BridgeRoute(source=source, target=target, method=method, priority=priority, fallback=fallback, transform=transform)
            self._save(); return rid

    def remove_route(self, rid: str) -> bool:
        with self._lock:
            if rid in self._routes: del self._routes[rid]; self._save(); return True
            return False

    def get_routes(self, source: Optional[str] = None, target: Optional[str] = None) -> List[BridgeRoute]:
        with self._lock:
            result = list(self._routes.values())
            if source: result = [r for r in result if r.source == source]
            if target: result = [r for r in result if r.target == target]
            return sorted(result, key=lambda r: r.priority)

    def _find_route(self, source: str, target: str, method: str) -> Optional[BridgeRoute]:
        candidates = self.get_routes(source, target)
        for r in candidates:
            if r.method == method and r.enabled: return r
        return None

    def _log_event(self, event: BridgeEvent) -> None:
        with open(self._events_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event), default=str) + "
")

    def dispatch(self, source: str, target: str, method: str, payload: Any, timeout: float = 10.0) -> Dict[str, Any]:
        with self._lock:
            event_id = f"evt_{int(time.time()*1000)}_{str(uuid.uuid4())[:6]}"
            event = BridgeEvent(id=event_id, source=source, target=target, event_type=method, payload=payload)
            start = time.time()
            route = self._find_route(source, target, method)
            if not route:
                event.status = "failed"; event.latency = time.time() - start
                self._log_event(event); self._event_log.append(event)
                return {"success": False, "error": "No route found", "event_id": event_id}
            target_subsystem = self._subsystems.get(target)
            if not target_subsystem:
                if route.fallback and route.fallback in self._subsystems:
                    target_subsystem = self._subsystems[route.fallback]
                    event.route_used = f"{route.fallback} (fallback)"
                else:
                    event.status = "failed"; event.latency = time.time() - start
                    self._log_event(event); self._event_log.append(event)
                    return {"success": False, "error": f"Target '{target}' not registered and no fallback", "event_id": event_id}
            else: event.route_used = f"{source} -> {target}"
            try:
                if route.transform and hasattr(self, route.transform): payload = getattr(self, route.transform)(payload)
                target_method = getattr(target_subsystem, method, None)
                if not target_method:
                    event.status = "failed"; event.latency = time.time() - start
                    self._log_event(event); self._event_log.append(event)
                    return {"success": False, "error": f"Method '{method}' not found on {target}", "event_id": event_id}
                result = target_method(**payload) if isinstance(payload, dict) else target_method(payload)
                event.status = "delivered"; event.latency = time.time() - start
                self._log_event(event); self._event_log.append(event)
                return {"success": True, "result": result, "event_id": event_id, "latency": event.latency}
            except Exception as e:
                event.status = "failed"; event.latency = time.time() - start
                self._log_event(event); self._event_log.append(event)
                return {"success": False, "error": f"{type(e).__name__}: {e}", "event_id": event_id, "latency": event.latency}

    def broadcast(self, source: str, targets: List[str], method: str, payload: Any) -> Dict[str, Dict[str, Any]]:
        results = {}
        for target in targets: results[target] = self.dispatch(source, target, method, payload)
        return results

    def get_event_stats(self, window: int = 1000) -> Dict[str, Any]:
        events = self._event_log[-window:]
        total = len(events); delivered = sum(1 for e in events if e.status == "delivered")
        failed = sum(1 for e in events if e.status == "failed")
        avg_latency = sum(e.latency for e in events) / total if total else 0
        by_target = {}
        for e in events:
            t = e.target
            if t not in by_target: by_target[t] = {"total": 0, "delivered": 0, "failed": 0}
            by_target[t]["total"] += 1
            if e.status == "delivered": by_target[t]["delivered"] += 1
            if e.status == "failed": by_target[t]["failed"] += 1
        return {"total_events": total, "delivered": delivered, "failed": failed, "success_rate": delivered / total if total else 0.0, "avg_latency": round(avg_latency, 4), "by_target": by_target, "channels": len(self._routes)}

    def print_summary(self) -> str:
        stats = self.get_event_stats()
        lines = ["=== Integration Bridge Summary ===", f"Registered Subsystems: {len(self._subsystems)} ({', '.join(self._subsystems.keys())})", f"Active Routes: {len(self._routes)}", f"Events (last 1000): {stats['total_events']}", f"Success Rate: {stats['success_rate']:.2%}", f"Avg Latency: {stats['avg_latency']:.3f}s", "
--- Routes ---"]
        for rid, r in sorted(self._routes.items(), key=lambda x: x[1].priority):
            fb = f" -> fallback:{r.fallback}" if r.fallback else ""
            lines.append(f"  [{r.priority}] {r.source} -> {r.target}.{r.method}{fb}")
        return "
".join(lines)

if __name__ == "__main__":
    bridge = IntegrationBridgeNative()
    bridge.add_route("scheduler", "messaging", "publish", priority=1, fallback="gateway")
    bridge.add_route("health", "orchestrator", "alert", priority=1)
    print(bridge.print_summary())
