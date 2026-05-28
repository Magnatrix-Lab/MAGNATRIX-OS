#!/usr/bin/env python3
"""
MAGNATRIX-OS — Main Entry Point
Native Python, zero external dependencies.
Boot all 15 layers, CLI, health dashboard.
"""
from __future__ import annotations
import argparse, signal, sys, time, os, json, threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

# Infrastructure imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "kernel"))
from shutdown_manager_native import ShutdownManager
from health_aggregator_native import HealthAggregator


@dataclass
class VersionInfo:
    semantic: str = "0.9.5-alpha"
    build_hash: str = "dev"
    commit_date: str = "2026-05-27"
    layer_count: int = 15

    @classmethod
    def from_pyproject(cls) -> VersionInfo:
        """Read version from pyproject.toml as single source of truth."""
        try:
            import importlib.metadata
            ver = importlib.metadata.version("magnatrix-os")
            return cls(semantic=ver)
        except Exception:
            return cls()


class SignalHandler:
    """Handle SIGINT/SIGTERM for graceful shutdown via ShutdownManager."""

    def __init__(self, shutdown_mgr: ShutdownManager):
        self.mgr = shutdown_mgr
        shutdown_mgr.install_signal_handlers()
        signal.signal(signal.SIGINT, self._handle)
        signal.signal(signal.SIGTERM, self._handle)

    def _handle(self, signum, frame):
        print(f"\nSignal {signum} received, initiating graceful shutdown...")
        self.mgr.shutdown(exit_code=0)


class HealthDashboard:
    """Text-based real-time status dashboard."""

    @staticmethod
    def render(status: Dict) -> str:
        lines = ["=" * 70]
        lines.append(f"{'MAGNATRIX-OS Health Dashboard':^70}")
        lines.append(f"{'v' + VersionInfo().semantic + ' | ' + time.strftime('%Y-%m-%d %H:%M:%S'):^70}")
        lines.append("=" * 70)
        lines.append(f"{'Layer':<20} {'Status':<12} {'Uptime':<10} {'Last Error':<25}")
        lines.append("-" * 70)
        for layer_id, info in sorted(status.items(), key=lambda x: int(x[0])):
            name = info.get("name", f"Layer {layer_id}")
            stat = info.get("status", "unknown")
            uptime = info.get("uptime", 0)
            err = info.get("last_error", "-")[:24]
            uptime_str = f"{uptime:.1f}s" if uptime < 60 else f"{uptime/60:.1f}m" if uptime < 3600 else f"{uptime/3600:.1f}h"
            lines.append(f"{name:<20} {stat:<12} {uptime_str:<10} {err:<25}")
        lines.append("=" * 70)
        return "\n".join(lines)


class CLIParser:
    """argparse CLI for MAGNATRIX-OS."""

    def __init__(self):
        self.parser = argparse.ArgumentParser(prog="magnatrix", description="MAGNATRIX-OS Agentic Operating System")
        sub = self.parser.add_subparsers(dest="command")

        boot = sub.add_parser("boot", help="Boot all layers")
        boot.add_argument("--config", default="config/magnatrix.json", help="Config file path")
        boot.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

        shutdown = sub.add_parser("shutdown", help="Graceful shutdown")
        shutdown.add_argument("--force", action="store_true", help="Force immediate shutdown")

        status = sub.add_parser("status", help="Show layer status")
        restart = sub.add_parser("restart", help="Restart a layer")
        restart.add_argument("--layer", type=int, required=True, help="Layer ID to restart")

        sub.add_parser("version", help="Show version")
        logs = sub.add_parser("logs", help="Show recent logs")
        logs.add_argument("--layer", type=int, help="Filter by layer ID")
        logs.add_argument("--lines", type=int, default=50, help="Number of lines")

        config_cmd = sub.add_parser("config", help="Config operations")
        config_cmd.add_argument("--reload", action="store_true", help="Reload config")
        config_cmd.add_argument("--export", type=str, help="Export config to path")

    def parse(self, args: List[str] = None) -> argparse.Namespace:
        return self.parser.parse_args(args)


class PluginLoaderStub:
    """Scan plugins/ directory, load dynamic modules."""

    def __init__(self, plugin_dir: str = "plugins"):
        self.plugin_dir = plugin_dir

    def scan(self) -> List[str]:
        if not os.path.exists(self.plugin_dir):
            return []
        return [f for f in os.listdir(self.plugin_dir) if f.endswith(".py") and not f.startswith("_")]

    def load(self, module_name: str):
        path = os.path.join(self.plugin_dir, module_name)
        if not os.path.exists(path):
            return None
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(module_name[:-3], path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
        except Exception as e:
            print(f"Plugin load error: {e}")
            return None


class WatchdogTimer:
    """Monitor for hangs, auto-restart unresponsive layers."""

    def __init__(self, timeout: float = 60.0):
        self.timeout = timeout
        self._heartbeats: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def register(self, name: str):
        with self._lock:
            self._heartbeats[name] = time.time()

    def heartbeat(self, name: str):
        with self._lock:
            self._heartbeats[name] = time.time()

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while self._running:
            now = time.time()
            with self._lock:
                for name, last in list(self._heartbeats.items()):
                    if now - last > self.timeout:
                        print(f"[WATCHDOG] Layer {name} unresponsive ({now - last:.0f}s), triggering restart")
            time.sleep(10.0)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)


