#!/usr/bin/env python3
"""
CLI TUI Manager for MAGNATRIX-OS
Terminal User Interface — manage MAGNATRIX-OS from command line.
Pure stdlib ANSI escape codes — no curses/ncurses dependency.

Usage: python magnatrix.py tui

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import os
import sys
import time
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ANSI:
    """ANSI escape code utilities."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    REVERSE = "\033[7m"
    HIDDEN = "\033[8m"
    # Colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    # Bright colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    # Backgrounds
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"
    # Cursor
    CLEAR = "\033[2J"
    CLEAR_LINE = "\033[2K"
    HOME = "\033[H"
    CURSOR_UP = "\033[A"
    CURSOR_DOWN = "\033[B"
    CURSOR_RIGHT = "\033[C"
    CURSOR_LEFT = "\033[D"
    HIDE_CURSOR = "\033[?25l"
    SHOW_CURSOR = "\033[?25h"
    # Extended
    SAVE_CURSOR = "\033[s"
    RESTORE_CURSOR = "\033[u"

    @staticmethod
    def move(row: int, col: int) -> str:
        return f"\033[{row};{col}H"

    @staticmethod
    def color(r: int, g: int, b: int) -> str:
        return f"\033[38;2;{r};{g};{b}m"

    @staticmethod
    def bg_color(r: int, g: int, b: int) -> str:
        return f"\033[48;2;{r};{g};{b}m"

    @staticmethod
    def width() -> int:
        try:
            return os.get_terminal_size().columns
        except Exception:
            return 80

    @staticmethod
    def height() -> int:
        try:
            return os.get_terminal_size().lines
        except Exception:
            return 24


class BoxDrawer:
    """Draw boxes and lines with Unicode box-drawing characters."""
    H = "─"
    V = "│"
    TL = "┌"
    TR = "┐"
    BL = "└"
    BR = "┘"
    T = "┬"
    B = "┴"
    L = "├"
    R = "┤"
    C = "┼"

    @classmethod
    def hline(cls, width: int) -> str:
        return cls.H * width

    @classmethod
    def box(cls, width: int, height: int, title: str = "") -> List[str]:
        lines = [f"{cls.TL}{cls.hline(width - 2)}{cls.TR}"]
        if title:
            title_str = f" {title} "
            pad = (width - 2 - len(title_str)) // 2
            lines[0] = f"{cls.TL}{cls.H * pad}{ANSI.BOLD}{ANSI.BRIGHT_CYAN}{title_str}{ANSI.RESET}{cls.H * (width - 2 - pad - len(title_str))}{cls.TR}"
        for _ in range(height - 2):
            lines.append(f"{cls.V}{' ' * (width - 2)}{cls.V}")
        lines.append(f"{cls.BL}{cls.hline(width - 2)}{cls.BR}")
        return lines


class TUIWidget:
    """Base widget for TUI."""

    def __init__(self, x: int, y: int, width: int, height: int) -> None:
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def render(self) -> List[str]:
        return []

    def draw(self, screen: 'ScreenBuffer') -> None:
        for i, line in enumerate(self.render()):
            if i < self.height:
                screen.write(self.y + i, self.x, line[:self.width])


class HeaderWidget(TUIWidget):
    """Top header bar."""

    def __init__(self, x: int, y: int, width: int) -> None:
        super().__init__(x, y, width, 3)

    def render(self) -> List[str]:
        w = self.width
        line1 = f"{ANSI.BG_BLUE}{ANSI.BRIGHT_WHITE}{ANSI.BOLD} MAGNATRIX-OS {ANSI.RESET}{ANSI.BG_BLUE}{ANSI.BRIGHT_WHITE}  Private, Uncensored AI Operating System  v2.0.0 {ANSI.RESET}"
        line2 = f"{ANSI.BRIGHT_BLACK} {BoxDrawer.hline(w - 2)}{ANSI.RESET}"
        return [line1 + " " * (w - len(line1)), line2]


class StatsWidget(TUIWidget):
    """Stats bar showing key metrics."""

    def __init__(self, x: int, y: int, width: int) -> None:
        super().__init__(x, y, width, 2)
        self._data: Dict[str, Any] = {}

    def set_data(self, data: Dict[str, Any]) -> None:
        self._data = data

    def render(self) -> List[str]:
        w = self.width
        stats = self._data
        items = [
            f"{ANSI.GREEN}●{ANSI.RESET} Running",
            f"{ANSI.CYAN}Modules:{ANSI.RESET} {stats.get('modules', 0)}",
            f"{ANSI.CYAN}Active:{ANSI.RESET} {stats.get('active', 0)}",
            f"{ANSI.CYAN}CPU:{ANSI.RESET} {stats.get('cpu', 0):.1f}%",
            f"{ANSI.CYAN}Mem:{ANSI.RESET} {stats.get('memory', 0):.1f}%",
            f"{ANSI.CYAN}Uptime:{ANSI.RESET} {stats.get('uptime', '0s')}",
        ]
        line = "  ".join(items)
        return [line + " " * (w - len(line))]


class ModuleListWidget(TUIWidget):
    """Scrollable module list."""

    def __init__(self, x: int, y: int, width: int, height: int) -> None:
        super().__init__(x, y, width, height)
        self._modules: List[Dict[str, Any]] = []
        self._selected = 0
        self._offset = 0

    def set_modules(self, modules: List[Dict[str, Any]]) -> None:
        self._modules = modules

    def render(self) -> List[str]:
        lines = []
        w = self.width - 2
        for i in range(self.height - 2):
            idx = self._offset + i
            if idx < len(self._modules):
                m = self._modules[idx]
                state = m.get("state", "unknown")
                name = m.get("name", "unknown")
                load_ms = m.get("load_ms", 0)
                if idx == self._selected:
                    prefix = f"{ANSI.REVERSE}▶{ANSI.RESET}{ANSI.REVERSE}"
                    suffix = f"{ANSI.RESET}"
                else:
                    status_icon = "🟢" if state == "active" else "🔴" if state == "error" else "⚪"
                    prefix = f" {status_icon}"
                    suffix = ""
                color = ANSI.GREEN if state == "active" else ANSI.RED if state == "error" else ANSI.YELLOW
                line = f"{prefix} {color}{name:20s}{ANSI.RESET} {ANSI.DIM}{state:10s}{ANSI.RESET} {ANSI.CYAN}{load_ms:6.1f}ms{ANSI.RESET}{suffix}"
                lines.append(line[:w])
            else:
                lines.append(" " * w)
        return lines

    def move_down(self) -> None:
        if self._selected < len(self._modules) - 1:
            self._selected += 1
            if self._selected >= self._offset + self.height - 2:
                self._offset = self._selected - (self.height - 3)

    def move_up(self) -> None:
        if self._selected > 0:
            self._selected -= 1
            if self._selected < self._offset:
                self._offset = self._selected

    def get_selected(self) -> Optional[str]:
        if 0 <= self._selected < len(self._modules):
            return self._modules[self._selected].get("name")
        return None


class LogWidget(TUIWidget):
    """Live log tailer."""

    def __init__(self, x: int, y: int, width: int, height: int) -> None:
        super().__init__(x, y, width, height)
        self._logs: List[str] = []

    def add_log(self, level: str, message: str) -> None:
        color = ANSI.GREEN if level == "INFO" else ANSI.YELLOW if level == "WARN" else ANSI.RED if level == "ERROR" else ANSI.CYAN
        self._logs.append(f"{color}{level:5s}{ANSI.RESET} {message}")
        if len(self._logs) > 100:
            self._logs = self._logs[-50:]

    def render(self) -> List[str]:
        lines = []
        w = self.width - 2
        visible = self._logs[-(self.height - 2):]
        for entry in visible:
            lines.append(entry[:w])
        while len(lines) < self.height - 2:
            lines.append(" " * w)
        return lines


class MenuWidget(TUIWidget):
    """Bottom menu bar."""

    def __init__(self, x: int, y: int, width: int) -> None:
        super().__init__(x, y, width, 1)

    def render(self) -> List[str]:
        items = [
            f"{ANSI.BG_BLUE}{ANSI.BRIGHT_WHITE} F1 Help {ANSI.RESET}",
            f"{ANSI.BG_BLUE}{ANSI.BRIGHT_WHITE} F2 Status {ANSI.RESET}",
            f"{ANSI.BG_BLUE}{ANSI.BRIGHT_WHITE} F3 Modules {ANSI.RESET}",
            f"{ANSI.BG_BLUE}{ANSI.BRIGHT_WHITE} F4 Logs {ANSI.RESET}",
            f"{ANSI.BG_BLUE}{ANSI.BRIGHT_WHITE} F5 Refresh {ANSI.RESET}",
            f"{ANSI.BG_BLUE}{ANSI.BRIGHT_WHITE} F6 Start {ANSI.RESET}",
            f"{ANSI.BG_BLUE}{ANSI.BRIGHT_WHITE} F7 Stop {ANSI.RESET}",
            f"{ANSI.BG_BLUE}{ANSI.BRIGHT_WHITE} F9 Update {ANSI.RESET}",
            f"{ANSI.BG_RED}{ANSI.BRIGHT_WHITE} F10 Quit {ANSI.RESET}",
        ]
        line = "".join(items)
        return [line + " " * (self.width - len(line))]


class ScreenBuffer:
    """Double-buffered screen rendering."""

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._buffer: List[str] = [" " * width for _ in range(height)]
        self._prev: List[str] = ["" * width for _ in range(height)]

    def write(self, row: int, col: int, text: str) -> None:
        if 0 <= row < self.height and 0 <= col < self.width:
            line = self._buffer[row]
            new_line = line[:col] + text + line[col + len(text):]
            self._buffer[row] = new_line[:self.width]

    def clear(self) -> None:
        self._buffer = [" " * self.width for _ in range(self.height)]

    def flush(self) -> None:
        out = []
        for i, line in enumerate(self._buffer):
            if i >= len(self._prev) or line != self._prev[i]:
                out.append(f"{ANSI.move(i + 1, 1)}{ANSI.CLEAR_LINE}{line}")
        if out:
            sys.stdout.write("".join(out))
            sys.stdout.flush()
        self._prev = self._buffer[:]
        self._buffer = [" " * self.width for _ in range(self.height)]


class TUIManager:
    """Main TUI manager orchestrating all widgets."""

    def __init__(self, repo_root: str) -> None:
        self.root = Path(repo_root).resolve()
        self._running = False
        self._screen: Optional[ScreenBuffer] = None
        self._widgets: List[TUIWidget] = []
        self._header: Optional[HeaderWidget] = None
        self._stats: Optional[StatsWidget] = None
        self._modules: Optional[ModuleListWidget] = None
        self._logs: Optional[LogWidget] = None
        self._menu: Optional[MenuWidget] = None
        self._registry: Optional[Any] = None
        self._refresh_thread: Optional[threading.Thread] = None

    def _init_widgets(self) -> None:
        w, h = ANSI.width(), ANSI.height()
        self._screen = ScreenBuffer(w, h)
        self._header = HeaderWidget(1, 1, w)
        self._stats = StatsWidget(1, 4, w)
        self._logs = LogWidget(1, h - 8, w, 6)
        self._modules = ModuleListWidget(1, 6, w, h - 14)
        self._menu = MenuWidget(1, h - 1, w)
        self._widgets = [self._header, self._stats, self._modules, self._logs, self._menu]

    def _load_registry(self) -> None:
        try:
            import importlib
            mod = importlib.import_module("magnatrix")
            self._registry = mod.ModuleRegistry(str(self.root))
        except Exception as e:
            self._logs.add_log("WARN", f"Registry load: {e}")

    def _update_data(self) -> None:
        if self._registry:
            try:
                stats = self._registry.stats()
                self._stats.set_data({
                    "modules": stats.get("total_registered", 0),
                    "active": stats.get("loaded", 0),
                    "cpu": 0.0,
                    "memory": 0.0,
                    "uptime": "running",
                })
                self._modules.set_modules(self._registry.list_modules())
            except Exception as e:
                self._logs.add_log("WARN", f"Update data: {e}")
        else:
            self._stats.set_data({"modules": 104, "active": 0, "cpu": 0, "memory": 0, "uptime": "N/A"})
            self._modules.set_modules([])

    def _draw(self) -> None:
        for widget in self._widgets:
            widget.draw(self._screen)
        self._screen.flush()

    def _refresh_loop(self) -> None:
        while self._running:
            self._update_data()
            self._draw()
            time.sleep(1)

    def _handle_input(self) -> None:
        import tty, termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while self._running:
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    ch = sys.stdin.read(1)
                    if ch == "\x1b":
                        seq = sys.stdin.read(2)
                        if seq == "[A":
                            self._modules.move_up()
                        elif seq == "[B":
                            self._modules.move_down()
                    elif ch in ("q", "Q"):
                        self._running = False
                    elif ch == "\x0c":  # Ctrl+L
                        self._draw()
                    elif ch == "\r":
                        sel = self._modules.get_selected()
                        if sel:
                            self._logs.add_log("INFO", f"Selected: {sel}")
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    def start(self) -> None:
        self._running = True
        sys.stdout.write(ANSI.HIDE_CURSOR + ANSI.CLEAR + ANSI.HOME)
        sys.stdout.flush()
        self._init_widgets()
        self._load_registry()
        self._logs.add_log("INFO", "TUI Manager started")
        self._logs.add_log("INFO", f"Repo: {self.root}")
        # Start refresh thread
        self._refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True, name="TUIRefresh")
        self._refresh_thread.start()
        # Handle input
        try:
            self._handle_input()
        except KeyboardInterrupt:
            pass
        finally:
            self._running = False
            sys.stdout.write(ANSI.SHOW_CURSOR + ANSI.CLEAR + ANSI.HOME)
            sys.stdout.flush()
            print("MAGNATRIX-OS TUI exited.")

    def stop(self) -> None:
        self._running = False


