"""Quant Arbitrage Detector - Detect mispricings and arbitrage opportunities."""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class ArbitrageOpportunity:
    opportunity_id: str
    type: str  # yield_curve, cross_market, basis, carry
    long_leg: str
    short_leg: str
    expected_profit_bps: float
    confidence: float
    timestamp: float
    detected: bool = True

    def to_dict(self) -> Dict:
        return {
            "opportunity_id": self.opportunity_id,
            "type": self.type,
            "long_leg": self.long_leg,
            "short_leg": self.short_leg,
            "expected_profit_bps": round(self.expected_profit_bps, 2),
            "confidence": round(self.confidence, 3),
            "timestamp": self.timestamp,
            "detected": self.detected,
        }


@dataclass
class Mispricing:
    mispricing_id: str
    instrument: str
    model_price: float
    market_price: float
    deviation_bps: float
    z_score: float
    timestamp: float

    def to_dict(self) -> Dict:
        return {
            "mispricing_id": self.mispricing_id,
            "instrument": self.instrument,
            "model_price": round(self.model_price, 4),
            "market_price": round(self.market_price, 4),
            "deviation_bps": round(self.deviation_bps, 2),
            "z_score": round(self.z_score, 4),
            "timestamp": self.timestamp,
        }


class QuantArbitrageDetector:
    """Detect arbitrage opportunities and mispricings in fixed-income markets."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "quant_arbitrage"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.opportunities: List[ArbitrageOpportunity] = []
        self.mispricings: List[Mispricing] = []
        self._load_state()

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for o in data.get("opportunities", []):
                    self.opportunities.append(ArbitrageOpportunity(**o))
                for m in data.get("mispricings", []):
                    self.mispricings.append(Mispricing(**m))
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {
            "opportunities": [o.to_dict() for o in self.opportunities[-500:]],
            "mispricings": [m.to_dict() for m in self.mispricings[-500:]],
        }
        state_file.write_text(json.dumps(state, indent=2))

    def _nelson_siegel_rate(self, maturity: float, beta0: float, beta1: float, beta2: float, tau: float = 2.5) -> float:
        m = maturity / 12.0
        if m <= 0:
            return beta0
        exp_term = math.exp(-m / tau)
        return beta0 + beta1 * exp_term + beta2 * (m / tau) * exp_term

    def detect_yield_curve_arbitrage(self, rates: Dict[int, float], model_params: Tuple[float, float, float]) -> List[ArbitrageOpportunity]:
        """Detect arbitrage by comparing market rates to model-implied rates."""
        beta0, beta1, beta2 = model_params
        opportunities = []
        for maturity, market_rate in rates.items():
            model_rate = self._nelson_siegel_rate(maturity, beta0, beta1, beta2)
            deviation = market_rate - model_rate
            if abs(deviation) > 0.10:  # > 10 bps deviation
                opp = ArbitrageOpportunity(
                    opportunity_id=f"arb_yc_{maturity}_{int(time.time())}",
                    type="yield_curve",
                    long_leg=f"m{maturity}" if deviation > 0 else "model_synthetic",
                    short_leg=f"model_synthetic" if deviation > 0 else f"m{maturity}",
                    expected_profit_bps=abs(deviation) * 100,
                    confidence=min(1.0, abs(deviation) * 10),
                    timestamp=time.time(),
                )
                opportunities.append(opp)
                self.opportunities.append(opp)
                mis = Mispricing(
                    mispricing_id=f"mis_{maturity}_{int(time.time())}",
                    instrument=f"m{maturity}",
                    model_price=round(model_rate, 4),
                    market_price=round(market_rate, 4),
                    deviation_bps=round(deviation * 100, 2),
                    z_score=round(deviation / 0.15, 4) if deviation != 0 else 0.0,
                    timestamp=time.time(),
                )
                self.mispricings.append(mis)
        self._save_state()
        return opportunities

    def detect_cross_market(self, us_rates: Dict[int, float], eu_rates: Dict[int, float]) -> List[ArbitrageOpportunity]:
        """Detect cross-market arbitrage (US vs EU)."""
        opportunities = []
        common = set(us_rates.keys()) & set(eu_rates.keys())
        for mat in common:
            spread = us_rates[mat] - eu_rates[mat]
            if abs(spread) > 0.50:
                opp = ArbitrageOpportunity(
                    opportunity_id=f"arb_cm_{mat}_{int(time.time())}",
                    type="cross_market",
                    long_leg="eu" if spread > 0 else "us",
                    short_leg="us" if spread > 0 else "eu",
                    expected_profit_bps=abs(spread) * 100,
                    confidence=min(1.0, abs(spread) * 2),
                    timestamp=time.time(),
                )
                opportunities.append(opp)
                self.opportunities.append(opp)
        self._save_state()
        return opportunities

    def detect_carry_trade(self, short_rate: float, long_rate: float, holding_period_months: int = 6) -> Optional[ArbitrageOpportunity]:
        """Detect carry trade opportunities."""
        carry = long_rate - short_rate
        if carry > 0.25:
            opp = ArbitrageOpportunity(
                opportunity_id=f"arb_carry_{int(time.time())}",
                type="carry",
                long_leg=f"long_{long_rate}",
                short_leg=f"short_{short_rate}",
                expected_profit_bps=carry * holding_period_months * 8.33,
                confidence=min(1.0, carry * 4),
                timestamp=time.time(),
            )
            self.opportunities.append(opp)
            self._save_state()
            return opp
        return None

    def get_active_opportunities(self, max_age_sec: float = 3600) -> List[ArbitrageOpportunity]:
        now = time.time()
        return [o for o in self.opportunities if now - o.timestamp < max_age_sec]

    def get_stats(self) -> Dict:
        types = {}
        for o in self.opportunities:
            types[o.type] = types.get(o.type, 0) + 1
        avg_profit = sum(o.expected_profit_bps for o in self.opportunities) / max(1, len(self.opportunities))
        return {
            "opportunities_total": len(self.opportunities),
            "mispricings_total": len(self.mispricings),
            "avg_expected_profit_bps": round(avg_profit, 2),
            "by_type": types,
        }

    def to_dict(self) -> Dict:
        return {
            "opportunities": [o.to_dict() for o in self.opportunities[-100:]],
            "mispricings": [m.to_dict() for m in self.mispricings[-100:]],
            "stats": self.get_stats(),
        }


__all__ = ["QuantArbitrageDetector", "ArbitrageOpportunity", "Mispricing"]