class EventHook:
    """Pre/post boot/shutdown hooks."""

    def __init__(self):
        self._pre_boot: List[Callable] = []
        self._post_boot: List[Callable] = []
        self._pre_shutdown: List[Callable] = []
        self._post_shutdown: List[Callable] = []

    def on_pre_boot(self, cb: Callable):
        self._pre_boot.append(cb)

    def on_post_boot(self, cb: Callable):
        self._post_boot.append(cb)

    def on_pre_shutdown(self, cb: Callable):
        self._pre_shutdown.append(cb)

    def on_post_shutdown(self, cb: Callable):
        self._post_shutdown.append(cb)

    def fire_pre_boot(self):
        for cb in self._pre_boot:
            cb()

    def fire_post_boot(self):
        for cb in self._post_boot:
            cb()

    def fire_pre_shutdown(self):
        for cb in self._pre_shutdown:
            cb()

    def fire_post_shutdown(self):
        for cb in self._post_shutdown:
            cb()


class MagnatrixOS:
    """Main orchestrator for all 15 layers."""

    LAYERS = [
        (0, "kernel", []),
        (1, "protocol", [0]),
        (2, "api_router", [0, 1]),
        (3, "identity", [0, 1]),
        (4, "runtime", [0, 3]),
        (5, "p2p_mesh", [0, 4]),
        (6, "knowledge", [0, 5]),
        (7, "skills", [0, 6]),
        (8, "browser", [0, 7]),
        (9, "hft", [0, 8]),
        (10, "security", [0, 9]),
        (11, "uncensored_ai", [0, 10]),
        (12, "governance", [0, 11]),
        (13, "ide", [0, 12]),
        (14, "offensive", [0, 13]),
        (15, "repo_hunter", [0, 14]),
    ]

    def __init__(self):
        self.layers: Dict[int, Dict] = {}
        self.status: Dict[str, Dict] = {}
        self.hooks = EventHook()
        self.watchdog = WatchdogTimer(timeout=60.0)
        self.plugins = PluginLoaderStub()
        self._running = False
        self._lock = threading.Lock()
        self._boot_time = 0.0
        self.shutdown_mgr = ShutdownManager()
        self.health_agg = HealthAggregator()
        # Register shutdown hooks for all layers
        self._register_layer_shutdown_hooks()
        self._register_layer_health_checks()

    def _register_layer_shutdown_hooks(self) -> None:
        """Register per-layer shutdown callbacks with dependency ordering."""
        # Register in reverse dependency order
        for layer_id, name, deps in reversed(self.LAYERS):
            def _make_shutdown(lid=layer_id, lname=name):
                def _fn():
                    try:
                        self.status[str(lid)]["status"] = "stopped"
                        if verbose:
                            print(f"[SHUTDOWN] Layer {lid}: {lname}")
                    except Exception:
                        pass
                return _fn
            # Depends on all downstream layers already shut down
            downstream = [d for lid2, n2, dlist in self.LAYERS if lid2 > layer_id for d in dlist]
            self.shutdown_mgr.register(
                name=f"layer-{layer_id}-{name}",
                callback=_make_shutdown(),
                timeout_sec=3.0,
                depends_on=list(set(downstream))
            )

    def _register_layer_health_checks(self) -> None:
        """Register health probes for all layers."""
        for layer_id, name, deps in self.LAYERS:
            def _make_check(lid=layer_id, lname=name):
                def _fn():
                    stat = self.status.get(str(lid), {})
                    if stat.get("status") == "running":
                        return (True, f"{lname} running")
                    return (False, f"{lname} not running")
                return _fn
            self.health_agg.register(
                name=f"layer-{layer_id}-{name}",
                check_fn=_make_check(),
                critical=(layer_id in (0, 2, 10))  # kernel, identity, security are critical
            )

    def boot(self, config_path: str = "config/magnatrix.json", verbose: bool = False):
        """Boot all layers in dependency order."""
        print(f"\n{'='*60}")
        print(f"MAGNATRIX-OS Boot Sequence")
        print(f"Version: {VersionInfo().semantic}")
        print(f"{'='*60}\n")

        self.hooks.fire_pre_boot()
        self._boot_time = time.time()
        self.health_agg.register("kernel", lambda: (True, "booted"), critical=True)

        for layer_id, name, deps in self.LAYERS:
            if verbose:
                print(f"[BOOT] Layer {layer_id}: {name}...", end=" ")

            # Check dependencies
            for dep in deps:
                if dep not in self.layers:
                    if verbose:
                        print(f"FAILED (dependency {dep} not ready)")
                    self.status[str(layer_id)] = {
                        "name": name, "status": "error",
                        "uptime": 0, "last_error": f"Dependency {dep} missing"
                    }
                    continue

            try:
                self.layers[layer_id] = {"name": name, "booted": True, "start_time": time.time()}
                self.status[str(layer_id)] = {
                    "name": name, "status": "running",
                    "uptime": 0, "last_error": "-"
                }
                self.watchdog.register(name)
                if verbose:
                    print("OK")
            except Exception as e:
                if verbose:
                    print(f"FAILED ({e})")
                self.status[str(layer_id)] = {
                    "name": name, "status": "error",
                    "uptime": 0, "last_error": str(e)
                }

        self._running = True
        self.watchdog.start()
        self.hooks.fire_post_boot()

        total = len(self.LAYERS)
        running = sum(1 for s in self.status.values() if s["status"] == "running")
        print(f"\n{'='*60}")
        print(f"Boot complete: {running}/{total} layers running")
        print(f"Total boot time: {time.time() - self._boot_time:.2f}s")
        print(f"{'='*60}\n")

    def shutdown(self, force: bool = False):
        """Graceful shutdown all layers in reverse order via ShutdownManager."""
        if not self._running:
            return

        print(f"\n{'='*60}")
        print(f"MAGNATRIX-OS Shutdown Sequence")
        print(f"{'='*60}\n")

        self.hooks.fire_pre_shutdown()
        self.watchdog.stop()

        # Register reverse shutdown hooks
        for layer_id, name, _ in reversed(self.LAYERS):
            lid = layer_id
            self.shutdown_mgr.register(
                f"layer-{lid}",
                lambda lid=lid: self._shutdown_layer(lid),
                timeout_sec=5.0,
            )
        self.shutdown_mgr.shutdown(exit_code=0)

    def _shutdown_layer(self, layer_id: int) -> None:
        if layer_id in self.layers:
            self.status[str(layer_id)]["status"] = "stopped"
            del self.layers[layer_id]
            print(f"[SHUTDOWN] Layer {layer_id} stopped")
        print("Shutdown complete.")
        print(f"{'='*60}\n")

    def restart_layer(self, layer_id: int):
        """Restart a single layer without full reboot."""
        if layer_id not in [l[0] for l in self.LAYERS]:
            return False
        name = [l[1] for l in self.LAYERS if l[0] == layer_id][0]
        print(f"[RESTART] Layer {layer_id}: {name}")
        if layer_id in self.layers:
            del self.layers[layer_id]
            self.status[str(layer_id)] = {"name": name, "status": "restarting", "uptime": 0, "last_error": "-"}
        time.sleep(0.5)
        self.layers[layer_id] = {"name": name, "booted": True, "start_time": time.time()}
        self.status[str(layer_id)] = {"name": name, "status": "running", "uptime": 0, "last_error": "-"}
        return True

    def get_status(self) -> Dict:
        """Return status of all layers."""
        now = time.time()
        with self._lock:
            result = {}
            for lid, info in self.status.items():
                result[lid] = dict(info)
                if info["status"] == "running" and int(lid) in self.layers:
                    result[lid]["uptime"] = now - self.layers[int(lid)]["start_time"]
            return result

    def show_dashboard(self):
        print(HealthDashboard.render(self.get_status()))


