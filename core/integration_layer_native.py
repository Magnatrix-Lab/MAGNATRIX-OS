#!/usr/bin/env python3
"""
Integration Layer — MAGNATRIX-OS Central Nervous System
============================================================
Event bus, message router, module connector, and integration manager
that wire all 142+ modules into a unified, communicating system.

Pure Python stdlib only. No external dependencies.
Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations

import fnmatch
import json
import os
import queue
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


class EventPriority(Enum):
    """Priority levels for event delivery."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class Event:
    """A typed event flowing through the EventBus."""
    topic: str
    payload: Any
    source: str = "unknown"
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    priority: EventPriority = EventPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)


class EventBus:
    """
    Publish/subscribe event bus with priority, wildcards, and async delivery.
    
    Topics: hierarchical dot-separated, e.g. "module.auth.login.success"
    Wildcards: "*" matches one level, "**" matches any levels.
    
    Example:
        bus = EventBus()
        bus.subscribe("module.**", handler)
        bus.publish("module.auth.login.success", {"user": "admin"})
    """

    def __init__(self, max_history: int = 1000):
        self._handlers: Dict[str, List[Tuple[Callable, EventPriority]]] = {}
        self._once_handlers: Dict[str, List[Tuple[Callable, EventPriority]]] = {}
        self._lock = threading.RLock()
        self._event_queue: queue.PriorityQueue = queue.PriorityQueue()
        self._history: List[Event] = []
        self._max_history = max_history
        self._running = False
        self._dispatcher_thread: Optional[threading.Thread] = None
        self._stats = {"published": 0, "delivered": 0, "dropped": 0}

    def start(self) -> None:
        """Start async event dispatch."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._dispatcher_thread = threading.Thread(target=self._dispatch_loop, daemon=True)
            self._dispatcher_thread.start()

    def stop(self) -> None:
        """Stop async dispatch."""
        with self._lock:
            self._running = False
        # Signal queue to wake dispatcher
        self._event_queue.put((0, None))
        if self._dispatcher_thread and self._dispatcher_thread.is_alive():
            self._dispatcher_thread.join(timeout=2.0)

    def _dispatch_loop(self) -> None:
        """Background thread: dequeue events and dispatch to handlers."""
        while self._running:
            try:
                _, event = self._event_queue.get(timeout=0.5)
                if event is None:
                    continue
                self._deliver(event)
            except queue.Empty:
                continue

    def _topic_match(self, pattern: str, topic: str) -> bool:
        """Match topic against pattern with * and ** wildcards."""
        if pattern == topic:
            return True
        if pattern == "**":
            return True
        # Convert ** wildcard to fnmatch-compatible pattern
        # Replace ** with a placeholder, then * with ?, then restore **
        pat = pattern.replace("**", "\x00\x00")
        pat = pat.replace("*", "?")
        pat = pat.replace("\x00\x00", "*")
        # fnmatch doesn't handle ** for multi-level, so we do it manually
        if "**" in pattern:
            # Split pattern by **
            parts = pattern.split("**")
            if len(parts) == 2:
                prefix, suffix = parts
                if prefix and not topic.startswith(prefix.rstrip(".")):
                    return False
                if suffix and not topic.endswith(suffix.lstrip(".")):
                    return False
                return True
            return True
        return fnmatch.fnmatch(topic, pat)

    def subscribe(self, topic_pattern: str, handler: Callable[[Event], None],
                  priority: EventPriority = EventPriority.NORMAL) -> None:
        """Subscribe a handler to a topic pattern."""
        with self._lock:
            if topic_pattern not in self._handlers:
                self._handlers[topic_pattern] = []
            self._handlers[topic_pattern].append((handler, priority))

    def subscribe_once(self, topic_pattern: str, handler: Callable[[Event], None],
                       priority: EventPriority = EventPriority.NORMAL) -> None:
        """Subscribe a handler that auto-unsubscribes after first delivery."""
        with self._lock:
            if topic_pattern not in self._once_handlers:
                self._once_handlers[topic_pattern] = []
            self._once_handlers[topic_pattern].append((handler, priority))

    def unsubscribe(self, topic_pattern: str, handler: Callable[[Event], None]) -> None:
        """Remove a handler subscription."""
        with self._lock:
            if topic_pattern in self._handlers:
                self._handlers[topic_pattern] = [
                    (h, p) for h, p in self._handlers[topic_pattern] if h != handler
                ]
            if topic_pattern in self._once_handlers:
                self._once_handlers[topic_pattern] = [
                    (h, p) for h, p in self._once_handlers[topic_pattern] if h != handler
                ]

    def publish(self, topic: str, payload: Any, source: str = "unknown",
                priority: EventPriority = EventPriority.NORMAL,
                metadata: Optional[Dict[str, Any]] = None) -> str:
        """Publish an event to all matching subscribers. Returns event ID."""
        event = Event(
            topic=topic, payload=payload, source=source,
            priority=priority, metadata=metadata or {}
        )
        with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history.pop(0)
            self._stats["published"] += 1

        if self._running:
            self._event_queue.put((priority.value, event))
        else:
            self._deliver(event)
        return event.event_id

    def _deliver(self, event: Event) -> None:
        """Deliver event to all matching handlers."""
        handlers_to_call: List[Tuple[Callable, EventPriority]] = []
        once_to_call: List[Tuple[Callable, EventPriority]] = []
        once_patterns: List[str] = []

        with self._lock:
            for pattern, handlers in self._handlers.items():
                if self._topic_match(pattern, event.topic):
                    handlers_to_call.extend(handlers)
            for pattern, handlers in self._once_handlers.items():
                if self._topic_match(pattern, event.topic):
                    once_to_call.extend(handlers)
                    once_patterns.append(pattern)
            # Remove once handlers
            for pattern in once_patterns:
                if pattern in self._once_handlers:
                    del self._once_handlers[pattern]

        all_handlers = handlers_to_call + once_to_call
        # Sort by priority (lower = higher priority)
        all_handlers.sort(key=lambda x: x[1].value)

        for handler, _ in all_handlers:
            try:
                handler(event)
                self._stats["delivered"] += 1
            except Exception as e:
                self._stats["dropped"] += 1
                # Don't let one handler crash others
                continue

    def get_history(self, topic_pattern: Optional[str] = None,
                    limit: int = 100) -> List[Event]:
        """Get historical events, optionally filtered by pattern."""
        with self._lock:
            events = list(self._history)
        if topic_pattern:
            events = [e for e in events if self._topic_match(topic_pattern, e.topic)]
        return events[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Return event statistics."""
        return dict(self._stats)

    def get_subscriber_count(self) -> int:
        """Count total active subscriptions."""
        with self._lock:
            return sum(len(h) for h in self._handlers.values())


