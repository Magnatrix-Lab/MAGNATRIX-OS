# context-stats Integration — MAGNATRIX Agentic OS

> **Repo**: https://github.com/luongnv89/context-stats | 104 stars | Token/Cost Analytics

## Status: ADOPTED

---

## Integration Strategy: Embed

context-stats menjadi **monitoring engine Layer 1.5** di MAGNATRIX. Track token usage, cost, context zones, dan cache efficiency untuk semua brain agents.

## Directory

```
api-router/context-stats/
├── README.md              # This file
├── config.yaml            # Monitoring config
├── src/                   # Python source (from upstream)
│   ├── claude_statusline/
│   ├── cache_analyzer/
│   └── cost_reporter/
├── dashboards/            # Dashboard templates
└── alerts/                # Alert rules
```

## Context Zones (Integration dengan CCL)

| Zone | Color | Token % | Action |
|------|-------|---------|--------|
| Planning | 🟢 | < 30% | Keep planning |
| Code-only | 🟡 | 30-60% | Finish task, no new plans |
| Mixed | 🟠 | 60-80% | Reduce context, summarize |
| Critical | 🔴 | 80-95% | Emergency: switch model |
| Exceeded | ⚫ | > 95% | Kill or summarize |

## Status Line (Brain Dashboard)

```
hermes | main [3] | 64,000 free (32.0%) | Code | MI:0.918 | +2,500 | Llama3-Uncensored | abc-123
```

| Element | Meaning |
|---------|---------|
| `hermes` | Brain agent name |
| `main [3]` | Session ID + task count |
| `64,000 free (32.0%)` | Available context tokens |
| `Code` | Context zone |
| `MI:0.918` | Model Intelligence score |
| `+2,500` | Tokens consumed since last refresh |
| `Llama3-Uncensored` | Active model |

## MI (Model Intelligence) Score Integration

MI Score = cosine similarity antara current output vs baseline quality.

```python
# Trigger model switch kalau MI drop
if mi_score < 0.75:
    ccl.switch_model(emergency=True)  # → stronger model
    alert_log.warning(f"MI score dropped: {mi_score}")
```

## Commands

```bash
# Install
cd api-router/context-stats
pip install -e .

# Live monitoring
context-stats statusline --brain hermes --refresh 5

# Session report
context-stats export --brain hermes --session latest

# Weekly cost report
context-stats report --brain all --period 7d

# Cache analysis
context-stats cache --brain gqris --show-misses
```

## CCL + context-stats Flow

```
Brain Request → CCL (route) → Model (inference)
                    ↓              ↓
            context-stats    context-stats
            (track tokens)   (track cost)
                    ↓              ↓
            Dashboard ←───── Alert (kalau zone critical)
```

## Alert Rules

```yaml
alerts:
  - name: token-critical
    condition: zone == "critical"
    action: notify + suggest-model-switch

  - name: cost-daily-limit
    condition: daily_cost > $5.00
    action: block-cloud + force-local-only

  - name: cache-inefficient
    condition: cache_hit_rate < 30%
    action: suggest-prompt-optimization

  - name: mi-score-drop
    condition: mi_score < 0.75
    action: suggest-stronger-model
```

## Notes

- context-stats = monitor. CCL = router. Kombinasi = Layer 1.5 complete.
- License: MIT — aman embed.
- Integration: Pure Python, easy merge ke MAGNATRIX Python layer.
