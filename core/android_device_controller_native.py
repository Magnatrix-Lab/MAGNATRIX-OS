"""
android_device_controller_native.py
MAGNATRIX-OS — Android Device Controller

scrcpy/ADB bridge for device discovery, connection management,
and screen mirroring control. Pure Python standard library.
"""

import os
import re
import json
import subprocess
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class AndroidDevice:
    serial: str
    status: str
    model: str = "unknown"
    brand: str = "unknown"
    android_version: str = "unknown"
    resolution: str = "unknown"
    is_wireless: bool = False
    ip_address: str = ""


class AndroidDeviceController:
    """Core scrcpy/ADB device controller."""

    def __init__(self, scrcpy_path: str = "scrcpy", adb_path: str = "adb"):
        self.scrcpy_path = scrcpy_path
        self.adb_path = adb_path
        self.devices: Dict[str, AndroidDevice] = {}
        self._active_sessions: Dict[str, subprocess.Popen] = {}

    def _adb(self, args: List[str]) -> Tuple[int, str, str]:
        try:
            proc = subprocess.run(
                [self.adb_path] + args,
                capture_output=True, text=True, timeout=30
            )
            return proc.returncode, proc.stdout, proc.stderr
        except Exception as e:
            return -1, "", str(e)

    def discover(self) -> List[AndroidDevice]:
        rc, out, _ = self._adb(["devices", "-l"])
        if rc != 0:
            return []
        devices = []
        for line in out.strip().splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2:
                serial = parts[0]
                status = parts[1]
                model = self._extract_prop(parts, "model")
                brand = self._extract_prop(parts, "device")
                is_wireless = ":" in serial
                ip = serial.split(":")[0] if is_wireless else ""
                dev = AndroidDevice(
                    serial=serial, status=status, model=model,
                    brand=brand, is_wireless=is_wireless, ip_address=ip
                )
                # Get extra info
                dev.android_version = self.get_prop(serial, "ro.build.version.release")
                dev.resolution = self.get_resolution(serial)
                devices.append(dev)
                self.devices[serial] = dev
        return devices

    def _extract_prop(self, parts: List[str], key: str) -> str:
        for p in parts:
            if p.startswith(f"{key}:"):
                return p.split(":", 1)[1]
        return "unknown"

    def get_prop(self, serial: str, prop: str) -> str:
        rc, out, _ = self._adb(["-s", serial, "shell", "getprop", prop])
        return out.strip() if rc == 0 else "unknown"

    def get_resolution(self, serial: str) -> str:
        rc, out, _ = self._adb(["-s", serial, "shell", "wm", "size"])
        if rc == 0:
            m = re.search(r'(\d+x\d+)', out)
            return m.group(1) if m else "unknown"
        return "unknown"

    def connect_tcp(self, ip: str, port: int = 5555) -> bool:
        rc, _, _ = self._adb(["connect", f"{ip}:{port}"])
        return rc == 0

    def disconnect(self, serial: str) -> bool:
        rc, _, _ = self._adb(["disconnect", serial])
        return rc == 0

    def start_mirror(self, serial: str, options: Optional[Dict] = None) -> bool:
        opts = options or {}
        cmd = [self.scrcpy_path, "-s", serial]
        if opts.get("no_control"):
            cmd.append("--no-control")
        if opts.get("fullscreen"):
            cmd.append("--fullscreen")
        if opts.get("record"):
            cmd.extend(["--record", opts["record"]])
        if opts.get("crop"):
            cmd.extend(["--crop", opts["crop"]])
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._active_sessions[serial] = proc
            return True
        except Exception:
            return False

    def stop_mirror(self, serial: str) -> bool:
        if serial in self._active_sessions:
            self._active_sessions[serial].terminate()
            del self._active_sessions[serial]
            return True
        return False

    def list_active_sessions(self) -> List[str]:
        return list(self._active_sessions.keys())

    def to_dict(self) -> Dict:
        return {
            "devices": [asdict(d) for d in self.devices.values()],
            "active_sessions": self.list_active_sessions(),
        }
