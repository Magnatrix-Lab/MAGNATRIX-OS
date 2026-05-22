---
name: bankr-defi
agent: executor
description: Execute DeFi operations via Bankr multi-chain infrastructure
schedule: "*/5 * * * *"
---

# bankr-defi

## Objective
Jalankan DeFi operations menggunakan Bankr AI agent platform: token swap, bridge, stake, portfolio tracking, dan token launch. Integrasi dengan MAGNATRIX trading engine untuk cross-chain arbitrage.

## Steps
1. Cek wallet balance dan chain connectivity.
2. Monitor market data untuk opportunity (spread, yield, launch).
3. Jika signal dari analyst valid (confidence > 0.75):
   - Swap: execute via Bankr router dengan slippage protection
   - Bridge: cross-chain transfer jika arbitrage detected
   - Stake: deposit ke highest-yield pool
4. Track portfolio PnL dan update knowledge graph.
5. Jika token launch opportunity (new trending), evaluate concept via 5 forces dan deploy jika score > 70.
6. Log semua transactions dengan tx hash ke knowledge graph.
7. Broadcast TRADE_EXECUTED ke mesh.

## Output
- Transaction log: {tx_hash, type, chain, from_token, to_token, amount, status}
- Portfolio snapshot: {total_value, chain_breakdown, pnl_24h}
- Mesh broadcast: msg_type=BANKR_TRADE_EXECUTED

## Exit Codes
- SKILL_OK: Operation executed successfully
- SKILL_PARTIAL: Sebagian executed, partial fill
- SKILL_FAIL: Insufficient balance, slippage exceeded, atau API error