class MessageRouter:
    """
    Request/response message router between modules.
    
    Supports direct send, broadcast, and capability-based routing.
    
    Example:
        router = MessageRouter()
        router.register_handler("auth", auth_module.handle)
        router.send("auth", {"action": "verify", "token": "abc"})
    """

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._capabilities: Dict[str, List[str]] = {}  # module -> capabilities
        self._pending_responses: Dict[str, threading.Event] = {}
        self._response_data: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._stats = {"sent": 0, "received": 0, "broadcasts": 0, "errors": 0}

    def register_handler(self, module_name: str, handler: Callable,
                         capabilities: Optional[List[str]] = None) -> None:
        """Register a module handler with optional capabilities."""
        with self._lock:
            self._handlers[module_name] = handler
            if capabilities:
                self._capabilities[module_name] = capabilities

    def unregister_handler(self, module_name: str) -> None:
        """Remove a module handler."""
        with self._lock:
            self._handlers.pop(module_name, None)
            self._capabilities.pop(module_name, None)

    def send(self, target_module: str, message: Dict[str, Any],
             timeout: float = 5.0) -> Optional[Any]:
        """Send a message to a specific module and wait for response."""
        msg_id = str(uuid.uuid4())[:8]
        message = {**message, "_msg_id": msg_id, "_source": "router"}

        with self._lock:
            handler = self._handlers.get(target_module)
            if not handler:
                self._stats["errors"] += 1
                return None
            self._pending_responses[msg_id] = threading.Event()
            self._stats["sent"] += 1

        try:
            # Call handler in current thread
            result = handler(message)
            with self._lock:
                self._response_data[msg_id] = result
                self._pending_responses[msg_id].set()
                self._stats["received"] += 1
            return result
        except Exception as e:
            with self._lock:
                self._stats["errors"] += 1
                self._pending_responses[msg_id].set()
            return None

    def send_async(self, target_module: str, message: Dict[str, Any]) -> None:
        """Fire-and-forget message to a module."""
        def _send():
            self.send(target_module, message, timeout=5.0)
        threading.Thread(target=_send, daemon=True).start()

    def broadcast(self, message: Dict[str, Any],
                  filter_fn: Optional[Callable[[str], bool]] = None) -> Dict[str, Any]:
        """Broadcast to all modules matching optional filter. Returns aggregated results."""
        results = {}
        with self._lock:
            targets = list(self._handlers.keys())
        if filter_fn:
            targets = [t for t in targets if filter_fn(t)]
        for target in targets:
            try:
                result = self.send(target, message, timeout=2.0)
                results[target] = result
            except Exception:
                results[target] = None
        with self._lock:
            self._stats["broadcasts"] += 1
        return results

    def get_modules_by_capability(self, capability: str) -> List[str]:
        """Find modules that provide a specific capability."""
        with self._lock:
            return [
                name for name, caps in self._capabilities.items()
                if capability in caps
            ]

    def get_stats(self) -> Dict[str, Any]:
        return dict(self._stats)


