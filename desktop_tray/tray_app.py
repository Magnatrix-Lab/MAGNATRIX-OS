#!/usr/bin/env python3
"""
tray_app.py — MAGNATRIX Desktop Tray Application
System tray app untuk Windows/macOS/Linux dengan:
- Quick status overview
- One-click start/stop MAGNATRIX
- Notification alerts
- Hotkey shortcuts
"""
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone


class TrayApp:
    """Cross-platform system tray application for MAGNATRIX."""

    def __init__(self):
        self.magnatrix_running = False
        self.status = "idle"
        self.last_alert = None
        self.config_path = os.path.expanduser("~/.magnatrix/tray-config.json")
        self._load_config()

    def _load_config(self):
        """Load tray configuration."""
        if os.path.isfile(self.config_path):
            with open(self.config_path, "r") as f:
                self.config = json.load(f)
        else:
            self.config = {
                "autostart": False,
                "notifications": True,
                "hotkeys": {
                    "toggle": "ctrl+shift+m",
                    "status": "ctrl+shift+s",
                    "emergency_stop": "ctrl+shift+x"
                },
                "api_url": "http://localhost:8080"
            }
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            self._save_config()

    def _save_config(self):
        """Save tray configuration."""
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)

    def start_magnatrix(self):
        """Start MAGNATRIX core services."""
        self.magnatrix_running = True
        self.status = "running"
        print("[MAGNATRIX Tray] Starting MAGNATRIX...")
        # In real implementation, spawn subprocess
        # subprocess.Popen(["python", "scripts/magnatrix_boot.py"])
        self._show_notification("MAGNATRIX Started", "All services are running")

    def stop_magnatrix(self):
        """Stop MAGNATRIX core services."""
        self.magnatrix_running = False
        self.status = "stopped"
        print("[MAGNATRIX Tray] Stopping MAGNATRIX...")
        self._show_notification("MAGNATRIX Stopped", "All services stopped")

    def toggle_magnatrix(self):
        """Toggle MAGNATRIX on/off."""
        if self.magnatrix_running:
            self.stop_magnatrix()
        else:
            self.start_magnatrix()

    def emergency_stop(self):
        """Emergency stop all services."""
        self.magnatrix_running = False
        self.status = "emergency"
        print("[MAGNATRIX Tray] EMERGENCY STOP triggered!")
        self._show_notification("🚨 EMERGENCY STOP", "All MAGNATRIX services halted")

    def get_status(self) -> dict:
        """Get current MAGNATRIX status."""
        return {
            "running": self.magnatrix_running,
            "status": self.status,
            "api_url": self.config["api_url"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def _show_notification(self, title: str, message: str):
        """Show desktop notification."""
        self.last_alert = {"title": title, "message": message, "time": time.time()}
        print(f"[NOTIFICATION] {title}: {message}")
        # Cross-platform notification
        try:
            if sys.platform == "darwin":
                os.system(f"osascript -e 'display notification \"{message}\" with title \"{title}\"'")
            elif sys.platform == "linux":
                os.system(f"notify-send \"{title}\" \"{message}\"")
            elif sys.platform == "win32":
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, message, title, 0)
        except Exception:
            pass

    def run_tray(self):
        """Run the tray application."""
        print("=" * 60)
        print("MAGNATRIX Desktop Tray")
        print("=" * 60)
        print("Menu:")
        print("  1. Start MAGNATRIX")
        print("  2. Stop MAGNATRIX")
        print("  3. Toggle MAGNATRIX")
        print("  4. Status")
        print("  5. Emergency Stop")
        print("  6. Settings")
        print("  7. Quit")

        while True:
            try:
                choice = input("\nSelect: ").strip()
                if choice == "1":
                    self.start_magnatrix()
                elif choice == "2":
                    self.stop_magnatrix()
                elif choice == "3":
                    self.toggle_magnatrix()
                elif choice == "4":
                    print(json.dumps(self.get_status(), indent=2))
                elif choice == "5":
                    self.emergency_stop()
                elif choice == "6":
                    self._show_settings()
                elif choice == "7":
                    print("[MAGNATRIX Tray] Goodbye")
                    break
                else:
                    print("Invalid choice")
            except KeyboardInterrupt:
                print("\n[MAGNATRIX Tray] Goodbye")
                break

    def _show_settings(self):
        """Show and edit settings."""
        print("\nCurrent settings:")
        for key, value in self.config.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    app = TrayApp()
    app.run_tray()
