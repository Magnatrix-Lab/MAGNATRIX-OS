---
name: execute-trade
agent: executor
description: Eksekusi order trading via Jupiter atau exchange connector
schedule: "*/5 * * * *"
---

# execute-trade

## Objective
Eksekusi order trading yang sudah divalidasi oleh analyst dan lulus risk check guardian.

## Steps
1. Terima payload trade (symbol, side, amount, max_slippage).
2. Verifikasi preflight: cek balance, cek market open, cek rate limit.
3. Kirim order ke Jupiter API atau exchange connector.
4. Track order status sampai filled/cancelled.
5. Postflight: log ke knowledge graph, broadcast TRADE_EXECUTED ke mesh.

## Output
- JSON: {order_id, symbol, side, amount, filled_price, status, fees, timestamp}
- Broadcast TRADE_EXECUTED ke writer dan ops

## Exit Codes
- SKILL_OK: Trade executed successfully
- SKILL_FAIL: Order rejected atau error API
- SKILL_PARTIAL: Partial fill
