#!/usr/bin/env python3
"""prediction_market_native.py — MAGNATRIX-OS Trading Layer
Native Prediction Market Trading Engine (AMATI-PELAJARI-TIRU dari OctagonAI Kalshi Bot).

═══════════════════════════════════════════════════════════════════════════════
Fitur:
  - AI Edge Detection: model probability vs market probability = edge
  - 5-Gate Risk Engine: Kelly, liquidity, spread, category limit, drawdown
  - Half-Kelly Position Sizing dengan liquidity adjustment
  - Deep Research Pipeline: probability estimates, price drivers, catalysts
  - Kalshi-style API Client: RSA-PSS signing, REST, demo/prod env
  - SQLite Caching: cache research results, minimize API calls
  - Multi-Provider LLM: pluggable probability estimation
  - Event Contract Model: YES/NO binary outcome markets

Usage:
    engine = NativePredictionMarketEngine(
        api_key="kalshi_key", private_key="rsa.pem", demo=True
    )
    engine.add_research_provider(octagon_research_fn)

    markets = engine.search_markets("crypto")
    for m in markets:
        edge = engine.compute_edge(m)
        if edge["confidence"] == "very_high":
            kelly = engine.kelly_size(edge["edge"], edge["market_prob"])
            gate = engine.risk_gate(m, kelly)
            if gate["passed"]:
                engine.buy(m["ticker"], kelly["contracts"], kelly["side"])
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import sqlite3
import time
import urllib.request
import urllib.parse
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# Data Model
# ═══════════════════════════════════════════════════════════════════════════════

class Confidence(Enum):
    VERY_HIGH = "very_high"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


@dataclass
class EventContract:
    ticker: str
    event_ticker: str
    title: str
    category: str
    yes_ask: float          # cents (0-100)
    yes_bid: float
    no_ask: float
    no_bid: float
    volume_24h: float
    open_interest: float
    close_time: Optional[float] = None
    status: str = "open"
    tick_size: float = 1.0  # cents

    @property
    def mid_price(self) -> float:
        return (self.yes_bid + self.yes_ask) / 2

    @property
    def spread_cents(self) -> float:
        return self.yes_ask - self.yes_bid

    @property
    def implied_prob(self) -> float:
        return self.mid_price / 100


@dataclass
class EdgeSnapshot:
    ticker: str
    model_prob: float       # AI-estimated probability
    market_prob: float      # current market implied probability
    edge: float             # model_prob - market_prob
    confidence: str
    drivers: List[Dict[str, str]] = field(default_factory=list)
    catalysts: List[str] = field(default_factory=list)
    timestamp: float = 0.0


@dataclass
class KellyResult:
    side: str               # 'yes' or 'no'
    fraction: float         # raw Kelly fraction
    adjusted_fraction: float
    contracts: int
    dollar_amount_cents: float
    entry_price_cents: float
    available_bankroll: float
    skipped_reason: str = ""


@dataclass
class RiskCheck:
    name: str
    passed: bool
    reason: str


@dataclass
class ResearchReport:
    model_prob: float
    drivers: List[Dict[str, str]]
    catalysts: List[str]
    sources: List[str]
    reasoning: str


# ═══════════════════════════════════════════════════════════════════════════════
# SQLite Cache Layer
# ═══════════════════════════════════════════════════════════════════════════════

CACHE_SCHEMA = """
CREATE TABLE IF NOT EXISTS research_cache (
    ticker TEXT PRIMARY KEY,
    model_prob REAL,
    drivers TEXT,       -- JSON
    catalysts TEXT,     -- JSON
    sources TEXT,       -- JSON
    reasoning TEXT,
    fetched_at REAL,
    ttl_seconds REAL DEFAULT 3600
);

CREATE TABLE IF NOT EXISTS edge_cache (
    ticker TEXT PRIMARY KEY,
    model_prob REAL,
    market_prob REAL,
    edge REAL,
    confidence TEXT,
    computed_at REAL,
    ttl_seconds REAL DEFAULT 300
);

CREATE TABLE IF NOT EXISTS trade_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL,
    ticker TEXT,
    side TEXT,
    contracts INTEGER,
    price_cents REAL,
    pnl_cents REAL,
    strategy TEXT,
    reasoning TEXT
);

