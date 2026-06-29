"""Breakout Screener - Screen thousands of stocks for breakout candidates."""
from __future__ import annotations
import json, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class ScreenResult:
    result_id: str
    symbol: str
    price: float
    change_pct: float
    volume_ratio: float
    market_cap: float
    sector: str
    score: float
    passed: bool

    def to_dict(self) -> Dict:
        return {"result_id": self.result_id, "symbol": self.symbol, "price": round(self.price,4),
                "change_pct": round(self.change_pct,4), "volume_ratio": round(self.volume_ratio,4),
                "market_cap": round(self.market_cap,2), "sector": self.sector,
                "score": round(self.score,4), "passed": self.passed}

class BreakoutScreener:
    """Screen stocks for breakout criteria: price move, volume, market cap, sector."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "breakout_screener"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[ScreenResult] = []
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for r in data.get("results",[]): self.results.append(ScreenResult(**r))
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"results": [r.to_dict() for r in self.results[-500:]]}, indent=2))

    def screen(self, symbol: str, price: float, change_pct: float, volume_ratio: float,
               market_cap: float, sector: str = "") -> ScreenResult:
        score = 0.0
        passed = False
        if market_cap >= 300_000_000:
            score += 0.2
            if change_pct >= 6.0:
                score += 0.4
            if volume_ratio >= 2.0:
                score += 0.4
        passed = score >= 0.6
        result = ScreenResult(
            result_id="scr_" + symbol + "_" + str(int(time.time())),
            symbol=symbol, price=price, change_pct=round(change_pct,4), volume_ratio=round(volume_ratio,4),
            market_cap=market_cap, sector=sector, score=round(score,4), passed=passed)
        self.results.append(result)
        self._save_state()
        return result

    def screen_batch(self, stocks: List[Dict]) -> List[ScreenResult]:
        return [self.screen(s["symbol"], s.get("price",0), s.get("change_pct",0),
                            s.get("volume_ratio",0), s.get("market_cap",0), s.get("sector","")) for s in stocks]

    def get_passed(self) -> List[ScreenResult]:
        return [r for r in self.results if r.passed]

    def get_stats(self) -> Dict:
        passed = sum(1 for r in self.results if r.passed)
        return {"results_total": len(self.results), "passed": passed,
                "pass_rate": round(passed/max(1,len(self.results)),4)}

    def to_dict(self) -> Dict:
        return {"results": [r.to_dict() for r in self.results[-100:]], "stats": self.get_stats()}

__all__ = ["BreakoutScreener", "ScreenResult"]
