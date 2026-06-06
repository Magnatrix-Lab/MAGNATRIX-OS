#!/usr/bin/env python3
"""
Hardware Profiler for MAGNATRIX-OS Local LLM Hosting
Detects system hardware (RAM, CPU, GPU, disk) to recommend optimal models.
Cross-platform: Linux, macOS, Windows.
Native stdlib only — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import json
import os
import platform
import re
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple, Any


@dataclasses.dataclass
class HardwareProfile:
    """Complete hardware profile of the system."""
    # CPU
    cpu_cores_physical: int = 0
    cpu_cores_logical: int = 0
    cpu_architecture: str = ""
    cpu_model: str = ""
    cpu_freq_mhz: float = 0.0
    cpu_vendor: str = ""

    # RAM
    ram_total_gb: float = 0.0
    ram_available_gb: float = 0.0
    ram_swap_gb: float = 0.0

    # GPU
    gpu_count: int = 0
    gpu_vendors: List[str] = dataclasses.field(default_factory=list)
    gpu_models: List[str] = dataclasses.field(default_factory=list)
    gpu_vram_total_gb: float = 0.0
    has_nvidia: bool = False
    has_amd: bool = False
    has_apple_silicon: bool = False

    # Disk
    disk_total_gb: float = 0.0
    disk_free_gb: float = 0.0

    # OS
    os_name: str = ""
    os_version: str = ""
    os_arch: str = ""

    # Derived scores
    cpu_score: int = 0  # 1-10, higher = better for LLM inference
    memory_score: int = 0  # 1-10
    gpu_score: int = 0  # 1-10, 0 = no GPU
    overall_tier: str = "unknown"  # edge, low, mid, high, enthusiast

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu": {
                "cores_physical": self.cpu_cores_physical,
                "cores_logical": self.cpu_cores_logical,
                "architecture": self.cpu_architecture,
                "model": self.cpu_model,
                "freq_mhz": self.cpu_freq_mhz,
                "vendor": self.cpu_vendor,
                "score": self.cpu_score,
            },
            "memory": {
                "total_gb": self.ram_total_gb,
                "available_gb": self.ram_available_gb,
                "swap_gb": self.ram_swap_gb,
                "score": self.memory_score,
            },
            "gpu": {
                "count": self.gpu_count,
                "vendors": self.gpu_vendors,
                "models": self.gpu_models,
                "vram_total_gb": self.gpu_vram_total_gb,
                "has_nvidia": self.has_nvidia,
                "has_amd": self.has_amd,
                "has_apple_silicon": self.has_apple_silicon,
                "score": self.gpu_score,
            },
            "disk": {
                "total_gb": self.disk_total_gb,
                "free_gb": self.disk_free_gb,
            },
            "os": {
                "name": self.os_name,
                "version": self.os_version,
                "arch": self.os_arch,
            },
            "tier": self.overall_tier,
        }

    def can_run_model(self, ram_required_gb: float, disk_required_gb: float) -> bool:
        """Check if this hardware can run a model with given requirements."""
        if self.ram_available_gb < ram_required_gb * 0.8:
            return False
        if self.disk_free_gb < disk_required_gb * 1.5:
            return False
        return True


class HardwareProfiler:
    """Detects system hardware for LLM model selection."""

    def __init__(self) -> None:
        self._profile: Optional[HardwareProfile] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def profile(self, refresh: bool = False) -> HardwareProfile:
        """Get (or refresh) hardware profile."""
        if self._profile is None or refresh:
            self._profile = self._detect()
        return self._profile

    def quick_summary(self) -> str:
        """One-line hardware summary."""
        p = self.profile()
        gpu_str = f"+ {len(p.gpu_models)} GPU(s)" if p.gpu_count > 0 else "CPU-only"
        return f"{p.cpu_model} ({p.cpu_cores_logical} cores) | {p.ram_total_gb:.1f}GB RAM | {gpu_str} | Tier: {p.overall_tier}"

    # ------------------------------------------------------------------
    # Detection internals
    # ------------------------------------------------------------------

    def _detect(self) -> HardwareProfile:
        p = HardwareProfile()
        p.os_name = platform.system()
        p.os_version = platform.release()
        p.os_arch = platform.machine()

        self._detect_cpu(p)
        self._detect_memory(p)
        self._detect_gpu(p)
        self._detect_disk(p)
        self._compute_scores(p)

        return p

    def _detect_cpu(self, p: HardwareProfile) -> None:
        """Detect CPU information."""
        try:
            p.cpu_cores_logical = os.cpu_count() or 1
        except Exception:
            p.cpu_cores_logical = 1

        # Physical cores (may equal logical on some platforms)
        try:
            if hasattr(os, 'sysconf') and 'SC_NPROCESSORS_ONLN' in os.sysconf_names:
                p.cpu_cores_physical = os.sysconf('SC_NPROCESSORS_ONLN')
            else:
                p.cpu_cores_physical = p.cpu_cores_logical
        except Exception:
            p.cpu_cores_physical = p.cpu_cores_logical

        # Architecture
        p.cpu_architecture = platform.machine() or "unknown"

        # CPU model and vendor
        if p.os_name == "Linux":
            self._read_cpuinfo_linux(p)
        elif p.os_name == "Darwin":  # macOS
            self._read_cpuinfo_macos(p)
        elif p.os_name == "Windows":
            self._read_cpuinfo_windows(p)

        # Frequency detection
        try:
            if p.os_name == "Linux":
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if "cpu MHz" in line:
                            match = re.search(r'(\d+\.\d+)', line)
                            if match:
                                p.cpu_freq_mhz = float(match.group(1))
                                break
            elif p.os_name == "Darwin":
                result = subprocess.run(
                    ["sysctl", "-n", "hw.cpufrequency"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    freq_hz = int(result.stdout.strip())
                    p.cpu_freq_mhz = freq_hz / 1e6
            elif p.os_name == "Windows":
                result = subprocess.run(
                    ["wmic", "cpu", "get", "MaxClockSpeed", "/value"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    match = re.search(r'MaxClockSpeed=(\d+)', result.stdout)
                    if match:
                        p.cpu_freq_mhz = float(match.group(1))
        except Exception:
            pass

        if p.cpu_freq_mhz == 0:
            p.cpu_freq_mhz = 2400.0  # Default assumption

    def _read_cpuinfo_linux(self, p: HardwareProfile) -> None:
        try:
            with open("/proc/cpuinfo", "r") as f:
                content = f.read()
                # Vendor
                if "AuthenticAMD" in content:
                    p.cpu_vendor = "AMD"
                elif "GenuineIntel" in content:
                    p.cpu_vendor = "Intel"
                elif "ARM" in content or "aarch64" in p.cpu_architecture:
                    p.cpu_vendor = "ARM"

                # Model name
                match = re.search(r'model name\s*:\s*(.+)', content)
                if match:
                    p.cpu_model = match.group(1).strip()
                elif "ARM" in content or "aarch64" in p.cpu_architecture:
                    # Try to get ARM model from other sources
                    match = re.search(r'CPU implementer\s*:\s*(.+)', content)
                    if match:
                        p.cpu_model = f"ARM ({match.group(1).strip()})"
                    else:
                        p.cpu_model = "ARM Processor"
        except Exception:
            pass

    def _read_cpuinfo_macos(self, p: HardwareProfile) -> None:
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                p.cpu_model = result.stdout.strip()
                if "Apple" in p.cpu_model:
                    p.cpu_vendor = "Apple"
                    p.has_apple_silicon = True
                elif "Intel" in p.cpu_model:
                    p.cpu_vendor = "Intel"
                elif "AMD" in p.cpu_model:
                    p.cpu_vendor = "AMD"
        except Exception:
            pass

        # Try to detect Apple Silicon specifically
        if p.cpu_architecture == "arm64":
            p.has_apple_silicon = True
            p.cpu_vendor = "Apple"
            if not p.cpu_model:
                p.cpu_model = "Apple Silicon"

    def _read_cpuinfo_windows(self, p: HardwareProfile) -> None:
        try:
            result = subprocess.run(
                ["wmic", "cpu", "get", "Name", "/value"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                match = re.search(r'Name=(.+)', result.stdout)
                if match:
                    p.cpu_model = match.group(1).strip()
                if "Intel" in p.cpu_model:
                    p.cpu_vendor = "Intel"
                elif "AMD" in p.cpu_model:
                    p.cpu_vendor = "AMD"
        except Exception:
            pass

    def _detect_memory(self, p: HardwareProfile) -> None:
        """Detect RAM and swap information."""
        if p.os_name == "Linux":
            self._read_meminfo_linux(p)
        elif p.os_name == "Darwin":
            self._read_meminfo_macos(p)
        elif p.os_name == "Windows":
            self._read_meminfo_windows(p)

    def _read_meminfo_linux(self, p: HardwareProfile) -> None:
        try:
            with open("/proc/meminfo", "r") as f:
                meminfo = f.read()

                total_match = re.search(r'MemTotal:\s+(\d+)\s+kB', meminfo)
                if total_match:
                    p.ram_total_gb = int(total_match.group(1)) / (1024 * 1024)

                avail_match = re.search(r'MemAvailable:\s+(\d+)\s+kB', meminfo)
                if avail_match:
                    p.ram_available_gb = int(avail_match.group(1)) / (1024 * 1024)
                else:
                    free_match = re.search(r'MemFree:\s+(\d+)\s+kB', meminfo)
                    if free_match:
                        p.ram_available_gb = int(free_match.group(1)) / (1024 * 1024)

                swap_total = re.search(r'SwapTotal:\s+(\d+)\s+kB', meminfo)
                if swap_total:
                    p.ram_swap_gb = int(swap_total.group(1)) / (1024 * 1024)
        except Exception:
            pass

    def _read_meminfo_macos(self, p: HardwareProfile) -> None:
        try:
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                p.ram_total_gb = int(result.stdout.strip()) / (1024 ** 3)

            # Available memory via vm_stat
            result = subprocess.run(
                ["vm_stat"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                page_size = 4096  # Default macOS page size
                free_match = re.search(r'free:\s+(\d+)\.', result.stdout)
                if free_match:
                    free_pages = int(free_match.group(1).replace(".", ""))
                    p.ram_available_gb = (free_pages * page_size) / (1024 ** 3)
        except Exception:
            pass

    def _read_meminfo_windows(self, p: HardwareProfile) -> None:
        try:
            result = subprocess.run(
                ["wmic", "ComputerSystem", "get", "TotalPhysicalMemory", "/value"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                match = re.search(r'TotalPhysicalMemory=(\d+)', result.stdout)
                if match:
                    p.ram_total_gb = int(match.group(1)) / (1024 ** 3)

            result = subprocess.run(
                ["wmic", "OS", "get", "FreePhysicalMemory", "/value"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                match = re.search(r'FreePhysicalMemory=(\d+)', result.stdout)
                if match:
                    p.ram_available_gb = int(match.group(1)) / (1024 ** 2)  # KB to GB
        except Exception:
            pass

    def _detect_gpu(self, p: HardwareProfile) -> None:
        """Detect GPU information."""
        if p.os_name == "Linux":
            self._detect_gpu_linux(p)
        elif p.os_name == "Darwin":
            self._detect_gpu_macos(p)
        elif p.os_name == "Windows":
            self._detect_gpu_windows(p)

    def _detect_gpu_linux(self, p: HardwareProfile) -> None:
        # Try nvidia-smi
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        parts = line.split(",")
                        if len(parts) >= 2:
                            p.gpu_models.append(parts[0].strip())
                            vram_str = parts[1].strip()
                            match = re.search(r'(\d+)', vram_str)
                            if match:
                                p.gpu_vram_total_gb += int(match.group(1)) / 1024  # MiB to GiB
                            p.gpu_count += 1
                            p.has_nvidia = True
                            p.gpu_vendors.append("NVIDIA")
        except Exception:
            pass

        # Try AMD (rocm-smi or lspci)
        if p.gpu_count == 0:
            try:
                result = subprocess.run(
                    ["lspci"], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and "AMD" in result.stdout:
                    # Simple AMD detection via lspci
                    for line in result.stdout.split("\n"):
                        if "VGA" in line and "AMD" in line:
                            p.gpu_count += 1
                            p.has_amd = True
                            p.gpu_vendors.append("AMD")
                            match = re.search(r'\[(.*?)\]', line)
                            if match:
                                p.gpu_models.append(match.group(1))
                            else:
                                p.gpu_models.append("AMD GPU")
            except Exception:
                pass

        # Try Intel GPU
        if p.gpu_count == 0:
            try:
                result = subprocess.run(
                    ["lspci"], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and "Intel" in result.stdout:
                    for line in result.stdout.split("\n"):
                        if "VGA" in line and "Intel" in line:
                            p.gpu_count += 1
                            p.gpu_vendors.append("Intel")
                            match = re.search(r'\[(.*?)\]', line)
                            if match:
                                p.gpu_models.append(match.group(1))
            except Exception:
                pass

    def _detect_gpu_macos(self, p: HardwareProfile) -> None:
        if p.has_apple_silicon:
            # Apple Silicon has unified memory, GPU shares RAM
            p.gpu_count = 1
            p.gpu_vendors.append("Apple")
            p.gpu_models.append("Apple Silicon GPU")
            p.gpu_vram_total_gb = p.ram_total_gb * 0.5  # Approximate shared allocation
            return

        # Intel Mac with AMD GPU
        try:
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                output = result.stdout
                # Parse GPU info from system_profiler
                if "AMD" in output or "Radeon" in output:
                    p.has_amd = True
                    p.gpu_vendors.append("AMD")
                    p.gpu_count += 1
                if "NVIDIA" in output or "GeForce" in output:
                    p.has_nvidia = True
                    p.gpu_vendors.append("NVIDIA")
                    p.gpu_count += 1
        except Exception:
            pass

    def _detect_gpu_windows(self, p: HardwareProfile) -> None:
        try:
            result = subprocess.run(
                ["wmic", "path", "win32_VideoController", "get", "Name,AdapterRAM", "/value"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                output = result.stdout
                # Parse output
                names = re.findall(r'Name=(.+)', output)
                rams = re.findall(r'AdapterRAM=(\d+)', output)
                for i, name in enumerate(names):
                    name = name.strip()
                    p.gpu_models.append(name)
                    p.gpu_count += 1
                    if "NVIDIA" in name or "GeForce" in name or "RTX" in name or "Tesla" in name:
                        p.has_nvidia = True
                        p.gpu_vendors.append("NVIDIA")
                    elif "AMD" in name or "Radeon" in name:
                        p.has_amd = True
                        p.gpu_vendors.append("AMD")
                    elif "Intel" in name:
                        p.gpu_vendors.append("Intel")
                    else:
                        p.gpu_vendors.append("Unknown")

                    if i < len(rams):
                        try:
                            vram_bytes = int(rams[i])
                            p.gpu_vram_total_gb += vram_bytes / (1024 ** 3)
                        except ValueError:
                            pass
        except Exception:
            pass

    def _detect_disk(self, p: HardwareProfile) -> None:
        """Detect disk space."""
        try:
            if p.os_name == "Windows":
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                total_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p("C:\\"), 
                    ctypes.pointer(free_bytes), 
                    ctypes.pointer(total_bytes), 
                    None
                )
                p.disk_total_gb = total_bytes.value / (1024 ** 3)
                p.disk_free_gb = free_bytes.value / (1024 ** 3)
            else:
                # Unix-like
                stat = os.statvfs("/")
                p.disk_total_gb = (stat.f_blocks * stat.f_frsize) / (1024 ** 3)
                p.disk_free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
        except Exception:
            pass

    def _compute_scores(self, p: HardwareProfile) -> None:
        """Compute performance scores and tier."""
        # CPU score (1-10): based on cores and frequency
        core_score = min(p.cpu_cores_logical / 4, 5)  # Up to 5 points for 20+ cores
        freq_score = min((p.cpu_freq_mhz - 1000) / 400, 3)  # Up to 3 points for high freq
        arch_bonus = 2 if p.cpu_architecture in ("x86_64", "AMD64") else 1
        p.cpu_score = min(10, max(1, int(core_score + freq_score + arch_bonus)))

        # Memory score (1-10): based on RAM
        if p.ram_total_gb >= 64:
            p.memory_score = 10
        elif p.ram_total_gb >= 32:
            p.memory_score = 8
        elif p.ram_total_gb >= 16:
            p.memory_score = 6
        elif p.ram_total_gb >= 8:
            p.memory_score = 4
        elif p.ram_total_gb >= 4:
            p.memory_score = 2
        else:
            p.memory_score = 1

        # GPU score (1-10): based on VRAM and vendor
        if p.gpu_count == 0:
            p.gpu_score = 0
        elif p.gpu_vram_total_gb >= 24:
            p.gpu_score = 10
        elif p.gpu_vram_total_gb >= 16:
            p.gpu_score = 8
        elif p.gpu_vram_total_gb >= 8:
            p.gpu_score = 6
        elif p.gpu_vram_total_gb >= 4:
            p.gpu_score = 4
        else:
            p.gpu_score = 2

        # Apple Silicon bonus
        if p.has_apple_silicon and p.ram_total_gb >= 8:
            p.gpu_score = max(p.gpu_score, 6)  # Unified memory is efficient

        # Overall tier
        if p.ram_total_gb < 4:
            p.overall_tier = "edge"
        elif p.ram_total_gb < 8:
            p.overall_tier = "low"
        elif p.ram_total_gb < 16:
            p.overall_tier = "mid"
        elif p.ram_total_gb < 32:
            p.overall_tier = "high"
        else:
            p.overall_tier = "enthusiast"

        # GPU can bump tier up
        if p.gpu_score >= 6 and p.overall_tier in ("low", "mid"):
            p.overall_tier = "high" if p.overall_tier == "mid" else "mid"


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== MAGNATRIX-OS Hardware Profiler ===\n")
    profiler = HardwareProfiler()
    profile = profiler.profile()

    print(f"Quick Summary: {profiler.quick_summary()}\n")
    print("Detailed Profile:")
    print(json.dumps(profile.to_dict(), indent=2))
    print("\n=== Hardware Profiler Demo Complete ===")


if __name__ == "__main__":
    _demo()
