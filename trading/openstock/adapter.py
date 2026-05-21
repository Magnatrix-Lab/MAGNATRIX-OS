#!/usr/bin/env python3
"""OpenStock Adapter — MAGNATRIX Layer 8 Trading Data"""

import requests
import json
from datetime import datetime

class OpenStockAdapter:
    def __init__(self, base_url="http://localhost:3000"):
        self.base_url = base_url
        # Fallback: use CoinGecko public API if OpenStock not deployed
        self.cg_url = "https://api.coingecko.com/api/v3"

    def get_price(self, symbol="bitcoin"):
        """Fetch real-time price from CoinGecko (free public API)."""
        try:
            r = requests.get(f"{self.cg_url}/simple/price", params={
                "ids": symbol,
                "vs_currencies": "usd",
                "include_24hr_change": "true"
            }, timeout=10)
            data = r.json()
            price = data.get(symbol, {}).get("usd", 0)
            change = data.get(symbol, {}).get("usd_24h_change", 0)
            return {"symbol": symbol, "price": price, "change_24h": change, "source": "coingecko"}
        except Exception as e:
            return {"symbol": symbol, "price": 0, "error": str(e), "source": "failed"}

    def get_sentiment(self, symbol="bitcoin"):
        """Mock sentiment — replace with real RSS/Reddit analysis."""
        # In production: fetch CoinDesk RSS, Reddit, Twitter
        return {"symbol": symbol, "sentiment": 0.0, "source": "mock"}

    def get_news(self, symbol="bitcoin", limit=5):
        """Fetch news from CoinDesk RSS."""
        try:
            # Using jina.ai summarizer for RSS
            rss_url = "https://feeds.coindesk.com/coindesk"
            jina_url = f"https://r.jina.ai/{rss_url}"
            r = requests.get(jina_url, timeout=15)
            lines = r.text.strip().split("
")[:limit]
            return [{"headline": line[:100], "source": "coindesk"} for line in lines if line.strip()]
        except Exception as e:
            return [{"headline": f"Error fetching news: {e}", "source": "error"}]

if __name__ == "__main__":
    adapter = OpenStockAdapter()
    print("=== OpenStock Adapter Test ===")
    print(adapter.get_price("bitcoin"))
    print(adapter.get_price("ethereum"))
    print(adapter.get_sentiment("bitcoin"))
    print(adapter.get_news("bitcoin", 3))
