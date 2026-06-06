#!/usr/bin/env python3
"""
Environment Detector for MAGNATRIX-OS
Detects OS, architecture, Python version, available capabilities,
and system constraints. Native stdlib only (platform, sys, os).

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import json
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclasses.dataclass
class EnvironmentInfo:
    os_name: str
    os_version: str
    arch: str
    processor: str
    python_version: str
    python_executable: str
    cpu_count: int
    memory_total: int
    hostname: str
    username: str
    timezone: str
    capabilities: Set[str]
    constraints: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "os_name": self.os_name,
            "os_version": self.os_version,
            "arch": self.arch,
            "processor": self.processor,
            "python_version": self.python_version,
            "python_executable": self.python_executable,
            "cpu_count": self.cpu_count,
            "memory_total": self.memory_total,
            "hostname": self.hostname,
            "username": self.username,
            "timezone": self.timezone,
            "capabilities": sorted(self.capabilities),
            "constraints": self.constraints,
        }


class EnvironmentDetector:
    """Detects and reports the runtime environment capabilities."""

    def __init__(self) -> None:
        self._info: Optional[EnvironmentInfo] = None
        self._scan()

    def _scan(self) -> None:
        os_name = platform.system()
        os_version = platform.release()
        arch = platform.machine()
        processor = platform.processor()
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        cpu_count = os.cpu_count() or 1
        memory_total = self._get_memory()
        hostname = platform.node()
        username = os.getlogin() if hasattr(os, "getlogin") else "unknown"
        timezone = self._get_timezone()
        capabilities = self._detect_capabilities()
        constraints = self._detect_constraints()
        self._info = EnvironmentInfo(
            os_name=os_name,
            os_version=os_version,
            arch=arch,
            processor=processor,
            python_version=python_version,
            python_executable=sys.executable,
            cpu_count=cpu_count,
            memory_total=memory_total,
            hostname=hostname,
            username=username,
            timezone=timezone,
            capabilities=capabilities,
            constraints=constraints,
        )

    def _get_memory(self) -> int:
        try:
            if hasattr(os, "sysconf"):
                return os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
        except Exception:
            pass
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        return int(line.split()[1]) * 1024
        except Exception:
            pass
        return 0

    def _get_timezone(self) -> str:
        try:
            return time.strftime("%Z")
        except Exception:
            return "UTC"

    def _detect_capabilities(self) -> Set[str]:
        caps = set()
        # Check for sqlite3
        try:
            import sqlite3
            caps.add("sqlite3")
        except ImportError:
            pass
        # Check for threading
        caps.add("threading")
        # Check for multiprocessing
        try:
            import multiprocessing
            caps.add("multiprocessing")
        except ImportError:
            pass
        # Check for SSL
        try:
            import ssl
            caps.add("ssl")
        except ImportError:
            pass
        # Check for ctypes
        try:
            import ctypes
            caps.add("ctypes")
        except ImportError:
            pass
        # Check for tkinter
        try:
            import tkinter
            caps.add("tkinter")
        except ImportError:
            pass
        # Check for venv/virtualenv
        if hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix:
            caps.add("virtualenv")
        # Check for 64-bit
        if sys.maxsize > 2**32:
            caps.add("64bit")
        else:
            caps.add("32bit")
        # Check for write permissions
        if os.access("/tmp", os.W_OK):
            caps.add("writable_tmp")
        # Check for network
        caps.add("network")
        # Check for git
        if self._has_command("git"):
            caps.add("git")
        # Check for docker
        if self._has_command("docker"):
            caps.add("docker")
        # Check for GPU (very basic)
        if os.path.exists("/proc/driver/nvidia") or os.path.exists("/dev/nvidia0"):
            caps.add("nvidia_gpu")
        return caps

    def _detect_constraints(self) -> Dict[str, Any]:
        constraints = {}
        # File descriptor limit
        try:
            import resource
            soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
            constraints["max_fds"] = soft
        except Exception:
            pass
        # Stack size
        try:
            import resource
            constraints["stack_size"] = resource.getrlimit(resource.RLIMIT_STACK)[0]
        except Exception:
            pass
        # Check if running in container
        if os.path.exists("/.dockerenv"):
            constraints["container"] = "docker"
        elif os.path.exists("/run/.containerenv"):
            constraints["container"] = "podman"
        else:
            try:
                with open("/proc/1/cgroup", "r") as f:
                    if "docker" in f.read() or "containerd" in f.read():
                        constraints["container"] = "docker"
            except Exception:
                pass
        # Check for read-only filesystem
        constraints["read_only_root"] = not os.access("/", os.W_OK)
        return constraints

    def _has_command(self, cmd: str) -> bool:
        for path in os.environ.get("PATH", "").split(os.pathsep):
            if os.path.exists(os.path.join(path, cmd)):
                return True
        return False

    def get_info(self) -> EnvironmentInfo:
        return self._info

    def has_capability(self, cap: str) -> bool:
        return cap in self._info.capabilities

    def get_constraints(self) -> Dict[str, Any]:
        return self._info.constraints

    def is_container(self) -> bool:
        return "container" in self._info.constraints

    def export_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._info.to_dict(), f, indent=2, ensure_ascii=False)

    def stats(self) -> Dict[str, Any]:
        return {
            "capabilities": len(self._info.capabilities),
            "constraints": len(self._info.constraints),
            "os": self._info.os_name,
            "python": self._info.python_version,
            "arch": self._info.arch,
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    det = EnvironmentDetector()
    print("=== Environment Detector Demo ===\n")
    info = det.get_info()
    print(f"OS: {info.os_name} {info.os_version}")
    print(f"Arch: {info.arch} ({info.processor})")
    print(f"Python: {info.python_version}")
    print(f"CPUs: {info.cpu_count}")
    print(f"Memory: {info.memory_total / (1024**3):.1f} GB")
    print(f"Hostname: {info.hostname}")
    print(f"Capabilities: {sorted(info.capabilities)}")
    print(f"Constraints: {info.constraints}")
    print(f"Stats: {det.stats()}")


if __name__ == "__main__":
    _demo()