class ModuleConnector:
    """
    Auto-connects loaded modules into the EventBus and MessageRouter.
    
    Discovers module capabilities via CAPABILITIES or PROVIDES attributes,
    then builds the wiring map automatically.
    
    Example:
        connector = ModuleConnector(event_bus, message_router)
        connector.wire_all(registry)
    """

    CONNECTIONS = [
        ("auth", "logging", "auth.success"),
        ("auth", "logging", "auth.failure"),
        ("cache", "logging", "cache.hit"),
        ("cache", "logging", "cache.miss"),
        ("database", "logging", "db.query"),
        ("search", "logging", "search.query"),
        ("analytics", "logging", "analytics.event"),
        ("security", "logging", "security.alert"),
        ("agent", "logging", "agent.action"),
        ("multi_agent", "logging", "multi_agent.collaboration"),
        ("code", "logging", "code.audit"),
        ("cicd", "logging", "cicd.deploy"),
        ("secret", "logging", "secret.rotation"),
        ("intrusion_detection", "logging", "intrusion.alert"),
        ("backup", "logging", "backup.snapshot"),
        ("self_healing", "logging", "self_healing.recovery"),
    ]

    def __init__(self, event_bus: EventBus, message_router: MessageRouter):
        self._bus = event_bus
        self._router = message_router
        self._wiring_map: Dict[str, List[Dict[str, Any]]] = {}
        self._connected: Set[Tuple[str, str, str]] = set()
        self._lock = threading.RLock()

    def wire_all(self, registry: Any) -> Dict[str, Any]:
        """
        Auto-wire all modules from a registry.
        
        Registry must have: get_module(name), list_modules() methods.
        """
        wired = {"event_bus": 0, "message_router": 0, "connections": 0}
        modules = []
        try:
            modules = registry.list_modules()
        except Exception:
            pass
        if not modules:
            try:
                modules = [{"name": k} for k in getattr(registry, "_modules", {})]
            except Exception:
                pass

        for mod_info in modules:
            name = mod_info.get("name", "")
            instance = None
            try:
                instance = registry.get_module(name) if hasattr(registry, "get_module") else None
            except Exception:
                pass
            if not instance:
                continue

            # Wire to EventBus
            self._wire_to_event_bus(name, instance)
            wired["event_bus"] += 1

            # Wire to MessageRouter
            self._wire_to_message_router(name, instance)
            wired["message_router"] += 1

        # Wire predefined connections
        for source, target, event_type in self.CONNECTIONS:
            self.connect(source, target, event_type)
            wired["connections"] += 1

        return wired

    def _wire_to_event_bus(self, name: str, instance: Any) -> None:
        """Wire a module's event handlers to the EventBus."""
        # If module has an on_event method, auto-subscribe to its topics
        if hasattr(instance, "on_event") and callable(instance.on_event):
            self._bus.subscribe(f"module.{name}.**", instance.on_event)

        # If module has CAPABILITIES, subscribe to relevant topics
        capabilities = getattr(instance, "CAPABILITIES", None) or getattr(instance, "PROVIDES", [])
        if capabilities:
            for cap in capabilities:
                self._bus.subscribe(f"capability.{cap}.**", instance.on_event)

    def _wire_to_message_router(self, name: str, instance: Any) -> None:
        """Wire a module to the MessageRouter."""
        handler = getattr(instance, "handle_message", None)
        if handler and callable(handler):
            capabilities = getattr(instance, "CAPABILITIES", None) or getattr(instance, "PROVIDES", [])
            self._router.register_handler(name, handler, capabilities)

    def connect(self, source: str, target: str, event_type: str) -> bool:
        """Manually connect two modules via an event type."""
        key = (source, target, event_type)
        with self._lock:
            if key in self._connected:
                return False
            self._connected.add(key)
            if source not in self._wiring_map:
                self._wiring_map[source] = []
            self._wiring_map[source].append({"target": target, "event": event_type})
        return True

    def disconnect(self, source: str, target: str, event_type: str) -> bool:
        """Remove a connection."""
        key = (source, target, event_type)
        with self._lock:
            if key not in self._connected:
                return False
            self._connected.discard(key)
            if source in self._wiring_map:
                self._wiring_map[source] = [
                    c for c in self._wiring_map[source]
                    if not (c["target"] == target and c["event"] == event_type)
                ]
        return True

    def get_wiring_map(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return the current wiring map."""
        with self._lock:
            return {k: list(v) for k, v in self._wiring_map.items()}


class IntegrationManager:
    """
    Top-level orchestrator for the integration layer.
    
    Manages EventBus, MessageRouter, and ModuleConnector lifecycle.
    On start, auto-wires all modules and enables event propagation.
    
    Example:
        mgr = IntegrationManager()
        mgr.start(registry)
        mgr.status()  # shows wiring map, stats
    """

    def __init__(self):
        self._event_bus = EventBus()
        self._message_router = MessageRouter()
        self._connector = ModuleConnector(self._event_bus, self._message_router)
        self._registry: Optional[Any] = None
        self._running = False
        self._lock = threading.RLock()
        self._health_thread: Optional[threading.Thread] = None

    def start(self, registry: Optional[Any] = None) -> Dict[str, Any]:
        """Start the integration layer. Auto-wire modules if registry provided."""
        with self._lock:
            if self._running:
                return {"status": "already_running"}
            self._running = True
            self._registry = registry

        self._event_bus.start()
        result = {"event_bus_started": True, "wired": {}}

        if registry:
            try:
                wired = self._connector.wire_all(registry)
                result["wired"] = wired
            except Exception as e:
                result["wire_error"] = str(e)

        # Start health check thread
        self._health_thread = threading.Thread(target=self._health_loop, daemon=True)
        self._health_thread.start()

        # Publish system started event
        self._event_bus.publish(
            "system.integration.started",
            {"timestamp": time.time(), "modules_wired": result.get("wired", {})},
            source="integration_manager"
        )

        return result

    def stop(self) -> Dict[str, Any]:
        """Stop the integration layer."""
        with self._lock:
            if not self._running:
                return {"status": "not_running"}
            self._running = False

        self._event_bus.publish(
            "system.integration.stopping",
            {"timestamp": time.time()},
            source="integration_manager"
        )
        self._event_bus.stop()
        return {"status": "stopped"}

    def _health_loop(self) -> None:
        """Periodic health check and heartbeat events."""
        while self._running:
            time.sleep(30)
            if not self._running:
                break
            self._event_bus.publish(
                "system.integration.heartbeat",
                {"timestamp": time.time(), "subscribers": self._event_bus.get_subscriber_count()},
                source="integration_manager",
                priority=EventPriority.BACKGROUND
            )

    def status(self) -> Dict[str, Any]:
        """Return full integration status."""
        return {
            "running": self._running,
            "event_bus": self._event_bus.get_stats(),
            "message_router": self._message_router.get_stats(),
            "wiring_map": self._connector.get_wiring_map(),
            "subscriber_count": self._event_bus.get_subscriber_count(),
        }

    def get_wiring_map(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return module wiring map."""
        return self._connector.get_wiring_map()

    def get_event_bus(self) -> EventBus:
        return self._event_bus

    def get_message_router(self) -> MessageRouter:
        return self._message_router

    def get_connector(self) -> ModuleConnector:
        return self._connector

    def publish(self, topic: str, payload: Any, source: str = "integration",
                priority: EventPriority = EventPriority.NORMAL) -> str:
        """Publish an event through the EventBus."""
        return self._event_bus.publish(topic, payload, source, priority)

    def send(self, target_module: str, message: Dict[str, Any]) -> Optional[Any]:
        """Send a message through the MessageRouter."""
        return self._message_router.send(target_module, message)

    def broadcast(self, message: Dict[str, Any],
                  filter_fn: Optional[Callable[[str], bool]] = None) -> Dict[str, Any]:
        """Broadcast to all modules."""
        return self._message_router.broadcast(message, filter_fn)
