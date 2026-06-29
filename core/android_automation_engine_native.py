"""
android_automation_engine_native.py
MAGNATRIX-OS — Android Automation Engine

Script-based UI automation, macro recording/playback, and workflow engine.
Pure Python standard library.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class MacroStep:
    action: str  # tap, swipe, text, key, sleep, assert
    params: Dict
    timestamp: float = 0.0


class AndroidAutomationEngine:
    """Macro recording and playback for Android device automation."""

    def __init__(self, input_simulator=None, screen_capture=None):
        self.input_simulator = input_simulator
        self.screen_capture = screen_capture
        self.macros: Dict[str, List[MacroStep]] = {}
        self.recording: List[MacroStep] = []
        self.is_recording = False
        self.macros_dir = Path("macros")
        self.macros_dir.mkdir(exist_ok=True)
        self._load_macros()

    def _load_macros(self) -> None:
        for f in self.macros_dir.glob("*.json"):
            with open(f, "r") as fp:
                data = json.load(fp)
                self.macros[f.stem] = [MacroStep(**s) for s in data]

    def _save_macro(self, name: str) -> None:
        path = self.macros_dir / f"{name}.json"
        with open(path, "w") as fp:
            json.dump([asdict(s) for s in self.macros[name]], fp, indent=2)

    def start_recording(self) -> None:
        self.recording = []
        self.is_recording = True

    def stop_recording(self, name: str) -> bool:
        if not self.is_recording or not self.recording:
            return False
        self.macros[name] = self.recording
        self._save_macro(name)
        self.is_recording = False
        self.recording = []
        return True

    def record_step(self, action: str, **params) -> None:
        if self.is_recording:
            self.recording.append(MacroStep(
                action=action, params=params, timestamp=time.time()
            ))

    def play_macro(self, name: str, serial: str, speed: float = 1.0) -> Dict:
        if name not in self.macros:
            return {"error": f"Macro '{name}' not found"}
        steps = self.macros[name]
        results = {"total": len(steps), "passed": 0, "failed": 0, "steps": []}
        if not self.input_simulator:
            return {"error": "No input simulator available"}
        for step in steps:
            ok = False
            if step.action == "tap":
                ok = self.input_simulator.tap(serial, step.params["x"], step.params["y"])
            elif step.action == "swipe":
                ok = self.input_simulator.swipe(
                    serial, step.params["x1"], step.params["y1"],
                    step.params["x2"], step.params["y2"],
                    step.params.get("duration", 300)
                )
            elif step.action == "text":
                ok = self.input_simulator.text(serial, step.params["text"])
            elif step.action == "key":
                ok = self.input_simulator.keyevent(serial, step.params["keycode"])
            elif step.action == "sleep":
                time.sleep(step.params["seconds"] / speed)
                ok = True
            elif step.action == "back":
                ok = self.input_simulator.back(serial)
            elif step.action == "home":
                ok = self.input_simulator.home(serial)
            if ok:
                results["passed"] += 1
            else:
                results["failed"] += 1
            results["steps"].append({"action": step.action, "ok": ok})
        return results

    def delete_macro(self, name: str) -> bool:
        if name in self.macros:
            del self.macros[name]
            path = self.macros_dir / f"{name}.json"
            if path.exists():
                path.unlink()
            return True
        return False

    def list_macros(self) -> List[str]:
        return list(self.macros.keys())

    def create_workflow(self, name: str, steps: List[Dict]) -> bool:
        macro = [MacroStep(action=s["action"], params=s.get("params", {})) for s in steps]
        self.macros[name] = macro
        self._save_macro(name)
        return True

    def to_dict(self) -> Dict:
        return {
            "macros": list(self.macros.keys()),
            "count": len(self.macros),
            "is_recording": self.is_recording,
        }
