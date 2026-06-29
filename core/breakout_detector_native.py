"""Breakout Detector - Detect stock breakouts based on price, volume, and market cap."""
from __future__ import annotations
import json, math, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

@dataclass
class BreakoutSignal:
    signal_id: str
    symbol: str
    price_move_pct: float
    volume_multiplier: float
    market_cap: float
    breakout_type: str  # price, volume, combined
    confidence: float
    timestamp: float
    triggered: bool = False

    def to_dict(self) -> Dict:
        return {"signal_id": self.signal_id, "symbol": self.symbol,
                "price_move_pct": round(self.price_move_pct,4),
                "volume_multiplier": round(self.volume_multiplier,4),
                "market_cap": round(self.market_cap,2),
                "breakout_type": self.breakout_type,
                "confidence": round(self.confidence,4), "timestamp": self.timestamp,
                "triggered": self.triggered}

class BreakoutDetector:
    """Detect stock breakouts: price moves, volume spikes, market cap filters."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "breakout_detector"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.signals: List[BreakoutSignal] = []
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for s in data.get("signals",[]): self.signals.append(BreakoutSignal(**s))
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"signals": [s.to_dict() for s in self.signals[-500:]]}, indent=2))

    def detect(self, symbol: str, current_price: float, prev_price: float, current_volume: float,
               avg_volume: float, market_cap: float) -> BreakoutSignal:
        price_move = (current_price - prev_price) / prev_price * 100 if prev_price > 0 else 0.0
        vol_mult = current_volume / avg_volume if avg_volume > 0 else 0.0
        # Filter: real company (not micro-cap)
        if market_cap < 300_000_000:
            btype = "ignored_microcap"
            conf = 0.0
        elif price_move >= 6.0 and vol_mult >= 2.0:
            btype = "combined_breakout"
            conf = min(1.0, (price_move / 10.0) * (vol_mult / 3.0))
        elif price_move >= 6.0:
            btype = "price_breakout"
            conf = min(1.0, price_move / 10.0)
        elif vol_mult >= 2.0:
            btype = "volume_breakout"
            conf = min(1.0, vol_mult / 3.0)
        else:
            btype = "none"
            conf = 0.0
        sig = BreakoutSignal(
            signal_id="sig_" + symbol + "_" + str(int(time.time())),
            symbol=symbol, price_move_pct=round(price_move,4), volume_multiplier=round(vol_mult,4),
            market_cap=market_cap, breakout_type=btype, confidence=round(conf,4), timestamp=time.time(),
            triggered=(conf > 0.5))
        self.signals.append(sig)
        self._save_state()
        return sig

    def get_active_signals(self, min_confidence: float = 0.5) -> List[BreakoutSignal]:
        return [s for s in self.signals if s.confidence >= min_confidence and s.triggered]

    def get_stats(self) -> Dict:
        triggered = [s for s in self.signals if s.triggered]
        by_type = {}
        for s in triggered: by_type[s.breakout_type] = by_type.get(s.breakout_type,0)+1
        return {"signals_total": len(self.signals), "triggered": len(triggered), "by_type": by_type}

    def to_dict(self) -> Dict:
        return {"signals": [s.to_dict() for s in self.signals[-100:]], "stats": self.get_stats()}

__all__ = ["BreakoutDetector", "BreakoutSignal"]