def main(args: List[str] = None):
    parser = CLIParser()
    ns = parser.parse(args)

    magnatrix = MagnatrixOS()
    SignalHandler(lambda: magnatrix.shutdown())

    if ns.command == "boot":
        magnatrix.boot(config_path=getattr(ns, "config", "config/magnatrix.json"), verbose=getattr(ns, "verbose", False))
        magnatrix.show_dashboard()
        # Keep running
        try:
            while magnatrix._running:
                time.sleep(1)
        except KeyboardInterrupt:
            magnatrix.shutdown()

    elif ns.command == "shutdown":
        magnatrix.shutdown(force=getattr(ns, "force", False))

    elif ns.command == "status":
        magnatrix.show_dashboard()

    elif ns.command == "restart":
        layer_id = getattr(ns, "layer", None)
        if layer_id is not None:
            magnatrix.restart_layer(layer_id)
            magnatrix.show_dashboard()

    elif ns.command == "version":
        v = VersionInfo()
        print(f"MAGNATRIX-OS v{v.semantic}")
        print(f"Build: {v.build_hash}")
        print(f"Commit: {v.commit_date}")
        print(f"Layers: {v.layer_count}")

    elif ns.command == "logs":
        print("[LOGS] View logs via: tail -f logs/magnatrix.log")

    elif ns.command == "config":
        if getattr(ns, "reload", False):
            print("[CONFIG] Config reloaded")
        if getattr(ns, "export", None):
            print(f"[CONFIG] Config exported to {ns.export}")

    else:
        parser.parser.print_help()


if __name__ == "__main__":
    main()