# ---------------------------------------------------------------------------
# Self-contained demo (render once, no input loop)
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== CLI TUI Manager Demo ===\n")
    # Static render demo
    w = min(120, ANSI.width())
    h = 24
    screen = ScreenBuffer(w, h)
    header = HeaderWidget(1, 1, w)
    stats = StatsWidget(1, 4, w)
    stats.set_data({"modules": 104, "active": 98, "cpu": 12.5, "memory": 45.2, "uptime": "2h 15m"})
    modules = ModuleListWidget(1, 6, w, 12)
    modules.set_modules([
        {"name": "config", "state": "active", "load_ms": 1.2},
        {"name": "logging", "state": "active", "load_ms": 0.8},
        {"name": "cache", "state": "active", "load_ms": 0.5},
        {"name": "llm", "state": "active", "load_ms": 2.1},
        {"name": "rag", "state": "active", "load_ms": 3.5},
        {"name": "genesis_hub", "state": "active", "load_ms": 5.2},
        {"name": "web_dashboard", "state": "active", "load_ms": 4.8},
        {"name": "doc_intel", "state": "active", "load_ms": 6.1},
        {"name": "websocket", "state": "error", "load_ms": 0.0},
    ])
    logs = LogWidget(1, 18, w, 5)
    logs.add_log("INFO", "System booted successfully")
    logs.add_log("INFO", "104 modules registered, 98 active")
    logs.add_log("WARN", "websocket module failed to load")
    menu = MenuWidget(1, 23, w)

    for widget in [header, stats, modules, logs, menu]:
        widget.draw(screen)

    # Draw border
    box_lines = BoxDrawer.box(w, h)
    for i, line in enumerate(box_lines):
        if i < h:
            screen.write(i + 1, 1, line)

    # Render to terminal
    sys.stdout.write(ANSI.CLEAR + ANSI.HOME)
    for line in screen._buffer:
        sys.stdout.write(line + "\n")
    sys.stdout.flush()
    print("\n(Demo: static render only. Run with full TUI for interactive mode)")


if __name__ == "__main__":
    _demo()
