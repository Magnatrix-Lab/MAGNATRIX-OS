"""
High Win Rate Trading Bot - Complete Implementation
===================================================
Strategies: Mean Reversion, Grid Trading, Momentum
Target: 90%+ Win Rate with Controlled Risk
Asset Classes: Forex, Crypto, Stocks, Futures
Framework: Backtesting.py

Usage:
    python high_win_rate_trading_bot.py

Requirements:
    pip install backtesting pandas numpy yfinance matplotlib
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# TECHNICAL INDICATORS
# =============================================================================

def sma(series, period):
    """Simple Moving Average"""
    return pd.Series(series).rolling(window=period).mean()

def ema(series, period):
    """Exponential Moving Average"""
    return pd.Series(series).ewm(span=period, adjust=False).mean()

def rsi(series, period=14):
    """Relative Strength Index (0-100)"""
    delta = pd.Series(series).diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def bb_lower(series, period, std_dev):
    s = pd.Series(series)
    return s.rolling(window=period).mean() - s.rolling(window=period).std() * std_dev

def bb_upper(series, period, std_dev):
    s = pd.Series(series)
    return s.rolling(window=period).mean() + s.rolling(window=period).std() * std_dev

def atr_calc(high, low, close, period=14):
    """Average True Range"""
    h = pd.Series(high)
    l = pd.Series(low)
    c = pd.Series(close)
    tr1 = h - l
    tr2 = abs(h - c.shift(1))
    tr3 = abs(l - c.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


# =============================================================================
# STRATEGY CLASSES (module-level for Backtesting.py)
# =============================================================================

from backtesting import Strategy

class GridBot(Strategy):
    """Grid Trading - High win rate with tight profit targets"""
    tp_pct = 0.015
    sl_pct = 0.05

    def init(self):
        pass

    def next(self):
        price = self.data.Close[-1]
        if not self.position:
            self.buy(sl=price * (1 - self.sl_pct), tp=price * (1 + self.tp_pct))


class MeanReversionBot(Strategy):
    """Mean Reversion using RSI + Bollinger Bands"""
    bb_period = 20
    bb_std = 2.5
    rsi_period = 14
    rsi_oversold = 30
    rsi_overbought = 70
    tp_pct = 0.012
    sl_pct = 0.04

    def init(self):
        self.rsi_val = self.I(rsi, self.data.Close, self.rsi_period)
        self.bb_low = self.I(bb_lower, self.data.Close, self.bb_period, self.bb_std)
        self.bb_high = self.I(bb_upper, self.data.Close, self.bb_period, self.bb_std)

    def next(self):
        if len(self.data) < max(self.bb_period, self.rsi_period) + 5:
            return
        price = self.data.Close[-1]
        rsi_c = self.rsi_val[-1]
        if self.position:
            return
        if rsi_c < self.rsi_oversold:
            self.buy(sl=price * (1 - self.sl_pct), tp=price * (1 + self.tp_pct))
        elif rsi_c > self.rsi_overbought:
            self.sell(sl=price * (1 + self.sl_pct), tp=price * (1 - self.tp_pct))


class MomentumBot(Strategy):
    """Momentum Trend Following with EMA Crossover"""
    fast = 9
    slow = 21
    trend = 50
    tp_rr = 2.0
    sl_atr = 2.5

    def init(self):
        self.ema_fast = self.I(ema, self.data.Close, self.fast)
        self.ema_slow = self.I(ema, self.data.Close, self.slow)
        self.ema_trend = self.I(ema, self.data.Close, self.trend)
        self.atr_val = self.I(atr_calc, self.data.High, self.data.Low, self.data.Close, 14)

    def next(self):
        if len(self.data) < 60:
            return
        price = self.data.Close[-1]
        atr_c = max(self.atr_val[-1], price * 0.005)
        uptrend = self.ema_fast[-1] > self.ema_slow[-1] > self.ema_trend[-1]
        downtrend = self.ema_fast[-1] < self.ema_slow[-1] < self.ema_trend[-1]
        bull_cross = (self.ema_fast[-1] > self.ema_slow[-1] and 
                     self.ema_fast[-2] <= self.ema_slow[-2])
        bear_cross = (self.ema_slow[-1] > self.ema_fast[-1] and 
                     self.ema_slow[-2] <= self.ema_fast[-2])

        if bull_cross and uptrend:
            if not self.position or self.position.is_short:
                if self.position: self.position.close()
                sl = price - atr_c * self.sl_atr
                tp = price + (price - sl) * self.tp_rr
                self.buy(sl=sl, tp=tp)
        elif bear_cross and downtrend:
            if not self.position or self.position.is_long:
                if self.position: self.position.close()
                sl = price + atr_c * self.sl_atr
                tp = price - (sl - price) * self.tp_rr
                self.sell(sl=sl, tp=tp)


# =============================================================================
# KELLY CRITERION & EXPECTANCY
# =============================================================================

def kelly_criterion(win_rate, avg_win, avg_loss, fraction=0.25):
    """Calculate optimal position size using Kelly Criterion"""
    p = win_rate
    q = 1 - p
    b = avg_win / avg_loss if avg_loss > 0 else 1.0
    kelly = (p * b - q) / b if b > 0 else 0
    return max(0, min(0.5, kelly * fraction))

def trading_expectancy(win_rate, avg_win, avg_loss):
    """Calculate expected profit/loss per trade"""
    return (win_rate * avg_win) - ((1 - win_rate) * avg_loss)


# =============================================================================
# PERFORMANCE ANALYSIS
# =============================================================================

def analyze_strategy(stats, strategy_name="Strategy"):
    """Print comprehensive performance analysis"""
    print("\n" + "="*60)
    print(f"PERFORMANCE REPORT: {strategy_name}")
    print("="*60)

    metrics = {
        'Total Return (%)': f"{stats.get('Return [%]', 0):.2f}",
        'Annualized Return (%)': f"{stats.get('Return (Ann.) [%]', 0):.2f}",
        'Sharpe Ratio': f"{stats.get('Sharpe Ratio', 0):.2f}",
        'Max Drawdown (%)': f"{stats.get('Max. Drawdown [%]', 0):.2f}",
        'Win Rate (%)': f"{stats.get('Win Rate [%]', 0):.1f}",
        'Total Trades': f"{stats.get('# Trades', 0)}",
        'Profit Factor': f"{stats.get('Profit Factor', 0):.2f}",
        'Avg Trade (%)': f"{stats.get('Avg. Trade [%]', 0):.4f}",
        'Expectancy (%)': f"{stats.get('Expectancy [%]', 0):.4f}",
    }

    for metric, value in metrics.items():
        print(f"  {metric:25s}: {value}")

    wr = stats.get('Win Rate [%]', 50) / 100
    pf = stats.get('Profit Factor', 1.5)
    if pf > 0 and 0 < wr < 1:
        est_aw = pf * (1 - wr) / wr
        kelly = kelly_criterion(wr, est_aw, 1.0, 0.25)
        print(f"  {'Quarter Kelly Position Size':25s}: {kelly:.2%}")

    print("="*60)


# =============================================================================
# MAIN
# =============================================================================

def main():
    from backtesting import Backtest
    from backtesting.test import EURUSD, GOOG

    print("="*60)
    print("HIGH WIN RATE TRADING BOT - BACKTEST SUITE")
    print("="*60)

    # [1] Grid Strategy on EURUSD
    print("\n[1/3] Running Grid Trading Strategy on EURUSD...")
    bt1 = Backtest(EURUSD, GridBot, cash=10000, commission=0.0001)
    stats1 = bt1.run()
    analyze_strategy(stats1, "Grid Trading (EURUSD)")

    # [2] Mean Reversion on EURUSD
    print("\n[2/3] Running Mean Reversion Strategy on EURUSD...")
    bt2 = Backtest(EURUSD, MeanReversionBot, cash=10000, commission=0.0001)
    stats2 = bt2.run()
    analyze_strategy(stats2, "Mean Reversion (EURUSD)")

    # [3] Momentum on GOOG
    print("\n[3/3] Running Momentum Strategy on GOOG...")
    bt3 = Backtest(GOOG, MomentumBot, cash=10000, commission=0.001)
    stats3 = bt3.run()
    analyze_strategy(stats3, "Momentum Trend (GOOG)")

    # Summary
    print("\n" + "="*60)
    print("STRATEGY COMPARISON SUMMARY")
    print("="*60)
    comparison = pd.DataFrame({
        'Grid Trading': [
            stats1.get('Win Rate [%]', 0),
            stats1.get('Return [%]', 0),
            stats1.get('Max. Drawdown [%]', 0),
            stats1.get('Profit Factor', 0),
            stats1.get('# Trades', 0)
        ],
        'Mean Reversion': [
            stats2.get('Win Rate [%]', 0),
            stats2.get('Return [%]', 0),
            stats2.get('Max. Drawdown [%]', 0),
            stats2.get('Profit Factor', 0),
            stats2.get('# Trades', 0)
        ],
        'Momentum': [
            stats3.get('Win Rate [%]', 0),
            stats3.get('Return [%]', 0),
            stats3.get('Max. Drawdown [%]', 0),
            stats3.get('Profit Factor', 0),
            stats3.get('# Trades', 0)
        ]
    }, index=['Win Rate (%)', 'Total Return (%)', 'Max Drawdown (%)', 
              'Profit Factor', 'Total Trades'])
    print(comparison.to_string())
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
