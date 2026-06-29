"""OSINT Screenshot Collector — URL screenshot orchestration."""
from dataclasses import dataclass
from pathlib import Path
import json, time

@dataclass
class ScreenshotEntry:
    url: str = ""
    viewport: str = "1920x1080"
    status: str = "pending"  # pending | captured | failed
    file_path: str = ""
    timestamp: float = 0.0
    render_time_ms: int = 0

class OsintScreenshotCollector:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._screenshots: list[ScreenshotEntry] = []
        self._default_viewport = "1920x1080"
        self._persist_path = self.root / "osint_screenshots.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._screenshots = [ScreenshotEntry(**s) for s in data.get("screenshots", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "screenshots": [s.__dict__ for s in self._screenshots]
        }, indent=2))

    def add_url(self, url: str, viewport: str = "") -> ScreenshotEntry:
        entry = ScreenshotEntry(url=url, viewport=viewport or self._default_viewport, timestamp=time.time())
        self._screenshots.append(entry)
        self._save()
        return entry

    def capture(self, url: str) -> ScreenshotEntry:
        for entry in self._screenshots:
            if entry.url == url and entry.status == "pending":
                entry.status = "captured"
                entry.file_path = f"screenshots/{hash(url) % 100000}.png"
                entry.render_time_ms = 1200  # Simulated
                entry.timestamp = time.time()
                self._save()
                return entry
        return ScreenshotEntry(url=url, status="failed")

    def batch_capture(self, urls: list[str]) -> list[ScreenshotEntry]:
        results = []
        for url in urls:
            results.append(self.capture(url))
        return results

    def list_pending(self) -> list[ScreenshotEntry]:
        return [s for s in self._screenshots if s.status == "pending"]

    def to_dict(self) -> dict:
        return {"screenshot_count": len(self._screenshots), "pending": len(self.list_pending()), "captured": sum(1 for s in self._screenshots if s.status == "captured")}

    def get_stats(self) -> dict:
        return {"total": len(self._screenshots), "captured": sum(1 for s in self._screenshots if s.status == "captured"), "failed": sum(1 for s in self._screenshots if s.status == "failed"), "pending": len(self.list_pending())}

__all__ = ["OsintScreenshotCollector", "ScreenshotEntry"]
