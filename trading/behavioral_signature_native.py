#!/usr/bin/env python3
"""behavioral_signature_native.py — MAGNATRIX-OS Trading Layer
Behavioral Signature Analysis & Opponent Detection.

Pattern: AMATI-PELAJARI-TIRU dari screenshot "Behavioral Signature" (Meridian-A Capital analysis).

Features:
  - Entry Lag Detection: detect if trader enters 72h after analyst coverage
  - Consensus Chasing: detect if trader follows post-poll consensus
  - Position Overlap Analysis: detect when opponent is on same/opposite side
  - Opposite Side Detection: "we are on opposite side of 7 of 9 open positions"
  - Win/Late Pattern: track W/L ratio, avg entry, avg close
  - Behavioral Clustering: group traders by behavioral patterns
  - Whale Detection: detect large positions that move market

Usage:
    sig = NativeBehavioralSignature()
    sig.add_trader("Meridian-A", trades=meridian_trades)
    sig.analyze("Meridian-A")
    # Detect if we are on opposite side
    overlap = sig.detect_overlap("Meridian-A", my_positions)
    print(f"Opposite side: {overlap['opposite_count']} / {overlap['total_common']}")
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


# ══════════════════════════════════════════════════════════════════════════════
# Data Model
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class TraderTrade:
    ticker: str
    side: str
    entry_price: float
    exit_price: float
    entry_time: float
    exit_time: float
    size: float
    pnl: float
    source: str = ""  # e.g., "analyst_coverage", "consensus", "independent"


@dataclass
class BehavioralProfile:
    trader_id: str
    total_trades: int
    win_rate: float
    avg_entry: float
    avg_close: float
    avg_hold_time: float
    entry_lag_hours: float
    consensus_chase_pct: float
    opposite_side_pct: float
    worst_position: float
    overlap_count: int
    behavioral_tags: List[str] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════════════
# Behavioral Signature Analyzer
# ══════════════════════════════════════════════════════════════════════════════

class NativeBehavioralSignature:
    """Analyze opponent trader behavior and detect patterns."""

    def __init__(self) -> None:
        self._traders: Dict[str, List[TraderTrade]] = {}
        self._profiles: Dict[str, BehavioralProfile] = {}
        self._analyst_coverage: Dict[str, float] = {}  # ticker → coverage_time

    def add_analyst_coverage(self, ticker: str, coverage_time: float) -> None:
        self._analyst_coverage[ticker] = coverage_time

    def add_trader(self, trader_id: str, trades: List[TraderTrade]) -> None:
        self._traders[trader_id] = trades

    def analyze(self, trader_id: str) -> BehavioralProfile:
        trades = self._traders.get(trader_id, [])
        if not trades:
            return BehavioralProfile(trader_id=trader_id, total_trades=0, win_rate=0,
                                     avg_entry=0, avg_close=0, avg_hold_time=0,
                                     entry_lag_hours=0, consensus_chase_pct=0,
                                     opposite_side_pct=0, worst_position=0, overlap_count=0)

        wins = [t for t in trades if t.pnl > 0]
        win_rate = len(wins) / len(trades) if trades else 0

        avg_entry = sum(t.entry_price for t in trades) / len(trades)
        avg_close = sum(t.exit_price for t in trades if t.exit_price > 0) / max(1, sum(1 for t in trades if t.exit_price > 0))
        avg_hold = sum(t.exit_time - t.entry_time for t in trades if t.exit_time > 0) / max(1, sum(1 for t in trades if t.exit_time > 0))

        # Entry lag: time between analyst coverage and entry
        lags = []
        for t in trades:
            cov_time = self._analyst_coverage.get(t.ticker)
            if cov_time and t.entry_time > cov_time:
                lags.append((t.entry_time - cov_time) / 3600)  # hours
        entry_lag = sum(lags) / len(lags) if lags else 0

        # Consensus chase: trades that follow majority direction
        consensus_chase = sum(1 for t in trades if t.source == "consensus") / len(trades) if trades else 0

        # Worst position
        worst = min((t.pnl for t in trades), default=0)

        # Tags
        tags = []
        if entry_lag > 48:
            tags.append("late_entry")
        if entry_lag > 72:
            tags.append("lags_analyst_coverage_by_72h")
        if consensus_chase > 0.5:
            tags.append("consensus_chaser")
        if win_rate < 0.35:
            tags.append("poor_performer")
        if worst < -10000:
            tags.append("large_loss_taker")

        profile = BehavioralProfile(
            trader_id=trader_id, total_trades=len(trades), win_rate=win_rate,
            avg_entry=avg_entry, avg_close=avg_close, avg_hold_time=avg_hold,
            entry_lag_hours=entry_lag, consensus_chase_pct=consensus_chase,
            opposite_side_pct=0, worst_position=worst,
            overlap_count=0, behavioral_tags=tags,
        )
        self._profiles[trader_id] = profile
        return profile

    def detect_overlap(self, trader_id: str, my_positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect how many positions we share with trader, and on which side."""
        their_trades = self._traders.get(trader_id, [])
        their_tickers = {t.ticker: t.side for t in their_trades}
        my_tickers = {p["ticker"]: p["side"] for p in my_positions}

        common = set(their_tickers.keys()) & set(my_tickers.keys())
        same_side = sum(1 for t in common if their_tickers[t] == my_tickers[t])
        opposite_side = sum(1 for t in common if their_tickers[t] != my_tickers[t])

        return {
            "trader_id": trader_id,
            "total_common": len(common),
            "same_side": same_side,
            "opposite_side": opposite_side,
            "opposite_pct": opposite_side / len(common) if common else 0,
            "their_only": [t for t in their_tickers if t not in my_tickers],
            "my_only": [t for t in my_tickers if t not in their_tickers],
        }

    def cluster_traders(self) -> Dict[str, List[str]]:
        """Group traders by behavioral tags."""
        clusters: Dict[str, List[str]] = {}
        for tid, profile in self._profiles.items():
            for tag in profile.behavioral_tags:
                clusters.setdefault(tag, []).append(tid)
        return clusters

    def whale_detection(self, trader_id: str, threshold: float = 100000.0) -> List[Dict[str, Any]]:
        """Detect large positions from a trader."""
        trades = self._traders.get(trader_id, [])
        whales = []
        for t in trades:
            if t.size >= threshold:
                whales.append({
                    "ticker": t.ticker, "side": t.side, "size": t.size,
                    "entry_price": t.entry_price, "entry_time": t.entry_time,
                })
        return whales

    def compare_all(self, my_positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compare all known traders against my positions."""
        results = []
        for tid in self._traders:
            overlap = self.detect_overlap(tid, my_positions)
            profile = self._profiles.get(tid)
            results.append({
                "trader_id": tid,
                "overlap": overlap,
                "profile": {
                    "win_rate": profile.win_rate if profile else 0,
                    "tags": profile.behavioral_tags if profile else [],
                } if profile else None,
            })
        return results

    def status(self) -> Dict[str, Any]:
        return {
            "traders": len(self._traders),
            "profiles": len(self._profiles),
            "clusters": {tag: len(traders) for tag, traders in self.cluster_traders().items()},
        }


# ══════════════════════════════════════════════════════════════════════════════
# Self-test
# ══════════════════════════════════════════════════════════════════════════════

def _self_test() -> int:
    print("=" * 60)
    print("Native Behavioral Signature — Self Test")
    print("=" * 60)
    passed = 0
    total = 7

    sig = NativeBehavioralSignature()

    # Setup analyst coverage
    sig.add_analyst_coverage("BTC-UP", 1000000.0)
    sig.add_analyst_coverage("ETH-UP", 1000100.0)

    # Test 1: Add trader
    print("[Test 1] Add trader trades")
    trades = [
        TraderTrade("BTC-UP", "YES", 0.55, 0.89, 1000800.0, 1003600.0, 50000, 15000, "consensus"),
        TraderTrade("ETH-UP", "YES", 0.35, 0.72, 1001000.0, 1004000.0, 30000, 8000, "consensus"),
        TraderTrade("BTC-UP", "NO", 0.45, 0.20, 1002000.0, 1005000.0, 20000, -20000, "independent"),
    ]
    sig.add_trader("Meridian-A", trades)
    ok = len(sig._traders) == 1
    print(f"  1 trader added: {ok} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    # Test 2: Analyze profile
    print("[Test 2] Analyze profile")
    profile = sig.analyze("Meridian-A")
    ok2 = profile.total_trades == 3 and profile.win_rate > 0
    print(f"  Trades={profile.total_trades}, win_rate={profile.win_rate:.2%}: {ok2} — {'PASS' if ok2 else 'FAIL'}")
    passed += ok2

    # Test 3: Entry lag detection
    print("[Test 3] Entry lag detection")
    ok3 = profile.entry_lag_hours > 0
    print(f"  Entry lag: {profile.entry_lag_hours:.1f}h — {'PASS' if ok3 else 'FAIL'}")
    passed += ok3

    # Test 4: Consensus chase
    print("[Test 4] Consensus chase detection")
    ok4 = profile.consensus_chase_pct > 0.5
    print(f"  Consensus chase: {profile.consensus_chase_pct:.2%}: {ok4} — {'PASS' if ok4 else 'FAIL'}")
    passed += ok4

    # Test 5: Overlap detection
    print("[Test 5] Overlap detection")
    my_positions = [
        {"ticker": "BTC-UP", "side": "YES"},
        {"ticker": "ETH-UP", "side": "NO"},
    ]
    overlap = sig.detect_overlap("Meridian-A", my_positions)
    ok5 = overlap["total_common"] == 2 and overlap["opposite_side"] == 2  # Meridian's last BTC trade is NO, opposite to our YES
    print(f"  Common={overlap['total_common']}, opposite={overlap['opposite_side']}: {ok5} — {'PASS' if ok5 else 'FAIL'}")
    passed += ok5

    # Test 6: Behavioral tags
    print("[Test 6] Behavioral tags")
    ok6 = "consensus_chaser" in profile.behavioral_tags
    print(f"  Tags: {profile.behavioral_tags}: {ok6} — {'PASS' if ok6 else 'FAIL'}")
    passed += ok6

    # Test 7: Clustering
    print("[Test 7] Clustering")
    clusters = sig.cluster_traders()
    ok7 = len(clusters) > 0
    print(f"  Clusters: {list(clusters.keys())}: {ok7} — {'PASS' if ok7 else 'FAIL'}")
    passed += ok7

    print(f"\nPASS: {passed}/{total}")
    print("=" * 60)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
