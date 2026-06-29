"""Breakout News Analyzer - News headline and sentiment analysis."""
from __future__ import annotations
import json, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class NewsItem:
    item_id: str
    symbol: str
    headline: str
    source: str
    sentiment: float  # -1 to 1
    relevance: float  # 0 to 1
    timestamp: float

    def to_dict(self) -> Dict:
        return {"item_id": self.item_id, "symbol": self.symbol, "headline": self.headline,
                "source": self.source, "sentiment": round(self.sentiment,4),
                "relevance": round(self.relevance,4), "timestamp": self.timestamp}

class BreakoutNewsAnalyzer:
    """Analyze news headlines for sentiment and relevance to breakouts."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "breakout_news"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.items: List[NewsItem] = []
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for i in data.get("items",[]): self.items.append(NewsItem(**i))
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"items": [i.to_dict() for i in self.items[-500:]]}, indent=2))

    def _analyze_sentiment(self, headline: str) -> float:
        positive = ["surge", "gain", "rise", "breakout", "beat", "growth", "rally", "bullish", "strong"]
        negative = ["drop", "fall", "crash", "decline", "bearish", "weak", "loss", "cut"]
        h = headline.lower()
        score = 0.0
        for p in positive: score += 0.2 * h.count(p)
        for n in negative: score -= 0.2 * h.count(n)
        return max(-1.0, min(1.0, score))

    def add_news(self, symbol: str, headline: str, source: str = "") -> NewsItem:
        sentiment = self._analyze_sentiment(headline)
        relevance = min(1.0, 0.5 + abs(sentiment))
        item = NewsItem(
            item_id="news_" + symbol + "_" + str(int(time.time()*1000)),
            symbol=symbol, headline=headline, source=source,
            sentiment=round(sentiment,4), relevance=round(relevance,4), timestamp=time.time())
        self.items.append(item)
        self._save_state()
        return item

    def get_sentiment(self, symbol: str) -> float:
        items = [i for i in self.items if i.symbol == symbol]
        if not items: return 0.0
        return sum(i.sentiment for i in items) / len(items)

    def get_stats(self) -> Dict:
        avg_sent = sum(i.sentiment for i in self.items) / max(1,len(self.items))
        return {"items_total": len(self.items), "avg_sentiment": round(avg_sent,4)}

    def to_dict(self) -> Dict:
        return {"items": [i.to_dict() for i in self.items[-100:]], "stats": self.get_stats()}

__all__ = ["BreakoutNewsAnalyzer", "NewsItem"]
