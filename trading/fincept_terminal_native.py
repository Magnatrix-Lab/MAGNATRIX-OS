"""
FinceptTerminal Native — Pure-Python Bloomberg-Alternative Terminal
====================================================================
A single-file, ~1700-line financial terminal reimplementation.

Sections:
  1. DataHub            (lines ~001–200)
  2. MarketDataEngine   (lines ~200–400)
  3. AnalyticsEngine    (lines ~400–650)
  4. QuantLibBridge     (lines ~650–850)
  5. AIAgentSquad       (lines ~850–1050)
  6. PortfolioManager   (lines ~1050–1200)
  7. TradingCore        (lines ~1200–1350)
  8. TerminalUI         (lines ~1350–1500)
  9. WorkflowEngine     (lines ~1500–1550)
 10. FinceptKernel     (lines ~1550–1700)

CRITICAL CONSTRAINTS
--------------------
- Pure Python idioms. Uses array.array, statistics, dataclasses, typing,
  sqlite3, json, math, random, datetime, urllib.request stdlib.
- NO pandas / numpy as hard dependencies. Optional numpy with
  try/except ImportError fallback to pure Python.
- ALL classes have docstrings, type hints, and __repr__.

Author: Magnatrix-OS subagent
"""

from __future__ import annotations

import array
import bisect
import hashlib
import json
import math
import os
import random
import sqlite3
import statistics
import sys
import threading
import time
import urllib.request
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (
    Any, Callable, Dict, Generic, Iterable, List, Optional,
    Protocol, Sequence, Tuple, TypeVar, Union,
)

# ---------------------------------------------------------------------------
# Optional numpy fallback
# ---------------------------------------------------------------------------
try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    np = None  # type: ignore[assignment]
    _HAS_NUMPY = False


# ===========================================================================
# SECTION 1 — DATAHUB  (lines ~001–200)
# ===========================================================================

class DataConnector(ABC):
    """Abstract base for every market-data connector.

    Subclasses must implement ``fetch()``, ``subscribe()``, and
    ``unsubscribe()``.
    """

    def __init__(self, name: str, rate_limit_per_sec: float = 5.0) -> None:
        self._name: str = name
        self._rate_limit_per_sec: float = rate_limit_per_sec
        self._tokens: float = rate_limit_per_sec
        self._last_ts: float = time.time()
        self._lock: threading.Lock = threading.Lock()

    @property
    def name(self) -> str:
        return self._name

    def _acquire_token(self) -> bool:
        """Token-bucket rate limiter. Returns True if a token was acquired."""
        now = time.time()
        with self._lock:
            elapsed = now - self._last_ts
            self._tokens = min(
                self._rate_limit_per_sec,
                self._tokens + elapsed * self._rate_limit_per_sec,
            )
            self._last_ts = now
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False

    @abstractmethod
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        """Fetch raw data for *symbol* at *interval*."""

    @abstractmethod
    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        """Subscribe to live ticks for *symbol*."""

    @abstractmethod
    def unsubscribe(self, symbol: str) -> None:
        """Unsubscribe from live ticks for *symbol*."""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self._name!r}>"


# ---------------------------------------------------------------------------
# 100+ named connector stubs
# ---------------------------------------------------------------------------

class YahooFinanceConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        if not self._acquire_token():
            raise RuntimeError("Rate limit exceeded")
        return {"source": "yahoo", "symbol": symbol, "interval": interval, "price": 150.0}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class PolygonConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "polygon", "symbol": symbol, "price": 151.0}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class KrakenConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "kraken", "symbol": symbol, "price": 35000.0}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class FREDConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "fred", "symbol": symbol, "value": 4.5}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class IMFConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "imf", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class WorldBankConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "worldbank", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class AlphaVantageConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "alphavantage", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class IEXCloudConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "iex", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class QuandlConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "quandl", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BinanceConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "binance", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class CoinbaseConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "coinbase", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BybitConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "bybit", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class OKXConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "okx", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class KuCoinConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "kucoin", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BitfinexConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "bitfinex", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class GeminiConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "gemini", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BitstampConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "bitstamp", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BittrexConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "bittrex", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class HuobiConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "huobi", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class DeribitConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "deribit", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class OANDAConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "oanda", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class ForexComConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "forexcom", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class ICEDataConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "icedata", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class CMEGroupConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "cme", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class NSEIndiaConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "nseindia", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BSEIndiaConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "bseindia", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class ZerodhaConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "zerodha", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class UpstoxConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "upstox", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class AngelOneConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "angelone", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class 5PaisaConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "5paisa", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class MotilalOswalConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "motilaloswal", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class ICICIDirectConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "icicidirect", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class HDFCSecuritiesConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "hdfcsec", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class KotakSecuritiesConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "kotaksec", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class SBIsecuritiesConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "sbisec", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class SharekhanConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "sharekhan", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class FyersConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "fyers", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class AliceBlueConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "aliceblue", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class SamcoConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "samco", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class TradierConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "tradier", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class WebullConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "webull", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class ETradeConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "etrade", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class RobinhoodConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "robinhood", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class AlpacaConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "alpaca", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class IBKRConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "ibkr", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class TDConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "td", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class MorningstarConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "morningstar", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class FactSetConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "factset", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class RefinitivConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "refinitiv", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class SIXConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "six", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class LSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "lse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class DeutscheBoerseConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "deutscheboerse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class EuronextConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "euronext", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class SGXConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "sgx", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class ASXConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "asx", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class TSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "tse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class HKEXConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "hkex", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class SSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "sse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class SZSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "szse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BSEChinaConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "bsechina", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class MoscowExchangeConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "moex", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BISTConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "bist", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class TADAWULConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "tadawul", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class JPXConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "jpx", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class KRXConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "krx", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BMVConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "bmv", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BovespaConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "bovespa", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class MERVALConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "merval", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class JohannesburgSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "jse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class EgyptSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "egx", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class NigeriaSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "ngx", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class GhanaSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "gse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class KenyaSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "nsekenya", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class MoroccoSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "casablanca", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class TunisiaSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "bvmt", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class ZambiaSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "luse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class UgandaSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "use", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class TanzaniaSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "dse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class RwandaSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "rse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BotswanaSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "bsebotswana", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class NamibiaSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "nsx", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class MalawiSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "mse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class MozambiqueSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "bvm", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BarbadosSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "bsebarbados", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class JamaicaSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "jsejamaica", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class TrinidadTobagoSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "ttse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BahamasSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "bisb", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class EasternCaribbeanSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "ecs", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BermudaSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "bsx", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class CaymanIslandsSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "csd", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class EuronextGrowthConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "euronextgrowth", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BorsaItalianaConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "borsaitaliana", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class WienerBoerseConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "wiener", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BorsaIstanbulConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "borsaistanbul", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class TelAvivSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "tase", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class OsloBorsConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "oslobors", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class NasdaqNordicConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "nasdaqnordic", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class CyprusSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "cse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class MaltaSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "mse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class LjubljanaSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "lse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class ZagrebSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "zse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class RigaSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "nasdaqriga", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class TallinnSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "nasdaqtallinn", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class VilniusSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "nasdaqvilnius", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class AthensSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "athex", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class SofiaSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "bse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BelgradeSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "belex", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class SarajevoSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "sase", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class SkopjeSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "mse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class ChisinauSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "moldova", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class AstanaIFConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "aifc", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class ArmeniaSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "amx", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class GeorgiaSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "gse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class AzerbaijanSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "bse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class UzbekistanSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "uzse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class KyrgyzstanSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "kse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class MongoliaSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "mse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class LaosSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "lse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class CambodiaSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "csx", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class MyanmarSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "ysx", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class NepalSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "nepse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BhutanSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "rsebhutan", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class MaldivesSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "msex", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class SriLankaSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "cse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BangladeshSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "dse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class PakistanSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "psx", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class IranSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "tse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class IraqSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "isx", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class SyriaSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "dse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class LebanonSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "bse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class JordanSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "ase", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class PalestineSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "pex", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class OmanMSConnectConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "msx", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class QatarSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "qse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class KuwaitSEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "boursakuwait", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BahrainBourseConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "bahrainbourse", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class UAEADSMConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "adsm", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class DFMConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "dfm", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class NSEIFSCConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "nseifsc", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class IndiaINXConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "indiainx", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class MCXIndiaConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "mcx", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class NCDEXConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "ncdex", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class ICEXConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "icex", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class CDSLConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "cdsl", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class NSDLConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "nsdl", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class SEBIConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "sebi", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class ReserveBankIndiaConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "rbi", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class USFedConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "fed", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class ECBConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "ecb", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BOEConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "boe", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BOJConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "boj", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class PBOCConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "pboc", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class SNBConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "snb", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class RiksbankConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "riksbank", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class NorgesBankConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "norgesbank", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BankOfCanadaConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "bankofcanada", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class RBAConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "rba", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class RBNZConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "rbnz", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BCBConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "bcb", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BancoDeMexicoConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "banxico", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class SouthAfricaReserveBankConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "sarb", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class CentralBankOfEgyptConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "cbe", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class CentralBankOfNigeriaConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "cbn", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BankOfGhanaConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "bog", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BankOfTanzaniaConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "bot", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BankOfUgandaConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "bou", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


