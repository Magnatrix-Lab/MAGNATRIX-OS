"""
the0_native_engine.py
========================
MAGNATRIX Native Algorithmic Trading Execution Engine
Layer 8: HFT Trading

Pola AMATI-PELAJARI-TIRU dari the0 (github.com/alexanderwanyoike/the0):
- Amati:  Microservices dengan master-worker pattern, NATS JetStream event streaming,
          multi-language SDK, reconciliation loops, containerized bot execution
- Pelajari: Core pattern adalah (1) Bot Definition JSON Schema, (2) Instance dengan config,
            (3) Execution Model (scheduled/realtime), (4) Master-Worker reconciliation,
            (5) Event-driven state machine, (6) Isolated resource management
- Tiru:   Reimplementasi native Python dengan:
            - Asyncio-based execution engine (bukan Go gRPC)
            - In-memory + Redis state (bukan MongoDB + NATS)
            - Python-native strategy runtime (bukan multi-language container)
            - DAG dependency resolution untuk strategy pipeline
            - Integration dengan existing MAGNATRIX: mesh messaging, skill registry,
              pipeline executor, free LLM router, telemetry

Architecture:
    StrategyDefinition (JSON Schema config)
        ↓
    StrategyInstance (config values + state)
        ↓
    ExecutionEngine (master-worker reconciliation)
        ↓
    BotRunner (realtime) / BotScheduler (cron)
        ↓
    StrategyRuntime (isolated async execution)
        ↓
    ResultAggregator → mesh broadcast → telemetry
"""

import asyncio
import json
import hashlib
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Union
from enum import Enum, auto
from collections import defaultdict
import threading
import inspect


class ExecutionModel(Enum):
    SCHEDULED = auto()   # Cron-based execution
    REALTIME = auto()    # Continuous streaming execution
    EVENT_DRIVEN = auto()  # Triggered by mesh SIGNAL


class BotState(Enum):
    PENDING = "pending"
    DEPLOYING = "deploying"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class StrategyDefinition:
    """Reusable bot definition - inspired by the0's custom bot concept"""
    id: str
    name: str
    version: str
    description: str = ""
    # JSON Schema untuk parameter konfigurasi
    config_schema: Dict = field(default_factory=dict)
    # Strategy function reference (Python native - tiru multi-language dengan single runtime)
    strategy_module: str = ""
    strategy_entrypoint: str = "execute"
    # Execution model
    default_execution_model: ExecutionModel = ExecutionModel.SCHEDULED
    # Resource limits
    max_memory_mb: int = 512
    timeout_seconds: int = 300
    # Dependencies antar strategy (DAG)
    dependencies: List[str] = field(default_factory=list)
    # Risk parameters
    max_drawdown_pct: float = 5.0
    max_position_size: float = 1000.0
    # Metadata
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def validate_config(self, config: Dict) -> tuple[bool, List[str]]:
        """Validasi config terhadap JSON Schema"""
        errors = []
        required = self.config_schema.get("required", [])
        properties = self.config_schema.get("properties", {})

        for key in required:
            if key not in config:
                errors.append(f"Missing required field: {key}")

        for key, value in config.items():
            if key in properties:
                prop = properties[key]
                ptype = prop.get("type")
                if ptype == "number" and not isinstance(value, (int, float)):
                    errors.append(f"{key}: expected number, got {type(value).__name__}")
                elif ptype == "string" and not isinstance(value, str):
                    errors.append(f"{key}: expected string, got {type(value).__name__}")
                elif ptype == "boolean" and not isinstance(value, bool):
                    errors.append(f"{key}: expected boolean, got {type(value).__name__}")

        return len(errors) == 0, errors

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["default_execution_model"] = self.default_execution_model.name
        return d


