"""Breakout Chart Capture - Chart screenshot and visualization capture."""
from __future__ import annotations
import json, time, hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class ChartCapture:
    capture_id: str
    symbol: str
    timeframe: str
    image_path: str
    indicators: List[str] = field(default_factory=list)
    captured_at: float = 0.0

    def to_dict(self) -> Dict:
        return {"capture_id": self.capture_id, "symbol": self.symbol, "timeframe": self.timeframe,
                "image_path": self.image_path, "indicators": self.indicators, "captured_at": self.captured_at}

class BreakoutChartCapture:
    """Capture chart screenshots with technical indicators."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "breakout_chart"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.captures: List[ChartCapture] = []
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for c in data.get("captures",[]): self.captures.append(ChartCapture(**c))
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"captures": [c.to_dict() for c in self.captures[-200:]]}, indent=2))

    def capture(self, symbol: str, timeframe: str = "1d", indicators: Optional[List[str]] = None) -> ChartCapture:
        if indicators is None: indicators = ["volume", "sma_20", "sma_50"]
        capture_id = "chart_" + symbol + "_" + timeframe + "_" + str(int(time.time()))
        image_path = str(self.data_dir / "charts" / (capture_id + ".png"))
        (self.data_dir / "charts").mkdir(parents=True, exist_ok=True)
        cap = ChartCapture(
            capture_id=capture_id, symbol=symbol, timeframe=timeframe,
            image_path=image_path, indicators=indicators, captured_at=time.time())
        self.captures.append(cap)
        self._save_state()
        return cap

    def get_captures(self, symbol: str) -> List[ChartCapture]:
        return [c for c in self.captures if c.symbol == symbol]

    def get_stats(self) -> Dict:
        return {"captures_total": len(self.captures), "symbols": len(set(c.symbol for c in self.captures))}

    def to_dict(self) -> Dict:
        return {"captures": [c.to_dict() for c in self.captures[-50:]], "stats": self.get_stats()}

__all__ = ["BreakoutChartCapture", "ChartCapture"]
