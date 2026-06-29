"""
android_screen_capture_native.py
MAGNATRIX-OS — Android Screen Capture & Recording

Screenshot, frame extraction, and screen recording pipeline.
Pure Python standard library.
"""

import os
import time
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CaptureConfig:
    output_dir: str = "captures"
    format: str = "png"
    quality: int = 80
    max_files: int = 1000


class AndroidScreenCapture:
    """Screen capture and recording for Android devices."""

    def __init__(self, adb_path: str = "adb"):
        self.adb_path = adb_path
        self.output_dir = Path("captures")
        self.output_dir.mkdir(exist_ok=True)

    def _adb(self, args: List[str]) -> Tuple[int, str, str]:
        try:
            proc = subprocess.run(
                [self.adb_path] + args,
                capture_output=True, text=True, timeout=30
            )
            return proc.returncode, proc.stdout, proc.stderr
        except Exception as e:
            return -1, "", str(e)

    def screenshot(self, serial: str, filename: Optional[str] = None) -> Optional[str]:
        if not filename:
            filename = f"screenshot_{serial.replace(":", "_")}_{int(time.time())}.png"
        device_path = "/sdcard/screen_tmp.png"
        rc, _, _ = self._adb(["-s", serial, "shell", "screencap", "-p", device_path])
        if rc != 0:
            return None
        local_path = self.output_dir / filename
        rc, _, _ = self._adb(["-s", serial, "pull", device_path, str(local_path)])
        self._adb(["-s", serial, "shell", "rm", device_path])
        return str(local_path) if rc == 0 else None

    def start_recording(self, serial: str, duration: int = 30, filename: Optional[str] = None) -> Optional[str]:
        if not filename:
            filename = f"record_{serial.replace(":", "_")}_{int(time.time())}.mp4"
        device_path = f"/sdcard/record_tmp.mp4"
        cmd = [self.adb_path, "-s", serial, "shell", "screenrecord", "--time-limit", str(duration), device_path]
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {"pid": proc.pid, "device_path": device_path, "local_filename": filename}
        except Exception:
            return None

    def stop_recording(self, serial: str, session_info: Dict) -> Optional[str]:
        try:
            import signal
            os.kill(session_info["pid"], signal.SIGTERM)
        except Exception:
            pass
        time.sleep(1)
        local_path = self.output_dir / session_info["local_filename"]
        rc, _, _ = self._adb(["-s", serial, "pull", session_info["device_path"], str(local_path)])
        self._adb(["-s", serial, "shell", "rm", session_info["device_path"]])
        return str(local_path) if rc == 0 else None

    def list_captures(self) -> List[Dict]:
        captures = []
        for f in sorted(self.output_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            st = f.stat()
            captures.append({
                "name": f.name,
                "size": st.st_size,
                "modified": datetime.fromtimestamp(st.st_mtime).isoformat(),
                "path": str(f),
            })
        return captures

    def clear_captures(self) -> int:
        count = 0
        for f in self.output_dir.iterdir():
            f.unlink()
            count += 1
        return count
