# MAGNATRIX-OS Trading Modules — Task Brief

## Package 1: Risk Engine + Performance Analytics + Trade Journal
### File: `trading/risk_engine_native.py` (Risk Engine)
- Position sizing: fixed fractional, optimal f, Kelly criterion, volatility-adjusted
- Portfolio heat: max concurrent risk, sector concentration limit
- Drawdown circuit breaker: auto stop trading when drawdown exceeds threshold
- Daily loss limit: max daily loss $ or %, reset at midnight UTC
- Correlation check: prevent simultaneous long/short in correlated pairs
- Stop-loss / take-profit manager: trailing stop, ATR-based stops
- Risk per trade: configurable (default 1% of equity)
- Pure Python, stdlib only, `NativeRiskEngine` class with `run()` demo

### File: `trading/performance_analytics_native.py` (Performance Analytics)
- Sharpe ratio, Sortino ratio, Calmar ratio, Omega ratio
- Win rate, expectancy, profit factor, avg win/loss ratio
- Max drawdown, underwater plot (drawdown depth + duration)
- Equity curve + rolling metrics (30-day window)
- Pure Python, stdlib only, `NativePerformanceAnalytics` class

### File: `trading/trade_journal_native.py` (Trade Journal)
- SQLite database: trades, signals, P&L, reasoning, confidence, strategy
- P&L attribution by strategy: which strategy contributed how much
- Daily/weekly P&L report auto-generate
- Query interface: get trades by date, strategy, symbol, P&L range
- Pure Python, stdlib only, `NativeTradeJournal` class

## Package 2: Backtest Engine + Order Execution Engine
### File: `trading/backtest_engine_native.py` (Event-Driven Backtest)
- Event-driven engine: tick-by-tick processing, not just OHLCV
- Slippage model: fixed bps or proportional to spread
- Transaction cost analysis: maker/taker fee, spread impact
- Walk-forward optimization: in-sample train, out-sample test, rolling window
- Equity curve tracking: capital, drawdown, positions over time
- Performance metrics at end: Sharpe, Sortino, max DD, win rate
- Pure Python, stdlib only, `NativeBacktestEngine` class

### File: `trading/execution_engine_native.py` (Order Execution)
- Smart order routing: pick best exchange by price + liquidity
- Execution algorithms: TWAP, VWAP, Iceberg, Market, Limit
- Order state machine: DRAFT → PENDING → PARTIAL → FILLED → CANCELLED → FAILED
- Fill probability estimator: based on spread depth + recent volume
- Partial fill handling: auto-cancel remainder or let it fill
- Execution quality: slippage analysis, fill rate tracking
- Pure Python, stdlib only, `NativeExecutionEngine` class

## Package 3: Live Market Data Feed + Strategy Scheduler
### File: `trading/market_data_feed_native.py` (Native WebSocket Feed)
- Pure Python WebSocket client: handshake, frame parsing, auto-reconnect, heartbeat
- Connect to Binance, Bybit, OKX public WebSocket streams
- Parse: trade stream (price, qty, timestamp), order book depth (bids/asks), ticker (24h stats)
- Reconnection: exponential backoff, max retries, fallback to REST polling
- Rate limiter: per-exchange WebSocket connection limits
- Pure Python, stdlib only, `NativeMarketDataFeed` class
- No external deps: no websockets, no aiohttp, no ccxt

### File: `trading/strategy_scheduler_native.py` (Strategy Scheduler)
- Time-based activation: "only trade 09:00-16:00 UTC" config
- Market regime filter: bull/bear/range detection using SMA/EMA crossover
- Regime → strategy mapping: activate different strategy per regime
- News blackout: configurable blackout periods (e.g., FOMC, NFP)
- Strategy lifecycle: start → run → stop → cooldown
- Pure Python, stdlib only, `NativeStrategyScheduler` class

## Implementation Rules (all files)
- Pure Python, stdlib only (sqlite3 for journal, socket for WebSocket)
- `Native<ClassName>` with `run()` or `execute()` method
- Docstrings, type hints, `if __name__ == "__main__":` demo block
- Self-test: print PASS/FAIL, exit code 0 if all pass
- Follow existing `_native.py` style in repo
