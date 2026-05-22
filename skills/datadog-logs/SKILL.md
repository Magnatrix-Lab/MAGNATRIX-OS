---
name: datadog-logs
agent: ops
description: Monitor dan analyze logs via Datadog untuk anomaly detection dan alerting
schedule: "*/5 * * * *"
---

# datadog-logs

## Objective
Integrasi dengan Datadog (atau log aggregation system) untuk monitor MAGNATRIX logs, detect anomaly patterns, dan generate alerts.

## Steps
1. Query Datadog Logs API untuk log entries 5 menit terakhir.
2. Filter berdasarkan service tags: magnatrix-kernel, magnatrix-trading, magnatrix-governance.
3. Aggregate log levels: ERROR count, WARN count, INFO volume.
4. Detect anomaly patterns: error spikes, repeated exceptions, latency outliers.
5. Cek apakah ada correlation antara error spike dan trading activity atau governance decisions.
6. Jika anomaly detected dan melebihi threshold (e.g. 10x baseline), broadcast ALERT ke mesh.
7. Generate incident report dengan affected services dan suggested actions.
8. Log ke knowledge graph sebagai incident entity.

## Output
- Log report: {period, total_logs, error_count, warn_count, anomaly_detected, alert_level}
- Mesh broadcast: msg_type=LOG_ALERT jika anomaly
- Knowledge entity: type=incident

## Exit Codes
- SKILL_OK: Logs normal, no anomaly
- SKILL_WARN: Anomaly detected tapi within acceptable range
- SKILL_FAIL: Datadog API error atau query timeout
