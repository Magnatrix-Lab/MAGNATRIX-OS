#!/usr/bin/env python3
"""
magnatrix_boot.py — MAGNATRIX Unified Boot Script
Entry point untuk menjalankan seluruh MAGNATRIX Agentic OS.
Mendeteksi environment, memuat config, dan menjalankan semua service.
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional


class MagnatrixBootloader:
    """Unified bootloader untuk MAGNATRIX Agentic OS."""

    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config = {}
        self.services: Dict[str, subprocess.Popen] = {}
        self.service_specs = {
            "api-gateway": {
                "cmd": [sys.executable, "api-gateway/gateway_server.py"],
                "port": 8080,
                "delay": 0,
            },
            "dashboard": {
                "cmd": [sys.executable, "web-ui/dashboard_server.py"],
                "port": 8095,
                "delay": 2,
            },
            "chat-bridge": {
                "cmd": [sys.executable, "chat-bridge/chat_server.py"],
                "port": 8765,
                "delay": 2,
            },
        }
        self._load_env()

    def _load_env(self):
        """Load environment configuration."""
        env_path = os.path.join(self.base_dir, ".env")
        if os.path.isfile(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        self.config[k.strip()] = v.strip().strip('"').strip("'")

    def _check_prerequisites(self) -> List[str]:
        """Check prerequisites."""
        missing = []
        required = ["python3", "docker"]
        for cmd in required:
            if not self._command_exists(cmd):
                missing.append(cmd)
        return missing

    @staticmethod
    def _command_exists(cmd: str) -> bool:
        """Check if command exists."""
        try:
            subprocess.run([cmd, "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _start_service(self, name: str) -> bool:
        """Start a single service."""
        spec = self.service_specs.get(name)
        if not spec:
            print(f"[MAGNATRIX Boot] Unknown service: {name}")
            return False

        cmd = spec["cmd"]
        cwd = self.base_dir

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.services[name] = proc
            print(f"[MAGNATRIX Boot] Started {name} (PID: {proc.pid})")
            return True
        except Exception as e:
            print(f"[MAGNATRIX Boot] Failed to start {name}: {e}")
            return False

    def start_all(self) -> Dict[str, bool]:
        """Start all services."""
        print("=" * 60)
        print("🧠 MAGNATRIX Agentic OS — Unified Boot")
        print("=" * 60)
        print(f"Base dir: {self.base_dir}")
        print(f"Config loaded: {len(self.config)} keys")

        # Check prerequisites
        missing = self._check_prerequisites()
        if missing:
            print(f"\n⚠️  Missing prerequisites: {', '.join(missing)}")

        results = {}
        for name, spec in self.service_specs.items():
            if spec.get("delay", 0) > 0:
                time.sleep(spec["delay"])
            results[name] = self._start_service(name)

        # Print summary
        print("\n" + "=" * 60)
        print("Boot Summary")
        print("=" * 60)
        total = len(results)
        started = sum(1 for v in results.values() if v)
        for name, ok in results.items():
            status = "✅ STARTED" if ok else "❌ FAILED"
            print(f"  {status:12s} {name}")
        print(f"\n  {started}/{total} services started")

        return results

    def stop_all(self):
        """Stop all services."""
        print("\n[MAGNATRIX Boot] Stopping all services...")
        for name, proc in self.services.items():
            try:
                proc.terminate()
                proc.wait(timeout=5)
                print(f"  ✅ Stopped {name}")
            except Exception as e:
                print(f"  ⚠️  Error stopping {name}: {e}")
                try:
                    proc.kill()
                except Exception:
                    pass
        self.services.clear()

    def get_status(self) -> Dict:
        """Get boot status."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "base_dir": self.base_dir,
            "services_running": len(self.services),
            "services": {
                name: {"pid": proc.pid, "running": proc.poll() is None}
                for name, proc in self.services.items()
            },
            "config": self.config,
        }


def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="MAGNATRIX Unified Boot")
    parser.add_argument("--start", action="store_true", help="Start all services")
    parser.add_argument("--stop", action="store_true", help="Stop all services")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--service", type=str, help="Start specific service")
    args = parser.parse_args()

    boot = MagnatrixBootloader()

    if args.stop:
        boot.stop_all()
    elif args.status:
        print(json.dumps(boot.get_status(), indent=2))
    elif args.service:
        boot._start_service(args.service)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            boot.stop_all()
    else:
        # Default: start all
        results = boot.start_all()
        if any(results.values()):
            print("\n[MAGNATRIX Boot] Press Ctrl+C to stop all services")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                boot.stop_all()
        else:
            print("\n[MAGNATRIX Boot] No services started. Check errors above.")
            sys.exit(1)


if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX Agentic OS — Unified Boot Script")
    print("Target: Super AI | 100% Self-Contained | Open Source")
    print("=" * 60)
    main()
