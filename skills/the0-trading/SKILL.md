---
id: the0-trading-engine
name: the0 Algorithmic Trading Engine
version: 1.0.0
category: trading
tags: [trading, algorithmic, bot, execution, strategy]
author: MAGNATRIX-OS
layer: 8
description: |
  Native algorithmic trading execution engine inspired by the0.
  Pola AMATI-PELAJARI-TIRU dari github.com/alexanderwanyoike/the0:
  - Master-worker reconciliation loops
  - Multi-strategy runtime dengan JSON Schema config
  - Execution models: scheduled, realtime, event-driven
  - Isolated bot execution dengan resource management
  - DAG dependency resolution untuk strategy pipeline

  Features:
  - 8 built-in strategies: SMA Crossover, RSI Momentum, Grid Trading,
    Mean Reversion, Breakout, Momentum, Arbitrage Scanner, AI Sentiment
  - Asyncio-based execution engine (reimagined dari Go gRPC)
  - MAGNATRIX mesh integration untuk signal broadcast
  - Telemetry integration untuk performance tracking
  - Emergency HALT mechanism swarm-wide

inputs:
  - name: strategy_id
    type: string
    description: Strategy definition ID (e.g., sma-crossover-v1)
    required: true
  - name: config
    type: object
    description: Strategy configuration matching JSON Schema
    required: true
  - name: execution_model
    type: string
    description: scheduled | realtime | event_driven
    default: scheduled
  - name: name
    type: string
    description: Bot instance name
    default: ""

outputs:
  - name: instance_id
    type: string
    description: Deployed bot instance ID
  - name: status
    type: string
    description: Bot deployment status
  - name: signal
    type: string
    description: Latest trading signal (BUY/SELL/HOLD)

execution:
  module: trading.the0_native_engine
  class: TradingOrchestrator
  method: create_bot

examples:
  - description: Deploy SMA Crossover bot
    input:
      strategy_id: sma-crossover-v1
      config:
        symbol: BTC/USDT
        fast_period: 10
        slow_period: 20
        initial_capital: 10000
      name: BTC-SMA-Bot

integration:
  mesh_channel: trading.signals
  telemetry_events: [strategy_execution, bot_state_change]
  halt_command: emergency_halt
