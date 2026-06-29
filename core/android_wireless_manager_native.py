"""
android_wireless_manager_native.py
MAGNATRIX-OS — Android Wireless Manager

Wireless ADB pairing, connection history, and network device management.
Pure Python standard library.
"""

import json
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class WirelessConnection:
    ip: str
    port: int
    serial: str
    model: str
    last_connected: str
    connection_count: int = 1


class AndroidWirelessManager:
    """Wireless ADB pairing and connection management."""

    def __init__(self, adb_path: str = "adb", history_file: str = "wireless_history.json"):
        self.adb_path = adb_path
        self.history_file = Path(history_file)
        self.history: Dict[str, WirelessConnection] = {}
        self._load_history()

    def _adb(self, args: List[str]) -> Tuple[int, str, str]:
        try:
            proc = subprocess.run(
                [self.adb_path] + args,
                capture_output=True, text=True, timeout=30
            )
            return proc.returncode, proc.stdout, proc.stderr
        except Exception as e:
            return -1, "", str(e)

    def _load_history(self) -> None:
        if self.history_file.exists():
            with open(self.history_file, "r") as f:
                data = json.load(f)
                for k, v in data.items():
                    self.history[k] = WirelessConnection(**v)

    def _save_history(self) -> None:
        with open(self.history_file, "w") as f:
            json.dump({k: asdict(v) for k, v in self.history.items()}, f, indent=2)

    def pair(self, ip: str, port: int, pairing_code: str) -> bool:
        rc, _, _ = self._adb(["pair", f"{ip}:{port}", pairing_code])
        return rc == 0

    def connect(self, ip: str, port: int = 5555) -> Optional[str]:
        rc, out, _ = self._adb(["connect", f"{ip}:{port}"])
        if rc == 0 and "connected" in out.lower():
            serial = f"{ip}:{port}"
            # Get device info
            _, model_out, _ = self._adb(["-s", serial, "shell", "getprop", "ro.product.model"])
            model = model_out.strip() or "unknown"
            # Update history
            if serial in self.history:
                self.history[serial].connection_count += 1
                self.history[serial].last_connected = datetime.now().isoformat()
            else:
                self.history[serial] = WirelessConnection(
                    ip=ip, port=port, serial=serial, model=model,
                    last_connected=datetime.now().isoformat()
                )
            self._save_history()
            return serial
        return None

    def disconnect(self, serial: str) -> bool:
        rc, _, _ = self._adb(["disconnect", serial])
        return rc == 0

    def disconnect_all(self) -> bool:
        rc, _, _ = self._adb(["disconnect"])
        return rc == 0

    def get_history(self) -> List[Dict]:
        return [asdict(v) for v in self.history.values()]

    def remove_from_history(self, serial: str) -> bool:
        if serial in self.history:
            del self.history[serial]
            self._save_history()
            return True
        return False

    def reconnect_all(self) -> List[str]:
        connected = []
        for conn in self.history.values():
            serial = self.connect(conn.ip, conn.port)
            if serial:
                connected.append(serial)
        return connected

    def to_dict(self) -> Dict:
        return {
            "history": [asdict(v) for v in self.history.values()],
            "count": len(self.history),
        }
