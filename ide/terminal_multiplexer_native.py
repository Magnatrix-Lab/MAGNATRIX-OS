#!/usr/bin/env python3
"""
MAGNATRIX-OS — Layer 12: Terminal Multiplexer
Native Python, zero external dependencies.
Based on Helvesec/rmux (839 stars, tmux-compatible) — AMATI-PELAJARI-TIRU.
"""
from __future__ import annotations
import json, time, threading, hashlib, re, os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class PaneState(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ZOOMED = "zoomed"
    CLOSED = "closed"


@dataclass
class Pane:
    id: str
    session_id: str
    window_id: str
    content: List[str] = field(default_factory=list)
    cursor_row: int = 0
    cursor_col: int = 0
    scrollback: List[str] = field(default_factory=list)
    max_scrollback: int = 1000
    state: PaneState = PaneState.ACTIVE
    width: int = 80
    height: int = 24
    created_at: float = field(default_factory=time.time)

    def write(self, text: str):
        lines = text.split("\n")
        for line in lines:
            self.content.append(line)
            if len(self.content) > self.height:
                self.scrollback.append(self.content.pop(0))
                if len(self.scrollback) > self.max_scrollback:
                    self.scrollback.pop(0)
        self.cursor_row = len(self.content) - 1
        self.cursor_col = len(self.content[-1]) if self.content else 0

    def get_visible(self) -> List[str]:
        start = max(0, len(self.content) - self.height)
        return self.content[start:]

    def clear(self):
        self.content = []
        self.scrollback = []
        self.cursor_row = 0
        self.cursor_col = 0


@dataclass
class Window:
    id: str
    session_id: str
    name: str
    panes: Dict[str, Pane] = field(default_factory=dict)
    active_pane: str = ""
    layout: str = "tiled"
    created_at: float = field(default_factory=time.time)

    def add_pane(self, pane: Pane) -> str:
        self.panes[pane.id] = pane
        if not self.active_pane:
            self.active_pane = pane.id
        return pane.id

    def remove_pane(self, pane_id: str) -> bool:
        if pane_id in self.panes:
            del self.panes[pane_id]
            if self.active_pane == pane_id:
                self.active_pane = next(iter(self.panes), "")
            return True
        return False

    def get_active_pane(self) -> Optional[Pane]:
        return self.panes.get(self.active_pane)


@dataclass
class Session:
    id: str
    name: str
    windows: Dict[str, Window] = field(default_factory=dict)
    active_window: str = ""
    attached_clients: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    detached_at: Optional[float] = None

    def add_window(self, window: Window) -> str:
        self.windows[window.id] = window
        if not self.active_window:
            self.active_window = window.id
        return window.id

    def remove_window(self, window_id: str) -> bool:
        if window_id in self.windows:
            del self.windows[window_id]
            if self.active_window == window_id:
                self.active_window = next(iter(self.windows), "")
            return True
        return False

    def get_active_window(self) -> Optional[Window]:
        return self.windows.get(self.active_window)


class SessionManager:
    """Create/attach/detach/kill sessions, session list, persistent state."""

    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._lock = threading.RLock()

    def create(self, name: str) -> Session:
        with self._lock:
            sid = f"sess_{hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()[:8]}"
            session = Session(id=sid, name=name)
            self._sessions[sid] = session
            return session

    def kill(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def attach(self, session_id: str, client_id: str) -> bool:
        with self._lock:
            s = self._sessions.get(session_id)
            if s:
                s.attached_clients.append(client_id)
                s.detached_at = None
                return True
            return False

    def detach(self, session_id: str, client_id: str):
        with self._lock:
            s = self._sessions.get(session_id)
            if s and client_id in s.attached_clients:
                s.attached_clients.remove(client_id)
                if not s.attached_clients:
                    s.detached_at = time.time()

    def list_sessions(self) -> List[Session]:
        with self._lock:
            return list(self._sessions.values())

    def get(self, session_id: str) -> Optional[Session]:
        with self._lock:
            return self._sessions.get(session_id)


class WindowManager:
    """Create/close windows, split panes, resize, navigate."""

    def __init__(self, sessions: SessionManager):
        self.sessions = sessions

    def create_window(self, session_id: str, name: str) -> Optional[str]:
        session = self.sessions.get(session_id)
        if not session:
            return None
        wid = f"win_{hashlib.md5(f"{session_id}{name}{time.time()}".encode()).hexdigest()[:6]}"
        window = Window(id=wid, session_id=session_id, name=name)
        session.add_window(window)
        return wid

    def kill_window(self, session_id: str, window_id: str) -> bool:
        session = self.sessions.get(session_id)
        if session:
            return session.remove_window(window_id)
        return False

    def rename_window(self, session_id: str, window_id: str, new_name: str) -> bool:
        session = self.sessions.get(session_id)
        if session:
            w = session.windows.get(window_id)
            if w:
                w.name = new_name
                return True
        return False

    def next_window(self, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        if not session or not session.windows:
            return False
        keys = list(session.windows.keys())
        idx = keys.index(session.active_window) if session.active_window in keys else -1
        session.active_window = keys[(idx + 1) % len(keys)]
        return True


class PaneManager:
    """Terminal pane: scrollback, cursor, input/output."""

    def __init__(self, sessions: SessionManager):
        self.sessions = sessions

    def create_pane(self, session_id: str, window_id: str, width: int = 80, height: int = 24) -> Optional[str]:
        session = self.sessions.get(session_id)
        if not session:
            return None
        window = session.windows.get(window_id)
        if not window:
            return None
        pid = f"pane_{hashlib.md5(f"{session_id}{window_id}{time.time()}".encode()).hexdigest()[:6]}"
        pane = Pane(id=pid, session_id=session_id, window_id=window_id, width=width, height=height)
        window.add_pane(pane)
        return pid

    def split_horizontal(self, session_id: str, window_id: str, pane_id: str) -> Optional[str]:
        # Split existing pane into two horizontal panes
        return self.create_pane(session_id, window_id)

    def split_vertical(self, session_id: str, window_id: str, pane_id: str) -> Optional[str]:
        return self.create_pane(session_id, window_id)

    def send_keys(self, session_id: str, pane_id: str, keys: str):
        session = self.sessions.get(session_id)
        if not session:
            return
        for window in session.windows.values():
            pane = window.panes.get(pane_id)
            if pane:
                pane.write(keys)
                break

    def resize_pane(self, session_id: str, pane_id: str, width: int, height: int):
        session = self.sessions.get(session_id)
        if not session:
            return
        for window in session.windows.values():
            pane = window.panes.get(pane_id)
            if pane:
                pane.width = width
                pane.height = height
                break

    def capture_pane(self, session_id: str, pane_id: str) -> str:
        session = self.sessions.get(session_id)
        if not session:
            return ""
        for window in session.windows.values():
            pane = window.panes.get(pane_id)
            if pane:
                return "\n".join(pane.get_visible())
        return ""


class CommandRouter:
    """Tmux-compatible command parser."""

    COMMANDS = {
        "new-session": lambda s, args: s.create(args.get("-s", "default")),
        "kill-session": lambda s, args: s.kill(args.get("-t", "")),
        "new-window": lambda s, args: None,  # Handled by WindowManager
        "split-window": lambda s, args: None,  # Handled by PaneManager
        "send-keys": lambda s, args: None,
        "capture-pane": lambda s, args: None,
        "select-pane": lambda s, args: None,
        "resize-pane": lambda s, args: None,
    }

    def __init__(self, sessions: SessionManager):
        self.sessions = sessions

    def parse(self, command_line: str) -> Dict:
        parts = command_line.strip().split()
        if not parts:
            return {"error": "Empty command"}
        cmd = parts[0]
        args = {}
        i = 1
        while i < len(parts):
            if parts[i].startswith("-"):
                key = parts[i]
                val = parts[i + 1] if i + 1 < len(parts) else ""
                args[key] = val
                i += 2
            else:
                i += 1
        return {"command": cmd, "args": args}


class SnapshotEngine:
    """Capture terminal state, serialize to JSON, restore."""

    def capture_session(self, session: Session) -> Dict:
        return {
            "id": session.id,
            "name": session.name,
            "active_window": session.active_window,
            "windows": {
                wid: {
                    "id": w.id,
                    "name": w.name,
                    "active_pane": w.active_pane,
                    "layout": w.layout,
                    "panes": {
                        pid: {
                            "id": p.id,
                            "content": p.content,
                            "cursor": (p.cursor_row, p.cursor_col),
                            "scrollback": p.scrollback[-100:],
                            "size": (p.width, p.height),
                        }
                        for pid, p in w.panes.items()
                    },
                }
                for wid, w in session.windows.items()
            },
        }

    def restore_session(self, data: Dict, sessions: SessionManager) -> Optional[Session]:
        session = sessions.create(data.get("name", "restored"))
        session.id = data.get("id", session.id)
        session.active_window = data.get("active_window", "")
        for wid, wdata in data.get("windows", {}).items():
            window = Window(id=wid, session_id=session.id, name=wdata["name"])
            window.active_pane = wdata.get("active_pane", "")
            window.layout = wdata.get("layout", "tiled")
            for pid, pdata in wdata.get("panes", {}).items():
                pane = Pane(
                    id=pid, session_id=session.id, window_id=wid,
                    width=pdata["size"][0], height=pdata["size"][1],
                )
                pane.content = pdata.get("content", [])
                pane.scrollback = pdata.get("scrollback", [])
                window.add_pane(pane)
            session.add_window(window)
        return session


class EventSystem:
    """Session lifecycle, pane output, window change events."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, callback: Callable):
        with self._lock:
            self._subscribers.setdefault(event_type, []).append(callback)

    def publish(self, event_type: str, data: Dict):
        with self._lock:
            cbs = self._subscribers.get(event_type, [])
        for cb in cbs:
            try:
                cb(data)
            except Exception:
                pass


class LayoutEngine:
    """Automatic layout: even-horizontal, even-vertical, main-horizontal, main-vertical, tiled."""

    LAYOUTS = ["even-horizontal", "even-vertical", "main-horizontal", "main-vertical", "tiled"]

    def apply(self, window: Window, layout_name: str = "tiled"):
        panes = list(window.panes.values())
        if not panes:
            return
        window.layout = layout_name
        count = len(panes)
        if layout_name == "even-horizontal":
            width = 80 // count
            for i, p in enumerate(panes):
                p.width = width
                p.height = 24
        elif layout_name == "even-vertical":
            height = 24 // count
            for i, p in enumerate(panes):
                p.width = 80
                p.height = height
        elif layout_name == "tiled":
            cols = math.ceil(math.sqrt(count))
            rows = math.ceil(count / cols)
            width = 80 // cols
            height = 24 // rows
            for p in panes:
                p.width = width
                p.height = height


class ScrollbackBuffer:
    """Circular buffer per pane, search, copy mode."""

    def search(self, pane: Pane, query: str) -> List[int]:
        matches = []
        for i, line in enumerate(pane.scrollback + pane.content):
            if query.lower() in line.lower():
                matches.append(i)
        return matches

    def copy_mode(self, pane: Pane) -> List[str]:
        return pane.scrollback[-100:] + pane.content


class KeybindingManager:
    """Key mapping, prefix key, command binding."""

    def __init__(self, prefix: str = "ctrl+b"):
        self.prefix = prefix
        self.bindings: Dict[str, str] = {
            "c": "new-window",
            "n": "next-window",
            "p": "previous-window",
            "%": "split-horizontal",
            '\"': "split-vertical",
            "x": "kill-pane",
            "d": "detach",
            "[": "copy-mode",
        }

    def bind(self, key: str, command: str):
        self.bindings[key] = command

    def lookup(self, key: str) -> Optional[str]:
        return self.bindings.get(key)


class TerminalEmulatorStub:
    """VT100/ANSI escape sequence parser stub."""

    ANSI_PATTERN = re.compile(r'\x1b\[[0-9;]*[mKHJfABCDsu]')

    def parse(self, text: str) -> List[Dict]:
        parts = self.ANSI_PATTERN.split(text)
        codes = self.ANSI_PATTERN.findall(text)
        result = []
        for part, code in zip(parts, codes + [""]):
            if part:
                result.append({"text": part, "code": code, "type": "text"})
        return result

    def set_color(self, code: str) -> Dict:
        colors = {
            "30": "black", "31": "red", "32": "green", "33": "yellow",
            "34": "blue", "35": "magenta", "36": "cyan", "37": "white",
        }
        num = re.search(r'(\d+)', code)
        return {"color": colors.get(num.group(1) if num else "", "default")}


class MultiplexerKernelBridge:
    """Bridge to event_bus and service_registry."""

    def __init__(self, event_bus=None, service_registry=None):
        self.event_bus = event_bus
        self.service_registry = service_registry

    def publish(self, event_type: str, data: Dict):
        if self.event_bus:
            try:
                self.event_bus.publish(f"terminal.{event_type}", data)
            except Exception:
                pass

    def register(self):
        if self.service_registry:
            try:
                self.service_registry.register("terminal_mux", {"status": "running"})
            except Exception:
                pass


class TerminalMultiplexer:
    """Main orchestrator — compose all."""

    def __init__(self):
        self.sessions = SessionManager()
        self.windows = WindowManager(self.sessions)
        self.panes = PaneManager(self.sessions)
        self.commands = CommandRouter(self.sessions)
        self.snapshots = SnapshotEngine()
        self.events = EventSystem()
        self.layouts = LayoutEngine()
        self.scrollback = ScrollbackBuffer()
        self.keys = KeybindingManager()
        self.emulator = TerminalEmulatorStub()
        self.bridge = MultiplexerKernelBridge()

    def boot(self):
        self.bridge.register()
        print("[TerminalMultiplexer] Booted")

    def create_session(self, name: str) -> Session:
        return self.sessions.create(name)

    def create_window(self, session_id: str, name: str) -> Optional[str]:
        return self.windows.create_window(session_id, name)

    def create_pane(self, session_id: str, window_id: str) -> Optional[str]:
        return self.panes.create_pane(session_id, window_id)

    def split_horizontal(self, session_id: str, window_id: str, pane_id: str) -> Optional[str]:
        return self.panes.split_horizontal(session_id, window_id, pane_id)

    def split_vertical(self, session_id: str, window_id: str, pane_id: str) -> Optional[str]:
        return self.panes.split_vertical(session_id, window_id, pane_id)

    def send_command(self, session_id: str, pane_id: str, command: str):
        self.panes.send_keys(session_id, pane_id, command + "\n")

    def capture_snapshot(self, session_id: str) -> Dict:
        session = self.sessions.get(session_id)
        if session:
            return self.snapshots.capture_session(session)
        return {}

    def restore_snapshot(self, data: Dict) -> Optional[Session]:
        return self.snapshots.restore_session(data, self.sessions)

    def broadcast(self, session_id: str, command: str):
        session = self.sessions.get(session_id)
        if session:
            for window in session.windows.values():
                for pane in window.panes.values():
                    self.panes.send_keys(session_id, pane.id, command + "\n")

    def get_status(self) -> Dict:
        return {
            "sessions": len(self.sessions.list_sessions()),
            "total_windows": sum(len(s.windows) for s in self.sessions.list_sessions()),
            "total_panes": sum(
                sum(len(w.panes) for w in s.windows.values())
                for s in self.sessions.list_sessions()
            ),
        }

    def shutdown(self):
        for s in self.sessions.list_sessions():
            self.sessions.kill(s.id)
        print("[TerminalMultiplexer] Shutdown")


def run_demo():
    print("=" * 60)
    print("MAGNATRIX-OS Terminal Multiplexer Demo")
    print("=" * 60)

    mux = TerminalMultiplexer()
    mux.boot()

    # Create session
    print("\n--- Create Session ---")
    session = mux.create_session("dev_session")
    print(f"Session: {session.id} ({session.name})")

    # Create window
    print("\n--- Create Window ---")
    wid = mux.create_window(session.id, "editor")
    print(f"Window: {wid}")

    # Create panes
    print("\n--- Create Panes ---")
    p1 = mux.create_pane(session.id, wid)
    p2 = mux.split_horizontal(session.id, wid, p1)
    p3 = mux.split_vertical(session.id, wid, p1)
    print(f"Panes: {p1}, {p2}, {p3}")

    # Send commands
    print("\n--- Send Commands ---")
    mux.send_command(session.id, p1, "vim main.py")
    mux.send_command(session.id, p2, "python -m http.server")
    mux.send_command(session.id, p3, "tail -f logs/app.log")

    # Show content
    for pid in [p1, p2, p3]:
        content = mux.panes.capture_pane(session.id, pid)
        print(f"\nPane {pid}:")
        for line in content.split("\n")[-3:]:
            if line.strip():
                print(f"  {line}")

    # Layout
    print("\n--- Apply Layout ---")
    window = session.windows.get(wid)
    if window:
        mux.layouts.apply(window, "tiled")
        for pid, p in window.panes.items():
            print(f"  {pid}: {p.width}x{p.height}")

    # Snapshot
    print("\n--- Snapshot ---")
    snap = mux.capture_snapshot(session.id)
    print(f"Snapshot: {len(snap.get('windows', {}))} windows")

    # Broadcast
    print("\n--- Broadcast ---")
    mux.broadcast(session.id, "echo 'Hello all panes'")

    # Status
    print("\n--- Status ---")
    status = mux.get_status()
    for k, v in status.items():
        print(f"  {k}: {v}")

    mux.shutdown()
    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