class BankOfZambiaConnector(DataConnector):
    def fetch(self, symbol: str, interval: str = "1d") -> Any:
        self._acquire_token()
        return {"source": "boz", "symbol": symbol}

    def subscribe(self, symbol: str, callback: Callable[[Any], None]) -> None:
        pass

    def unsubscribe(self, symbol: str) -> None:
        pass


# ---------------------------------------------------------------------------
# DataHub — unified query layer + SQLite cache + failover
# ---------------------------------------------------------------------------

class DataHub:
    """Central market-data gateway.

    Provides:
    - Connector registry (100+ named sources)
    - Unified ``query(source, symbol, interval)`` API
    - SQLite-backed cache with TTL
    - Failover: primary → secondary
    """

    def __init__(self, db_path: str = ":memory:", default_ttl_sec: int = 300) -> None:
        self._registry: Dict[str, DataConnector] = {}
        self._db_path: str = db_path
        self._default_ttl_sec: int = default_ttl_sec
        self._init_db()
        self._register_defaults()

    # -- internal -----------------------------------------------------------

    def _init_db(self) -> None:
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                payload TEXT,
                ts REAL
            )
            """
        )
        self._conn.commit()

    def _register_defaults(self) -> None:
        defaults: Dict[str, type[DataConnector]] = {
            "yahoo": YahooFinanceConnector,
            "polygon": PolygonConnector,
            "kraken": KrakenConnector,
            "fred": FREDConnector,
            "imf": IMFConnector,
            "worldbank": WorldBankConnector,
            "alphavantage": AlphaVantageConnector,
            "iex": IEXCloudConnector,
            "quandl": QuandlConnector,
            "binance": BinanceConnector,
            "coinbase": CoinbaseConnector,
            "bybit": BybitConnector,
            "okx": OKXConnector,
            "kucoin": KuCoinConnector,
            "bitfinex": BitfinexConnector,
            "gemini": GeminiConnector,
            "bitstamp": BitstampConnector,
            "bittrex": BittrexConnector,
            "huobi": HuobiConnector,
            "deribit": DeribitConnector,
            "oanda": OANDAConnector,
            "forexcom": ForexComConnector,
            "icedata": ICEDataConnector,
            "cme": CMEGroupConnector,
            "nseindia": NSEIndiaConnector,
            "bseindia": BSEIndiaConnector,
            "zerodha": ZerodhaConnector,
            "upstox": UpstoxConnector,
            "angelone": AngelOneConnector,
            "5paisa": FiversPaisaConnector,
            "motilaloswal": MotilalOswalConnector,
            "icicidirect": ICICIDirectConnector,
            "hdfcsec": HDFCSecuritiesConnector,
            "kotaksec": KotakSecuritiesConnector,
            "sbisec": SBIsecuritiesConnector,
            "sharekhan": SharekhanConnector,
            "fyers": FyersConnector,
            "aliceblue": AliceBlueConnector,
            "samco": SamcoConnector,
            "tradier": TradierConnector,
            "webull": WebullConnector,
            "etrade": ETradeConnector,
            "robinhood": RobinhoodConnector,
            "alpaca": AlpacaConnector,
            "ibkr": IBKRConnector,
            "td": TDConnector,
            "morningstar": MorningstarConnector,
            "factset": FactSetConnector,
            "refinitiv": RefinitivConnector,
            "six": SIXConnector,
            "lse": LSEConnector,
            "deutscheboerse": DeutscheBoerseConnector,
            "euronext": EuronextConnector,
            "sgx": SGXConnector,
            "asx": ASXConnector,
            "tse": TSEConnector,
            "hkex": HKEXConnector,
            "sse": SSEConnector,
            "szse": SZSEConnector,
            "bsechina": BSEChinaConnector,
            "moex": MoscowExchangeConnector,
            "bist": BISTConnector,
            "tadawul": TADAWULConnector,
            "jpx": JPXConnector,
            "krx": KRXConnector,
            "bmv": BMVConnector,
            "bovespa": BovespaConnector,
            "merval": MERVALConnector,
            "jse": JohannesburgSEConnector,
            "egx": EgyptSEConnector,
            "ngx": NigeriaSEConnector,
            "gse": GhanaSEConnector,
            "nsekenya": KenyaSEConnector,
            "casablanca": MoroccoSEConnector,
            "bvmt": TunisiaSEConnector,
            "luse": ZambiaSEConnector,
            "use": UgandaSEConnector,
            "dse": DSEConnector,
            "rse": RwandaSEConnector,
            "bsebotswana": BotswanaSEConnector,
            "nsx": NamibiaSEConnector,
            "mse": MalawiSEConnector,
            "bvm": MozambiqueSEConnector,
            "bsebarbados": BarbadosSEConnector,
            "jsejamaica": JamaicaSEConnector,
            "ttse": TrinidadTobagoSEConnector,
            "bisb": BahamasSEConnector,
            "ecs": EasternCaribbeanSEConnector,
            "bsx": BermudaSEConnector,
            "csd": CaymanIslandsSEConnector,
            "euronextgrowth": EuronextGrowthConnector,
            "borsaitaliana": BorsaItalianaConnector,
            "wiener": WienerBoerseConnector,
            "borsaistanbul": BorsaIstanbulConnector,
            "tase": TelAvivSEConnector,
            "oslobors": OsloBorsConnector,
            "nasdaqnordic": NasdaqNordicConnector,
            "cse": CyprusSEConnector,
            "mse": MaltaSEConnector,
            "ljubljana": LjubljanaSEConnector,
            "zagreb": ZagrebSEConnector,
            "nasdaqriga": RigaSEConnector,
            "nasdaqtallinn": TallinnSEConnector,
            "nasdaqvilnius": VilniusSEConnector,
            "athex": AthensSEConnector,
            "sofia": SofiaSEConnector,
            "belex": BelgradeSEConnector,
            "sase": SarajevoSEConnector,
            "skopje": SkopjeSEConnector,
            "chisinau": ChisinauSEConnector,
            "aifc": AstanaIFConnector,
            "amx": ArmeniaSEConnector,
            "gse": GeorgiaSEConnector,
            "baku": AzerbaijanSEConnector,
            "uzse": UzbekistanSEConnector,
            "kse": KyrgyzstanSEConnector,
            "mongolia": MongoliaSEConnector,
            "lao": LaosSEConnector,
            "csx": CambodiaSEConnector,
            "ysx": MyanmarSEConnector,
            "nepse": NepalSEConnector,
            "bhutan": BhutanSEConnector,
            "maldives": MaldivesSEConnector,
            "srilanka": SriLankaSEConnector,
            "bangladesh": BangladeshSEConnector,
            "psx": PakistanSEConnector,
            "tseiran": IranSEConnector,
            "isx": IraqSEConnector,
            "dsesyr": SyriaSEConnector,
            "bselebanon": LebanonSEConnector,
            "ase": JordanSEConnector,
            "pex": PalestineSEConnector,
            "msx": OmanMSConnectConnector,
            "qse": QatarSEConnector,
            "boursakuwait": KuwaitSEConnector,
            "bahrain": BahrainBourseConnector,
            "adsm": UAEADSMConnector,
            "dfm": DFMConnector,
            "nseifsc": NSEIFSCConnector,
            "indiainx": IndiaINXConnector,
            "mcx": MCXIndiaConnector,
            "ncdex": NCDEXConnector,
            "icex": ICEXConnector,
            "cdsl": CDSLConnector,
            "nsdl": NSDLConnector,
            "sebi": SEBIConnector,
            "rbi": ReserveBankIndiaConnector,
            "fed": USFedConnector,
            "ecb": ECBConnector,
            "boe": BOEConnector,
            "boj": BOJConnector,
            "pboc": PBOCConnector,
            "snb": SNBConnector,
            "riksbank": RiksbankConnector,
            "norgesbank": NorgesBankConnector,
            "bankofcanada": BankOfCanadaConnector,
            "rba": RBAConnector,
            "rbnz": RBNZConnector,
            "bcb": BCBConnector,
            "banxico": BancoDeMexicoConnector,
            "sarb": SouthAfricaReserveBankConnector,
            "cbe": CentralBankOfEgyptConnector,
            "cbn": CentralBankOfNigeriaConnector,
            "bog": BankOfGhanaConnector,
            "bot": BankOfTanzaniaConnector,
            "bou": BankOfUgandaConnector,
            "boz": BankOfZambiaConnector,
        }
        for k, cls in defaults.items():
            self.register(k, cls(k))

    # -- public API ---------------------------------------------------------

    def register(self, name: str, connector: DataConnector) -> None:
        """Register a connector under *name*."""
        self._registry[name] = connector

    def unregister(self, name: str) -> None:
        """Remove a connector from the registry."""
        self._registry.pop(name, None)

    def _cache_key(self, source: str, symbol: str, interval: str) -> str:
        return hashlib.sha256(f"{source}:{symbol}:{interval}".encode()).hexdigest()

    def _get_cache(self, key: str) -> Optional[Any]:
        cur = self._conn.execute(
            "SELECT payload, ts FROM cache WHERE key = ?", (key,)
        )
        row = cur.fetchone()
        if row is None:
            return None
        payload, ts = row
        if time.time() - ts > self._default_ttl_sec:
            return None
        return json.loads(payload)

    def _set_cache(self, key: str, value: Any) -> None:
        payload = json.dumps(value)
        self._conn.execute(
            "INSERT OR REPLACE INTO cache (key, payload, ts) VALUES (?, ?, ?)",
            (key, payload, time.time()),
        )
        self._conn.commit()

    def query(
        self,
        source: str,
        symbol: str,
        interval: str = "1d",
        fallback: Optional[str] = None,
    ) -> Any:
        """Query *source* for *symbol*.

        If the primary source fails and *fallback* is given, the fallback
        connector is tried automatically.
        """
        key = self._cache_key(source, symbol, interval)
        cached = self._get_cache(key)
        if cached is not None:
            return cached

        primary = self._registry.get(source)
        if primary is None:
            if fallback:
                return self.query(fallback, symbol, interval)
            raise KeyError(f"Unknown source {source!r}")

        try:
            result = primary.fetch(symbol, interval)
        except Exception:
            if fallback:
                return self.query(fallback, symbol, interval)
            raise

        self._set_cache(key, result)
        return result

    def connectors(self) -> List[str]:
        """Return a sorted list of registered connector names."""
        return sorted(self._registry.keys())

    def __repr__(self) -> str:
        return f"<DataHub connectors={len(self._registry)} db={self._db_path!r}>"


# ===========================================================================
# SECTION 2 — MARKETDATAENGINE  (lines ~200–400)
# ===========================================================================

class AssetClass(Enum):
    EQUITY = auto()
    CRYPTO = auto()
    FOREX = auto()
    COMMODITY = auto()
    FIXED_INCOME = auto()


@dataclass(frozen=True)
class Tick:
    """A single market tick."""
    symbol: str
    price: float
    volume: float
    ts: datetime
    bid: float = 0.0
    ask: float = 0.0

    def __repr__(self) -> str:
        return (
            f"Tick({self.symbol!r}, {self.price:.4f}, vol={self.volume}, "
            f"ts={self.ts.isoformat()})"
        )


@dataclass
class OHLCVBar:
    """An OHLCV bar aggregated over an interval."""
    symbol: str
    open_: float
    high: float
    low: float
    close: float
    volume: float
    ts: datetime
    interval: str = "1m"

    def __repr__(self) -> str:
        return (
            f"OHLCVBar({self.symbol!r} O={self.open_:.4f} H={self.high:.4f} "
            f"L={self.low:.4f} C={self.close:.4f} V={self.volume} "
            f"[{self.interval}] @ {self.ts.isoformat()})"
        )


class OHLCVBuilder:
    """Builds OHLCV bars from a tick stream using a configurable interval."""

    def __init__(self, symbol: str, interval_sec: int = 60) -> None:
        self._symbol: str = symbol
        self._interval_sec: int = interval_sec
        self._current_bar: Optional[OHLCVBar] = None
        self._bars: List[OHLCVBar] = []

    def ingest(self, tick: Tick) -> Optional[OHLCVBar]:
        """Ingest a tick; returns a completed bar when the interval closes."""
        epoch = tick.ts.timestamp()
        bucket = epoch - (epoch % self._interval_sec)
        bar_ts = datetime.fromtimestamp(bucket)

        if self._current_bar is None or self._current_bar.ts != bar_ts:
            if self._current_bar is not None:
                self._bars.append(self._current_bar)
            self._current_bar = OHLCVBar(
                symbol=self._symbol,
                open_=tick.price,
                high=tick.price,
                low=tick.price,
                close=tick.price,
                volume=tick.volume,
                ts=bar_ts,
                interval=f"{self._interval_sec}s",
            )
            return self._bars[-1] if self._bars else None

        bar = self._current_bar
        bar.high = max(bar.high, tick.price)
        bar.low = min(bar.low, tick.price)
        bar.close = tick.price
        bar.volume += tick.volume
        return None

    def bars(self) -> List[OHLCVBar]:
        """Return all completed bars."""
        return self._bars.copy()

    def __repr__(self) -> str:
        return f"<OHLCVBuilder symbol={self._symbol!r} bars={len(self._bars)}>"


class OrderBook:
    """L2/L3 order-book with bid/ask, spread, depth, mid-price."""

    def __init__(self, symbol: str) -> None:
        self._symbol: str = symbol
        self._bids: List[Tuple[float, float]] = []  # (price, qty)
        self._asks: List[Tuple[float, float]] = []

    def update_bids(self, levels: List[Tuple[float, float]]) -> None:
        """Replace the bid side with *levels*."""
        self._bids = sorted(levels, key=lambda x: x[0], reverse=True)

    def update_asks(self, levels: List[Tuple[float, float]]) -> None:
        """Replace the ask side with *levels*."""
        self._asks = sorted(levels, key=lambda x: x[0])

    def best_bid(self) -> Optional[Tuple[float, float]]:
        return self._bids[0] if self._bids else None

    def best_ask(self) -> Optional[Tuple[float, float]]:
        return self._asks[0] if self._asks else None

    def spread(self) -> Optional[float]:
        bb = self.best_bid()
        ba = self.best_ask()
        if bb and ba:
            return ba[0] - bb[0]
        return None

    def mid_price(self) -> Optional[float]:
        bb = self.best_bid()
        ba = self.best_ask()
        if bb and ba:
            return (bb[0] + ba[0]) / 2.0
        return None

    def depth(self) -> Tuple[float, float]:
        """Return (total_bid_qty, total_ask_qty)."""
        bid_qty = sum(q for _, q in self._bids)
        ask_qty = sum(q for _, q in self._asks)
        return bid_qty, ask_qty

    def __repr__(self) -> str:
        return (
            f"<OrderBook {self._symbol!r} bids={len(self._bids)} "
            f"asks={len(self._asks)}>"
        )


class TimeSeriesIndex:
    """Immutable-ish index backed by sorted timestamps with binary search."""

    def __init__(self, timestamps: Sequence[datetime]) -> None:
        self._timestamps: List[datetime] = list(timestamps)

    def _to_epoch(self, dt: datetime) -> float:
        return dt.timestamp()

    def locate(self, dt: datetime) -> int:
        """Return the index of *dt* or the insertion point via bisect."""
        epochs = [t.timestamp() for t in self._timestamps]
        target = dt.timestamp()
        return bisect.bisect_left(epochs, target)

    def slice(self, start: datetime, end: datetime) -> List[int]:
        """Return indices whose timestamps fall in [start, end)."""
        epochs = [t.timestamp() for t in self._timestamps]
        s = bisect.bisect_left(epochs, start.timestamp())
        e = bisect.bisect_left(epochs, end.timestamp())
        return list(range(s, e))

    def __repr__(self) -> str:
        return f"<TimeSeriesIndex size={len(self._timestamps)}>"


class GapDetector:
    """Detects missing intervals in a time series."""

    def __init__(self, interval_sec: int = 60) -> None:
        self._interval_sec: int = interval_sec

    def detect(self, timestamps: Sequence[datetime]) -> List[Tuple[datetime, datetime]]:
        """Return a list of (start, end) gaps."""
        if len(timestamps) < 2:
            return []
        gaps: List[Tuple[datetime, datetime]] = []
        for i in range(1, len(timestamps)):
            diff = (timestamps[i] - timestamps[i - 1]).total_seconds()
            if diff > self._interval_sec * 1.5:
                gaps.append((timestamps[i - 1], timestamps[i]))
        return gaps

    def __repr__(self) -> str:
        return f"<GapDetector interval={self._interval_sec}s>"


class RollupEngine:
    """Resample 1-min bars into 5-min, 1-hour, 1-day via pure Python."""

    RATIOS: Dict[str, int] = {"5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}

    def __init__(self, bars: List[OHLCVBar]) -> None:
        self._bars: List[OHLCVBar] = bars

    def rollup(self, target: str) -> List[OHLCVBar]:
        """Roll up to *target* interval."""
        ratio = self.RATIOS.get(target, 1)
        if ratio == 1 or not self._bars:
            return self._bars.copy()

        out: List[OHLCVBar] = []
        chunk: List[OHLCVBar] = []
        for bar in self._bars:
            chunk.append(bar)
            if len(chunk) >= ratio:
                out.append(self._aggregate(chunk, target))
                chunk = []
        if chunk:
            out.append(self._aggregate(chunk, target))
        return out

    @staticmethod
    def _aggregate(chunk: List[OHLCVBar], interval: str) -> OHLCVBar:
        return OHLCVBar(
            symbol=chunk[0].symbol,
            open_=chunk[0].open_,
            high=max(b.high for b in chunk),
            low=min(b.low for b in chunk),
            close=chunk[-1].close,
            volume=sum(b.volume for b in chunk),
            ts=chunk[0].ts,
            interval=interval,
        )

    def __repr__(self) -> str:
        return f"<RollupEngine bars={len(self._bars)}>"


