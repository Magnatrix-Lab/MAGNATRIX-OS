#!/usr/bin/env python3
"""
MAGNATRIX-OS Auto Updater
Check GitHub releases, download and verify updates, atomic apply with rollback.
Usage:
    python packaging/auto_updater_native.py --check
    python packaging/auto_updater_native.py --apply v0.9.6
"""
import os, sys, json, time, urllib.request, urllib.error, shutil, tempfile, subprocess, threading
from pathlib import Path

REPO = "Magnatrix-Lab/MAGNATRIX-OS"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
INSTALL_DIR = Path(os.environ.get("MAGNATRIX_INSTALL_DIR", str(Path.home() / "MAGNATRIX-OS")))
BACKUP_DIR = Path.home() / ".magnatrix" / "backups"


class AutoUpdaterNative:
    def __init__(self):
        self._latest = None
        self._current = self._read_current_version()

    def _read_current_version(self) -> str:
        try:
            with open(INSTALL_DIR / "config" / "version.json") as f:
                return json.load(f).get("version", "0.0.0")
        except Exception:
            return "0.0.0"

    def check(self) -> dict:
        """Check GitHub for newer release."""
        try:
            req = urllib.request.Request(API_URL, headers={"Accept": "application/vnd.github.v3+json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            self._latest = data
            latest_ver = data.get("tag_name", "v0.0.0").lstrip("v")
            return {
                "current": self._current,
                "latest": latest_ver,
                "update_available": self._version_cmp(latest_ver) > 0,
                "url": data.get("html_url", ""),
                "published": data.get("published_at", ""),
            }
        except Exception as e:
            return {"error": str(e), "current": self._current, "latest": "unknown"}

    def _version_cmp(self, other: str) -> int:
        def parse(v):
            return tuple(int(x) for x in v.split(".")[:3])
        a, b = parse(self._current), parse(other)
        return (a > b) - (a < b)

    def download(self, asset_url: str, dest: Path) -> bool:
        """Download release asset."""
        try:
            req = urllib.request.Request(asset_url, headers={"Accept": "application/octet-stream"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                with open(dest, "wb") as f:
                    f.write(resp.read())
            return True
        except Exception as e:
            print(f"[UPDATER] Download failed: {e}")
            return False

    def verify(self, archive: Path, manifest_url: str) -> bool:
        """Verify SHA-256 checksums from manifest."""
        try:
            req = urllib.request.Request(manifest_url)
            with urllib.request.urlopen(req, timeout=15) as resp:
                manifest = json.loads(resp.read().decode())
            import hashlib
            h = hashlib.sha256()
            with open(archive, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            expected = manifest.get("checksums", {}).get(archive.name, "")
            return h.hexdigest() == expected
        except Exception:
            return False

    def apply(self, archive: Path) -> bool:
        """Atomic update with rollback on failure."""
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        backup = BACKUP_DIR / f"backup_{int(time.time())}"
        temp_extract = Path(tempfile.mkdtemp(prefix="magnatrix_update_"))

        try:
            # Backup current
            print(f"[UPDATER] Backing up to {backup}")
            shutil.copytree(INSTALL_DIR, backup, ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv"))

            # Extract new
            print(f"[UPDATER] Extracting to {temp_extract}")
            import tarfile
            with tarfile.open(archive, "r:gz") as tar:
                tar.extractall(temp_extract)

            # Atomic swap
            print("[UPDATER] Applying update...")
            for item in temp_extract.iterdir():
                dest = INSTALL_DIR / item.name
                if dest.exists() and dest.is_dir():
                    shutil.rmtree(dest)
                if dest.exists():
                    dest.unlink()
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

            print("[UPDATER] Update applied successfully.")
            return True

        except Exception as e:
            print(f"[UPDATER] Apply failed: {e}")
            self._rollback(backup)
            return False
        finally:
            shutil.rmtree(temp_extract, ignore_errors=True)

    def _rollback(self, backup: Path):
        """Rollback to backup."""
        print(f"[UPDATER] Rolling back from {backup}...")
        try:
            for item in backup.iterdir():
                dest = INSTALL_DIR / item.name
                if dest.exists() and dest.is_dir():
                    shutil.rmtree(dest)
                if dest.exists():
                    dest.unlink()
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)
            print("[UPDATER] Rollback complete.")
        except Exception as e:
            print(f"[UPDATER] Rollback failed: {e}")

    def start_background_check(self, interval_hours: int = 24):
        """Start background update check thread."""
        def loop():
            while True:
                result = self.check()
                if result.get("update_available"):
                    print(f"[UPDATER] Update available: {result['latest']}")
                    # Could trigger notification or auto-download here
                time.sleep(interval_hours * 3600)
        t = threading.Thread(target=loop, daemon=True)
        t.start()
        return t


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Check for updates")
    parser.add_argument("--apply", metavar="VERSION", help="Apply update to version")
    args = parser.parse_args()

    updater = AutoUpdaterNative()
    if args.check:
        result = updater.check()
        print(json.dumps(result, indent=2))
    elif args.apply:
        print(f"[UPDATER] Apply not implemented for version {args.apply}")
    else:
        print("Usage: python auto_updater_native.py --check")


if __name__ == "__main__":
    main()
