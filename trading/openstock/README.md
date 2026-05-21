# OpenStock Integration — MAGNATRIX Agentic OS

> **Repo**: https://github.com/Open-Dev-Society/OpenStock | 11.5k stars | Open-source market platform
> **License**: AGPL-3.0 (deploy as service, API call)

## Status: ADOPTED

---

## Integration Strategy: Service Deployment

OpenStock di-deploy sebagai **standalone container** di MAGNATRIX. MAGNATRIX call via API (no code embed, AGPL-safe).

## Directory

```
trading/openstock/
├── README.md              # This file
├── docker-compose.yml     # OpenStock container + MongoDB
├── adapter.py             # MAGNATRIX adapter
└── config.yaml            # Adapter config
```

## Features untuk MAGNATRIX Layer 8

| Feature | Value untuk Trading |
|---------|-------------------|
| **Real-time Prices** | Finnhub API feed untuk signal generation |
| **TradingView Charts** | Technical analysis visualization |
| **Sentiment Insights** | Reddit + X + News + Polymarket → trading signal |
| **Watchlist** | Track portfolio symbols |
| **Alerts** | Price movement notifications |
| **Market News** | Finnhub news feed → knowledge layer |

## Adapter (adapter.py)

```python
#!/usr/bin/env python3
"""MAGNATRIX adapter untuk OpenStock."""

import requests

class OpenStockAdapter:
    def __init__(self, base_url="http://localhost:3000", api_key=None):
        self.base_url = base_url
        self.api_key = api_key
    
    def get_price(self, symbol: str) -> dict:
        """Get real-time price untuk symbol."""
        r = requests.get(f"{self.base_url}/api/stock/{symbol}")
        return r.json()
    
    def get_sentiment(self, symbol: str) -> dict:
        """Get sentiment analysis (Reddit + X + News + Polymarket)."""
        r = requests.get(f"{self.base_url}/api/sentiment/{symbol}")
        return r.json()
    
    def get_news(self, symbol: str, limit: int = 10) -> list:
        """Get market news untuk symbol."""
        r = requests.get(f"{self.base_url}/api/news/{symbol}?limit={limit}")
        return r.json()
    
    def add_to_watchlist(self, symbol: str, user_id: str) -> dict:
        """Add symbol ke watchlist."""
        r = requests.post(
            f"{self.base_url}/api/watchlist",
            json={"symbol": symbol, "user_id": user_id}
        )
        return r.json()
    
    def set_alert(self, symbol: str, condition: str, threshold: float) -> dict:
        """Set price alert."""
        r = requests.post(
            f"{self.base_url}/api/alerts",
            json={"symbol": symbol, "condition": condition, "threshold": threshold}
        )
        return r.json()

# MCP Tool exposed
def tool_stock_price(params: dict) -> dict:
    adapter = OpenStockAdapter()
    return adapter.get_price(params["symbol"])

def tool_stock_sentiment(params: dict) -> dict:
    adapter = OpenStockAdapter()
    return adapter.get_sentiment(params["symbol"])
```

## Sentiment → Trading Signal Pipeline

```
OpenStock Sentiment
       ↓
Reddit: +0.7 | X: +0.5 | News: +0.3 | Polymarket: +0.6
       ↓
Composite Score: +0.525 (bullish)
       ↓
GQRIS Brain: "Sentiment bullish untuk BTC → generate BUY signal"
       ↓
Risk Manager: Kelly sizing 0.3x
       ↓
Execution Engine: Paper trade / Live trade
```

## Commands

```bash
# Deploy OpenStock
cd trading/openstock
docker-compose up -d

# Test adapter
python adapter.py --test --symbol BTC-USD

# Get sentiment
python adapter.py --sentiment --symbol ETH-USD

# Add watchlist
python adapter.py --watchlist --symbol SOL-USD
```

## Integration dengan Trading Engine

```
GQRIS Brain (Layer 8)
    ├── Signal Generator ← OpenStock price + sentiment
    ├── Risk Manager ← portfolio data
    └── Execution Engine ← CCXT + OpenStock watchlist
```

## Notes

- License: AGPL-3.0 → deploy as service, API call only (no code embed)
- Stack: Next.js 15 + MongoDB + Finnhub + TradingView
- Sentiment: Reddit + X.com + News + Polymarket (4 sources)
- AI: Gemini via Inngest for inference
- Pair dengan CCXT untuk trade execution
