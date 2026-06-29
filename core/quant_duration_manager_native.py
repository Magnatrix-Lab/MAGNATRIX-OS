"""Quant Duration Manager - Duration management and portfolio immunization."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class BondPosition:
    position_id: str
    bond_name: str
    face_value: float
    coupon_rate: float
    maturity_years: float
    yield_to_maturity: float
    price: float = 0.0
    duration: float = 0.0
    convexity: float = 0.0
    weight: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "position_id": self.position_id,
            "bond_name": self.bond_name,
            "face_value": self.face_value,
            "coupon_rate": self.coupon_rate,
            "maturity_years": self.maturity_years,
            "yield_to_maturity": self.yield_to_maturity,
            "price": round(self.price, 4),
            "duration": round(self.duration, 4),
            "convexity": round(self.convexity, 4),
            "weight": round(self.weight, 4),
        }


@dataclass
class DurationTarget:
    target_id: str
    target_duration: float
    target_date: str = ""
    cash_value: float = 0.0
    portfolio_duration: float = 0.0
    hedge_ratio: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "target_id": self.target_id,
            "target_duration": self.target_duration,
            "target_date": self.target_date,
            "cash_value": self.cash_value,
            "portfolio_duration": round(self.portfolio_duration, 4),
            "hedge_ratio": round(self.hedge_ratio, 4),
        }


class QuantDurationManager:
    """Duration management, portfolio immunization, and hedge ratio calculation."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "quant_duration"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.positions: List[BondPosition] = []
        self.targets: List[DurationTarget] = []
        self._load_state()

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for p in data.get("positions", []):
                    self.positions.append(BondPosition(**p))
                for t in data.get("targets", []):
                    self.targets.append(DurationTarget(**t))
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {
            "positions": [p.to_dict() for p in self.positions],
            "targets": [t.to_dict() for t in self.targets],
        }
        state_file.write_text(json.dumps(state, indent=2))

    def _bond_price(self, face_value: float, coupon_rate: float, maturity_years: float, ytm: float, freq: int = 2) -> float:
        """Calculate bond price from YTM."""
        if ytm <= 0:
            return face_value
        coupon = face_value * coupon_rate / freq
        n = int(maturity_years * freq)
        pv_coupons = sum(coupon / ((1 + ytm / freq) ** i) for i in range(1, n + 1))
        pv_face = face_value / ((1 + ytm / freq) ** n)
        return pv_coupons + pv_face

    def _bond_duration(self, face_value: float, coupon_rate: float, maturity_years: float, ytm: float, freq: int = 2) -> float:
        """Calculate Macaulay duration."""
        price = self._bond_price(face_value, coupon_rate, maturity_years, ytm, freq)
        if price <= 0:
            return 0.0
        coupon = face_value * coupon_rate / freq
        n = int(maturity_years * freq)
        weighted_time = sum(i * (coupon / ((1 + ytm / freq) ** i)) for i in range(1, n + 1))
        weighted_time += n * (face_value / ((1 + ytm / freq) ** n))
        return (weighted_time / price) / freq

    def _bond_convexity(self, face_value: float, coupon_rate: float, maturity_years: float, ytm: float, freq: int = 2) -> float:
        """Calculate bond convexity."""
        price = self._bond_price(face_value, coupon_rate, maturity_years, ytm, freq)
        if price <= 0:
            return 0.0
        coupon = face_value * coupon_rate / freq
        n = int(maturity_years * freq)
        y = ytm / freq
        weighted_sq = sum(i * (i + 1) * (coupon / ((1 + y) ** i)) for i in range(1, n + 1))
        weighted_sq += n * (n + 1) * (face_value / ((1 + y) ** n))
        return (weighted_sq / price) / (freq * freq)

    def add_position(self, bond_name: str, face_value: float, coupon_rate: float, maturity_years: float, yield_to_maturity: float) -> BondPosition:
        price = self._bond_price(face_value, coupon_rate, maturity_years, yield_to_maturity)
        duration = self._bond_duration(face_value, coupon_rate, maturity_years, yield_to_maturity)
        convexity = self._bond_convexity(face_value, coupon_rate, maturity_years, yield_to_maturity)
        pos = BondPosition(
            position_id=f"pos_{bond_name}_{len(self.positions)}",
            bond_name=bond_name,
            face_value=face_value,
            coupon_rate=coupon_rate,
            maturity_years=maturity_years,
            yield_to_maturity=yield_to_maturity,
            price=round(price, 4),
            duration=round(duration, 4),
            convexity=round(convexity, 4),
        )
        self.positions.append(pos)
        self._recalc_weights()
        self._save_state()
        return pos

    def _recalc_weights(self) -> None:
        total_value = sum(p.price for p in self.positions)
        if total_value > 0:
            for p in self.positions:
                p.weight = round(p.price / total_value, 4)

    def portfolio_duration(self) -> float:
        """Calculate weighted average portfolio duration."""
        if not self.positions:
            return 0.0
        return sum(p.weight * p.duration for p in self.positions)

    def portfolio_convexity(self) -> float:
        """Calculate weighted average portfolio convexity."""
        if not self.positions:
            return 0.0
        return sum(p.weight * p.convexity for p in self.positions)

    def estimate_pnl(self, yield_change_bps: float) -> float:
        """Estimate P&L from yield change using duration + convexity."""
        dur = self.portfolio_duration()
        conv = self.portfolio_convexity()
        total_value = sum(p.price for p in self.positions)
        dy = yield_change_bps / 10000.0
        # Approximate price change: -D * dy + 0.5 * C * dy^2
        price_change = -dur * dy + 0.5 * conv * dy * dy
        return round(total_value * price_change, 2)

    def immunize(self, target_duration: float, target_date: str = "") -> DurationTarget:
        """Set duration immunization target."""
        current_dur = self.portfolio_duration()
        hedge_ratio = (target_duration - current_dur) / max(1, current_dur) if current_dur > 0 else 0.0
        total_value = sum(p.price for p in self.positions)
        target = DurationTarget(
            target_id=f"imm_{len(self.targets)}",
            target_duration=target_duration,
            target_date=target_date,
            cash_value=round(total_value, 2),
            portfolio_duration=round(current_dur, 4),
            hedge_ratio=round(hedge_ratio, 4),
        )
        self.targets.append(target)
        self._save_state()
        return target

    def rebalance(self, target_duration: float) -> List[BondPosition]:
        """Suggest rebalancing to match target duration."""
        current_dur = self.portfolio_duration()
        if current_dur <= 0:
            return self.positions
        scale = target_duration / current_dur
        for p in self.positions:
            # Adjust by scaling face values
            p.face_value = round(p.face_value * scale, 2)
            p.price = self._bond_price(p.face_value, p.coupon_rate, p.maturity_years, p.yield_to_maturity)
            p.duration = self._bond_duration(p.face_value, p.coupon_rate, p.maturity_years, p.yield_to_maturity)
        self._recalc_weights()
        self._save_state()
        return self.positions

    def get_stats(self) -> Dict:
        return {
            "positions_total": len(self.positions),
            "portfolio_value": round(sum(p.price for p in self.positions), 2),
            "portfolio_duration": round(self.portfolio_duration(), 4),
            "portfolio_convexity": round(self.portfolio_convexity(), 4),
            "immunization_targets": len(self.targets),
        }

    def to_dict(self) -> Dict:
        return {
            "positions": [p.to_dict() for p in self.positions],
            "targets": [t.to_dict() for t in self.targets],
            "stats": self.get_stats(),
        }


__all__ = ["QuantDurationManager", "BondPosition", "DurationTarget"]
