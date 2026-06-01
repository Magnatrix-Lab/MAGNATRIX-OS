#!/usr/bin/env python3
"""
ai/llm_computer_use_native.py
MAGNATRIX-OS — Computer Use / Vision-Action Engine for the LLM Arena
AMATI pattern: screenshot analysis, UI element detection, task automation

Pure Python, stdlib only. Simulates screen analysis, element detection,
action execution, and task planning for computer interaction.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ───────────────────────────────────────────────────────────────
# 0. UTILITIES
# ───────────────────────────────────────────────────────────────

def _now() -> float:
    return time.time()


# ───────────────────────────────────────────────────────────────
# 1. SCREEN ANALYZER
# ───────────────────────────────────────────────────────────────

@dataclass
class UIElement:
    element_id: str
    element_type: str  # button, input, text, link, dropdown, checkbox
    text: str
    x: int
    y: int
    width: int
    height: int
    clickable: bool = False


class ScreenAnalyzer:
    """Simulate screenshot analysis and UI element detection."""

    def analyze(self, screen_id: str, content: str) -> List[UIElement]:
        elements = []
        # Simulate detecting elements from screen content
        lines = content.split("\n")
        y = 10
        for i, line in enumerate(lines):
            if line.strip().startswith("[") and line.strip().endswith("]"):
                # Button
                text = line.strip()[1:-1]
                elements.append(UIElement(f"btn_{i}", "button", text, 10, y, 100, 20, True))
            elif line.strip().startswith("Input:"):
                elements.append(UIElement(f"inp_{i}", "input", line.strip(), 10, y, 200, 20, True))
            elif line.strip().startswith("Link:"):
                elements.append(UIElement(f"lnk_{i}", "link", line.strip()[5:], 10, y, 80, 15, True))
            elif line.strip():
                elements.append(UIElement(f"txt_{i}", "text", line.strip(), 10, y, 300, 15, False))
            y += 25
        return elements


# ───────────────────────────────────────────────────────────────
# 2. ELEMENT DETECTOR
# ───────────────────────────────────────────────────────────────

class ElementDetector:
    """Identify clickable elements, form fields, etc."""

    def find_clickable(self, elements: List[UIElement]) -> List[UIElement]:
        return [e for e in elements if e.clickable]

    def find_by_type(self, elements: List[UIElement], element_type: str) -> List[UIElement]:
        return [e for e in elements if e.element_type == element_type]

    def find_by_text(self, elements: List[UIElement], text: str) -> List[UIElement]:
        return [e for e in elements if text.lower() in e.text.lower()]


# ───────────────────────────────────────────────────────────────
# 3. ACTION EXECUTOR
# ───────────────────────────────────────────────────────────────

class ActionExecutor:
    """Simulate mouse clicks, keyboard input, scrolling."""

    def __init__(self) -> None:
        self._history: List[Dict[str, Any]] = []

    def click(self, element: UIElement) -> Dict[str, Any]:
        result = {"action": "click", "target": element.element_id, "text": element.text, "success": True}
        self._history.append(result)
        return result

    def type_text(self, element: UIElement, text: str) -> Dict[str, Any]:
        result = {"action": "type", "target": element.element_id, "input": text, "success": True}
        self._history.append(result)
        return result

    def scroll(self, direction: str = "down", amount: int = 300) -> Dict[str, Any]:
        result = {"action": "scroll", "direction": direction, "amount": amount, "success": True}
        self._history.append(result)
        return result

    def history(self) -> List[Dict[str, Any]]:
        return self._history.copy()


# ───────────────────────────────────────────────────────────────
# 4. TASK PLANNER
# ───────────────────────────────────────────────────────────────

class TaskPlanner:
    """Break computer tasks into actionable steps."""

    def plan(self, task: str) -> List[Dict[str, Any]]:
        steps = []
        if "navigate" in task.lower() or "go to" in task.lower():
            steps.append({"step": 1, "action": "navigate", "target": "URL from task"})
        if "fill" in task.lower() or "enter" in task.lower():
            steps.append({"step": len(steps) + 1, "action": "find_input", "target": "form field"})
            steps.append({"step": len(steps) + 1, "action": "type", "target": "form field"})
        if "click" in task.lower() or "submit" in task.lower() or "press" in task.lower():
            steps.append({"step": len(steps) + 1, "action": "click", "target": "button"})
        if not steps:
            steps = [
                {"step": 1, "action": "analyze", "target": "screen"},
                {"step": 2, "action": "identify", "target": "relevant elements"},
                {"step": 3, "action": "interact", "target": "target element"},
            ]
        return steps


# ───────────────────────────────────────────────────────────────
# 5. STATE TRACKER
# ───────────────────────────────────────────────────────────────

class StateTracker:
    """Track screen state changes after each action."""

    def __init__(self) -> None:
        self._states: List[Dict[str, Any]] = []

    def record(self, action: Dict[str, Any], screen_before: str, screen_after: str) -> Dict[str, Any]:
        changed = screen_before != screen_after
        state = {
            "action": action,
            "changed": changed,
            "timestamp": _now(),
        }
        self._states.append(state)
        return state

    def is_success(self, action: Dict[str, Any], expected_change: bool = True) -> bool:
        if not self._states:
            return False
        last = self._states[-1]
        return last["changed"] if expected_change else True

    def get_history(self) -> List[Dict[str, Any]]:
        return self._states.copy()


# ───────────────────────────────────────────────────────────────
# 6. SCREENSHOT CACHE
# ───────────────────────────────────────────────────────────────

class ScreenshotCache:
    """Cache analyzed screenshots to avoid re-processing."""

    def __init__(self, max_size: int = 10) -> None:
        self._cache: Dict[str, List[UIElement]] = {}
        self._max_size = max_size

    def get(self, screen_id: str) -> Optional[List[UIElement]]:
        return self._cache.get(screen_id)

    def put(self, screen_id: str, elements: List[UIElement]) -> None:
        if len(self._cache) >= self._max_size:
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        self._cache[screen_id] = elements

    def has_changed(self, screen_id: str, new_elements: List[UIElement]) -> bool:
        cached = self._cache.get(screen_id)
        if not cached:
            return True
        return len(cached) != len(new_elements)


# ───────────────────────────────────────────────────────────────
# 7. COMPUTER USE ENGINE
# ───────────────────────────────────────────────────────────────

class ComputerUseEngine:
    """Main orchestrator: screenshot -> analyze -> plan -> execute -> verify."""

    def __init__(self) -> None:
        self.analyzer = ScreenAnalyzer()
        self.detector = ElementDetector()
        self.executor = ActionExecutor()
        self.planner = TaskPlanner()
        self.tracker = StateTracker()
        self.cache = ScreenshotCache()

    def execute_task(self, task: str, screen_content: str, screen_id: str = "screen_1") -> Dict[str, Any]:
        # Plan
        steps = self.planner.plan(task)

        # Analyze screen
        cached = self.cache.get(screen_id)
        if cached:
            elements = cached
        else:
            elements = self.analyzer.analyze(screen_id, screen_content)
            self.cache.put(screen_id, elements)

        # Execute steps
        executed = []
        for step in steps:
            action_type = step["action"]
            if action_type == "click":
                targets = self.detector.find_clickable(elements)
                if targets:
                    result = self.executor.click(targets[0])
                else:
                    result = {"action": "click", "success": False, "error": "No clickable element found"}
            elif action_type == "type":
                inputs = self.detector.find_by_type(elements, "input")
                if inputs:
                    result = self.executor.type_text(inputs[0], "sample text")
                else:
                    result = {"action": "type", "success": False, "error": "No input found"}
            elif action_type == "navigate":
                result = {"action": "navigate", "target": step.get("target"), "success": True}
            else:
                result = {"action": action_type, "success": True}
            executed.append({"step": step, "result": result})
            self.tracker.record(result, screen_content, screen_content)

        return {
            "task": task,
            "steps_planned": len(steps),
            "steps_executed": len(executed),
            "elements_detected": len(elements),
            "clickable_elements": len(self.detector.find_clickable(elements)),
            "execution_log": executed,
            "action_history": self.executor.history(),
        }

    def stats(self) -> Dict[str, Any]:
        return {"screenshots_cached": len(self.cache._cache), "actions": len(self.executor.history())}


# ───────────────────────────────────────────────────────────────
# 8. DEMO
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Computer Use Engine Demo")
    print("=" * 60)

    engine = ComputerUseEngine()

    # Simulated screen content
    screen = """Welcome to Example.com
[Login]
Input: Username
Input: Password
[Submit]
Link: Forgot password
Copyright 2024
"""

    task = "Navigate to the login page and fill in the username field"
    print(f"\n[TASK] {task}")
    result = engine.execute_task(task, screen, "login_screen")

    print(f"  Steps planned: {result['steps_planned']}")
    print(f"  Steps executed: {result['steps_executed']}")
    print(f"  Elements detected: {result['elements_detected']}")
    print(f"  Clickable elements: {result['clickable_elements']}")
    print(f"  Execution log:")
    for entry in result["execution_log"]:
        print(f"    {entry['step']['action']} -> {entry['result']['action']} (success={entry['result']['success']})")

    print(f"\n[STATS] {json.dumps(engine.stats(), indent=2)}")

    print("\n" + "=" * 60)
    print("Demo complete. Computer Use Engine ready for LLM Arena.")
    print("=" * 60)
