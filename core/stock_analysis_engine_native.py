"""
stock_analysis_engine_native.py
MAGNATRIX-OS — Stock Analysis Engine

Inspired by daily_stock_analysis LLM-driven analysis:
Analyze stock data with multiple strategies and generate insights. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class AnalysisReport:
    symbol: str
    strategy: str
    recommendation: str
    score: float
    reasoning: str
    risk_level: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class StockAnalysisEngine:
    """LLM-driven stock analysis engine with multiple strategies."""

    STRATEGIES = {
        "momentum": {"name": "Momentum Analysis", "description": "Track price momentum and trends"},
        "value": {"name": "Value Analysis", "description": "Assess intrinsic value vs market price"},
        "growth": {"name": "Growth Analysis", "description": "Evaluate revenue and earnings growth"},
        "dividend": {"name": "Dividend Analysis", "description": "Analyze dividend yield and sustainability"},
        "risk": {"name": "Risk Assessment", "description": "Volatility and drawdown analysis"},
        "sentiment": {"name": "Sentiment Analysis", "description": "News and market sentiment scoring"},
    }

    def __init__(self, reports_dir: str = "./stock_reports"):
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(exist_ok=True)
        self.reports: Dict[str, List[AnalysisReport]] = {}
        self._load()

    def _load(self) -> None:
        file = self.reports_dir / "reports.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for symbol, rlist in data.items():
                        self.reports[symbol] = [AnalysisReport(**r) for r in rlist]
            except Exception:
                pass

    def _save(self) -> None:
        file = self.reports_dir / "reports.json"
        with open(file, "w", encoding="utf-8") as f:
            json.dump(
                {s: [asdict(r) for r in rlist] for s, rlist in self.reports.items()},
                f, indent=2,
            )

    def analyze(self, symbol: str, strategy: str, price_data: List[Dict[str, Any]]) -> AnalysisReport:
        if not price_data:
            return AnalysisReport(symbol=symbol, strategy=strategy, recommendation="HOLD", score=50.0, reasoning="No data", risk_level="unknown")

        closes = [d["close"] for d in price_data]
        avg = sum(closes) / len(closes)
        latest = closes[-1]

        if strategy == "momentum":
            ma5 = sum(closes[-5:]) / min(5, len(closes)) if len(closes) >= 5 else avg
            ma20 = sum(closes[-20:]) / min(20, len(closes)) if len(closes) >= 20 else avg
            if latest > ma5 > ma20:
                rec, score, risk = "BUY", 75.0, "medium"
            elif latest < ma5 < ma20:
                rec, score, risk = "SELL", 25.0, "medium"
            else:
                rec, score, risk = "HOLD", 50.0, "low"
            reason = f"MA5={ma5:.2f}, MA20={ma20:.2f}, Latest={latest:.2f}"
        elif strategy == "value":
            pe = latest / (avg * 0.05) if avg > 0 else 20
            if pe < 15:
                rec, score, risk = "BUY", 80.0, "low"
            elif pe > 30:
                rec, score, risk = "SELL", 20.0, "high"
            else:
                rec, score, risk = "HOLD", 50.0, "low"
            reason = f"Simulated P/E ratio: {pe:.2f}"
        elif strategy == "risk":
            volatility = (max(closes) - min(closes)) / avg * 100 if avg > 0 else 0
            if volatility > 20:
                rec, score, risk = "HOLD", 40.0, "high"
            elif volatility > 10:
                rec, score, risk = "HOLD", 55.0, "medium"
            else:
                rec, score, risk = "BUY", 70.0, "low"
            reason = f"Volatility: {volatility:.2f}%"
        else:
            rec, score, risk = "HOLD", 50.0, "low"
            reason = f"Generic analysis for {strategy}"

        report = AnalysisReport(
            symbol=symbol, strategy=strategy, recommendation=rec,
            score=round(score, 2), reasoning=reason, risk_level=risk,
        )
        self.reports.setdefault(symbol, []).append(report)
        self._save()
        return report

    def multi_strategy(self, symbol: str, price_data: List[Dict[str, Any]]) -> List[AnalysisReport]:
        return [self.analyze(symbol, s, price_data) for s in self.STRATEGIES.keys()]

    def consensus(self, symbol: str) -> Dict[str, Any]:
        reps = self.reports.get(symbol, [])
        if not reps:
            return {"symbol": symbol, "consensus": "UNKNOWN", "avg_score": 0}
        avg_score = sum(r.score for r in reps) / len(reps)
        buys = sum(1 for r in reps if r.recommendation == "BUY")
        sells = sum(1 for r in reps if r.recommendation == "SELL")
        if buys > sells:
            consensus = "BUY"
        elif sells > buys:
            consensus = "SELL"
        else:
            consensus = "HOLD"
        return {"symbol": symbol, "consensus": consensus, "avg_score": round(avg_score, 2), "reports": len(reps)}

    def get_reports(self, symbol: str) -> List[AnalysisReport]:
        return self.reports.get(symbol, [])

    def get_stats(self) -> Dict[str, Any]:
        total = sum(len(r) for r in self.reports.values())
        return {"total_reports": total, "strategies": len(self.STRATEGIES), "symbols": len(self.reports)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["StockAnalysisEngine", "AnalysisReport"]