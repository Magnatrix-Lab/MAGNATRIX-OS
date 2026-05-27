#!/usr/bin/env python3
"""
MAGNATRIX-OS Desktop Tray Native
Cross-platform system tray: Windows (pystray), macOS (rumps), Linux (AppIndicator).
Pure Python with graceful fallback to console-only mode.
"""
import os, sys, threading, time, subprocess, json
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass


@dataclass
class TrayConfig:
    icon_path: str = ""
    tooltip: str = "MAGNATRIX-OS"
    menu_items: List[Dict] = None


class TrayNative:
    """Base tray interface."""

    def __init__(self, config: TrayConfig = None):
        self.config = config or TrayConfig()
        self._running = False
        self._callbacks: Dict[str, Callable] = {}

    def register(self, action: str, callback: Callable):
        self._callbacks[action] = callback

    def start(self):
        raise NotImplementedError

    def stop(self):
        self._running = False

    def notify(self, title: str, message: str):
        """Show system notification."""
        pass


class WindowsTray(TrayNative):
    """Windows tray using pystray."""

    def start(self):
        try:
            import pystray
            from PIL import Image

            image = Image.new("RGB", (64, 64), color="black")
            menu = pystray.Menu(
                pystray.MenuItem("Status", lambda: self._trigger("status")),
                pystray.MenuItem("Open Dashboard", lambda: self._trigger("dashboard")),
                pystray.MenuItem("Start Trading", lambda: self._trigger("trading")),
                pystray.MenuItem("Exit", lambda: self.stop()),
            )
            self._icon = pystray.Icon("magnatrix", image, self.config.tooltip, menu)
            self._running = True
            threading.Thread(target=self._icon.run, daemon=True).start()
        except ImportError:
            print("[TRAY] pystray not installed — falling back to console mode")

    def _trigger(self, action: str):
        cb = self._callbacks.get(action)
        if cb:
            cb()

    def notify(self, title: str, message: str):
        try:
            import pystray
            if hasattr(self, "_icon"):
                self._icon.notify(message, title)
        except Exception:
            pass


class MacOSTray(TrayNative):
    """macOS tray using rumps."""

    def start(self):
        try:
            import rumps
            app = rumps.App(self.config.tooltip, quit_button="Exit")
            app.menu = [
                rumps.MenuItem("Status", callback=lambda _: self._trigger("status")),
                rumps.MenuItem("Open Dashboard", callback=lambda _: self._trigger("dashboard")),
                rumps.MenuItem("Start Trading", callback=lambda _: self._trigger("trading")),
            ]
            self._running = True
            threading.Thread(target=app.run, daemon=True).start()
        except ImportError:
            print("[TRAY] rumps not installed — falling back to console mode")

    def _trigger(self, action: str):
        cb = self._callbacks.get(action)
        if cb:
            cb()

    def notify(self, title: str, message: str):
        try:
            import rumps
            rumps.notification(title, "", message)
        except Exception:
            pass


class LinuxTray(TrayNative):
    """Linux tray using AppIndicator3."""

    def start(self):
        try:
            from gi.repository import Gtk, AppIndicator3
            indicator = AppIndicator3.Indicator.new(
                "magnatrix", "", AppIndicator3.IndicatorCategory.APPLICATION_STATUS
            )
            indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
            menu = Gtk.Menu()
            for label, action in [
                ("Status", "status"),
                ("Dashboard", "dashboard"),
                ("Trading", "trading"),
                ("Exit", "exit"),
            ]:
                item = Gtk.MenuItem(label=label)
                item.connect("activate", lambda _, a=action: self._trigger(a))
                menu.append(item)
            menu.show_all()
            indicator.set_menu(menu)
            self._running = True
            threading.Thread(target=Gtk.main, daemon=True).start()
        except ImportError:
            print("[TRAY] AppIndicator3 not installed — falling back to console mode")

    def _trigger(self, action: str):
        cb = self._callbacks.get(action)
        if cb:
            cb()

    def notify(self, title: str, message: str):
        try:
            subprocess.run(["notify-send", title, message], check=False)
        except Exception:
            pass


class DesktopTrayNative:
    """Desktop tray orchestrator — auto-detects platform."""

    def __init__(self):
        self.tray: Optional[TrayNative] = None
        self._detect_platform()

    def _detect_platform(self):
        if sys.platform == "win32":
            self.tray = WindowsTray()
        elif sys.platform == "darwin":
            self.tray = MacOSTray()
        else:
            self.tray = LinuxTray()

    def register(self, action: str, callback: Callable):
        if self.tray:
            self.tray.register(action, callback)

    def start(self):
        if self.tray:
            self.tray.start()

    def stop(self):
        if self.tray:
            self.tray.stop()

    def notify(self, title: str, message: str):
        if self.tray:
            self.tray.notify(title, message)


def _demo():
    print("=" * 60)
    print("MAGNATRIX-OS Desktop Tray Demo")
    print("=" * 60)

    tray = DesktopTrayNative()

    def on_status():
        print("[TRAY] Status clicked")

    def on_dashboard():
        print("[TRAY] Dashboard clicked")

    tray.register("status", on_status)
    tray.register("dashboard", on_dashboard)
    tray.start()

    print("\n[1] Tray started (platform: {})")
    print("[2] Simulating notification...")
    tray.notify("MAGNATRIX", "System ready")

    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    _demo()
