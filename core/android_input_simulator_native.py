"""
android_input_simulator_native.py
MAGNATRIX-OS — Android Input Simulator

Touch, swipe, keyboard, and mouse input automation via ADB.
Pure Python standard library.
"""

import subprocess
from typing import Tuple, List, Optional, Dict
from dataclasses import dataclass
from enum import Enum


class InputType(Enum):
    TAP = "tap"
    SWIPE = "swipe"
    KEYEVENT = "keyevent"
    TEXT = "text"
    LONG_PRESS = "longpress"


@dataclass
class Point:
    x: int
    y: int


class AndroidInputSimulator:
    """HID-like input simulation for Android devices."""

    def __init__(self, adb_path: str = "adb"):
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

    def tap(self, serial: str, x: int, y: int) -> bool:
        rc, _, _ = self._adb(["-s", serial, "shell", "input", "tap", str(x), str(y)])
        return rc == 0

    def swipe(self, serial: str, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        rc, _, _ = self._adb([
            "-s", serial, "shell", "input", "swipe",
            str(x1), str(y1), str(x2), str(y2), str(duration_ms)
        ])
        return rc == 0

    def long_press(self, serial: str, x: int, y: int, duration_ms: int = 800) -> bool:
        return self.swipe(serial, x, y, x, y, duration_ms)

    def text(self, serial: str, text: str) -> bool:
        # Escape special chars for shell
        safe_text = text.replace(" ", "%s").replace("&", "\\&")
        rc, _, _ = self._adb(["-s", serial, "shell", "input", "text", f"'{safe_text}'"])
        return rc == 0

    def keyevent(self, serial: str, keycode: int) -> bool:
        rc, _, _ = self._adb(["-s", serial, "shell", "input", "keyevent", str(keycode)])
        return rc == 0

    def back(self, serial: str) -> bool:
        return self.keyevent(serial, 4)

    def home(self, serial: str) -> bool:
        return self.keyevent(serial, 3)

    def recent_apps(self, serial: str) -> bool:
        return self.keyevent(serial, 187)

    def power(self, serial: str) -> bool:
        return self.keyevent(serial, 26)

    def volume_up(self, serial: str) -> bool:
        return self.keyevent(serial, 24)

    def volume_down(self, serial: str) -> bool:
        return self.keyevent(serial, 25)

    def scroll_down(self, serial: str, x: int = 540, y: int = 1000) -> bool:
        return self.swipe(serial, x, y + 400, x, y - 400, 300)

    def scroll_up(self, serial: str, x: int = 540, y: int = 1000) -> bool:
        return self.swipe(serial, x, y - 400, x, y + 400, 300)

    def execute_sequence(self, serial: str, actions: List[Dict]) -> Dict:
        results = {"total": len(actions), "passed": 0, "failed": 0, "details": []}
        for action in actions:
            action_type = action.get("type")
            ok = False
            if action_type == "tap":
                ok = self.tap(serial, action["x"], action["y"])
            elif action_type == "swipe":
                ok = self.swipe(serial, action["x1"], action["y1"], action["x2"], action["y2"], action.get("duration", 300))
            elif action_type == "text":
                ok = self.text(serial, action["text"])
            elif action_type == "key":
                ok = self.keyevent(serial, action["keycode"])
            elif action_type == "sleep":
                import time
                time.sleep(action["seconds"])
                ok = True
            if ok:
                results["passed"] += 1
            else:
                results["failed"] += 1
            results["details"].append({"action": action_type, "ok": ok})
        return results
