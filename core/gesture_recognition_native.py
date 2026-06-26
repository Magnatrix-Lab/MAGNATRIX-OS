#!/usr/bin/env python3
"""Gesture Recognition for MAGNATRIX-OS — Gesture-based control."""
from __future__ import annotations
import time
from typing import Any, Dict, List

class GestureRecognition:
    GESTURES = {
        "swipe_left": "previous",
        "swipe_right": "next",
        "tap": "select",
        "double_tap": "open",
        "long_press": "context_menu",
    }

    def __init__(self) -> None:
        self._last_gesture = ""
        self._gesture_count = 0

    def recognize(self, gesture_data: Dict[str, Any]) -> str:
        gesture = gesture_data.get("type", "unknown")
        self._last_gesture = gesture
        self._gesture_count += 1
        return self.GESTURES.get(gesture, "unknown")

    def stats(self) -> Dict[str, Any]:
        return {"total_gestures": self._gesture_count, "last": self._last_gesture}
