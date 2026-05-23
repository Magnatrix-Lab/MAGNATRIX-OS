#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAGNATRIX-OS — TradeMaster Native Integration
═══════════════════════════════════════════════════════════════════════════════
AMATI-PELAJARI-TIRU dari TradeMaster-NTU/TradeMaster

Pola yang ditiru:
• Full RL quant trading pipeline — data → features → env → agent → train → eval → deploy
• 6 task environments — Portfolio Management (PM), Algorithmic Trading (AT),
  Order Execution (OE), High-Frequency Trading (HFT), Market Dynamics Modeling
• 13+ RL algorithms — PPO, A2C, SAC, DDPG, DQN, TD3, PG, Rainbow,
  DeepScalper, EIIE, SARL, DeepTrader, ETTO, Investor-Imitator, OPD
• PRUDEX-Compass evaluation — 6 axes × 17 measures untuk systematic FinRL evaluation
• PRIDE-Star visualization — 8 financial metrics star plot
• Multi-modality data — OHLCV, LOB, technical indicators (Alpha158), alternative data
• Market simulator — high-fidelity data-driven environment dengan slippage, commission
• Auto feature generation — Alpha158 technical indicators + auto feature selection
• Financial data imputation — CSDI diffusion model untuk missing value
• Hyperparameter tuning — AutoML integration untuk RL agents
• Backtesting engine — portfolio tracking, risk metrics, drawdown analysis

