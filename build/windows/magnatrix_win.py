"""compiler
MAGNATRIX-OS Windows Entry Point
══════════════════════════════════
Single-file launcher untuk Windows. Menjalankan:
1. Kernel boot (kernel/kernel_native.py)
2. HTTP server untuk dashboard (website/)
3. System tray (desktop_tray/tray_native.py)
4. Graceful shutdown pada exit

Digunakan sebagai entry point PyInstaller:
    python -m PyInstaller build/windows/magnatrix.spec
"""
from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import threading
import time
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# ── Ensure repo root on sys.path ────────────────────────────────────────────
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ── Imports (with fallback messages) ──────────────────────────────────────
try:
    from kernel.kernel_native import KernelNative, KernelConfig, BootMode
except Exception as _e:
    KernelNative = None
    print(f"[WARN] Kernel import failed: {_e}")

try:
    from desktop_tray.tray_native import TrayConfig, WindowsTray
except Exception as _e:
    WindowsTray = None
    print(f"[WARN] Tray import failed: {_e}")

# ── Logging ────────────────────────────────────────────────────────────────

def _setup_logging(log_dir: Optional[str] = None, debug: bool = False) -> None:
    """Setup file + console logging."""
    if log_dir is None:
        log_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "MAGNATRIX-OS", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "magnatrix.log")
    level = logging.DEBUG if debug else logging.INFO
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    logging.basicConfig(
        level=level,
        format=fmt,
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout) if not getattr(sys, "frozen", False) else logging.StreamHandler(),
        ],
    )
    logging.info(f"Logging to {log_file}")


# ── HTTP Server (dashboard) ────────────────────────────────────────────────

class DashboardHandler(SimpleHTTPRequestHandler):
    """Serve website/ folder with CORS + cache control."""

    def __init__(self, *args, directory: Optional[str] = None, **kwargs) -> None:
        self.directory_override = directory
        super().__init__(*args, directory=directory, **kwargs)

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def log_message(self, fmt: str, *args) -> None:
        logging.getLogger("http").info(fmt % args)


class DashboardServer:
    """Threaded HTTP server for the dashboard SPA."""

    def __init__(self, root: str, port: int = 8080) -> None:
        self.root = Path(root).resolve()
        self.port = port
        self._srv: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> None:
        if not self.root.exists():
            logging.warning(f"Dashboard root {self.root} not found — creating stub")
            self.root.mkdir(parents=True, exist_ok=True)
            (self.root / "dashboard.html").write_text("<h1>MAGNATRIX-OS Dashboard</h1>", encoding="utf-8")

        def handler_factory(*args, **kwargs):
            return DashboardHandler(*args, directory=str(self.root), **kwargs)

        self._srv = HTTPServer(("0.0.0.0", self.port), handler_factory)
        self._thread = threading.Thread(target=self._srv.serve_forever, daemon=True)
        self._thread.start()
        self._running = True
        logging.info(f"Dashboard server running at http://localhost:{self.port}")

    def stop(self) -> None:
        if self._srv:
            self._srv.shutdown()
            self._srv.server_close()
        self._running = False


# ── Windows entry point ────────────────────────────────────────────────────

def _open_browser(port: int) -> None:
    try:
        webbrowser.open(f"http://localhost:{port}")
    except Exception:
        pass


def _get_data_dir() -> str:
    """Return platform-specific data directory."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        return os.path.join(appdata, "MAGNATRIX-OS")
    home = os.path.expanduser("~")
    if sys.platform == "darwin":
        return os.path.join(home, "Library", "Application Support", "MAGNATRIX-OS")
    return os.path.join(home, ".magnatrix-os")


def main() -> int:
    parser = argparse.ArgumentParser(description="MAGNATRIX-OS Windows Launcher")
    parser.add_argument("--port", type=int, default=8080, help="Dashboard HTTP port")
    parser.add_argument("--no-tray", action="store_true", help="Disable system tray")
    parser.add_argument("--console", action="store_true", help="Force console mode (even when windowed)")
    parser.add_argument("--debug", action="store_true", help="Debug logging")
    parser.add_argument("--data-dir", type=str, default=None, help="Override data directory")
    args = parser.parse_args()

    data_dir = args.data_dir or _get_data_dir()
    os.makedirs(data_dir, exist_ok=True)

    _setup_logging(os.path.join(data_dir, "logs"), debug=args.debug)
    logger = logging.getLogger("magnatrix")

    logger.info("════════════════════════════════════════════════════════════")
    logger.info("  MAGNATRIX-OS Windows Launcher v0.9.5")
    logger.info("  Open-Source AI Operating System → AGI → Super AI")
    logger.info("════════════════════════════════════════════════════════════")
    logger.info(f"Data directory: {data_dir}")
    logger.info(f"Repository root: {_REPO_ROOT}")
    logger.info(f"Python: {sys.version}")

    # ── Boot kernel ──────────────────────────────────────────────────────
    kernel = None
    if KernelNative is not None:
        try:
            cfg = KernelConfig(
                workspace_dir=data_dir,
                boot_mode=BootMode.COLD,
                log_level="DEBUG" if args.debug else "INFO",
            )
            kernel = KernelNative(cfg)
            kernel.boot()
            logger.info("Kernel booted successfully")
        except Exception as e:
            logger.exception(f"Kernel boot failed: {e}")
    else:
        logger.warning("NativeKernel not available — running in degraded mode")

    # ── Start dashboard server ──────────────────────────────────────────
    website_dir = _REPO_ROOT / "website"
    server = DashboardServer(str(website_dir), port=args.port)
    server.start()

    # ── System tray ───────────────────────────────────────────────────────
    tray = None
    if not args.no_tray and WindowsTray is not None and sys.platform == "win32":
        try:
            tray = WindowsTray(TrayConfig(tooltip="MAGNATRIX-OS"))
            tray.register("dashboard", lambda: _open_browser(args.port))
            tray.register("status", lambda: logger.info("Status requested from tray"))
            tray.register("trading", lambda: logger.info("Trading started from tray"))
            tray.start()
            logger.info("System tray started")
        except Exception as e:
            logger.warning(f"Tray failed: {e}")

    # ── Graceful shutdown ─────────────────────────────────────────────────
    _running = True

    def _shutdown(signum: Any = None, frame: Any = None) -> None:
        nonlocal _running
        if not _running:
            return
        _running = False
        logger.info("Shutdown signal received — stopping services...")
        if tray:
            try:
                tray.stop()
            except Exception:
                pass
        server.stop()
        if kernel:
            try:
                kernel.shutdown()
            except Exception:
                pass
        logger.info("Shutdown complete")

    if hasattr(signal, "SIGINT"):
        signal.signal(signal.SIGINT, _shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _shutdown)

    # ── Main loop ─────────────────────────────────────────────────────────
    logger.info("MAGNATRIX-OS is running. Press Ctrl+C to exit.")
    try:
        while _running:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt")
    finally:
        _shutdown()

    return 0


if __name__ == "__main__":
    sys.exit(main())
