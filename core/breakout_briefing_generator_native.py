"""Breakout Briefing Generator - AI-generated briefing and analysis."""
from __future__ import annotations
import json, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class Briefing:
    briefing_id: str
    symbol: str
    headline: str
    summary: str
    key_metrics: Dict[str, float] = field(default_factory=dict)
    risk_level: str = "medium"
    timestamp: float = 0.0

    def to_dict(self) -> Dict:
        return {"briefing_id": self.briefing_id, "symbol": self.symbol, "headline": self.headline,
                "summary": self.summary, "key_metrics": self.key_metrics,
                "risk_level": self.risk_level, "timestamp": self.timestamp}

class BreakoutBriefingGenerator:
    """Generate AI-style analysis briefings for breakout stocks."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "breakout_briefing"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.briefings: List[Briefing] = []
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for b in data.get("briefings",[]): self.briefings.append(Briefing(**b))
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"briefings": [b.to_dict() for b in self.briefings[-200:]]}, indent=2))

    def generate(self, symbol: str, price_move: float, volume_ratio: float, market_cap: float,
                 sector: str = "") -> Briefing:
        if price_move >= 10.0:
            headline = symbol + " surges " + str(round(price_move,1)) + "% on massive volume"
            risk = "high"
        elif price_move >= 6.0:
            headline = symbol + " breaks out with " + str(round(price_move,1)) + "% gain"
            risk = "medium"
        else:
            headline = symbol + " shows unusual activity"
            risk = "low"
        summary = (symbol + " is experiencing a significant breakout. " +
                   "Price move: " + str(round(price_move,1)) + "%. " +
                   "Volume is " + str(round(volume_ratio,1)) + "x average. " +
                   "Market cap: $" + str(round(market_cap/1e9,2)) + "B.")
        briefing = Briefing(
            briefing_id="brief_" + symbol + "_" + str(int(time.time())),
            symbol=symbol, headline=headline, summary=summary,
            key_metrics={"price_move": round(price_move,4), "volume_ratio": round(volume_ratio,4),
                         "market_cap": market_cap}, risk_level=risk, timestamp=time.time())
        self.briefings.append(briefing)
        self._save_state()
        return briefing

    def get_briefings(self, symbol: str) -> List[Briefing]:
        return [b for b in self.briefings if b.symbol == symbol]

    def get_stats(self) -> Dict:
        by_risk = {}
        for b in self.briefings: by_risk[b.risk_level] = by_risk.get(b.risk_level,0)+1
        return {"briefings_total": len(self.briefings), "by_risk": by_risk}

    def to_dict(self) -> Dict:
        return {"briefings": [b.to_dict() for b in self.briefings[-50:]], "stats": self.get_stats()}

__all__ = ["BreakoutBriefingGenerator", "Briefing"]
