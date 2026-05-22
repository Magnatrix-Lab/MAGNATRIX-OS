---
name: check-risk
agent: guardian
description: Monitor risk exposure dan drawdown
schedule: "*/3 * * * *"
---

# check-risk

## Objective
Monitor seluruh posisi terbuka, hitung total exposure, drawdown, dan flag anomaly.

## Steps
1. Ambil snapshot semua posisi dari trading layer.
2. Hitung total NAV, unrealized PnL, drawdown % dari peak.
3. Cek apakah ada posisi melebihi max_position_size (default 10% NAV).
4. Jika drawdown > 15% atau ada posisi > 10%, trigger HALT ke swarm.
5. Log risk metrics ke knowledge graph.

## Output
- Risk report JSON: nav, drawdown_pct, max_position_pct, anomaly_flag, halt_triggered
- Broadcast HALT ke mesh jika threshold breached

## Exit Codes
- SKILL_OK: Risk dalam batas normal
- SKILL_HALT: Risk threshold breached, HALT triggered
- SKILL_FAIL: Error mengambil data posisi