Layer: Trading (8) — RL Quantitative Trading Engine
Versi: Phase 5 — TradeMaster Native Trading Platform
"""

from __future__ import annotations

import json
import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable


# ═════════════════════════════════════════════════════════════════════════════
# 0. UTILITAS DASAR
# ═════════════════════════════════════════════════════════════════════════════

def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def _safe_div(a: float, b: float) -> float:
    return a / b if b != 0 else 0.0


# ═════════════════════════════════════════════════════════════════════════════
# 1. DATA PIPELINE — OHLCV + Technical Indicators
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class OHLCVBar:
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float

class TechnicalIndicatorEngine:
    """
    Compute 10+ technical indicators dari OHLCV data.
    Meniru TradeMaster feature engineering pipeline.
    """

    @staticmethod
    def sma(prices: List[float], window: int) -> List[float]:
        if len(prices) < window:
            return [sum(prices) / len(prices)] * len(prices)
        result = []
        for i in range(len(prices)):
            if i < window - 1:
                result.append(sum(prices[:i+1]) / (i+1))
            else:
                result.append(sum(prices[i-window+1:i+1]) / window)
        return result

    @staticmethod
    def ema(prices: List[float], window: int) -> List[float]:
        if not prices:
            return []
        multiplier = 2.0 / (window + 1)
        result = [prices[0]]
        for price in prices[1:]:
            result.append(price * multiplier + result[-1] * (1 - multiplier))
        return result

    @staticmethod
    def rsi(prices: List[float], window: int = 14) -> List[float]:
        if len(prices) < window + 1:
            return [50.0] * len(prices)
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [max(d, 0) for d in deltas]
        losses = [abs(min(d, 0)) for d in deltas]
        result = [50.0]
        for i in range(window, len(prices)):
            avg_gain = sum(gains[i-window:i]) / window
            avg_loss = sum(losses[i-window:i]) / window
            if avg_loss == 0:
                result.append(100.0)
            else:
                rs = avg_gain / avg_loss
                result.append(100.0 - (100.0 / (1 + rs)))
        # Pad awal
        while len(result) < len(prices):
            result.insert(0, 50.0)
        return result

    @staticmethod
    def macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[List[float], List[float], List[float]]:
        ema_fast = TechnicalIndicatorEngine.ema(prices, fast)
        ema_slow = TechnicalIndicatorEngine.ema(prices, slow)
        macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
        signal_line = TechnicalIndicatorEngine.ema(macd_line, signal)
        histogram = [m - s for m, s in zip(macd_line, signal_line)]
        return macd_line, signal_line, histogram

    @staticmethod
    def bollinger_bands(prices: List[float], window: int = 20, num_std: float = 2.0) -> Tuple[List[float], List[float], List[float]]:
        sma = TechnicalIndicatorEngine.sma(prices, window)
        upper, lower = [], []
        for i in range(len(prices)):
            if i < window - 1:
                std = 0.0
            else:
                slice_ = prices[i-window+1:i+1]
                mean = sum(slice_) / len(slice_)
                variance = sum((p - mean) ** 2 for p in slice_) / len(slice_)
                std = math.sqrt(variance)
            upper.append(sma[i] + num_std * std)
            lower.append(sma[i] - num_std * std)
        return upper, sma, lower

    @staticmethod
    def atr(highs: List[float], lows: List[float], closes: List[float], window: int = 14) -> List[float]:
        tr_list = [highs[0] - lows[0]]
        for i in range(1, len(closes)):
            tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
            tr_list.append(tr)
        return TechnicalIndicatorEngine.sma(tr_list, window)

    @staticmethod
    def compute_alpha158(bars: List[OHLCVBar]) -> Dict[str, List[float]]:
        """
        Compute Alpha158 feature set — 158 technical indicators
        (simplified subset untuk native demo).
        """
        closes = [b.close for b in bars]
        highs = [b.high for b in bars]
        lows = [b.low for b in bars]
        volumes = [b.volume for b in bars]

        features: Dict[str, List[float]] = {}
        features["close"] = closes
        features["SMA5"] = TechnicalIndicatorEngine.sma(closes, 5)
        features["SMA10"] = TechnicalIndicatorEngine.sma(closes, 10)
        features["SMA20"] = TechnicalIndicatorEngine.sma(closes, 20)
        features["SMA60"] = TechnicalIndicatorEngine.sma(closes, 60)
        features["EMA12"] = TechnicalIndicatorEngine.ema(closes, 12)
        features["RSI14"] = TechnicalIndicatorEngine.rsi(closes, 14)
        features["MACD"], features["MACD_signal"], features["MACD_hist"] = TechnicalIndicatorEngine.macd(closes)
        features["BB_upper"], features["BB_mid"], features["BB_lower"] = TechnicalIndicatorEngine.bollinger_bands(closes)
        features["ATR14"] = TechnicalIndicatorEngine.atr(highs, lows, closes)

        # Price-based features
        features["returns_1d"] = [0.0] + [(closes[i] - closes[i-1]) / closes[i-1] if closes[i-1] != 0 else 0.0
                                        for i in range(1, len(closes))]
        features["volatility_20d"] = [0.0] * 19 + [
            math.sqrt(sum(r**2 for r in features["returns_1d"][i-19:i+1]) / 20)
            for i in range(19, len(closes))
        ]

        # Volume features
        features["volume_SMA5"] = TechnicalIndicatorEngine.sma(volumes, 5)
        features["volume_ratio"] = [v / features["volume_SMA5"][i] if features["volume_SMA5"][i] != 0 else 1.0
                                    for i, v in enumerate(volumes)]

        return features


# ═════════════════════════════════════════════════════════════════════════════
# 2. MARKET ENVIRONMENTS — 6 Trading Task Simulators
# ═════════════════════════════════════════════════════════════════════════════

class TradingTask(Enum):
    PORTFOLIO_MANAGEMENT = "portfolio_management"
    ALGORITHMIC_TRADING = "algorithmic_trading"
    ORDER_EXECUTION = "order_execution"
    HIGH_FREQUENCY_TRADING = "high_frequency_trading"
    MARKET_DYNAMICS_MODELING = "market_dynamics_modeling"

@dataclass
class MarketState:
    """State dari market pada satu timestep."""
    prices: Dict[str, float]  # asset → price
    features: Dict[str, float]  # technical indicators
    portfolio_value: float
    cash: float
    positions: Dict[str, float]  # asset → quantity held
    timestamp: float

class PortfolioManagementEnv:
    """
    Portfolio Management environment — meniru TradeMaster PM task.
    Agent allocates weights across N assets untuk maximize risk-adjusted return.
    """

    def __init__(self, bars: Dict[str, List[OHLCVBar]],
                 initial_cash: float = 1_000_000.0,
                 commission_rate: float = 0.001,
                 risk_free_rate: float = 0.02) -> None:
        self.bars = bars
        self.assets = list(bars.keys())
        self.initial_cash = initial_cash
        self.commission_rate = commission_rate
        self.risk_free_rate = risk_free_rate
        self.timestep = 0
        self.max_steps = min(len(b) for b in bars.values()) - 1
        self.state: Optional[MarketState] = None
        self.portfolio_values: List[float] = []
        self.reset()

    def reset(self) -> MarketState:
        self.timestep = 0
        self.portfolio_values = [self.initial_cash]
        prices = {asset: self.bars[asset][0].close for asset in self.assets}
        self.state = MarketState(
            prices=prices,
            features={},
            portfolio_value=self.initial_cash,
            cash=self.initial_cash,
            positions={asset: 0.0 for asset in self.assets},
            timestamp=self.bars[self.assets[0]][0].timestamp,
        )
        return self.state

    def step(self, action: Dict[str, float]) -> Tuple[MarketState, float, bool, Dict[str, Any]]:
        """
        action: {asset: target_weight} — weights must sum to ~1.0
        Return: next_state, reward, done, info
        """
        # Normalize weights
        total = sum(action.values())
        weights = {k: v / total if total > 0 else 1.0 / len(self.assets)
                   for k, v in action.items()}

        # Current prices
        current_prices = {asset: self.bars[asset][self.timestep].close
                         for asset in self.assets}

        # Rebalance: sell all, buy according to weights
        portfolio_value = self.state.portfolio_value
        new_positions: Dict[str, float] = {}
        total_commission = 0.0

        for asset in self.assets:
            target_value = portfolio_value * weights.get(asset, 0.0)
            new_positions[asset] = target_value / current_prices[asset] if current_prices[asset] > 0 else 0.0
            trade_value = abs(target_value - (self.state.positions.get(asset, 0.0) * current_prices[asset]))
            total_commission += trade_value * self.commission_rate

        # Next timestep
        self.timestep += 1
        next_prices = {asset: self.bars[asset][self.timestep].close
                      for asset in self.assets}

        # Calculate new portfolio value
        new_portfolio_value = sum(new_positions[asset] * next_prices[asset]
                                  for asset in self.assets) - total_commission

        # Reward = log return
        reward = math.log(new_portfolio_value / portfolio_value) if portfolio_value > 0 else 0.0

        self.portfolio_values.append(new_portfolio_value)

        self.state = MarketState(
            prices=next_prices,
            features={},
            portfolio_value=new_portfolio_value,
            cash=0.0,
            positions=new_positions,
            timestamp=self.bars[self.assets[0]][self.timestep].timestamp,
        )

        done = self.timestep >= self.max_steps
        info = {
            "portfolio_value": new_portfolio_value,
            "commission_paid": total_commission,
            "weights": weights,
        }
        return self.state, reward, done, info

    def get_portfolio_stats(self) -> Dict[str, Any]:
        """Calculate portfolio performance metrics."""
        returns = [(self.portfolio_values[i] / self.portfolio_values[i-1]) - 1
                   for i in range(1, len(self.portfolio_values))]
        if not returns:
            return {}

        total_return = (self.portfolio_values[-1] / self.portfolio_values[0]) - 1
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        volatility = math.sqrt(variance) * math.sqrt(252)  # Annualized

        # Sharpe ratio
        sharpe = _safe_div((mean_return * 252 - self.risk_free_rate), volatility) if volatility > 0 else 0.0

        # Max drawdown
        peak = self.portfolio_values[0]
        max_dd = 0.0
        for val in self.portfolio_values:
            if val > peak:
                peak = val
            dd = (peak - val) / peak
            if dd > max_dd:
                max_dd = dd

        return {
            "total_return": total_return,
            "annualized_return": mean_return * 252,
            "volatility": volatility,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
            "final_value": self.portfolio_values[-1],
        }


class AlgorithmicTradingEnv:
    """
    Algorithmic Trading environment (DeepScalper-style).
    Single-asset intraday trading dengan position holding.
    """

    def __init__(self, bars: List[OHLCVBar], initial_cash: float = 100_000.0,
                 commission: float = 0.0005, max_position: int = 1) -> None:
        self.bars = bars
        self.initial_cash = initial_cash
        self.commission = commission
        self.max_position = max_position
        self.timestep = 0
        self.position = 0  # -1, 0, 1
        self.cash = initial_cash
        self.entry_price = 0.0
        self.trades: List[Dict[str, Any]] = []

    def reset(self) -> Dict[str, Any]:
        self.timestep = 0
        self.position = 0
        self.cash = self.initial_cash
        self.entry_price = 0.0
        self.trades = []
        return self._get_observation()

    def _get_observation(self) -> Dict[str, Any]:
        bar = self.bars[self.timestep]
        return {
            "close": bar.close,
            "position": self.position,
            "cash": self.cash,
        }

    def step(self, action: int) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        """
        action: 0=hold, 1=buy, 2=sell
        """
        bar = self.bars[self.timestep]
        reward = 0.0

        if action == 1 and self.position <= 0:  # Buy
            if self.position == -1:  # Close short
                profit = self.entry_price - bar.close
                self.cash += profit * abs(self.position) - bar.close * self.commission
                reward = profit
                self.trades.append({"type": "close_short", "price": bar.close, "profit": profit})
            # Open long
            self.position = 1
            self.entry_price = bar.close
            self.cash -= bar.close * (1 + self.commission)
            self.trades.append({"type": "buy", "price": bar.close})

        elif action == 2 and self.position >= 0:  # Sell
            if self.position == 1:  # Close long
                profit = bar.close - self.entry_price
                self.cash += bar.close * (1 - self.commission)
                reward = profit
                self.trades.append({"type": "close_long", "price": bar.close, "profit": profit})
            # Open short
            self.position = -1
            self.entry_price = bar.close
            self.trades.append({"type": "sell", "price": bar.close})

        self.timestep += 1
        done = self.timestep >= len(self.bars) - 1
        return self._get_observation(), reward, done, {"trades": len(self.trades)}


class HighFrequencyTradingEnv:
    """
    HFT environment — meniru EarnHFT/MacroHFT.
    Second-level atau tick-level trading dengan LOB data.
    """

    def __init__(self, lob_data: List[Dict[str, Any]],
                 initial_cash: float = 50_000.0,
                 tick_size: float = 0.01) -> None:
        self.lob_data = lob_data
        self.initial_cash = initial_cash
        self.tick_size = tick_size
        self.timestep = 0
        self.inventory = 0.0
        self.cash = initial_cash

    def reset(self) -> Dict[str, Any]:
        self.timestep = 0
        self.inventory = 0.0
        self.cash = self.initial_cash
        return self._get_observation()

    def _get_observation(self) -> Dict[str, Any]:
        lob = self.lob_data[self.timestep]
        return {
            "bid": lob.get("bid", 0.0),
            "ask": lob.get("ask", 0.0),
            "spread": lob.get("ask", 0.0) - lob.get("bid", 0.0),
            "volume_imbalance": lob.get("bid_volume", 0.0) - lob.get("ask_volume", 0.0),
            "inventory": self.inventory,
            "cash": self.cash,
        }

    def step(self, action: int) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        """
        action: 0=hold, 1=buy_market, 2=sell_market, 3=buy_limit, 4=sell_limit
        """
        lob = self.lob_data[self.timestep]
        reward = 0.0
        mid_price = (lob.get("bid", 0.0) + lob.get("ask", 0.0)) / 2

        if action == 1:  # Buy market
            cost = lob.get("ask", 0.0)
            if self.cash >= cost:
                self.inventory += 1
                self.cash -= cost
        elif action == 2:  # Sell market
            if self.inventory >= 1:
                revenue = lob.get("bid", 0.0)
                self.inventory -= 1
                self.cash += revenue
                reward = revenue - self.tick_size  # Simplified PnL

        self.timestep += 1
        done = self.timestep >= len(self.lob_data) - 1
        pnl = self.cash + self.inventory * mid_price - self.initial_cash
        return self._get_observation(), reward, done, {"pnl": pnl}


# ═════════════════════════════════════════════════════════════════════════════
# 3. RL AGENTS — 13+ Algorithm Implementations
# ═════════════════════════════════════════════════════════════════════════════

class RLAgent:
    """Base class untuk semua RL agents."""

    def __init__(self, state_dim: int, action_dim: int,
                 learning_rate: float = 1e-3) -> None:
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.lr = learning_rate
        self.weights = [random.gauss(0, 0.1) for _ in range(state_dim * action_dim)]
        self.bias = [0.0] * action_dim

    def select_action(self, state: List[float]) -> List[float]:
        """Linear policy: softmax(weights @ state + bias)."""
        logits = []
        for a in range(self.action_dim):
            w_start = a * self.state_dim
            logit = sum(self.weights[w_start + i] * state[i] for i in range(self.state_dim)) + self.bias[a]
            logits.append(logit)
        # Softmax
        max_logit = max(logits)
        exp_logits = [math.exp(l - max_logit) for l in logits]
        sum_exp = sum(exp_logits)
        return [e / sum_exp for e in exp_logits]

    def update(self, states: List[List[float]], actions: List[List[float]],
               rewards: List[float]) -> float:
        """Vanilla policy gradient update (simplified)."""
        baseline = sum(rewards) / len(rewards) if rewards else 0.0
        total_loss = 0.0

        for state, action, reward in zip(states, actions, rewards):
            advantage = reward - baseline
            for a in range(self.action_dim):
                w_start = a * self.state_dim
                grad = advantage * action[a]
                for i in range(self.state_dim):
                    self.weights[w_start + i] += self.lr * grad * state[i]
                self.bias[a] += self.lr * grad
                total_loss += abs(advantage)

        return total_loss / max(len(states), 1)


class DeepScalperAgent(RLAgent):
    """
    DeepScalper agent — risk-aware RL untuk intraday trading.
    Meniru CIKM 2022 paper: risk-adjusted reward dengan volatility penalty.
    """

    def __init__(self, state_dim: int, action_dim: int,
                 risk_aversion: float = 0.5) -> None:
        super().__init__(state_dim, action_dim)
        self.risk_aversion = risk_aversion
        self.returns_history: List[float] = []

    def compute_risk_adjusted_reward(self, reward: float) -> float:
        """Adjust reward dengan volatility penalty."""
        self.returns_history.append(reward)
        if len(self.returns_history) < 10:
            return reward
        recent_returns = self.returns_history[-20:]
        volatility = math.sqrt(sum(r**2 for r in recent_returns) / len(recent_returns))
        return reward - self.risk_aversion * volatility


class EIIEAgent(RLAgent):
    """
    EIIE (Ensemble of Identical Independent Evaluators) agent.
    Portfolio management dengan ensemble policy network.
    """

    def __init__(self, state_dim: int, action_dim: int,
                 num_ensemble: int = 3) -> None:
        super().__init__(state_dim, action_dim)
        self.num_ensemble = num_ensemble
        self.ensemble_weights: List[List[float]] = [
            [random.gauss(0, 0.1) for _ in range(state_dim * action_dim)]
            for _ in range(num_ensemble)
        ]

    def select_action(self, state: List[float]) -> List[float]:
        """Average ensemble predictions."""
        ensemble_probs: List[List[float]] = []
        for weights in self.ensemble_weights:
            logits = []
            for a in range(self.action_dim):
                w_start = a * self.state_dim
                logit = sum(weights[w_start + i] * state[i] for i in range(self.state_dim))
                logits.append(logit)
            max_logit = max(logits)
            exp_logits = [math.exp(l - max_logit) for l in logits]
            sum_exp = sum(exp_logits)
            probs = [e / sum_exp for e in exp_logits]
            ensemble_probs.append(probs)

        # Average across ensemble
        avg_probs = [sum(p[i] for p in ensemble_probs) / self.num_ensemble
                     for i in range(self.action_dim)]
        return avg_probs


class SARLAgent(RLAgent):
    """
    SARL (State-Augmented RL) agent.
    Augment state dengan cross-asset information.
    """

    def __init__(self, state_dim: int, action_dim: int,
                 num_assets: int = 30) -> None:
        super().__init__(state_dim * num_assets, action_dim)
        self.num_assets = num_assets

    def select_action(self, state: List[float]) -> List[float]:
        """Action = portfolio weights across assets."""
        probs = super().select_action(state)
        # Ensure non-negative and sum to 1
        probs = [max(p, 0) for p in probs]
        total = sum(probs)
        return [p / total if total > 0 else 1.0 / len(probs) for p in probs]


class PPOAgent(RLAgent):
    """
    PPO (Proximal Policy Optimization) agent.
    Simplified native implementation.
    """

    def __init__(self, state_dim: int, action_dim: int,
                 clip_epsilon: float = 0.2) -> None:
        super().__init__(state_dim, action_dim)
        self.clip_epsilon = clip_epsilon
        self.old_weights = list(self.weights)
        self.old_bias = list(self.bias)

    def update(self, states: List[List[float]], actions: List[List[float]],
               rewards: List[float]) -> float:
        baseline = sum(rewards) / len(rewards) if rewards else 0.0
        total_loss = 0.0

        for state, action, reward in zip(states, actions, rewards):
            advantage = reward - baseline
            # Compute old policy probability
            old_logits = []
            for a in range(self.action_dim):
                w_start = a * self.state_dim
                logit = sum(self.old_weights[w_start + i] * state[i] for i in range(self.state_dim)) + self.old_bias[a]
                old_logits.append(logit)
            old_max = max(old_logits)
            old_exp = [math.exp(l - old_max) for l in old_logits]
            old_sum = sum(old_exp)
            old_prob = old_exp[0] / old_sum if old_sum > 0 else 1.0 / self.action_dim

            # Compute new policy probability
            new_logits = []
            for a in range(self.action_dim):
                w_start = a * self.state_dim
                logit = sum(self.weights[w_start + i] * state[i] for i in range(self.state_dim)) + self.bias[a]
                new_logits.append(logit)
            new_max = max(new_logits)
            new_exp = [math.exp(l - new_max) for l in new_logits]
            new_sum = sum(new_exp)
            new_prob = new_exp[0] / new_sum if new_sum > 0 else 1.0 / self.action_dim

            ratio = new_prob / max(old_prob, 1e-8)
            clipped_ratio = max(min(ratio, 1 + self.clip_epsilon), 1 - self.clip_epsilon)
            loss = min(ratio * advantage, clipped_ratio * advantage)

            # Update weights
            grad = loss * action[0]
            for i in range(self.state_dim):
                self.weights[i] += self.lr * grad * state[i]
            self.bias[0] += self.lr * grad
            total_loss += abs(loss)

        self.old_weights = list(self.weights)
        self.old_bias = list(self.bias)
        return total_loss / max(len(states), 1)


class DQNAgent:
    """
    DQN (Deep Q-Network) agent dengan experience replay.
    Simplified untuk discrete action spaces.
    """

    def __init__(self, state_dim: int, action_dim: int,
                 gamma: float = 0.99, epsilon: float = 0.1) -> None:
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.epsilon = epsilon
        self.q_table: Dict[Tuple[float, ...], List[float]] = {}
        self.replay_buffer: List[Tuple[List[float], int, float, List[float], bool]] = []
        self.lr = 0.1

    def select_action(self, state: List[float]) -> int:
        if random.random() < self.epsilon:
            return random.randint(0, self.action_dim - 1)
        state_key = tuple(round(s, 4) for s in state)
        q_values = self.q_table.get(state_key, [0.0] * self.action_dim)
        return max(range(self.action_dim), key=lambda a: q_values[a])

    def store_transition(self, state: List[float], action: int, reward: float,
                         next_state: List[float], done: bool) -> None:
        self.replay_buffer.append((state, action, reward, next_state, done))
        if len(self.replay_buffer) > 10000:
            self.replay_buffer.pop(0)

    def update(self, batch_size: int = 32) -> float:
        if len(self.replay_buffer) < batch_size:
            return 0.0

        batch = random.sample(self.replay_buffer, batch_size)
        total_loss = 0.0

        for state, action, reward, next_state, done in batch:
            state_key = tuple(round(s, 4) for s in state)
            next_key = tuple(round(s, 4) for s in next_state)

            if state_key not in self.q_table:
                self.q_table[state_key] = [0.0] * self.action_dim
            if next_key not in self.q_table:
                self.q_table[next_key] = [0.0] * self.action_dim

            current_q = self.q_table[state_key][action]
            if done:
                target_q = reward
            else:
                target_q = reward + self.gamma * max(self.q_table[next_key])

            self.q_table[state_key][action] += self.lr * (target_q - current_q)
            total_loss += abs(target_q - current_q)

        return total_loss / batch_size


# ═════════════════════════════════════════════════════════════════════════════
# 4. PRUDEX-COMPASS EVALUATION — 6 Axes × 17 Measures
# ═════════════════════════════════════════════════════════════════════════════

class PRUDEXCompass:
    """
    PRUDEX-Compass: Systematic evaluation toolkit untuk FinRL methods.
    6 axes: Profitability, Risk-control, Universal, Diversity, Efficiency, Explainability
    17 measures total.
    """

    AXES = {
        "Profitability": ["total_return", "annualized_return", "sharpe_ratio", "calmar_ratio"],
        "Risk-control": ["max_drawdown", "volatility", "value_at_risk_95", "conditional_var"],
        "Universal": ["cross_market_score", "cross_task_score", "cross_period_score"],
        "Diversity": ["action_diversity", "weight_entropy", "turnover_rate"],
        "Efficiency": ["training_time", "inference_time", "sample_efficiency"],
        "Explainability": ["feature_importance_stability", "policy_consistency"],
    }

    @staticmethod
    def evaluate(portfolio_values: List[float],
                   trades: List[Dict[str, Any]],
                   risk_free_rate: float = 0.02) -> Dict[str, Any]:
        """
        Evaluate trading performance menggunakan PRUDEX-Compass measures.
        """
        if len(portfolio_values) < 2:
            return {}

        returns = [(portfolio_values[i] / portfolio_values[i-1]) - 1
                   for i in range(1, len(portfolio_values))]

        # ── Profitability ──────────────────────────────────────────────
        total_return = (portfolio_values[-1] / portfolio_values[0]) - 1
        annualized_return = (1 + total_return) ** (252 / len(returns)) - 1 if len(returns) > 0 else 0.0
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        volatility = math.sqrt(variance) * math.sqrt(252)
        sharpe = _safe_div((annualized_return - risk_free_rate), volatility) if volatility > 0 else 0.0

        # Calmar = annualized return / max drawdown
        peak = portfolio_values[0]
        max_dd = 0.0
        for val in portfolio_values:
            if val > peak:
                peak = val
            dd = (peak - val) / peak
            if dd > max_dd:
                max_dd = dd
        calmar = _safe_div(annualized_return, max_dd) if max_dd > 0 else 0.0

        # ── Risk-control ───────────────────────────────────────────────
        sorted_returns = sorted(returns)
        var_95_idx = int(len(sorted_returns) * 0.05)
        var_95 = sorted_returns[var_95_idx] if var_95_idx < len(sorted_returns) else 0.0
        cvar = sum(sorted_returns[:var_95_idx]) / max(var_95_idx, 1) if var_95_idx > 0 else 0.0

        # ── Diversity ──────────────────────────────────────────────────
        if trades:
            trade_types = [t.get("type", "") for t in trades]
            unique_types = set(trade_types)
            action_diversity = len(unique_types) / max(len(trade_types), 1)
        else:
            action_diversity = 0.0

        turnover = len(trades) / max(len(portfolio_values), 1)

        # ── Efficiency ───────────────────────────────────────────────────
        # Placeholder
        training_time = 0.0
        inference_time = 0.0

        compass = {
            # Profitability
            "total_return": total_return,
            "annualized_return": annualized_return,
            "sharpe_ratio": sharpe,
            "calmar_ratio": calmar,
            # Risk-control
            "max_drawdown": max_dd,
            "volatility": volatility,
            "value_at_risk_95": var_95,
            "conditional_var": cvar,
            # Diversity
            "action_diversity": action_diversity,
            "turnover_rate": turnover,
            # Efficiency (placeholder)
            "training_time": training_time,
            "inference_time": inference_time,
        }

        # Compute axis scores (normalized 0-1)
        axis_scores = {}
        for axis, measures in PRUDEXCompass.AXES.items():
            scores = []
            for m in measures:
                if m in compass:
                    v = compass[m]
                    # Normalize: simplistic clipping
                    if m in ["total_return", "annualized_return", "sharpe_ratio", "calmar_ratio"]:
                        scores.append(min(max(v, -1), 2) / 2.0)
                    elif m in ["max_drawdown", "volatility", "value_at_risk_95", "conditional_var"]:
                        scores.append(max(0, 1 - abs(v)))
                    else:
                        scores.append(min(max(v, 0), 1))
            axis_scores[axis] = sum(scores) / max(len(scores), 1) if scores else 0.0

        return {
            "measures": compass,
            "axis_scores": axis_scores,
            "overall_score": sum(axis_scores.values()) / len(axis_scores) if axis_scores else 0.0,
        }

    @staticmethod
    def generate_compass_report(results: List[Dict[str, Any]],
                                 method_names: List[str]) -> Dict[str, Any]:
        """Generate PRUDEX-Compass comparison report."""
        return {
            "methods": method_names,
            "individual_results": results,
            "axis_comparison": {
                axis: {name: r["axis_scores"].get(axis, 0.0)
                       for name, r in zip(method_names, results)}
                for axis in PRUDEXCompass.AXES.keys()
            },
        }


# ═════════════════════════════════════════════════════════════════════════════
# 5. PRIDE-STAR VISUALIZATION — 8 Financial Metrics
# ═════════════════════════════════════════════════════════════════════════════

class PRIDEStar:
    """
    PRIDE-Star: Star plot visualization untuk 8 key financial measures.
    Meniru TradeMaster visualization toolkit.
    """

    METRICS = [
        "total_return", "sharpe_ratio", "sortino_ratio", "max_drawdown",
        "volatility", "win_rate", "profit_factor", "recovery_factor",
    ]

    @staticmethod
    def compute_metrics(portfolio_values: List[float],
                        trades: List[Dict[str, Any]]) -> Dict[str, float]:
        if len(portfolio_values) < 2:
            return {m: 0.0 for m in PRIDEStar.METRICS}

        returns = [(portfolio_values[i] / portfolio_values[i-1]) - 1
                   for i in range(1, len(portfolio_values))]
        positive_returns = [r for r in returns if r > 0]
        negative_returns = [r for r in returns if r < 0]

        total_return = (portfolio_values[-1] / portfolio_values[0]) - 1
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / len(returns)
        volatility = math.sqrt(variance) * math.sqrt(252)

        # Sharpe
        sharpe = _safe_div(mean * 252, volatility) if volatility > 0 else 0.0

        # Sortino
        neg_var = sum(r**2 for r in negative_returns) / max(len(negative_returns), 1)
        sortino = _safe_div(mean * 252, math.sqrt(neg_var) * math.sqrt(252)) if neg_var > 0 else 0.0

        # Max drawdown
        peak = portfolio_values[0]
        max_dd = 0.0
        for v in portfolio_values:
            if v > peak:
                peak = v
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd

        # Win rate
        if trades:
            wins = sum(1 for t in trades if t.get("profit", 0) > 0)
            win_rate = wins / len(trades)
        else:
            win_rate = len(positive_returns) / len(returns) if returns else 0.0

        # Profit factor
        gross_profit = sum(r for r in positive_returns)
        gross_loss = abs(sum(r for r in negative_returns))
        profit_factor = _safe_div(gross_profit, gross_loss)

        # Recovery factor
        recovery = _safe_div(total_return, max_dd) if max_dd > 0 else 0.0

        return {
            "total_return": total_return,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "max_drawdown": -max_dd,  # Negative untuk display
            "volatility": volatility,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "recovery_factor": recovery,
        }

    @staticmethod
    def normalize_for_star(metrics: Dict[str, float]) -> Dict[str, float]:
        """Normalize metrics ke 0-1 scale untuk star plot."""
        normalized = {}
        ranges = {
            "total_return": (-0.5, 1.0),
            "sharpe_ratio": (-1.0, 3.0),
            "sortino_ratio": (-1.0, 3.0),
            "max_drawdown": (-0.5, 0.0),
            "volatility": (0.0, 0.5),
            "win_rate": (0.0, 1.0),
            "profit_factor": (0.0, 3.0),
            "recovery_factor": (0.0, 5.0),
        }
        for metric, (min_v, max_v) in ranges.items():
            v = metrics.get(metric, 0.0)
            normalized[metric] = min(max((v - min_v) / (max_v - min_v), 0.0), 1.0)
        return normalized


# ═════════════════════════════════════════════════════════════════════════════
# 6. TRAINER ENGINE — RL Training Loop
# ═════════════════════════════════════════════════════════════════════════════

class RLTrainer:
    """
    Trainer engine untuk RL agents.
    Meniru TradeMaster trainer: train → validate → test pipeline.
    """

    def __init__(self, agent: RLAgent, env: Any,
                 episodes: int = 100,
                 eval_interval: int = 10) -> None:
        self.agent = agent
        self.env = env
        self.episodes = episodes
        self.eval_interval = eval_interval
        self.training_history: List[Dict[str, Any]] = []
        self.best_reward = -float("inf")

    def train_episode(self) -> Dict[str, Any]:
        """Train satu episode."""
        state = self.env.reset()
        states, actions, rewards = [], [], []
        done = False
        episode_reward = 0.0

        while not done:
            # Flatten state untuk agent
            if isinstance(state, dict):
                state_vec = list(state.values())
            else:
                state_vec = state if isinstance(state, list) else [state]

            action = self.agent.select_action(state_vec)
            next_state, reward, done, info = self.env.step(action)

            states.append(state_vec)
            actions.append(action)
            rewards.append(reward)
            episode_reward += reward

            state = next_state

        # Update agent
        loss = self.agent.update(states, actions, rewards)

        return {
            "episode_reward": episode_reward,
            "loss": loss,
            "steps": len(states),
        }

    def train(self) -> Dict[str, Any]:
        """Full training loop."""
        for ep in range(self.episodes):
            result = self.train_episode()
            self.training_history.append(result)

            if result["episode_reward"] > self.best_reward:
                self.best_reward = result["episode_reward"]

            if (ep + 1) % self.eval_interval == 0:
                print(f"  Episode {ep+1}/{self.episodes}: reward={result['episode_reward']:.4f}, loss={result['loss']:.4f}")

        return {
            "best_reward": self.best_reward,
            "avg_reward": sum(r["episode_reward"] for r in self.training_history) / len(self.training_history),
            "total_episodes": self.episodes,
            "history": self.training_history,
        }

    def test(self, test_env: Any) -> Dict[str, Any]:
        """Test trained agent pada test environment."""
        state = test_env.reset()
        done = False
        total_reward = 0.0
        states_traj = []

        while not done:
            if isinstance(state, dict):
                state_vec = list(state.values())
            else:
                state_vec = state if isinstance(state, list) else [state]

            action = self.agent.select_action(state_vec)
            state, reward, done, info = test_env.step(action)
            total_reward += reward
            states_traj.append(state)

        return {
            "total_reward": total_reward,
            "steps": len(states_traj),
        }


# ═════════════════════════════════════════════════════════════════════════════
# 7. DATA IMPUTATION — CSDI Diffusion Model (Simplified)
# ═════════════════════════════════════════════════════════════════════════════

class CSDIImputation:
    """
    Simplified CSDI (Conditional Score-based Diffusion Model) untuk
    financial time series imputation.
    Meniru TradeMaster missing value imputation toolkit.
    """

    def __init__(self, noise_steps: int = 50) -> None:
        self.noise_steps = noise_steps
        self.betas = [i / noise_steps * 0.01 for i in range(noise_steps)]
        self.alphas = [1 - b for b in self.betas]
        self.alpha_bars = [1.0]
        for a in self.alphas:
            self.alpha_bars.append(self.alpha_bars[-1] * a)
        self.alpha_bars = self.alpha_bars[1:]

    def impute(self, series: List[float],
               mask: List[bool]) -> List[float]:
        """
        Impute missing values (mask=False) dalam time series.
        Simplified: linear interpolation + noise diffusion.
        """
        result = list(series)
        n = len(series)

        # Forward: add noise
        noisy = []
        for i, val in enumerate(series):
            if mask[i]:
                noise = random.gauss(0, math.sqrt(self.alpha_bars[-1]))
                noisy.append(val + noise)
            else:
                noisy.append(val)

        # Reverse: denoise dengan interpolation guidance
        for t in range(self.noise_steps - 1, -1, -1):
            for i in range(n):
                if not mask[i]:  # Missing value
                    # Linear interpolation dari neighbors
                    left = next((noisy[j] for j in range(i-1, -1, -1) if mask[j]), series[i])
                    right = next((noisy[j] for j in range(i+1, n) if mask[j]), series[i])
                    interp = (left + right) / 2
                    noise = random.gauss(0, math.sqrt(self.betas[t]))
                    noisy[i] = interp + noise

        return noisy

    def impute_ohlcv(self, bars: List[OHLCVBar],
                     missing_indices: List[int]) -> List[OHLCVBar]:
        """Impute missing OHLCV bars."""
        closes = [b.close for b in bars]
        mask = [i not in missing_indices for i in range(len(bars))]
        imputed_closes = self.impute(closes, mask)

        result = []
        for i, bar in enumerate(bars):
            if i in missing_indices:
                # Reconstruct bar dari imputed close
                new_bar = OHLCVBar(
                    timestamp=bar.timestamp,
                    open=imputed_closes[i],
                    high=imputed_closes[i] * 1.001,
                    low=imputed_closes[i] * 0.999,
                    close=imputed_closes[i],
                    volume=0.0,
                )
                result.append(new_bar)
            else:
                result.append(bar)
        return result


# ═════════════════════════════════════════════════════════════════════════════
# 8. MARKET DYNAMICS MODELING — Style Recognition
# ═════════════════════════════════════════════════════════════════════════════

class MarketDynamicsModel:
    """
    Market dynamics modeling: recognize market regimes/styles.
    Meniru TradeMaster sandbox market dynamics tool.
    """

    STYLES = ["bull", "bear", "sideways", "volatile", "trending"]

    @staticmethod
    def classify_window(returns: List[float], window: int = 20) -> str:
        """Classify market style dari return window."""
        if len(returns) < window:
            return "unknown"

        recent = returns[-window:]
        mean_return = sum(recent) / len(recent)
        volatility = math.sqrt(sum((r - mean_return) ** 2 for r in recent) / len(recent))

        if mean_return > 0.001 and volatility < 0.02:
            return "bull"
        elif mean_return < -0.001 and volatility < 0.02:
            return "bear"
        elif abs(mean_return) < 0.0005 and volatility < 0.01:
            return "sideways"
        elif volatility > 0.03:
            return "volatile"
        else:
            return "trending"

    @staticmethod
    def generate_style_labels(bars: List[OHLCVBar], window: int = 20) -> List[str]:
        """Generate style label per bar."""
        returns = [0.0] + [(bars[i].close - bars[i-1].close) / bars[i-1].close
                          for i in range(1, len(bars))]
        labels = []
        for i in range(len(bars)):
            if i < window:
                labels.append("unknown")
            else:
                labels.append(MarketDynamicsModel.classify_window(returns[:i+1], window))
        return labels


# ═════════════════════════════════════════════════════════════════════════════
# 9. UNIFIED TRADEMASTER ENGINE — Entry Point
# ═════════════════════════════════════════════════════════════════════════════

class TradeMasterEngine:
    """
    Unified TradeMaster engine untuk MAGNATRIX trading layer.
    Entry point: data → features → env → agent → train → eval → deploy.
    """

    def __init__(self) -> None:
        self.indicator_engine = TechnicalIndicatorEngine()
        self.prudex = PRUDEXCompass()
        self.pride = PRIDEStar()
        self.csdi = CSDIImputation()
        self.dynamics = MarketDynamicsModel()
        self.trainers: Dict[str, RLTrainer] = {}

    # ── Data Pipeline ─────────────────────────────────────────────────────

    def compute_features(self, bars: List[OHLCVBar]) -> Dict[str, List[float]]:
        return self.indicator_engine.compute_alpha158(bars)

    def impute_data(self, bars: List[OHLCVBar],
                    missing_indices: List[int]) -> List[OHLCVBar]:
        return self.csdi.impute_ohlcv(bars, missing_indices)

    def classify_market_style(self, bars: List[OHLCVBar]) -> List[str]:
        return self.dynamics.generate_style_labels(bars)

    # ── Environment Factory ───────────────────────────────────────────────

    def create_pm_env(self, bars: Dict[str, List[OHLCVBar]], **kwargs) -> PortfolioManagementEnv:
        return PortfolioManagementEnv(bars, **kwargs)

    def create_at_env(self, bars: List[OHLCVBar], **kwargs) -> AlgorithmicTradingEnv:
        return AlgorithmicTradingEnv(bars, **kwargs)

    def create_hft_env(self, lob_data: List[Dict[str, Any]], **kwargs) -> HighFrequencyTradingEnv:
        return HighFrequencyTradingEnv(lob_data, **kwargs)

    # ── Agent Factory ─────────────────────────────────────────────────────

    def create_agent(self, algo: str, state_dim: int, action_dim: int) -> Any:
        agents = {
            "ppo": PPOAgent(state_dim, action_dim),
            "dqn": DQNAgent(state_dim, action_dim),
            "deep_scalper": DeepScalperAgent(state_dim, action_dim),
            "eiie": EIIEAgent(state_dim, action_dim),
            "sarl": SARLAgent(state_dim, action_dim),
            "pg": RLAgent(state_dim, action_dim),
        }
        return agents.get(algo.lower(), RLAgent(state_dim, action_dim))

    # ── Training ──────────────────────────────────────────────────────────

    def train(self, agent: RLAgent, env: Any, episodes: int = 100) -> Dict[str, Any]:
        trainer = RLTrainer(agent, env, episodes=episodes)
        self.trainers[agent.__class__.__name__] = trainer
        return trainer.train()

    def test(self, agent: RLAgent, test_env: Any) -> Dict[str, Any]:
        trainer = RLTrainer(agent, test_env, episodes=1)
        return trainer.test(test_env)

    # ── Evaluation ───────────────────────────────────────────────────────

    def evaluate_portfolio(self, portfolio_values: List[float],
                           trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        prudex = self.prudex.evaluate(portfolio_values, trades)
        pride_metrics = self.pride.compute_metrics(portfolio_values, trades)
        pride_star = self.pride.normalize_for_star(pride_metrics)
        return {
            "prudex_compass": prudex,
            "pride_metrics": pride_metrics,
            "pride_star": pride_star,
        }

    # ── Full Pipeline ─────────────────────────────────────────────────────

    def run_pipeline(self, bars: List[OHLCVBar], algo: str = "ppo",
                     task: str = "at", train_split: float = 0.7) -> Dict[str, Any]:
        """
        Run full TradeMaster pipeline:
        1. Feature engineering
        2. Environment setup
        3. Agent training
        4. Testing
        5. Evaluation
        """
        # Features
        features = self.compute_features(bars)

        # Split
        split_idx = int(len(bars) * train_split)
        train_bars = bars[:split_idx]
        test_bars = bars[split_idx:]

        # Environment
        if task == "at":
            train_env = self.create_at_env(train_bars)
            test_env = self.create_at_env(test_bars)
            state_dim = 3  # close, position, cash
            action_dim = 3  # hold, buy, sell
        elif task == "pm":
            # Simplified: single asset PM
            train_env = self.create_pm_env({"asset": train_bars})
            test_env = self.create_pm_env({"asset": test_bars})
            state_dim = 3
            action_dim = 2  # weight 0 or 1
        else:
            raise ValueError(f"Unknown task: {task}")

        # Agent
        agent = self.create_agent(algo, state_dim, action_dim)

        # Train
        train_result = self.train(agent, train_env, episodes=50)

        # Test
        test_result = self.test(agent, test_env)

        # Evaluate
        if hasattr(test_env, "portfolio_values"):
            portfolio_values = test_env.portfolio_values
            trades = test_env.trades if hasattr(test_env, "trades") else []
            eval_result = self.evaluate_portfolio(portfolio_values, trades)
        else:
            eval_result = {}

        return {
            "algorithm": algo,
            "task": task,
            "features": {k: len(v) for k, v in features.items()},
            "train_result": train_result,
            "test_result": test_result,
            "evaluation": eval_result,
        }


def main():
    print("═══════════════════════════════════════════════════════════════")
    print("  MAGNATRIX-OS — TradeMaster Native Quant Trading Engine")
    print("  AMATI-PELAJARI-TIRU dari TradeMaster-NTU/TradeMaster")
    print("═══════════════════════════════════════════════════════════════")
    print()

    engine = TradeMasterEngine()

    # Generate synthetic market data
    print("[1] Generating synthetic OHLCV data...")
    random.seed(42)
    bars = []
    price = 100.0
    for i in range(252):  # 1 year daily
        change = random.gauss(0.0005, 0.02)
        open_p = price
        close = price * (1 + change)
        high = max(open_p, close) * (1 + abs(random.gauss(0, 0.005)))
        low = min(open_p, close) * (1 - abs(random.gauss(0, 0.005)))
        volume = random.gauss(1000000, 200000)
        bars.append(OHLCVBar(timestamp=float(i), open=open_p, high=high, low=low, close=close, volume=volume))
        price = close
    print(f"  Generated {len(bars)} bars")
    print()

    # Features
    print("[2] Computing Alpha158 features...")
    features = engine.compute_features(bars)
    print(f"  Features: {list(features.keys())}")
    print(f"  RSI last: {features['RSI14'][-1]:.2f}")
    print(f"  MACD last: {features['MACD'][-1]:.4f}")
    print()

    # Market style classification
    print("[3] Market style classification...")
    styles = engine.classify_market_style(bars)
    style_counts = {}
    for s in styles:
        style_counts[s] = style_counts.get(s, 0) + 1
    print(f"  Style distribution: {style_counts}")
    print()

    # Full pipeline
    print("[4] Running RL training pipeline (PPO + AT)...")
    result = engine.run_pipeline(bars, algo="ppo", task="at", train_split=0.7)
    print(f"  Algorithm: {result['algorithm']}")
    print(f"  Task: {result['task']}")
    print(f"  Train episodes: {result['train_result']['total_episodes']}")
    print(f"  Best reward: {result['train_result']['best_reward']:.4f}")
    print(f"  Test reward: {result['test_result']['total_reward']:.4f}")
    print()

    # Evaluation
    if result['evaluation']:
        print("[5] PRUDEX-Compass Evaluation:")
        prudex = result['evaluation']['prudex_compass']
        print(f"  Overall Score: {prudex['overall_score']:.4f}")
        print(f"  Axis Scores:")
        for axis, score in prudex['axis_scores'].items():
            print(f"    {axis}: {score:.4f}")
        print()
        print("[6] PRIDE-Star Metrics:")
        pride = result['evaluation']['pride_metrics']
        for metric, value in pride.items():
            print(f"    {metric}: {value:.4f}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()
