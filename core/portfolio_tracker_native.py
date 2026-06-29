"""
portfolio_tracker_native.py
MAGNATRIX-OS — Portfolio Tracker

Track stock portfolios with P&L, allocation, and rebalance. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class PortfolioHolding:
    symbol: str
    shares: float
    avg_cost: float
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0


@dataclass
class Portfolio:
    portfolio_id: str
    name: str
    holdings: List[PortfolioHolding] = field(default_factory=list)
    cash: float = 0.0
    total_value: float = 0.0
    total_pnl: float = 0.0
    created_at: str = ""
    last_updated: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class PortfolioTracker:
    """Track stock portfolios with P&L, allocation, and rebalance."""

    def __init__(self, portfolios_dir: str = "./portfolios"):
        self.portfolios_dir = Path(portfolios_dir)
        self.portfolios_dir.mkdir(exist_ok=True)
        self.portfolios: Dict[str, Portfolio] = {}
        self._load()

    def _load(self) -> None:
        file = self.portfolios_dir / "portfolios.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for pid, pd in data.items():
                        pd["holdings"] = [PortfolioHolding(**h) for h in pd.get("holdings", [])]
                        self.portfolios[pid] = Portfolio(**pd)
            except Exception:
                pass

    def _save(self) -> None:
        file = self.portfolios_dir / "portfolios.json"
        with open(file, "w", encoding="utf-8") as f:
            out = {}
            for pid, p in self.portfolios.items():
                d = asdict(p)
                d["holdings"] = [asdict(h) for h in p.holdings]
                out[pid] = d
            json.dump(out, f, indent=2)

    def create_portfolio(self, portfolio_id: str, name: str, cash: float = 0.0) -> Portfolio:
        p = Portfolio(portfolio_id=portfolio_id, name=name, cash=cash)
        self.portfolios[portfolio_id] = p
        self._save()
        return p

    def buy(self, portfolio_id: str, symbol: str, shares: float, price: float) -> bool:
        p = self.portfolios.get(portfolio_id)
        if not p:
            return False
        cost = shares * price
        if p.cash < cost:
            return False
        p.cash -= cost
        for h in p.holdings:
            if h.symbol == symbol:
                total_cost = h.avg_cost * h.shares + cost
                h.shares += shares
                h.avg_cost = round(total_cost / h.shares, 4)
                break
        else:
            p.holdings.append(PortfolioHolding(symbol=symbol, shares=shares, avg_cost=price))
        self._update(p)
        self._save()
        return True

    def sell(self, portfolio_id: str, symbol: str, shares: float, price: float) -> bool:
        p = self.portfolios.get(portfolio_id)
        if not p:
            return False
        for h in p.holdings:
            if h.symbol == symbol:
                if h.shares < shares:
                    return False
                proceeds = shares * price
                p.cash += proceeds
                h.shares -= shares
                if h.shares <= 0:
                    p.holdings.remove(h)
                self._update(p)
                self._save()
                return True
        return False

    def update_prices(self, portfolio_id: str, prices: Dict[str, float]) -> None:
        p = self.portfolios.get(portfolio_id)
        if not p:
            return
        for h in p.holdings:
            if h.symbol in prices:
                h.current_price = prices[h.symbol]
                h.market_value = round(h.shares * h.current_price, 2)
                h.unrealized_pnl = round(h.market_value - h.shares * h.avg_cost, 2)
                h.unrealized_pnl_pct = round(h.unrealized_pnl / (h.shares * h.avg_cost) * 100, 2) if h.avg_cost > 0 else 0.0
        self._update(p)
        self._save()

    def _update(self, p: Portfolio) -> None:
        p.total_value = round(p.cash + sum(h.market_value for h in p.holdings), 2)
        p.total_pnl = round(sum(h.unrealized_pnl for h in p.holdings), 2)
        p.last_updated = datetime.now().isoformat()

    def get_portfolio(self, portfolio_id: str) -> Optional[Portfolio]:
        return self.portfolios.get(portfolio_id)

    def get_allocation(self, portfolio_id: str) -> Dict[str, float]:
        p = self.portfolios.get(portfolio_id)
        if not p or p.total_value <= 0:
            return {}
        return {h.symbol: round(h.market_value / p.total_value, 4) for h in p.holdings}

    def get_stats(self) -> Dict[str, Any]:
        total_value = sum(p.total_value for p in self.portfolios.values())
        return {"portfolios": len(self.portfolios), "total_value": round(total_value, 2)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["PortfolioTracker", "Portfolio", "PortfolioHolding"]