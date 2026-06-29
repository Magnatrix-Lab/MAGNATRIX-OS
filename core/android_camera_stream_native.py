"""
android_camera_stream_native.py
MAGNATRIX-OS — Android Camera Stream

Camera/webcam mode streaming, lens control, torch, and zoom.
Pure Python standard library.
"""

import subprocess
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum


class CameraLens(Enum):
    BACK = "0"
    FRONT = "1"
    WIDE = "2"
    TELE = "3"


@dataclass
class CameraConfig:
    lens: str = "0"
    resolution: str = "1920x1080"
    fps: int = 30
    torch: bool = False
    zoom: float = 1.0


class AndroidCameraStream:
    """Camera stream and control for Android devices."""

    def __init__(self, scrcpy_path: str = "scrcpy", adb_path: str = "adb"):
        self.scrcpy_path = scrcpy_path
        self.adb_path = adb_path

    def _adb(self, args: List[str]) -> Tuple[int, str, str]:
        try:
            proc = subprocess.run(
                [self.adb_path] + args,
                capture_output=True, text=True, timeout=10
            )
            return proc.returncode, proc.stdout, proc.stderr
        except Exception as e:
            return -1, "", str(e)

    def start_camera(self, serial: str, config: Optional[CameraConfig] = None) -> bool:
        cfg = config or CameraConfig()
        cmd = [self.scrcpy_path, "-s", serial, "--camera=" + cfg.lens]
        if cfg.resolution:
            cmd.append(f"--camera-size={cfg.resolution}")
        if cfg.fps:
            cmd.append(f"--camera-fps={cfg.fps}")
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    def list_lenses(self, serial: str) -> List[Dict]:
        # Query available camera sensors
        rc, out, _ = self._adb(["-s", serial, "shell", "dumpsys", "media.camera"])
        lenses = []
        if rc == 0:
            current = {}
            for line in out.splitlines():
                if "Camera device" in line:
                    if current:
                        lenses.append(current)
                    current = {"id": line.strip().split()[-1]}
                elif "facing" in line and current:
                    current["facing"] = line.strip().split("=")[-1]
            if current:
                lenses.append(current)
        # Fallback: assume at least 2 cameras
        if not lenses:
            lenses = [{"id": "0", "facing": "BACK"}, {"id": "1", "facing": "FRONT"}]
        return lenses

    def set_torch(self, serial: str, on: bool) -> bool:
        # Use camera API to toggle torch
        value = "torch" if on else "off"
        rc, _, _ = self._adb(["-s", serial, "shell", "settings", "put", "system", "flashlight_mode", value])
        return rc == 0

    def set_zoom(self, serial: str, level: float) -> bool:
        # Clamp zoom between 1.0 and 5.0
        level = max(1.0, min(5.0, level))
        rc, _, _ = self._adb(["-s", serial, "shell", "am", "start", "-a", "android.intent.action.MAIN", "-e", "zoom", str(level)])
        return rc == 0

    def start_webcam_mode(self, serial: str, lens: str = "0") -> bool:
        cmd = [self.scrcpy_path, "-s", serial, "--camera=" + lens, "--v4l2-sink=/dev/video0"]
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    def get_camera_info(self, serial: str) -> Dict:
        lenses = self.list_lenses(serial)
        return {
            "lenses": lenses,
            "lens_count": len(lenses),
        }
