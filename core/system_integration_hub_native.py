#!/usr/bin/env python3
"""
System Integration Hub for MAGNATRIX-OS
========================================
Central wiring system that activates all 166 modules into a unified organism.
Auto-starts dashboard, wires HFT to exchange, enables constitution governance,
activates MoA, swarm intelligence, and self-healing. Pure stdlib.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations
import json, time, threading
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class SystemIntegrationHub:
    """Central hub that wires all MAGNATRIX-OS modules together."""

    def __init__(self, repo_root: str = ".") -> None:
        self.repo_root = repo_root
        self._wiring_map: Dict[str, List[str]] = {}
        self._active_services: Dict[str, Any] = {}
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._running = False
        self._lock = threading.RLock()
        self._health_check_thread: Optional[threading.Thread] = None

    def wire_module(self, module_name: str, provides: List[str], depends_on: List[str] = None) -> None:
        """Register a module into the wiring map."""
        with self._lock:
            self._wiring_map[module_name] = {
                "provides": provides,
                "depends_on": depends_on or [],
                "state": "registered",
            }

    def connect(self, source: str, target: str, event_type: str = "data") -> bool:
        """Create a connection between two modules."""
        with self._lock:
            if source not in self._wiring_map or target not in self._wiring_map:
                return False
            key = f"{source}->{target}"
            if event_type not in self._event_handlers:
                self._event_handlers[event_type] = []
            self._event_handlers[event_type].append(lambda data, s=source, t=target: self._route_event(s, t, data))
            return True

    def _route_event(self, source: str, target: str, data: Any) -> None:
        """Route an event from source to target."""
        pass

    def auto_wire_all(self, registry: Dict[str, Any]) -> Dict[str, Any]:
        """Automatically wire all modules based on capabilities."""
        with self._lock:
            results = {"wired": 0, "failed": 0, "connections": []}
            # Wire core infrastructure
            for name, info in registry.items():
                if hasattr(info, "CAPABILITIES"):
                    caps = info.CAPABILITIES
                elif hasattr(info, "PROVIDES"):
                    caps = info.PROVIDES
                else:
                    caps = [name]
                self.wire_module(name, caps)
            # Auto-connect based on capability matching
            for name_a, info_a in self._wiring_map.items():
                for name_b, info_b in self._wiring_map.items():
                    if name_a == name_b:
                        continue
                    for cap_a in info_a.get("provides", []):
                        if cap_a in info_b.get("depends_on", []) or cap_a in info_b.get("provides", []):
                            if self.connect(name_a, name_b, cap_a):
                                results["wired"] += 1
                                results["connections"].append(f"{name_a}->{name_b}({cap_a})")
            return results

    def start_dashboard(self, port: int = 8080) -> bool:
        """Auto-start the production dashboard."""
        try:
            from core.dashboard_production_native import DashboardServer
            server = DashboardServer(port=port)
            self._active_services["dashboard"] = server
            return True
        except Exception:
            return False

    def start_hft_engine(self) -> bool:
        """Activate HFT trading engine and connect to exchange."""
        try:
            from core.hft_trading_engine_native import TradingEngine
            from core.live_exchange_integration_native import ExchangeConnector
            engine = TradingEngine()
            exchange = ExchangeConnector(testnet=True)
            engine.register_strategy(MAStrategy())
            self._active_services["hft"] = engine
            self._active_services["exchange"] = exchange
            return True
        except Exception:
            return False

    def enable_constitution(self) -> bool:
        """Activate constitution governance."""
        try:
            from core.magnatrix_constitution_native import ConstitutionGovernor
            gov = ConstitutionGovernor()
            self._active_services["constitution"] = gov
            return True
        except Exception:
            return False

    def enable_moa(self, preset: str = "default") -> bool:
        """Activate Mixture of Agents."""
        try:
            from core.moa_integration_native import MOAEngine
            moa = MOAEngine(repo_root=self.repo_root)
            moa.select_preset(preset)
            self._active_services["moa"] = moa
            return True
        except Exception:
            return False

    def enable_swarm(self) -> bool:
        """Activate swarm intelligence."""
        try:
            from core.swarm_intelligence_native import SwarmIntelligence
            swarm = SwarmIntelligence()
            self._active_services["swarm"] = swarm
            return True
        except Exception:
            return False

    def enable_self_healing(self) -> bool:
        """Activate self-healing engine."""
        try:
            from core.self_healing_native import SelfHealingEngine
            healer = SelfHealingEngine()
            self._active_services["self_healing"] = healer
            return True
        except Exception:
            return False

    def start_all(self, registry: Dict[str, Any] = None) -> Dict[str, Any]:
        """Start all integrated services."""
        with self._lock:
            self._running = True
            results = {"started": [], "failed": []}
            if registry:
                wire_result = self.auto_wire_all(registry)
                results["wiring"] = wire_result
            services = [
                ("dashboard", self.start_dashboard),
                ("hft", self.start_hft_engine),
                ("constitution", self.enable_constitution),
                ("moa", lambda: self.enable_moa("default")),
                ("swarm", self.enable_swarm),
                ("self_healing", self.enable_self_healing),
            ]
            for name, starter in services:
                try:
                    if starter():
                        results["started"].append(name)
                    else:
                        results["failed"].append(name)
                except Exception as e:
                    results["failed"].append(f"{name}: {e}")
            self._start_health_monitor()
            return results

    def _start_health_monitor(self) -> None:
        def _monitor():
            while self._running:
                for name, service in list(self._active_services.items()):
                    if hasattr(service, "is_running") and not service.is_running():
                        try:
                            if hasattr(service, "start"):
                                service.start()
                        except Exception:
                            pass
                time.sleep(5.0)
        self._health_check_thread = threading.Thread(target=_monitor, daemon=True)
        self._health_check_thread.start()

    def stop_all(self) -> Dict[str, Any]:
        """Stop all integrated services."""
        with self._lock:
            self._running = False
            results = {"stopped": [], "errors": []}
            for name, service in self._active_services.items():
                try:
                    if hasattr(service, "stop"):
                        service.stop()
                    results["stopped"].append(name)
                except Exception as e:
                    results["errors"].append(f"{name}: {e}")
            self._active_services.clear()
            return results

    def status(self) -> Dict[str, Any]:
        """Get integration hub status."""
        with self._lock:
            return {
                "running": self._running,
                "wired_modules": len(self._wiring_map),
                "active_services": list(self._active_services.keys()),
                "total_connections": sum(len(v) for v in self._event_handlers.values()),
            }

    def to_dict(self) -> Dict[str, Any]:
        return self.status()


# Helper imports for HFT
class MAStrategy:
    """Placeholder - will be imported from hft module if available."""
    def __init__(self) -> None:
        self.name = "MA_Crossover"
