---
name: analyze-signal
agent: analyst
description: Evaluasi sinyal trading dari scout
description: "*/10 * * * *"
---

# analyze-signal

## Objective
Evaluasi sinyal trading yang diterima dari scout. Berikan confidence score 0-1 dan rekomendasi tindakan.

## Steps
1. Terima payload sinyal (symbol, price, change_24h, volume_spike).
2. Cross-check dengan knowledge graph untuk historical pattern.
3. Hitung confidence score berdasarkan: trend alignment, volume confirmation, support/resistance level.
4. Jika confidence > 0.75, generate trade thesis dan kirim ke executor.
5. Jika confidence < 0.5, discard dan log alasan.

## Output
- JSON dengan fields: symbol, confidence, thesis, recommended_action, risk_level
- Kirim ke mesh target=executor jika confidence > 0.75

## Exit Codes
- SKILL_OK: Analisis selesai, output valid
- SKILL_FAIL: Data tidak valid atau error internal
