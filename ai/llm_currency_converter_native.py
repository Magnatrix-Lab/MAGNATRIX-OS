"""LLM Currency Converter — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class CurrencyConverter:
    def __init__(self) -> None:
        self._rates: Dict[str, float] = {
            "USD": 1.0, "EUR": 0.92, "GBP": 0.79, "JPY": 149.5, "CNY": 7.2,
            "IDR": 15650.0, "SGD": 1.34, "AUD": 1.53, "CAD": 1.36, "CHF": 0.88,
            "KRW": 1330.0, "INR": 83.3, "THB": 35.5, "MYR": 4.75, "PHP": 55.8,
            "VND": 24300.0, "HKD": 7.82, "NZD": 1.64, "BRL": 4.95, "MXN": 17.2,
        }

    def set_rate(self, currency: str, rate_vs_usd: float) -> None:
        self._rates[currency] = rate_vs_usd

    def convert(self, amount: float, from_currency: str, to_currency: str) -> float:
        if from_currency not in self._rates or to_currency not in self._rates:
            raise ValueError("Currency not supported: " + from_currency + " or " + to_currency)
        usd_amount = amount / self._rates[from_currency]
        return usd_amount * self._rates[to_currency]

    def convert_batch(self, amounts: List[float], from_currency: str, to_currency: str) -> List[float]:
        return [self.convert(a, from_currency, to_currency) for a in amounts]

    def get_cross_rate(self, from_currency: str, to_currency: str) -> float:
        return self._rates[to_currency] / self._rates[from_currency]

    def get_supported_currencies(self) -> List[str]:
        return sorted(self._rates.keys())

    def format_currency(self, amount: float, currency: str, decimals: int = 2) -> str:
        return currency + " " + ("{:." + str(decimals) + "f}").format(amount)

    def get_stats(self) -> Dict[str, Any]:
        return {"currencies": len(self._rates), "base": "USD"}

def run() -> None:
    print("Currency Converter test")
    e = CurrencyConverter()
    print("  100 USD -> EUR: " + str(e.convert(100, "USD", "EUR")))
    print("  1000 USD -> IDR: " + str(e.convert(1000, "USD", "IDR")))
    print("  500 JPY -> USD: " + str(e.convert(500, "JPY", "USD")))
    print("  Cross rate EUR/GBP: " + str(e.get_cross_rate("EUR", "GBP")))
    print("  Batch: " + str(e.convert_batch([10, 20, 30], "USD", "EUR")))
    print("  Formatted: " + e.format_currency(1234.567, "USD"))
    print("  Stats: " + str(e.get_stats()))
    print("Currency Converter test complete.")

if __name__ == "__main__":
    run()
