"""
stock_alert_engine_native.py
MAGNATRIX-OS — Stock Alert Engine

Monitor stocks and trigger alerts on price thresholds, signal changes, and news events. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class StockAlert:
    alert_id: str
    symbol: str
    alert_type: str
    condition: str
    threshold: float
    triggered: bool = False
    triggered_at: str = ""
    message: str = ""


class StockAlertEngine:
    """Monitor stocks and trigger alerts."""

    ALERT_TYPES = ["price_above", "price_below", "change_pct_above", "change_pct_below", "volume_spike", "signal"]

    def __init__(self, alerts_dir: str = "./stock_alerts"):
        self.alerts_dir = Path(alerts_dir)
        self.alerts_dir.mkdir(exist_ok=True)
        self.alerts: Dict[str, StockAlert] = {}
        self.history: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        file = self.alerts_dir / "alerts.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for aid, ad in data.items():
                        self.alerts[aid] = StockAlert(**ad)
            except Exception:
                pass
        file2 = self.alerts_dir / "history.json"
        if file2.exists():
            try:
                with open(file2, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.alerts_dir / "alerts.json", "w", encoding="utf-8") as f:
            json.dump({aid: asdict(a) for aid, a in self.alerts.items()}, f, indent=2)
        with open(self.alerts_dir / "history.json", "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2)

    def create_alert(self, alert_id: str, symbol: str, alert_type: str, threshold: float) -> StockAlert:
        alert = StockAlert(
            alert_id=alert_id, symbol=symbol, alert_type=alert_type,
            condition=f"{alert_type} {threshold}", threshold=threshold,
        )
        self.alerts[alert_id] = alert
        self._save()
        return alert

    def check(self, symbol: str, price: float, change_pct: float, volume: int = 0, prev_volume: int = 0) -> List[StockAlert]:
        triggered = []
        for alert in self.alerts.values():
            if alert.symbol != symbol or alert.triggered:
                continue
            fired = False
            msg = ""
            if alert.alert_type == "price_above" and price > alert.threshold:
                fired, msg = True, f"{symbol} price {price} > {alert.threshold}"
            elif alert.alert_type == "price_below" and price < alert.threshold:
                fired, msg = True, f"{symbol} price {price} < {alert.threshold}"
            elif alert.alert_type == "change_pct_above" and change_pct > alert.threshold:
                fired, msg = True, f"{symbol} change {change_pct}% > {alert.threshold}%"
            elif alert.alert_type == "change_pct_below" and change_pct < alert.threshold:
                fired, msg = True, f"{symbol} change {change_pct}% < {alert.threshold}%"
            elif alert.alert_type == "volume_spike" and prev_volume > 0 and volume / prev_volume > alert.threshold:
                fired, msg = True, f"{symbol} volume spike {volume/prev_volume:.1f}x"
            if fired:
                alert.triggered = True
                alert.triggered_at = datetime.now().isoformat()
                alert.message = msg
                self.history.append({"alert_id": alert.alert_id, "symbol": symbol, "message": msg, "time": alert.triggered_at})
                triggered.append(alert)
        self._save()
        return triggered

    def reset_alert(self, alert_id: str) -> bool:
        alert = self.alerts.get(alert_id)
        if alert:
            alert.triggered = False
            alert.triggered_at = ""
            alert.message = ""
            self._save()
            return True
        return False

    def delete_alert(self, alert_id: str) -> bool:
        if alert_id in self.alerts:
            del self.alerts[alert_id]
            self._save()
            return True
        return False

    def get_alerts(self, symbol: Optional[str] = None) -> List[StockAlert]:
        if symbol:
            return [a for a in self.alerts.values() if a.symbol == symbol]
        return list(self.alerts.values())

    def get_stats(self) -> Dict[str, Any]:
        triggered = sum(1 for a in self.alerts.values() if a.triggered)
        return {"total_alerts": len(self.alerts), "triggered": triggered, "history": len(self.history)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["StockAlertEngine", "StockAlert"]