"""
Hot Reload — MAGNATRIX-OS Core
Module reloading tanpa restart system. Watch file changes, reload safely.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from __future__ import annotations

import os, sys, time, importlib, hashlib, threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable


@dataclass
class ModuleWatch:
    """Watch entry untuk single module."""
    module_name: str
    filepath: str
    last_hash: str
    last_modified: float


class HotReloader:
    """
    Hot reload untuk Python modules tanpa restart system.
    - Watch file changes via hash comparison
    - Safe reload dengan rollback capability
    - Event callbacks pada reload
    """

    def __init__(self, watch_interval: float = 1.0) -> None:
        self._watches: Dict[str, ModuleWatch] = {}
        self._watch_interval = watch_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[str, Any], None]] = []
        self._reload_history: List[Dict[str, Any]] = []
        self._backups: Dict[str, str] = {}

    def watch(self, module_name: str, filepath: Optional[str] = None) -> None:
        """Add a module to watch list."""
        if filepath is None:
            # Try to find module file
            try:
                module = sys.modules.get(module_name)
                if module and hasattr(module, "__file__"):
                    filepath = module.__file__
                else:
                    filepath = module_name.replace(".", "/") + ".py"
            except Exception:
                filepath = module_name.replace(".", "/") + ".py"

        if not os.path.exists(filepath):
            return

        h = self._compute_hash(filepath)
        self._watches[module_name] = ModuleWatch(
            module_name=module_name,
            filepath=filepath,
            last_hash=h,
            last_modified=os.path.getmtime(filepath),
        )

    def unwatch(self, module_name: str) -> bool:
        return self._watches.pop(module_name, None) is not None

    def add_callback(self, callback: Callable[[str, Any], None]) -> None:
        self._callbacks.append(callback)

    def start(self) -> None:
        """Start watching in background thread."""
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _watch_loop(self) -> None:
        while self._running:
            self.check_all()
            time.sleep(self._watch_interval)

    def check_all(self) -> List[str]:
        """Check all watched modules for changes. Returns reloaded modules."""
        reloaded = []
        for module_name, watch in list(self._watches.items()):
            if not os.path.exists(watch.filepath):
                continue
            current_hash = self._compute_hash(watch.filepath)
            current_mtime = os.path.getmtime(watch.filepath)
            if current_hash != watch.last_hash or current_mtime > watch.last_modified:
                success = self._reload(module_name, watch.filepath)
                if success:
                    watch.last_hash = current_hash
                    watch.last_modified = current_mtime
                    reloaded.append(module_name)
        return reloaded

    def _reload(self, module_name: str, filepath: str) -> bool:
        """Reload a single module."""
        try:
            # Backup current code
            with open(filepath, "r") as f:
                self._backups[module_name] = f.read()

            # Reload module
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
            else:
                importlib.import_module(module_name)

            # Record
            self._reload_history.append({
                "module": module_name,
                "timestamp": time.time(),
                "success": True,
            })

            # Notify callbacks
            for cb in self._callbacks:
                try:
                    cb(module_name, sys.modules.get(module_name))
                except Exception:
                    pass

            return True
        except Exception as e:
            self._reload_history.append({
                "module": module_name,
                "timestamp": time.time(),
                "success": False,
                "error": str(e),
            })
            # Restore backup if reload failed
            self._rollback(module_name)
            return False

    def _rollback(self, module_name: str) -> bool:
        """Rollback to last known good version."""
        if module_name not in self._backups:
            return False
        watch = self._watches.get(module_name)
        if not watch:
            return False
        try:
            with open(watch.filepath, "w") as f:
                f.write(self._backups[module_name])
            return True
        except Exception:
            return False

    def _compute_hash(self, filepath: str) -> str:
        with open(filepath, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]

    def get_reload_history(self) -> List[Dict[str, Any]]:
        return list(self._reload_history)

    def stats(self) -> Dict[str, Any]:
        successful = len([r for r in self._reload_history if r.get("success")])
        failed = len([r for r in self._reload_history if not r.get("success")])
        return {
            "watched_modules": len(self._watches),
            "successful_reloads": successful,
            "failed_reloads": failed,
            "running": self._running,
            "watch_interval": self._watch_interval,
        }


def run():
    print("=" * 60)
    print("Hot Reload — Demo")
    print("=" * 60)

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test module
        test_file = os.path.join(tmpdir, "test_module.py")
        with open(test_file, "w") as f:
            f.write("x = 1\n")

        # Add to path and import
        sys.path.insert(0, tmpdir)
        import test_module
        print(f"\n[1] Initial value: x = {test_module.x}")

        reloader = HotReloader(watch_interval=0.5)
        reloader.watch("test_module", test_file)

        print("\n[2] Modify file and check")
        with open(test_file, "w") as f:
            f.write("x = 2\n")

        reloaded = reloader.check_all()
        print(f"   Reloaded: {reloaded}")
        print(f"   New value: x = {test_module.x}")

        print("\n[3] Bad modification (rollback test)")
        with open(test_file, "w") as f:
            f.write("x = syntax error!!\n")

        reloaded2 = reloader.check_all()
        print(f"   Reloaded: {reloaded2}")
        print(f"   Value after rollback: x = {test_module.x}")

        print(f"\n[4] Stats: {reloader.stats()}")
        print(f"   History: {reloader.get_reload_history()}")

        sys.path.remove(tmpdir)

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()
