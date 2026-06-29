"""
financial_news_aggregator_native.py
MAGNATRIX-OS — Financial News Aggregator

Inspired by daily_stock_analysis real-time news:
Aggregate and filter financial news with sentiment scoring. Pure stdlib.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.parse import urlencode


@dataclass
class NewsArticle:
    article_id: str
    title: str
    source: str
    url: str
    summary: str
    symbols: List[str] = field(default_factory=list)
    sentiment: str = "neutral"
    sentiment_score: float = 0.0
    published_at: str = ""

    def __post_init__(self):
        if not self.published_at:
            self.published_at = datetime.now().isoformat()


class FinancialNewsAggregator:
    """Aggregate financial news with sentiment scoring."""

    SOURCES = ["bloomberg", "reuters", "cnbc", "wallstreet", "xueqiu", "eastmoney"]

    POSITIVE_WORDS = ["surge", "rise", "gain", "bull", "rally", "beat", "growth", "profit", "strong", "outperform"]
    NEGATIVE_WORDS = ["drop", "fall", "crash", "bear", "plunge", "miss", "loss", "weak", "underperform", "decline"]

    def __init__(self, news_dir: str = "./financial_news"):
        self.news_dir = Path(news_dir)
        self.news_dir.mkdir(exist_ok=True)
        self.articles: List[NewsArticle] = []
        self._load()

    def _load(self) -> None:
        file = self.news_dir / "news.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.articles = [NewsArticle(**a) for a in data]
            except Exception:
                pass

    def _save(self) -> None:
        file = self.news_dir / "news.json"
        with open(file, "w", encoding="utf-8") as f:
            json.dump([asdict(a) for a in self.articles], f, indent=2)

    def _score_sentiment(self, text: str) -> tuple:
        text_lower = text.lower()
        pos = sum(1 for w in self.POSITIVE_WORDS if w in text_lower)
        neg = sum(1 for w in self.NEGATIVE_WORDS if w in text_lower)
        if pos > neg:
            return "positive", round(min(pos / 5, 1.0), 2)
        elif neg > pos:
            return "negative", round(-min(neg / 5, 1.0), 2)
        return "neutral", 0.0

    def add_article(self, title: str, source: str, url: str, summary: str, symbols: List[str]) -> NewsArticle:
        aid = f"{source}_{len(self.articles)}"
        sentiment, score = self._score_sentiment(title + " " + summary)
        article = NewsArticle(
            article_id=aid, title=title, source=source, url=url,
            summary=summary, symbols=symbols, sentiment=sentiment, sentiment_score=score,
        )
        self.articles.append(article)
        self._save()
        return article

    def fetch_mock(self, symbol: str, count: int = 5) -> List[NewsArticle]:
        """Simulate fetching news for a symbol."""
        templates = [
            ("{symbol} reports strong Q3 earnings, beats estimates", "positive"),
            ("{symbol} announces new product launch targeting growth", "positive"),
            ("Analysts upgrade {symbol} target price amid bullish outlook", "positive"),
            ("{symbol} faces regulatory scrutiny in key market", "negative"),
            ("Market volatility impacts {symbol} trading volume", "neutral"),
        ]
        articles = []
        for i in range(count):
            tmpl, base_sent = templates[i % len(templates)]
            title = tmpl.format(symbol=symbol)
            sentiment, score = self._score_sentiment(title)
            article = NewsArticle(
                article_id=f"mock_{symbol}_{i}", title=title, source=random.choice(self.SOURCES),
                url="", summary=title, symbols=[symbol], sentiment=sentiment, sentiment_score=score,
            )
            self.articles.append(article)
            articles.append(article)
        self._save()
        return articles

    def get_news_for_symbol(self, symbol: str) -> List[NewsArticle]:
        return [a for a in self.articles if symbol in a.symbols]

    def get_sentiment_summary(self, symbol: str) -> Dict[str, Any]:
        articles = self.get_news_for_symbol(symbol)
        if not articles:
            return {"symbol": symbol, "sentiment": "neutral", "score": 0, "count": 0}
        avg_score = sum(a.sentiment_score for a in articles) / len(articles)
        pos = sum(1 for a in articles if a.sentiment == "positive")
        neg = sum(1 for a in articles if a.sentiment == "negative")
        overall = "positive" if pos > neg else "negative" if neg > pos else "neutral"
        return {"symbol": symbol, "sentiment": overall, "score": round(avg_score, 2), "count": len(articles), "positive": pos, "negative": neg}

    def get_stats(self) -> Dict[str, Any]:
        return {"total_articles": len(self.articles), "sources": len(self.SOURCES)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


import random

__all__ = ["FinancialNewsAggregator", "NewsArticle"]