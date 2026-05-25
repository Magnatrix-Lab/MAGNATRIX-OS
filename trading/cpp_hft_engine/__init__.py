"""MAGNATRIX-OS C++ HFT Engine Python bindings.

This module provides high-performance C++ components for:
  - Limit Order Book (LOB) management
  - Cross-exchange arbitrage detection
  - Tick-to-trade latency monitoring

Build (optional for C++ speedup):
    pip install pybind11
    cmake -Bbuild trading/cpp_hft_engine
    cmake --build build --config Release -j$(nproc)
    cp build/_hft_engine*.so trading/cpp_hft_engine/

Usage:
    from trading.cpp_hft_engine import HFTEngine, OrderBookManager
    engine = HFTEngine()
    engine.init()
    mgr = engine.book_manager()
    book = mgr.get_or_create("BTCUSDT")
    book.update_l1(50000_00000000, 150000000, 50001_00000000, 200000000, 0)
"""

# Try C++ extension first, fall back to pure Python
try:
    from ._hft_engine import (
        Side,
        PriceLevel,
        OrderBook,
        OrderBookManager,
        ArbitrageOpportunity,
        FeeSchedule,
        ArbitrageDetector,
        HFTEngine,
        price_to_fixed,
        fixed_to_price,
        qty_to_fixed,
        fixed_to_qty,
    )
    _BACKEND = "cpp"
except ImportError:
    # Pure Python fallback
    from .hft_engine_py import (
        PriceLevel,
        OrderBook,
        OrderBookManager,
        ArbitrageOpportunity,
        FeeSchedule,
        ArbitrageDetector,
        HFTEngine,
    )

    class Side:
        BUY = 0
        SELL = 1

    def price_to_fixed(p: float) -> int:
        return int(p * 1e8)

    def fixed_to_price(p: int) -> float:
        return p / 1e8

    def qty_to_fixed(q: float) -> int:
        return int(q * 1e8)

    def fixed_to_qty(q: int) -> float:
        return q / 1e8

    _BACKEND = "python"

__all__ = [
    "Side",
    "PriceLevel",
    "OrderBook",
    "OrderBookManager",
    "ArbitrageOpportunity",
    "FeeSchedule",
    "ArbitrageDetector",
    "HFTEngine",
    "price_to_fixed",
    "fixed_to_price",
    "qty_to_fixed",
    "fixed_to_qty",
]
