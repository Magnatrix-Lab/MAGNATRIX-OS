---
name: daily-digest
agent: writer
description: Generate daily digest dari aktivitas swarm
schedule: "0 0 * * *"
---

# daily-digest

## Objective
Generate daily digest yang merangkum semua aktivitas swarm: trading, research, ops, anomaly.

## Steps
1. Query knowledge graph untuk aktivitas 24h terakhir.
2. Aggregate: trades executed, research completed, ops alerts, anomaly count.
3. Generate narrative report dengan key highlights.
4. Format sebagai markdown digest.
5. Publish ke designated output channel (file, Telegram, chat bridge).

## Output
- Markdown file: digest_YYYY-MM-DD.md
- Broadcast DIGEST_PUBLISHED ke mesh

## Exit Codes
- SKILL_OK: Digest generated dan published
- SKILL_FAIL: Error query knowledge graph