@dataclass
class StrategyInstance:
    """Running deployment of a StrategyDefinition - tiru the0 bot instance"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    definition_id: str = ""
    name: str = ""
    # Configuration values
    config: Dict = field(default_factory=dict)
    # Execution settings
    execution_model: ExecutionModel = ExecutionModel.SCHEDULED
    # Schedule (untuk SCHEDULED model)
    cron_expression: str = "*/5 * * * *"  # default: every 5 minutes
    # Runtime state
    state: BotState = BotState.PENDING
    # History
    execution_count: int = 0
    last_execution_at: Optional[float] = None
    last_result: Optional[Dict] = None
    last_error: Optional[str] = None
    total_pnl: float = 0.0
    max_drawdown_seen: float = 0.0
    # Resource tracking
    memory_usage_mb: float = 0.0
    cpu_usage_pct: float = 0.0
    # Lifecycle
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    stopped_at: Optional[float] = None
    # Mesh integration
    mesh_channel: str = "trading.signals"
    # Reconciliation
    desired_state: BotState = BotState.RUNNING
    current_state: BotState = BotState.PENDING
    reconciliation_generation: int = 0

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["state"] = self.state.value
        d["execution_model"] = self.execution_model.name
        d["desired_state"] = self.desired_state.value
        d["current_state"] = self.current_state.value
        return d


@dataclass
class ExecutionResult:
    """Hasil eksekusi strategy - tiru the0 SDK result pattern"""
    instance_id: str
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp: float = field(default_factory=time.time)
    status: str = "success"  # success, error, timeout, halted
    # Trading-specific outputs
    signal: Optional[str] = None  # BUY, SELL, HOLD
    confidence: float = 0.0
    position_size: float = 0.0
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    pnl: float = 0.0
    # Metadata
    execution_time_ms: float = 0.0
    memory_peak_mb: float = 0.0
    logs: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    # Error info
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)

    def emit_metric(self, name: str, value: float, unit: str = "count"):
        """Tiru the0 SDK metric() function"""
        self.metrics[f"{name}:{unit}"] = value

    def log(self, message: str, level: str = "info"):
        """Tiru the0 SDK log() function"""
        self.logs.append(f"[{level.upper()}] {time.time():.3f} {message}")


class StrategyRuntime:
    """
    Isolated strategy execution environment.
    Tiru the0's containerized execution tapi native Python asyncio.
    """

    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self._semaphore = asyncio.Semaphore(max_workers)
        self._active_executions: Dict[str, asyncio.Task] = {}
        self._strategy_registry: Dict[str, Callable] = {}
        self._execution_history: List[ExecutionResult] = []
        self._lock = asyncio.Lock()

    def register_strategy(self, name: str, func: Callable):
        """Register a strategy function - tiru the0 SDK multi-language dengan Python native"""
        self._strategy_registry[name] = func

    def register_builtin_strategies(self):
        """Register built-in strategies - amati dari the0 pattern"""
        self.register_strategy("sma_crossover", self._sma_crossover)
        self.register_strategy("rsi_momentum", self._rsi_momentum)
        self.register_strategy("grid_trading", self._grid_trading)
        self.register_strategy("mean_reversion", self._mean_reversion)
        self.register_strategy("breakout", self._breakout_strategy)
        self.register_strategy("momentum", self._momentum_strategy)
        self.register_strategy("arbitrage", self._arbitrage_scanner)
        self.register_strategy("sentiment", self._sentiment_analysis)

    async def execute(self, instance: StrategyInstance, 
                      market_data: Optional[Dict] = None,
                      portfolio: Optional[Dict] = None) -> ExecutionResult:
        """Execute strategy with isolation - tiru the0 Bot Runner"""

        definition = instance.definition_id  # Would be resolved from registry
        execution_id = str(uuid.uuid4())[:12]
        start_time = time.time()

        result = ExecutionResult(
            instance_id=instance.id,
            execution_id=execution_id
        )

        async with self._semaphore:
            try:
                # Resource isolation via semaphore (tiru container isolation)
                # In production: use subprocess/subinterpreter untuk true isolation

                # Resolve strategy function
                strategy_func = self._strategy_registry.get(
                    instance.config.get("strategy_name", "sma_crossover"),
                    self._sma_crossover
                )

                # Prepare execution context - tiru the0 SDK parse() concept
                ctx = ExecutionContext(
                    config=instance.config,
                    market_data=market_data or {},
                    portfolio=portfolio or {},
                    state=instance.to_dict(),
                    result=result
                )

                # Execute with timeout
                task = asyncio.create_task(strategy_func(ctx))
                self._active_executions[execution_id] = task

                await asyncio.wait_for(task, timeout=instance.config.get("timeout", 300))

                result.execution_time_ms = (time.time() - start_time) * 1000
                result.status = "success"
                instance.execution_count += 1
                instance.last_execution_at = time.time()
                instance.last_result = result.to_dict()

            except asyncio.TimeoutError:
                result.status = "timeout"
                result.error_message = f"Execution timed out after {instance.config.get('timeout', 300)}s"
                result.log("TIMEOUT: Strategy execution exceeded time limit", "error")
            except Exception as e:
                result.status = "error"
                result.error_message = str(e)
                result.error_traceback = traceback.format_exc()
                result.log(f"ERROR: {e}", "error")
                instance.last_error = str(e)
                instance.state = BotState.ERROR
            finally:
                self._active_executions.pop(execution_id, None)
                self._execution_history.append(result)
                # Keep last 1000 results
                if len(self._execution_history) > 1000:
                    self._execution_history = self._execution_history[-1000:]

        return result

    def halt_execution(self, execution_id: str) -> bool:
        """Halt running execution - tiru the0 HALT mechanism via mesh"""
        task = self._active_executions.get(execution_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    # ==================== BUILT-IN STRATEGIES ====================
    # Tiru the0 pattern: strategy logic di-isolate, config via JSON Schema

    async def _sma_crossover(self, ctx: 'ExecutionContext'):
        """SMA Crossover - amati dari trading engine klasik, tiru dengan async"""
        cfg = ctx.config
        fast_period = cfg.get("fast_period", 10)
        slow_period = cfg.get("slow_period", 20)
        symbol = cfg.get("symbol", "BTC/USDT")

        prices = ctx.market_data.get("prices", [])
        if len(prices) < slow_period:
            ctx.result.log(f"Insufficient data: {len(prices)} < {slow_period}")
            ctx.result.signal = "HOLD"
            return

        fast_sma = sum(prices[-fast_period:]) / fast_period
        slow_sma = sum(prices[-slow_period:]) / slow_period

        ctx.result.emit_metric("fast_sma", fast_sma)
        ctx.result.emit_metric("slow_sma", slow_sma)
        ctx.result.emit_metric("price", prices[-1])

        if fast_sma > slow_sma:
            ctx.result.signal = "BUY"
            ctx.result.confidence = min(abs(fast_sma - slow_sma) / slow_sma * 100, 100)
        elif fast_sma < slow_sma:
            ctx.result.signal = "SELL"
            ctx.result.confidence = min(abs(fast_sma - slow_sma) / slow_sma * 100, 100)
        else:
            ctx.result.signal = "HOLD"
            ctx.result.confidence = 0.0

        ctx.result.log(f"SMA Crossover: fast={fast_sma:.2f} slow={slow_sma:.2f} signal={ctx.result.signal}")

    async def _rsi_momentum(self, ctx: 'ExecutionContext'):
        """RSI Momentum Strategy"""
        cfg = ctx.config
        period = cfg.get("period", 14)
        oversold = cfg.get("oversold", 30)
        overbought = cfg.get("overbought", 70)
        prices = ctx.market_data.get("prices", [])

        if len(prices) < period + 1:
            ctx.result.signal = "HOLD"
            return

        # Calculate RSI
        gains = losses = 0
        for i in range(1, period + 1):
            diff = prices[-i] - prices[-i-1]
            if diff > 0:
                gains += diff
            else:
                losses += abs(diff)

        avg_gain = gains / period
        avg_loss = losses / period
        rs = avg_gain / avg_loss if avg_loss > 0 else float('inf')
        rsi = 100 - (100 / (1 + rs))

        ctx.result.emit_metric("rsi", rsi)

        if rsi < oversold:
            ctx.result.signal = "BUY"
            ctx.result.confidence = (oversold - rsi) / oversold * 100
        elif rsi > overbought:
            ctx.result.signal = "SELL"
            ctx.result.confidence = (rsi - overbought) / (100 - overbought) * 100
        else:
            ctx.result.signal = "HOLD"

        ctx.result.log(f"RSI: {rsi:.2f} signal={ctx.result.signal}")

    async def _grid_trading(self, ctx: 'ExecutionContext'):
        """Grid Trading Strategy"""
        cfg = ctx.config
        grid_levels = cfg.get("grid_levels", 10)
        grid_spacing = cfg.get("grid_spacing", 0.01)  # 1%
        current_price = ctx.market_data.get("current_price", 0)

        if current_price <= 0:
            ctx.result.signal = "HOLD"
            return

        # Calculate grid
        upper = current_price * (1 + grid_spacing * grid_levels / 2)
        lower = current_price * (1 - grid_spacing * grid_levels / 2)

        ctx.result.emit_metric("grid_upper", upper)
        ctx.result.emit_metric("grid_lower", lower)
        ctx.result.emit_metric("grid_center", current_price)

        # Simplified: always set BUY at lower grid, SELL at upper
        position = ctx.portfolio.get("position", 0)
        if position == 0:
            ctx.result.signal = "BUY"
            ctx.result.entry_price = lower
        else:
            ctx.result.signal = "HOLD"

        ctx.result.log(f"Grid: upper={upper:.2f} lower={lower:.2f} center={current_price:.2f}")

    async def _mean_reversion(self, ctx: 'ExecutionContext'):
        """Mean Reversion Strategy"""
        cfg = ctx.config
        lookback = cfg.get("lookback", 20)
        threshold = cfg.get("zscore_threshold", 2.0)
        prices = ctx.market_data.get("prices", [])

        if len(prices) < lookback:
            ctx.result.signal = "HOLD"
            return

        recent = prices[-lookback:]
        mean = sum(recent) / len(recent)
        variance = sum((p - mean) ** 2 for p in recent) / len(recent)
        std = variance ** 0.5

        current = prices[-1]
        zscore = (current - mean) / std if std > 0 else 0

        ctx.result.emit_metric("zscore", zscore)
        ctx.result.emit_metric("mean", mean)

        if zscore < -threshold:
            ctx.result.signal = "BUY"
            ctx.result.confidence = min(abs(zscore) / threshold * 100, 100)
        elif zscore > threshold:
            ctx.result.signal = "SELL"
            ctx.result.confidence = min(abs(zscore) / threshold * 100, 100)
        else:
            ctx.result.signal = "HOLD"

        ctx.result.log(f"MeanReversion: z={zscore:.2f} signal={ctx.result.signal}")

    async def _breakout_strategy(self, ctx: 'ExecutionContext'):
        """Breakout Strategy"""
        cfg = ctx.config
        lookback = cfg.get("lookback", 20)
        prices = ctx.market_data.get("prices", [])

        if len(prices) < lookback:
            ctx.result.signal = "HOLD"
            return

        recent = prices[-lookback:]
        high = max(recent)
        low = min(recent)
        current = prices[-1]

        ctx.result.emit_metric("resistance", high)
        ctx.result.emit_metric("support", low)

        if current > high * 0.995:
            ctx.result.signal = "BUY"
            ctx.result.confidence = (current - high) / high * 100 if high > 0 else 0
            ctx.result.take_profit = current * 1.05
            ctx.result.stop_loss = low
        elif current < low * 1.005:
            ctx.result.signal = "SELL"
            ctx.result.confidence = (low - current) / low * 100 if low > 0 else 0
        else:
            ctx.result.signal = "HOLD"

        ctx.result.log(f"Breakout: H={high:.2f} L={low:.2f} C={current:.2f} signal={ctx.result.signal}")

    async def _momentum_strategy(self, ctx: 'ExecutionContext'):
        """Momentum Strategy"""
        cfg = ctx.config
        short_period = cfg.get("short_period", 5)
        long_period = cfg.get("long_period", 20)
        prices = ctx.market_data.get("prices", [])

        if len(prices) < long_period:
            ctx.result.signal = "HOLD"
            return

        short_return = (prices[-1] - prices[-short_period]) / prices[-short_period] if prices[-short_period] > 0 else 0
        long_return = (prices[-1] - prices[-long_period]) / prices[-long_period] if prices[-long_period] > 0 else 0

        ctx.result.emit_metric("short_momentum", short_return * 100)
        ctx.result.emit_metric("long_momentum", long_return * 100)

        if short_return > long_return * 1.5 and short_return > 0:
            ctx.result.signal = "BUY"
            ctx.result.confidence = min(short_return * 100, 100)
        elif short_return < long_return * 0.5 and short_return < 0:
            ctx.result.signal = "SELL"
            ctx.result.confidence = min(abs(short_return) * 100, 100)
        else:
            ctx.result.signal = "HOLD"

    async def _arbitrage_scanner(self, ctx: 'ExecutionContext'):
        """Cross-Exchange Arbitrage Scanner"""
        cfg = ctx.config
        min_spread = cfg.get("min_spread_pct", 0.5)
        exchanges = ctx.market_data.get("exchanges", {})

        if len(exchanges) < 2:
            ctx.result.signal = "HOLD"
            return

        prices = {ex: data.get("price", 0) for ex, data in exchanges.items()}
        valid_prices = {k: v for k, v in prices.items() if v > 0}

        if len(valid_prices) < 2:
            ctx.result.signal = "HOLD"
            return

        min_price = min(valid_prices.values())
        max_price = max(valid_prices.values())
        spread_pct = (max_price - min_price) / min_price * 100 if min_price > 0 else 0

        ctx.result.emit_metric("spread_pct", spread_pct)
        ctx.result.emit_metric("min_price", min_price)
        ctx.result.emit_metric("max_price", max_price)

        if spread_pct > min_spread:
            buy_ex = min(valid_prices, key=valid_prices.get)
            sell_ex = max(valid_prices, key=valid_prices.get)
            ctx.result.signal = "BUY"
            ctx.result.confidence = min(spread_pct, 100)
            ctx.result.log(f"Arbitrage: {spread_pct:.2f}% spread between {buy_ex} and {sell_ex}")
        else:
            ctx.result.signal = "HOLD"

    async def _sentiment_analysis(self, ctx: 'ExecutionContext'):
        """Sentiment-Based Strategy using MAGNATRIX LLM"""
        cfg = ctx.config
        symbol = cfg.get("symbol", "BTC")
        sentiment_source = cfg.get("source", "mesh")  # mesh, twitter, reddit, news

        # Would integrate with MAGNATRIX mesh messaging untuk sentiment
        sentiment_score = ctx.market_data.get("sentiment", 0.5)
        volume = ctx.market_data.get("volume", 0)

        ctx.result.emit_metric("sentiment", sentiment_score)
        ctx.result.emit_metric("volume", volume)

        if sentiment_score > 0.7 and volume > cfg.get("volume_threshold", 1000):
            ctx.result.signal = "BUY"
            ctx.result.confidence = sentiment_score * 100
        elif sentiment_score < 0.3 and volume > cfg.get("volume_threshold", 1000):
            ctx.result.signal = "SELL"
            ctx.result.confidence = (1 - sentiment_score) * 100
        else:
            ctx.result.signal = "HOLD"

        ctx.result.log(f"Sentiment: {sentiment_score:.2f} vol={volume} signal={ctx.result.signal}")


@dataclass
class ExecutionContext:
    """Tiru the0 SDK execution context - disediakan ke setiap strategy"""
    config: Dict
    market_data: Dict
    portfolio: Dict
    state: Dict
    result: ExecutionResult


class MasterWorkerEngine:
    """
    Master-Worker execution engine dengan reconciliation loop.
    Tiru the0's runtime services: master handles workload allocation,
    workers instantiate bots via reconciliation loops.
    """

    def __init__(self, num_workers: int = 4):
        self.num_workers = num_workers
        self.workers: List[BotWorker] = []
        self.instance_registry: Dict[str, StrategyInstance] = {}
        self.definition_registry: Dict[str, StrategyDefinition] = {}
        self.runtime = StrategyRuntime(max_workers=num_workers * 2)
        self._reconciliation_task: Optional[asyncio.Task] = None
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running = False
        self._mesh_broadcast: Optional[Callable] = None
        self._telemetry_callback: Optional[Callable] = None

        # Register built-in strategies
        self.runtime.register_builtin_strategies()

    def connect_mesh(self, broadcast_fn: Callable):
        """Connect to MAGNATRIX mesh messaging"""
        self._mesh_broadcast = broadcast_fn

    def connect_telemetry(self, telemetry_fn: Callable):
        """Connect to MAGNATRIX telemetry"""
        self._telemetry_callback = telemetry_fn

    def register_definition(self, definition: StrategyDefinition):
        """Register strategy definition - tiru the0 custom bot registration"""
        self.definition_registry[definition.id] = definition

    def deploy_instance(self, definition_id: str, config: Dict, 
                        name: str = "", execution_model: ExecutionModel = None) -> StrategyInstance:
        """Deploy instance - tiru the0 CLI deploy"""
        definition = self.definition_registry.get(definition_id)
        if not definition:
            raise ValueError(f"Definition {definition_id} not found")

        valid, errors = definition.validate_config(config)
        if not valid:
            raise ValueError(f"Config validation failed: {errors}")

        instance = StrategyInstance(
            definition_id=definition_id,
            name=name or f"{definition.name}-{uuid.uuid4().hex[:4]}",
            config=config,
            execution_model=execution_model or definition.default_execution_model
        )
        self.instance_registry[instance.id] = instance
        return instance

    async def start(self):
        """Start master-worker engine dengan reconciliation loop"""
        self._running = True

        # Spawn workers
        for i in range(self.num_workers):
            worker = BotWorker(worker_id=i, engine=self)
            self.workers.append(worker)
            asyncio.create_task(worker.run())

        # Start reconciliation loop - tiru the0 master reconciliation
        self._reconciliation_task = asyncio.create_task(self._reconciliation_loop())

        # Start scheduler untuk cron-based instances
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

        # Start realtime event loop
        asyncio.create_task(self._realtime_loop())

    async def stop(self):
        """Graceful shutdown"""
        self._running = False

        for worker in self.workers:
            await worker.stop()

        if self._reconciliation_task:
            self._reconciliation_task.cancel()
        if self._scheduler_task:
            self._scheduler_task.cancel()

    async def _reconciliation_loop(self, interval: float = 5.0):
        """
        Reconciliation loop - core the0 pattern.
        Bandingkan desired_state vs current_state, lakukan aksi untuk converge.
        """
        while self._running:
            try:
                for instance_id, instance in self.instance_registry.items():
                    if instance.desired_state != instance.current_state:
                        # Reconcile
                        if instance.desired_state == BotState.RUNNING and instance.current_state != BotState.RUNNING:
                            instance.current_state = BotState.DEPLOYING
                            await self._assign_to_worker(instance)
                        elif instance.desired_state == BotState.STOPPED and instance.current_state == BotState.RUNNING:
                            await self._stop_instance(instance)
                            instance.current_state = BotState.STOPPED
                        elif instance.desired_state == BotState.PAUSED:
                            instance.current_state = BotState.PAUSED

                        instance.reconciliation_generation += 1

                        # Broadcast state change
                        if self._mesh_broadcast:
                            self._mesh_broadcast({
                                "type": "BOT_STATE_CHANGE",
                                "instance_id": instance.id,
                                "from": instance.current_state.value,
                                "to": instance.desired_state.value,
                                "generation": instance.reconciliation_generation
                            })

                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Reconciliation error: {e}")
                await asyncio.sleep(interval)

    async def _scheduler_loop(self, tick_interval: float = 1.0):
        """Cron scheduler - tiru the0 Bot Scheduler"""
        while self._running:
            try:
                now = time.time()
                for instance in self.instance_registry.values():
                    if (instance.execution_model == ExecutionModel.SCHEDULED and 
                        instance.desired_state == BotState.RUNNING and
                        instance.current_state == BotState.RUNNING):

                        # Simple cron check (would use croniter library in production)
                        if self._should_run_cron(instance.cron_expression, now, instance.last_execution_at):
                            await self._execute_instance(instance)

                await asyncio.sleep(tick_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Scheduler error: {e}")
                await asyncio.sleep(tick_interval)

    async def _realtime_loop(self):
        """Realtime execution loop untuk REALTIME model"""
        while self._running:
            try:
                for instance in self.instance_registry.values():
                    if (instance.execution_model == ExecutionModel.REALTIME and
                        instance.desired_state == BotState.RUNNING and
                        instance.current_state == BotState.RUNNING):

                        await self._execute_instance(instance)

                        # Throttle based on config
                        await asyncio.sleep(instance.config.get("tick_interval", 1.0))

                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Realtime error: {e}")
                await asyncio.sleep(1)

    def _should_run_cron(self, cron: str, now: float, last_run: Optional[float]) -> bool:
        """Simplified cron check - would use croniter in production"""
        if last_run is None:
            return True
        # Default: run every 5 minutes
        return (now - last_run) >= 300

    async def _assign_to_worker(self, instance: StrategyInstance):
        """Assign instance to least-loaded worker"""
        if not self.workers:
            return

        # Find worker dengan fewest active instances
        worker = min(self.workers, key=lambda w: len(w.instances))
        await worker.add_instance(instance)
        instance.current_state = BotState.RUNNING
        instance.started_at = time.time()

    async def _stop_instance(self, instance: StrategyInstance):
        """Stop instance dan cleanup"""
        for worker in self.workers:
            if instance.id in worker.instances:
                await worker.remove_instance(instance)
        instance.stopped_at = time.time()

    async def _execute_instance(self, instance: StrategyInstance) -> ExecutionResult:
        """Execute instance melalui StrategyRuntime"""
        # Fetch market data (would integrate dengan exchange APIs)
        market_data = await self._fetch_market_data(instance)
        portfolio = await self._fetch_portfolio(instance)

        result = await self.runtime.execute(instance, market_data, portfolio)

        # Update instance PnL tracking
        instance.total_pnl += result.pnl
        if result.pnl < 0:
            dd = abs(result.pnl) / instance.config.get("initial_capital", 10000) * 100
            instance.max_drawdown_seen = max(instance.max_drawdown_seen, dd)

        # Telemetry
        if self._telemetry_callback:
            self._telemetry_callback({
                "metric": "strategy_execution",
                "instance_id": instance.id,
                "execution_time_ms": result.execution_time_ms,
                "signal": result.signal,
                "pnl": result.pnl,
                "status": result.status
            })

        # Mesh broadcast result
        if self._mesh_broadcast and result.signal in ("BUY", "SELL"):
            self._mesh_broadcast({
                "type": "SIGNAL",
                "channel": instance.mesh_channel,
                "instance_id": instance.id,
                "signal": result.signal,
                "confidence": result.confidence,
                "symbol": instance.config.get("symbol", "UNKNOWN"),
                "timestamp": time.time()
            })

        return result

    async def _fetch_market_data(self, instance: StrategyInstance) -> Dict:
        """Fetch market data - placeholder untuk exchange integration"""
        # Would integrate dengan exchange APIs, MAGNATRIX mesh, atau data feeds
        symbol = instance.config.get("symbol", "BTC/USDT")
        return {
            "symbol": symbol,
            "prices": [45000 + i * 10 for i in range(50)],  # Simulated
            "current_price": 45490,
            "volume": 15000,
            "sentiment": 0.6,
            "timestamp": time.time()
        }

    async def _fetch_portfolio(self, instance: StrategyInstance) -> Dict:
        """Fetch portfolio state"""
        return {
            "cash": instance.config.get("initial_capital", 10000),
            "position": 0,
            "unrealized_pnl": 0,
            "realized_pnl": instance.total_pnl
        }

    def halt_all(self):
        """Emergency halt - tiru the0 HALT mechanism via swarm"""
        for instance in self.instance_registry.values():
            instance.desired_state = BotState.STOPPED
        for execution_id in list(self.runtime._active_executions.keys()):
            self.runtime.halt_execution(execution_id)


class BotWorker:
    """
    Worker process untuk bot execution.
    Tiru the0's worker concept tapi asyncio-based.
    """

    def __init__(self, worker_id: int, engine: MasterWorkerEngine):
        self.worker_id = worker_id
        self.engine = engine
        self.instances: Dict[str, StrategyInstance] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def run(self):
        self._running = True
        while self._running:
            await asyncio.sleep(1)

    async def stop(self):
        self._running = False
        for instance in list(self.instances.values()):
            await self.remove_instance(instance)

    async def add_instance(self, instance: StrategyInstance):
        self.instances[instance.id] = instance

    async def remove_instance(self, instance: StrategyInstance):
        self.instances.pop(instance.id, None)


class TradingOrchestrator:
    """
    High-level orchestrator untuk Layer 8 Trading.
    Integrasi dengan MAGNATRIX ecosystem.
    """

    def __init__(self):
        self.engine = MasterWorkerEngine(num_workers=4)
        self._running = False

    async def initialize(self):
        """Register default strategy definitions"""
        definitions = [
            StrategyDefinition(
                id="sma-crossover-v1",
                name="SMA Crossover",
                version="1.0.0",
                description="Simple Moving Average crossover strategy",
                config_schema={
                    "type": "object",
                    "required": ["symbol", "fast_period", "slow_period"],
                    "properties": {
                        "symbol": {"type": "string", "default": "BTC/USDT"},
                        "fast_period": {"type": "number", "default": 10},
                        "slow_period": {"type": "number", "default": 20},
                        "initial_capital": {"type": "number", "default": 10000},
                        "strategy_name": {"type": "string", "default": "sma_crossover"}
                    }
                },
                default_execution_model=ExecutionModel.SCHEDULED
            ),
            StrategyDefinition(
                id="rsi-momentum-v1",
                name="RSI Momentum",
                version="1.0.0",
                description="RSI-based momentum strategy",
                config_schema={
                    "type": "object",
                    "required": ["symbol", "period"],
                    "properties": {
                        "symbol": {"type": "string", "default": "ETH/USDT"},
                        "period": {"type": "number", "default": 14},
                        "oversold": {"type": "number", "default": 30},
                        "overbought": {"type": "number", "default": 70},
                        "initial_capital": {"type": "number", "default": 10000},
                        "strategy_name": {"type": "string", "default": "rsi_momentum"}
                    }
                },
                default_execution_model=ExecutionModel.SCHEDULED
            ),
            StrategyDefinition(
                id="grid-trading-v1",
                name="Grid Trading",
                version="1.0.0",
                description="Grid trading bot",
                config_schema={
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "default": "BTC/USDT"},
                        "grid_levels": {"type": "number", "default": 10},
                        "grid_spacing": {"type": "number", "default": 0.01},
                        "initial_capital": {"type": "number", "default": 10000},
                        "strategy_name": {"type": "string", "default": "grid_trading"}
                    }
                },
                default_execution_model=ExecutionModel.REALTIME
            ),
            StrategyDefinition(
                id="arbitrage-scanner-v1",
                name="Arbitrage Scanner",
                version="1.0.0",
                description="Cross-exchange arbitrage scanner",
                config_schema={
                    "type": "object",
                    "properties": {
                        "exchanges": {"type": "array", "default": ["binance", "kraken", "coinbase"]},
                        "min_spread_pct": {"type": "number", "default": 0.5},
                        "tick_interval": {"type": "number", "default": 1.0},
                        "strategy_name": {"type": "string", "default": "arbitrage"}
                    }
                },
                default_execution_model=ExecutionModel.REALTIME
            ),
            StrategyDefinition(
                id="sentiment-ai-v1",
                name="AI Sentiment Trader",
                version="1.0.0",
                description="LLM-powered sentiment analysis trading",
                config_schema={
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "default": "BTC"},
                        "source": {"type": "string", "default": "mesh"},
                        "volume_threshold": {"type": "number", "default": 1000},
                        "strategy_name": {"type": "string", "default": "sentiment"}
                    }
                },
                default_execution_model=ExecutionModel.EVENT_DRIVEN
            ),
        ]

        for definition in definitions:
            self.engine.register_definition(definition)

    async def start(self):
        await self.engine.start()
        self._running = True

    async def stop(self):
        await self.engine.stop()
        self._running = False

    def create_bot(self, strategy_id: str, config: Dict, name: str = "") -> StrategyInstance:
        """Create and deploy trading bot"""
        instance = self.engine.deploy_instance(strategy_id, config, name)
        instance.desired_state = BotState.RUNNING
        return instance

    def stop_bot(self, instance_id: str):
        """Stop specific bot"""
        instance = self.engine.instance_registry.get(instance_id)
        if instance:
            instance.desired_state = BotState.STOPPED

    def pause_bot(self, instance_id: str):
        """Pause bot"""
        instance = self.engine.instance_registry.get(instance_id)
        if instance:
            instance.desired_state = BotState.PAUSED

    def resume_bot(self, instance_id: str):
        """Resume bot"""
        instance = self.engine.instance_registry.get(instance_id)
        if instance:
            instance.desired_state = BotState.RUNNING

    def get_status(self) -> Dict:
        """Get full system status"""
        return {
            "running": self._running,
            "definitions": len(self.engine.definition_registry),
            "instances": {
                iid: inst.to_dict() 
                for iid, inst in self.engine.instance_registry.items()
            },
            "workers": [
                {
                    "id": w.worker_id,
                    "instances": len(w.instances)
                }
                for w in self.engine.workers
            ],
            "active_executions": len(self.engine.runtime._active_executions),
            "execution_history": len(self.engine.runtime._execution_history)
        }

    def emergency_halt(self):
        """Emergency halt all trading - swarm HALT mechanism"""
        self.engine.halt_all()


# ==================== FAST API ENDPOINT ====================

"""
Integration dengan MAGNATRIX API Gateway:

from fastapi import FastAPI
app = FastAPI()
orchestrator = TradingOrchestrator()

@app.post("/trading/bots")
async def create_bot(strategy_id: str, config: dict, name: str = ""):
    return orchestrator.create_bot(strategy_id, config, name)

@app.get("/trading/status")
async def get_status():
    return orchestrator.get_status()

@app.post("/trading/halt")
async def emergency_halt():
    orchestrator.emergency_halt()
    return {"status": "halted"}
"""


if __name__ == "__main__":
    import traceback

    async def demo():
        orch = TradingOrchestrator()
        await orch.initialize()
        await orch.start()

        # Deploy SMA Crossover bot
        bot = orch.create_bot("sma-crossover-v1", {
            "symbol": "BTC/USDT",
            "fast_period": 10,
            "slow_period": 20,
            "initial_capital": 10000,
            "strategy_name": "sma_crossover"
        }, name="Demo-SMA-Bot")

        print(f"Deployed bot: {bot.id} - {bot.name}")

        # Wait for execution
        await asyncio.sleep(2)

        # Check status
        status = orch.get_status()
        print(json.dumps(status, indent=2, default=str))

        await orch.stop()

    asyncio.run(demo())
