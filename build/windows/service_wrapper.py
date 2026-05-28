"""
MAGNATRIX-OS Windows Service Wrapper
═════════════════════════════════════
Wraps the main application as a Windows Service using pywin32.
This allows MAGNATRIX-OS to run as a background service without
user login.

Install as service (administrator):
    python service_wrapper.py install
    python service_wrapper.py start

Remove service:
    python service_wrapper.py remove
"""
from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

# ── Ensure repo root on path ──────────────────────────────────────────────
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ── Service class (with fallback if pywin32 missing) ──────────────────────
try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
    import win32evtlogutil
    _HAS_PYWIN32 = True
except ImportError:
    _HAS_PYWIN32 = False
    # Stub classes for import on non-Windows / missing pywin32
    class win32serviceutil:
        class ServiceFramework:
            def __init__(self, args):
                pass
            def ReportServiceStatus(self, *a, **k):
                pass
            def SvcDoRun(self):
                raise NotImplementedError
            def SvcStop(self):
                raise NotImplementedError
    class win32service:
        SERVICE_RUNNING = 0x04
        SERVICE_STOP_PENDING = 0x03
        SERVICE_START_PENDING = 0x02
    class win32event:
        @staticmethod
        def CreateEvent(a, b, c, d):
            return None
        @staticmethod
        def SetEvent(h):
            pass
        @staticmethod
        def WaitForSingleObject(h, ms):
            return 0xFFFFFFFF
    class servicemanager:
        @staticmethod
        def LogMsg(*a, **k):
            pass
        @staticmethod
        def LogInfoMsg(s):
            print(f"[SERVICE] {s}")
        @staticmethod
        def PrepareToHostSingle(*a, **k):
            pass
        @staticmethod
        def Initialize(*a, **k):
            pass
        @staticmethod
        def StartServiceCtrlDispatcher(*a, **k):
            pass
    class win32evtlogutil:
        @staticmethod
        def ReportEvent(*a, **k):
            pass


class MagnatrixService(win32serviceutil.ServiceFramework):
    """Windows Service wrapper for MAGNATRIX-OS."""

    _svc_name_ = "MAGNATRIX-OS"
    _svc_display_name_ = "MAGNATRIX-OS AI Operating System"
    _svc_description_ = "Open-source AI Operating System with autonomous agents, HFT trading, and P2P mesh networking."

    def __init__(self, args):
        super().__init__(args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self._running = False
        self._kernel = None
        self._server = None
        self._tray = None

    def SvcDoRun(self):
        """Service main loop."""
        self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )
        self._running = True
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)

        # Start kernel and server (no tray in service mode)
        self._start_app(no_tray=True)

        # Block until stop signal
        while self._running:
            rc = win32event.WaitForSingleObject(self.hWaitStop, 5000)
            if rc == win32event.WAIT_OBJECT_0:
                break
            time.sleep(1)

        self._stop_app()
        servicemanager.LogInfoMsg("Service stopped")

    def SvcStop(self):
        """Handle service stop request."""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self._running = False
        win32event.SetEvent(self.hWaitStop)
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    # ── Internal helpers ─────────────────────────────────────────────────

    def _start_app(self, no_tray: bool = True) -> None:
        try:
            from magnatrix_win import _setup_logging, DashboardServer
            from kernel.kernel_native import KernelNative, KernelConfig, BootMode
            from desktop_tray.tray_native import TrayConfig, WindowsTray
        except Exception as e:
            servicemanager.LogInfoMsg(f"Import error: {e}")
            return

        data_dir = os.path.join(os.environ.get("PROGRAMDATA", "C:\\ProgramData"), "MAGNATRIX-OS")
        os.makedirs(data_dir, exist_ok=True)
        _setup_logging(os.path.join(data_dir, "logs"), debug=False)

        try:
            cfg = KernelConfig(workspace_dir=data_dir, boot_mode=BootMode.COLD, log_level="INFO")
            self._kernel = KernelNative(cfg)
            self._kernel.boot()
        except Exception as e:
            servicemanager.LogInfoMsg(f"Kernel boot failed: {e}")

        try:
            website_dir = _REPO_ROOT / "website"
            self._server = DashboardServer(str(website_dir), port=8080)
            self._server.start()
        except Exception as e:
            servicemanager.LogInfoMsg(f"Server start failed: {e}")

        if not no_tray:
            try:
                self._tray = WindowsTray(TrayConfig(tooltip="MAGNATRIX-OS"))
                self._tray.start()
            except Exception:
                pass

    def _stop_app(self) -> None:
        if self._tray:
            try:
                self._tray.stop()
            except Exception:
                pass
        if self._server:
            try:
                self._server.stop()
            except Exception:
                pass
        if self._kernel:
            try:
                self._kernel.shutdown()
            except Exception:
                pass


def main():
    """Entry point for command-line service control."""
    if _HAS_PYWIN32 and len(sys.argv) == 1:
        # No args → run as service
        servicemanager.PrepareToHostSingle(MagnatrixService)
        servicemanager.Initialize("MAGNATRIX-OS", None)
        servicemanager.StartServiceCtrlDispatcher()
    elif _HAS_PYWIN32:
        # install / remove / start / stop
        win32serviceutil.HandleCommandLine(MagnatrixService)
    else:
        print("[WARN] pywin32 not installed — service mode unavailable on this platform")
        print("Usage (Windows with pywin32):")
        print("  python service_wrapper.py install")
        print("  python service_wrapper.py start")
        print("  python service_wrapper.py stop")
        print("  python service_wrapper.py remove")
        sys.exit(1)


if __name__ == "__main__":
    main()