CREATE INDEX IF NOT EXISTS idx_trade_ticker ON trade_log(ticker);
CREATE INDEX IF NOT EXISTS idx_trade_time ON trade_log(timestamp);
"""


class PredictionMarketCache:
    """SQLite cache for research reports, edge snapshots, and trade history."""

    def __init__(self, db_path: str = "trading/prediction_market_cache.db") -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(CACHE_SCHEMA)
        self._conn.commit()

    def get_research(self, ticker: str) -> Optional[ResearchReport]:
        row = self._conn.execute(
            "SELECT * FROM research_cache WHERE ticker = ?", (ticker,)
        ).fetchone()
        if not row:
            return None
        if time.time() - row["fetched_at"] > row["ttl_seconds"]:
            return None
        return ResearchReport(
            model_prob=row["model_prob"],
            drivers=json.loads(row["drivers"] or "[]"),
            catalysts=json.loads(row["catalysts"] or "[]"),
            sources=json.loads(row["sources"] or "[]"),
            reasoning=row["reasoning"] or "",
        )

    def set_research(self, ticker: str, report: ResearchReport, ttl: float = 3600) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO research_cache
               (ticker, model_prob, drivers, catalysts, sources, reasoning, fetched_at, ttl_seconds)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (ticker, report.model_prob, json.dumps(report.drivers),
             json.dumps(report.catalysts), json.dumps(report.sources),
             report.reasoning, time.time(), ttl)
        )
        self._conn.commit()

    def get_edge(self, ticker: str) -> Optional[EdgeSnapshot]:
        row = self._conn.execute(
            "SELECT * FROM edge_cache WHERE ticker = ?", (ticker,)
        ).fetchone()
        if not row:
            return None
        if time.time() - row["computed_at"] > row["ttl_seconds"]:
            return None
        return EdgeSnapshot(
            ticker=row["ticker"], model_prob=row["model_prob"],
            market_prob=row["market_prob"], edge=row["edge"],
            confidence=row["confidence"],
        )

    def set_edge(self, edge: EdgeSnapshot, ttl: float = 300) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO edge_cache
               (ticker, model_prob, market_prob, edge, confidence, computed_at, ttl_seconds)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (edge.ticker, edge.model_prob, edge.market_prob, edge.edge,
             edge.confidence, time.time(), ttl)
        )
        self._conn.commit()

    def log_trade(self, ticker: str, side: str, contracts: int, price_cents: float,
                  pnl_cents: float = 0.0, strategy: str = "", reasoning: str = "") -> None:
        self._conn.execute(
            """INSERT INTO trade_log (timestamp, ticker, side, contracts, price_cents, pnl_cents, strategy, reasoning)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (time.time(), ticker, side, contracts, price_cents, pnl_cents, strategy, reasoning)
        )
        self._conn.commit()

    def get_trades(self, ticker: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        if ticker:
            rows = self._conn.execute(
                "SELECT * FROM trade_log WHERE ticker = ? ORDER BY timestamp DESC LIMIT ?",
                (ticker, limit)
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM trade_log ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        self._conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Kalshi-style API Client
# ═══════════════════════════════════════════════════════════════════════════════

class KalshiApiClient:
    """Kalshi REST API client with RSA-PSS signing."""

    PROD_URL = "https://api.elections.kalshi.com/trade-api/v2"
    DEMO_URL = "https://demo-api.kalshi.co/trade-api/v2"

    def __init__(self, api_key: str, private_key_path: str, demo: bool = True) -> None:
        self.api_key = api_key
        self.private_key_path = private_key_path
        self.base_url = self.DEMO_URL if demo else self.PROD_URL
        self._private_key: Optional[str] = None

    def _get_key(self) -> str:
        if self._private_key is None:
            with open(self.private_key_path, "r") as f:
                self._private_key = f.read()
        return self._private_key

    def _sign(self, method: str, path: str) -> Tuple[str, str]:
        """Return (timestamp, base64_signature)."""
        ts = str(int(time.time() * 1000))
        message = ts + method.upper() + path
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
            key = serialization.load_pem_private_key(self._get_key().encode(), password=None)
            sig = key.sign(message.encode(), padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32), hashes.SHA256())
            return ts, hashlib.b64encode(sig).decode()
        except ImportError:
            # Fallback: use openssl subprocess
            import subprocess, tempfile
            with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
                f.write(self._get_key())
                f.flush()
                msg_file = f.name + ".msg"
                with open(msg_file, "wb") as m:
                    m.write(message.encode())
                result = subprocess.run(
                    ["openssl", "dgst", "-sha256", "-sign", f.name, "-sigopt", "rsa_padding_mode:pss", "-sigopt", "rsa_pss_saltlen:32", msg_file],
                    capture_output=True,
                )
                os.unlink(msg_file)
                os.unlink(f.name)
                if result.returncode != 0:
                    raise RuntimeError(f"RSA sign failed: {result.stderr.decode()}")
                return ts, hashlib.b64encode(result.stdout).decode()

    def request(self, method: str, path: str, body: Optional[Dict] = None, params: Optional[Dict] = None) -> Any:
        url = self.base_url + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        ts, sig = self.sign(method, path)
        headers = {
            "KALSHI-ACCESS-KEY": self.api_key,
            "KALSHI-ACCESS-TIMESTAMP": ts,
            "KALSHI-ACCESS-SIGNATURE": sig,
            "Content-Type": "application/json",
        }
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body_text = e.read().decode() if hasattr(e, "read") else ""
            raise RuntimeError(f"Kalshi API {e.code}: {body_text}")

    def get_balance(self) -> Dict[str, Any]:
        return self.request("GET", "/portfolio/balance")

    def get_positions(self) -> List[Dict[str, Any]]:
        resp = self.request("GET", "/portfolio/positions")
        return resp.get("market_positions", resp.get("positions", []))

    def get_markets(self, status: str = "open", limit: int = 100) -> List[EventContract]:
        resp = self.request("GET", "/markets", params={"status": status, "limit": limit})
        markets = resp.get("markets", [])
        return [self._to_contract(m) for m in markets]

    def get_market(self, ticker: str) -> EventContract:
        resp = self.request("GET", f"/markets/{ticker}")
        return self._to_contract(resp.get("market", resp))

    def place_order(self, ticker: str, side: str, qty: int, price_cents: float,
                    order_type: str = "limit") -> Dict[str, Any]:
        body = {
            "ticker": ticker,
            "side": side,
            "count": qty,
            "price": price_cents,
            "type": order_type,
        }
        return self.request("POST", "/orders", body=body)

    def _to_contract(self, m: Dict) -> EventContract:
        return EventContract(
            ticker=m.get("ticker", ""),
            event_ticker=m.get("event_ticker", ""),
            title=m.get("title", ""),
            category=m.get("category", ""),
            yes_ask=float(m.get("yes_ask", 0)),
            yes_bid=float(m.get("yes_bid", 0)),
            no_ask=float(m.get("no_ask", 0)),
            no_bid=float(m.get("no_bid", 0)),
            volume_24h=float(m.get("volume_24h", 0)),
            open_interest=float(m.get("open_interest", 0)),
            close_time=m.get("close_time"),
            status=m.get("status", "open"),
            tick_size=float(m.get("tick_size", 1)),
        )

    # Alias for compatibility
    sign = _sign


# ═══════════════════════════════════════════════════════════════════════════════
# AI Research Provider (Pluggable)
# ═══════════════════════════════════════════════════════════════════════════════

class ResearchProvider:
    """Base class for AI probability estimation providers."""

    def estimate(self, contract: EventContract) -> ResearchReport:
        raise NotImplementedError


class MockResearchProvider(ResearchProvider):
    """Mock provider for testing. Returns synthetic probabilities."""

    def estimate(self, contract: EventContract) -> ResearchReport:
        # Synthetic: model slightly more extreme than market
        market_prob = contract.implied_prob
        model_prob = max(0.05, min(0.95, market_prob + random.uniform(-0.1, 0.1)))
        return ResearchReport(
            model_prob=model_prob,
            drivers=[{"claim": "Market sentiment", "impact": "moderate"}],
            catalysts=["Event resolution approaching"],
            sources=["synthetic_mock"],
            reasoning="Synthetic model probability for testing",
        )


class LLMResearchProvider(ResearchProvider):
    """LLM-based probability estimation via callback."""

    def __init__(self, llm_fn: Callable[[str, str], str]) -> None:
        self.llm_fn = llm_fn

    def estimate(self, contract: EventContract) -> ResearchReport:
        system = (
            "You are a prediction market analyst. Estimate the true probability of this event. "
            "Return JSON: {\"model_prob\": 0.65, \"drivers\": [{\"claim\": \"...\", \"impact\": \"high\"}], "
            "\"catalysts\": [\"...\"], \"sources\": [\"...\"], \"reasoning\": \"...\"}"
        )
        user = f"Event: {contract.title}\nTicker: {contract.ticker}\nMarket YES price: {contract.yes_bid}¢ bid / {contract.yes_ask}¢ ask\nCategory: {contract.category}"
        response = self.llm_fn(system, user)
        try:
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                data = json.loads(response[start:end+1])
                return ResearchReport(
                    model_prob=data.get("model_prob", contract.implied_prob),
                    drivers=data.get("drivers", []),
                    catalysts=data.get("catalysts", []),
                    sources=data.get("sources", []),
                    reasoning=data.get("reasoning", ""),
                )
        except Exception:
            pass
        return ResearchReport(
            model_prob=contract.implied_prob,
            drivers=[], catalysts=[], sources=["parse_failed"], reasoning="",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Edge Computer
# ═══════════════════════════════════════════════════════════════════════════════

class EdgeComputer:
    """Compute edge: model probability vs market probability."""

    @staticmethod
    def classify_confidence(abs_edge: float) -> str:
        if abs_edge >= 0.10:
            return Confidence.VERY_HIGH.value
        elif abs_edge >= 0.05:
            return Confidence.HIGH.value
        elif abs_edge >= 0.02:
            return Confidence.MODERATE.value
        return Confidence.LOW.value

    @staticmethod
    def compute(model_prob: float, market_prob: float) -> EdgeSnapshot:
        edge = model_prob - market_prob
        return EdgeSnapshot(
            ticker="", model_prob=model_prob, market_prob=market_prob,
            edge=edge, confidence=EdgeComputer.classify_confidence(abs(edge)),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Kelly Sizing
# ═══════════════════════════════════════════════════════════════════════════════

class KellySizer:
    """Half-Kelly position sizing with liquidity adjustment."""

    def __init__(self, multiplier: float = 0.5, max_position_pct: float = 0.10,
                 min_edge_threshold: float = 0.05) -> None:
        self.multiplier = multiplier
        self.max_position_pct = max_position_pct
        self.min_edge_threshold = min_edge_threshold

    def size(self, edge: float, market_prob: float, bankroll_cents: float,
             contract: Optional[EventContract] = None) -> KellyResult:
        if abs(edge) < self.min_edge_threshold:
            return KellyResult(side="yes", fraction=0, adjusted_fraction=0, contracts=0,
                               dollar_amount_cents=0, entry_price_cents=0,
                               available_bankroll=bankroll_cents,
                               skipped_reason="Edge below threshold")

        side = "yes" if edge > 0 else "no"
        model_prob = market_prob + edge
        model_prob = max(0.01, min(0.99, model_prob))

        # Kelly fraction for binary prediction market
        # f = edge / (1 - market_prob) for YES
        # f = |edge| / market_prob for NO
        if side == "yes":
            raw_f = edge / (1 - market_prob) if (1 - market_prob) > 0 else 0
        else:
            raw_f = abs(edge) / market_prob if market_prob > 0 else 0
        raw_f = max(0, min(raw_f, 1.0))

        adj_f = raw_f * self.multiplier

        # Liquidity adjustment
        liquidity_adj = 1.0
        if contract:
            spread_pct = contract.spread_cents / 100
            if spread_pct > 0.02:
                liquidity_adj *= 0.5
            if contract.volume_24h < 500:
                liquidity_adj *= 0.5
        adj_f *= liquidity_adj

        # Position limit
        max_dollar = bankroll_cents * self.max_position_pct
        dollar_amount = bankroll_cents * adj_f
        dollar_amount = min(dollar_amount, max_dollar)

        # Entry price
        entry_price = contract.yes_ask if side == "yes" else (contract.no_ask if contract else 50)
        if entry_price <= 0:
            entry_price = 50

        contracts = int(dollar_amount / entry_price)
        if contracts < 1:
            return KellyResult(side=side, fraction=raw_f, adjusted_fraction=adj_f,
                               contracts=0, dollar_amount_cents=0, entry_price_cents=entry_price,
                               available_bankroll=bankroll_cents,
                               skipped_reason="Kelly produced < 1 contract")

        return KellyResult(
            side=side, fraction=raw_f, adjusted_fraction=adj_f,
            contracts=contracts, dollar_amount_cents=contracts * entry_price,
            entry_price_cents=entry_price, available_bankroll=bankroll_cents,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 5-Gate Risk Engine
# ═══════════════════════════════════════════════════════════════════════════════

class RiskGate:
    """5-check pre-execution risk gate. All checks must pass."""

    def __init__(self, max_spread_cents: float = 5.0, min_volume_24h: float = 500,
                 max_per_category: int = 3, max_total_positions: int = 10,
                 max_drawdown_pct: float = 0.20, max_position_pct: float = 0.10) -> None:
        self.max_spread_cents = max_spread_cents
        self.min_volume_24h = min_volume_24h
        self.max_per_category = max_per_category
        self.max_total_positions = max_total_positions
        self.max_drawdown_pct = max_drawdown_pct
        self.max_position_pct = max_position_pct

    def check(self, contract: EventContract, kelly: KellyResult,
              positions: List[Dict], drawdown_pct: float) -> Dict[str, Any]:
        checks = []

        # 1. Kelly check
        kelly_max = kelly.available_bankroll * self.max_position_pct
        kelly_passed = kelly.contracts > 0 and kelly.dollar_amount_cents <= kelly_max
        checks.append(RiskCheck(
            name="kelly",
            passed=kelly_passed,
            reason=f"{kelly.contracts} {kelly.side.upper()} contracts, ${kelly.dollar_amount_cents/100:.2f}" if kelly_passed else (kelly.skipped_reason or "Kelly produced 0 contracts"),
        ))

        # 2. Liquidity check
        spread = contract.spread_cents
        spread_ok = spread < self.max_spread_cents
        volume_ok = contract.volume_24h >= self.min_volume_24h
        liquidity_passed = spread_ok and volume_ok
        checks.append(RiskCheck(
            name="liquidity",
            passed=liquidity_passed,
            reason=f"Spread={spread}¢, Vol24h={contract.volume_24h}" if liquidity_passed else f"Spread={spread}¢ (max {self.max_spread_cents}) or Vol={contract.volume_24h} (min {self.min_volume_24h})",
        ))

        # 3. Category concentration
        category_positions = sum(1 for p in positions if p.get("category") == contract.category)
        category_passed = category_positions < self.max_per_category
        checks.append(RiskCheck(
            name="category_limit",
            passed=category_passed,
            reason=f"{category_positions} in {contract.category} (max {self.max_per_category})" if category_passed else f"Category {contract.category} at limit ({category_positions})",
        ))

        # 4. Total positions
        total_passed = len(positions) < self.max_total_positions
        checks.append(RiskCheck(
            name="total_positions",
            passed=total_passed,
            reason=f"{len(positions)} open (max {self.max_total_positions})" if total_passed else f"Max positions reached ({len(positions)})",
        ))

        # 5. Drawdown
        dd_passed = drawdown_pct < self.max_drawdown_pct
        checks.append(RiskCheck(
            name="drawdown",
            passed=dd_passed,
            reason=f"DD={drawdown_pct*100:.1f}% (max {self.max_drawdown_pct*100}%)" if dd_passed else f"Drawdown {drawdown_pct*100:.1f}% exceeds max {self.max_drawdown_pct*100}%",
        ))

        all_passed = all(c.passed for c in checks)
        return {
            "passed": all_passed,
            "checks": [{"name": c.name, "passed": c.passed, "reason": c.reason} for c in checks],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Unified Prediction Market Engine
# ═══════════════════════════════════════════════════════════════════════════════

class NativePredictionMarketEngine:
    """Unified prediction market trading engine."""

    def __init__(self, api_key: str = "", private_key_path: str = "",
                 demo: bool = True, db_path: str = "trading/prediction_market_cache.db") -> None:
        self.api_key = api_key
        self.private_key_path = private_key_path
        self.demo = demo
        self.cache = PredictionMarketCache(db_path)
        self.kelly = KellySizer()
        self.risk = RiskGate()
        self.edge = EdgeComputer()
        self.research_provider: Optional[ResearchProvider] = MockResearchProvider()
        self.client: Optional[KalshiApiClient] = None
        self.positions: List[Dict[str, Any]] = []
        self.drawdown_pct = 0.0

        if api_key and private_key_path:
            self.client = KalshiApiClient(api_key, private_key_path, demo)

    def set_research_provider(self, provider: ResearchProvider) -> None:
        self.research_provider = provider

    def search_markets(self, keyword: str) -> List[EventContract]:
        if self.client:
            return self.client.get_markets()
        # Mock data for testing
        return [
            EventContract(ticker="KXBTC-26DEC-YES", event_ticker="KXBTC-26DEC",
                         title="BTC above $100k by Dec 2026", category="crypto",
                         yes_bid=55, yes_ask=58, no_bid=42, no_ask=45,
                         volume_24h=1200, open_interest=5000),
            EventContract(ticker="KXETH-26DEC-YES", event_ticker="KXETH-26DEC",
                         title="ETH above $5k by Dec 2026", category="crypto",
                         yes_bid=35, yes_ask=38, no_bid=62, no_ask=65,
                         volume_24h=800, open_interest=3000),
        ]

    def compute_edge(self, contract: EventContract) -> Dict[str, Any]:
        # Check cache first
        cached = self.cache.get_edge(contract.ticker)
        if cached:
            return {
                "ticker": cached.ticker, "model_prob": cached.model_prob,
                "market_prob": cached.market_prob, "edge": cached.edge,
                "confidence": cached.confidence, "cached": True,
            }

        # Fetch research
        research = self.cache.get_research(contract.ticker)
        if not research and self.research_provider:
            research = self.research_provider.estimate(contract)
            self.cache.set_research(contract.ticker, research)

        model_prob = research.model_prob if research else contract.implied_prob
        snap = self.edge.compute(model_prob, contract.implied_prob)
        snap.ticker = contract.ticker
        self.cache.set_edge(snap)

        return {
            "ticker": snap.ticker, "model_prob": snap.model_prob,
            "market_prob": snap.market_prob, "edge": snap.edge,
            "confidence": snap.confidence, "drivers": research.drivers if research else [],
            "cached": False,
        }

    def kelly_size(self, edge: float, market_prob: float,
                   bankroll_cents: float = 1000000,
                   contract: Optional[EventContract] = None) -> Dict[str, Any]:
        kelly = self.kelly.size(edge, market_prob, bankroll_cents, contract)
        return {
            "side": kelly.side, "contracts": kelly.contracts,
            "dollar_amount": kelly.dollar_amount_cents / 100,
            "fraction": kelly.adjusted_fraction,
            "entry_price": kelly.entry_price_cents / 100,
            "skipped_reason": kelly.skipped_reason,
        }

    def risk_gate(self, contract: EventContract, kelly_result: Dict[str, Any]) -> Dict[str, Any]:
        kelly = KellyResult(
            side=kelly_result["side"], contracts=kelly_result["contracts"],
            dollar_amount_cents=kelly_result["dollar_amount"] * 100,
            entry_price_cents=kelly_result["entry_price"] * 100,
            available_bankroll=1000000, fraction=0, adjusted_fraction=kelly_result["fraction"],
        )
        return self.risk.check(contract, kelly, self.positions, self.drawdown_pct)

    def buy(self, ticker: str, contracts: int, side: str, price_cents: float = 0) -> Dict[str, Any]:
        if self.client and contracts > 0:
            try:
                result = self.client.place_order(ticker, side, contracts, price_cents)
                self.cache.log_trade(ticker, side, contracts, price_cents, strategy="edge", reasoning="AI edge signal")
                return {"ok": True, "order": result}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        # Paper trade
        self.cache.log_trade(ticker, side, contracts, price_cents, strategy="edge_paper", reasoning="AI edge signal (paper)")
        return {"ok": True, "paper": True, "ticker": ticker, "side": side, "contracts": contracts}

    def scan_for_edges(self, min_confidence: str = "high") -> List[Dict[str, Any]]:
        markets = self.search_markets("")
        results = []
        for m in markets:
            edge = self.compute_edge(m)
            if edge["confidence"] in ("very_high", "high") or (min_confidence == "moderate" and edge["confidence"] == "moderate"):
                kelly = self.kelly_size(edge["edge"], edge["market_prob"], contract=m)
                if kelly["contracts"] > 0:
                    gate = self.risk_gate(m, kelly)
                    results.append({
                        "ticker": m.ticker, "title": m.title,
                        "edge": edge["edge"], "confidence": edge["confidence"],
                        "side": kelly["side"], "contracts": kelly["contracts"],
                        "risk_passed": gate["passed"], "risk_checks": gate["checks"],
                    })
        return results

    def status(self) -> Dict[str, Any]:
        return {
            "demo": self.demo,
            "provider": type(self.research_provider).__name__ if self.research_provider else None,
            "positions": len(self.positions),
            "drawdown_pct": self.drawdown_pct,
            "recent_trades": self.cache.get_trades(limit=5),
        }

    def close(self) -> None:
        self.cache.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Self-test
# ═══════════════════════════════════════════════════════════════════════════════

def _self_test() -> int:
    print("=" * 60)
    print("Native Prediction Market Engine — Self Test")
    print("=" * 60)
    passed = 0
    total = 8

    # Test 1: Edge computation
    print("[Test 1] Edge computation")
    ec = EdgeComputer()
    snap = ec.compute(0.72, 0.58)
    ok = snap.edge == 0.14 and snap.confidence == "very_high"
    print(f"  Edge=0.14, confidence=very_high: {ok} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    # Test 2: Kelly sizing
    print("[Test 2] Kelly sizing")
    ks = KellySizer(multiplier=0.5, max_position_pct=0.10)
    contract = EventContract(ticker="TEST", event_ticker="TEST", title="Test", category="test",
                                yes_bid=55, yes_ask=58, no_bid=42, no_ask=45,
                                volume_24h=1000, open_interest=5000)
    kelly = ks.size(edge=0.10, market_prob=0.58, bankroll_cents=100000, contract=contract)
    ok2 = kelly.contracts > 0 and kelly.side == "yes"
    print(f"  Contracts={kelly.contracts}, side={kelly.side}: {ok2} — {'PASS' if ok2 else 'FAIL'}")
    passed += ok2

    # Test 3: Risk gate
    print("[Test 3] Risk gate")
    rg = RiskGate()
    gate = rg.check(contract, kelly, [], drawdown_pct=0.05)
    ok3 = gate["passed"] and len(gate["checks"]) == 5
    print(f"  Gate passed: {ok3} — {'PASS' if ok3 else 'FAIL'}")
    passed += ok3

    # Test 4: Cache
    print("[Test 4] SQLite cache")
    import tempfile, os
    db_path = tempfile.mktemp(suffix=".db")
    cache = PredictionMarketCache(db_path)
    report = ResearchReport(model_prob=0.75, drivers=[], catalysts=[], sources=["test"], reasoning="")
    cache.set_research("TEST", report)
    cached = cache.get_research("TEST")
    ok4 = cached is not None and cached.model_prob == 0.75
    print(f"  Cache round-trip: {ok4} — {'PASS' if ok4 else 'FAIL'}")
    passed += ok4

    # Test 5: Engine scan
    print("[Test 5] Engine scan")
    engine = NativePredictionMarketEngine(demo=True, db_path=db_path)
    edges = engine.scan_for_edges(min_confidence="moderate")
    ok5 = len(edges) > 0
    print(f"  Found {len(edges)} edges: {ok5} — {'PASS' if ok5 else 'FAIL'}")
    passed += ok5

    # Test 6: Paper trade
    print("[Test 6] Paper trade")
    result = engine.buy("TEST", 5, "yes", 58)
    ok6 = result["ok"] and result.get("paper")
    print(f"  Paper trade OK: {ok6} — {'PASS' if ok6 else 'FAIL'}")
    passed += ok6

    # Test 7: Edge cache
    print("[Test 7] Edge cache")
    edge1 = engine.compute_edge(contract)
    edge2 = engine.compute_edge(contract)
    ok7 = edge2.get("cached") == True
    print(f"  Second call cached: {ok7} — {'PASS' if ok7 else 'FAIL'}")
    passed += ok7

    # Test 8: Status
    print("[Test 8] Status report")
    st = engine.status()
    ok8 = "demo" in st and "positions" in st
    print(f"  Status valid: {ok8} — {'PASS' if ok8 else 'FAIL'}")
    passed += ok8

    cache.close()
    os.unlink(db_path)

    print(f"\nPASS: {passed}/{total}")
    print("=" * 60)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
