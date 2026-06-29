"""Blockchain Gas Estimator -- Gas calculation, fee market analysis."""
from dataclasses import dataclass
from pathlib import Path
import json, statistics

@dataclass
class GasEstimate:
    tx_type: str = ""
    base_gas: int = 0
    data_gas: int = 0
    priority_fee: int = 0
    total_estimate: int = 0
    confidence: str = "medium"  # low | medium | high

class BlockchainGasEstimator:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._history: list[dict] = []
        self._base_fees: list[int] = []
        self._persist_path = self.root / "blockchain_gas.json"
        self._load()
        if not self._base_fees:
            self._base_fees = [20, 22, 25, 30, 28, 35, 40, 38, 45, 50, 48, 55, 60, 58, 65, 70, 68, 75, 80, 78]

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._history = data.get("history", [])
            self._base_fees = data.get("base_fees", [])

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "history": self._history,
            "base_fees": self._base_fees
        }, indent=2))

    def estimate(self, tx_type: str = "transfer", data_size: int = 0, priority: str = "medium") -> GasEstimate:
        base = {"transfer": 21000, "contract_call": 30000, "contract_deploy": 80000, "token_transfer": 65000}
        base_gas = base.get(tx_type, 21000)
        data_gas = data_size * 16  # 16 gas per byte of data

        # Priority fee based on market conditions
        if self._base_fees:
            median_fee = int(statistics.median(self._base_fees[-20:]))
        else:
            median_fee = 30

        priority_multiplier = {"low": 1.0, "medium": 1.2, "high": 1.5, "urgent": 2.0}
        multiplier = priority_multiplier.get(priority, 1.2)
        priority_fee = int(median_fee * multiplier)

        total = base_gas + data_gas + priority_fee
        estimate = GasEstimate(
            tx_type=tx_type, base_gas=base_gas, data_gas=data_gas,
            priority_fee=priority_fee, total_estimate=total, confidence=priority
        )
        self._history.append({"tx_type": tx_type, "estimate": total, "priority": priority})
        self._save()
        return estimate

    def add_base_fee(self, fee: int) -> None:
        self._base_fees.append(fee)
        self._save()

    def get_market_stats(self) -> dict:
        if not self._base_fees:
            return {"median": 0, "mean": 0, "min": 0, "max": 0}
        recent = self._base_fees[-50:]
        return {
            "median": round(statistics.median(recent), 2),
            "mean": round(statistics.mean(recent), 2),
            "min": min(recent),
            "max": max(recent)
        }

    def to_dict(self) -> dict:
        return {"history_count": len(self._history), "base_fee_samples": len(self._base_fees)}

    def get_stats(self) -> dict:
        by_type = {}
        for h in self._history:
            t = h.get("tx_type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
        return {"estimates": len(self._history), "by_type": by_type, "market": self.get_market_stats()}

__all__ = ["BlockchainGasEstimator", "GasEstimate"]
