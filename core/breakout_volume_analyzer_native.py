"""Breakout Volume Analyzer - Volume spike detection and analysis."""
from __future__ import annotations
import json, math, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class VolumeAnalysis:
    analysis_id: str
    symbol: str
    current_volume: float
    avg_volume: float
    volume_ratio: float
    volume_trend: str
    unusual_spike: bool
    timestamp: float

    def to_dict(self) -> Dict:
        return {"analysis_id": self.analysis_id, "symbol": self.symbol,
                "current_volume": self.current_volume, "avg_volume": self.avg_volume,
                "volume_ratio": round(self.volume_ratio,4), "volume_trend": self.volume_trend,
                "unusual_spike": self.unusual_spike, "timestamp": self.timestamp}

class BreakoutVolumeAnalyzer:
    """Analyze volume patterns: spikes, trends, unusual activity detection."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "breakout_volume"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.analyses: List[VolumeAnalysis] = []
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for a in data.get("analyses",[]): self.analyses.append(VolumeAnalysis(**a))
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"analyses": [a.to_dict() for a in self.analyses[-500:]]}, indent=2))

    def analyze(self, symbol: str, current_volume: float, historical_volumes: List[float]) -> VolumeAnalysis:
        if historical_volumes:
            avg = sum(historical_volumes) / len(historical_volumes)
            std = math.sqrt(sum((v-avg)**2 for v in historical_volumes) / len(historical_volumes)) if len(historical_volumes)>1 else 0
        else:
            avg, std = current_volume, 0
        ratio = current_volume / avg if avg > 0 else 0
        if ratio >= 3.0: trend = "extreme_spike"
        elif ratio >= 2.0: trend = "strong_spike"
        elif ratio >= 1.5: trend = "elevated"
        else: trend = "normal"
        unusual = ratio >= 2.0 and current_volume > avg + 2*std
        analysis = VolumeAnalysis(
            analysis_id="vol_" + symbol + "_" + str(int(time.time())),
            symbol=symbol, current_volume=current_volume, avg_volume=round(avg,2),
            volume_ratio=round(ratio,4), volume_trend=trend, unusual_spike=unusual, timestamp=time.time())
        self.analyses.append(analysis)
        self._save_state()
        return analysis

    def get_spike_symbols(self) -> List[str]:
        return list(set(a.symbol for a in self.analyses if a.unusual_spike))

    def get_stats(self) -> Dict:
        spikes = sum(1 for a in self.analyses if a.unusual_spike)
        return {"analyses_total": len(self.analyses), "spikes": spikes}

    def to_dict(self) -> Dict:
        return {"analyses": [a.to_dict() for a in self.analyses[-100:]], "stats": self.get_stats()}

__all__ = ["BreakoutVolumeAnalyzer", "VolumeAnalysis"]
