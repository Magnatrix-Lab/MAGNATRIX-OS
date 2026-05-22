---
name: scan-tokens
agent: scout
description: Scan token movements dan detect anomaly di pasar crypto
schedule: "*/5 * * * *"
---

# scan-tokens

## Objective
Pantau pergerakan token crypto (SOL ecosystem, ETH, BTC) dan deteksi anomaly seperti volume spike, price breakout, atau whale movement.

## Steps
1. Ambil data real-time dari Jupiter API untuk token pairs.
2. Scan DEX volume 1h/24h untuk perubahan > 2 std dev.
3. Cek on-chain data untuk whale wallet movement.
4. Generate signal jika ada anomaly yang memenuhi threshold.
5. Broadcast SIGNAL ke mesh dengan payload: symbol, price, change_24h, volume_spike, whale_alert.

## Output
- JSON signal: {symbol, price, change_24h, volume_spike, whale_alert, timestamp}
- Kirim ke mesh target=analyst jika anomaly detected

## Exit Codes
- SKILL_OK: Scan selesai, signal generated atau no anomaly
- SKILL_FAIL: API error atau data tidak valid
