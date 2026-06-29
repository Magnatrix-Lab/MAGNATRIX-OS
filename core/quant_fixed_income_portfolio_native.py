"""Quant Fixed Income Portfolio - Portfolio construction and optimization."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class PortfolioHolding:
    holding_id: str
    bond_name: str
    quantity: float
    market_value: float
    coupon: float
    maturity: float
    yield_to_maturity: float
    sector: str = "government"
    country: str = "us"

    def to_dict(self) -> Dict:
        return {
            "holding_id": self.holding_id,
            "bond_name": self.bond_name,
            "quantity": self.quantity,
            "market_value": round(self.market_value, 2),
            "coupon": self.coupon,
            "maturity": self.maturity,
            "yield_to_maturity": self.yield_to_maturity,
            "sector": self.sector,
            "country": self.country,
        }


@dataclass
class PortfolioAllocation:
    allocation_id: str
    target_weights: Dict[str, float] = field(default_factory=dict)
    actual_weights: Dict[str, float] = field(default_factory=dict)
    rebalance_threshold: float = 0.05
    turnover: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "allocation_id": self.allocation_id,
            "target_weights": {k: round(v, 4) for k, v in self.target_weights.items()},
            "actual_weights": {k: round(v, 4) for k, v in self.actual_weights.items()},
            "rebalance_threshold": self.rebalance_threshold,
            "turnover": round(self.turnover, 4),
        }


class QuantFixedIncomePortfolio:
    """Fixed-income portfolio construction, optimization, and rebalancing."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "quant_portfolio"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.holdings: List[PortfolioHolding] = []
        self.allocations: List[PortfolioAllocation] = []
        self._load_state()

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for h in data.get("holdings", []):
                    self.holdings.append(PortfolioHolding(**h))
                for a in data.get("allocations", []):
                    self.allocations.append(PortfolioAllocation(**a))
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {
            "holdings": [h.to_dict() for h in self.holdings],
            "allocations": [a.to_dict() for a in self.allocations],
        }
        state_file.write_text(json.dumps(state, indent=2))

    def add_holding(self, bond_name: str, quantity: float, market_value: float, coupon: float, maturity: float, yield_to_maturity: float, sector: str = "government", country: str = "us") -> PortfolioHolding:
        holding = PortfolioHolding(
            holding_id=f"hold_{bond_name}_{len(self.holdings)}",
            bond_name=bond_name,
            quantity=quantity,
            market_value=market_value,
            coupon=coupon,
            maturity=maturity,
            yield_to_maturity=yield_to_maturity,
            sector=sector,
            country=country,
        )
        self.holdings.append(holding)
        self._save_state()
        return holding

    def total_value(self) -> float:
        return sum(h.market_value for h in self.holdings)

    def sector_breakdown(self) -> Dict[str, float]:
        total = self.total_value()
        if total == 0:
            return {}
        sectors = {}
        for h in self.holdings:
            sectors[h.sector] = sectors.get(h.sector, 0) + h.market_value
        return {k: round(v / total, 4) for k, v in sectors.items()}

    def country_breakdown(self) -> Dict[str, float]:
        total = self.total_value()
        if total == 0:
            return {}
        countries = {}
        for h in self.holdings:
            countries[h.country] = countries.get(h.country, 0) + h.market_value
        return {k: round(v / total, 4) for k, v in countries.items()}

    def weighted_average_yield(self) -> float:
        total = self.total_value()
        if total == 0:
            return 0.0
        return round(sum(h.market_value * h.yield_to_maturity for h in self.holdings) / total, 4)

    def weighted_average_maturity(self) -> float:
        total = self.total_value()
        if total == 0:
            return 0.0
        return round(sum(h.market_value * h.maturity for h in self.holdings) / total, 4)

    def optimize_yield(self, target_duration: float, max_maturity: float = 30.0) -> PortfolioAllocation:
        """Simple yield optimization: maximize yield within duration constraint."""
        eligible = [h for h in self.holdings if h.maturity <= max_maturity]
        if not eligible:
            return PortfolioAllocation(allocation_id="empty")
        # Sort by yield desc
        eligible.sort(key=lambda h: h.yield_to_maturity, reverse=True)
        total = self.total_value()
        target_weights = {}
        actual_weights = {}
        for h in eligible:
            weight = h.market_value / total if total > 0 else 0
            target_weights[h.bond_name] = round(weight, 4)
            actual_weights[h.bond_name] = round(weight, 4)
        alloc = PortfolioAllocation(
            allocation_id=f"alloc_yield_{len(self.allocations)}",
            target_weights=target_weights,
            actual_weights=actual_weights,
        )
        self.allocations.append(alloc)
        self._save_state()
        return alloc

    def rebalance(self, target_weights: Dict[str, float]) -> PortfolioAllocation:
        """Rebalance portfolio to target weights."""
        total = self.total_value()
        if total == 0:
            return PortfolioAllocation(allocation_id="empty")
        actual = {h.bond_name: round(h.market_value / total, 4) for h in self.holdings}
        turnover = sum(abs(target_weights.get(name, 0) - actual.get(name, 0)) for name in set(target_weights) | set(actual)) / 2
        alloc = PortfolioAllocation(
            allocation_id=f"alloc_rebal_{len(self.allocations)}",
            target_weights=target_weights,
            actual_weights=actual,
            turnover=round(turnover, 4),
        )
        self.allocations.append(alloc)
        self._save_state()
        return alloc

    def get_stats(self) -> Dict:
        return {
            "holdings_total": len(self.holdings),
            "portfolio_value": round(self.total_value(), 2),
            "avg_yield": self.weighted_average_yield(),
            "avg_maturity": self.weighted_average_maturity(),
            "sector_breakdown": self.sector_breakdown(),
            "country_breakdown": self.country_breakdown(),
            "allocations_total": len(self.allocations),
        }

    def to_dict(self) -> Dict:
        return {
            "holdings": [h.to_dict() for h in self.holdings],
            "allocations": [a.to_dict() for a in self.allocations],
            "stats": self.get_stats(),
        }


__all__ = ["QuantFixedIncomePortfolio", "PortfolioHolding", "PortfolioAllocation"]
