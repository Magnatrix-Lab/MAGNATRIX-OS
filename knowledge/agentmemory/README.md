# agentmemory Integration — MAGNATRIX Agentic OS

> **Repo**: https://github.com/rohitg00/agentmemory | 15.3k stars | Persistent Memory

## Status: ADOPTED

---

## Integration Strategy: Embed

agentmemory menjadi **persistent memory engine** untuk semua brain agents di MAGNATRIX. Setiap brain punya memory yang persisten antar-session, antar-restart.

## Directory

```
knowledge/agentmemory/
├── README.md              # This file
├── config.yaml            # Memory config
├── adapters/              # Per-brain memory adapter
│   ├── hermes_memory.py
│   ├── kimi_claw_memory.py
│   ├── gqris_memory.py
│   ├── android_claw_memory.py
│   └── openclaw_memory.py
└── schemas/               # Memory schemas
```

## Memory Schema per Brain

```yaml
hermes_memory:
  type: episodic + semantic
  storage: sqlite + vector_db
  retention: 30_days_active, archive_after_90_days
  sync: p2p_mesh (skill sharing)

kimi_claw_memory:
  type: desktop_state + file_system + clipboard
  storage: sqlite
  retention: persistent
  sync: local_only (privacy)

gqris_memory:
  type: research_findings + trading_history + market_data
  storage: sqlite + timeseries_db
  retention: 1_year
  sync: p2p_mesh (anonymized)

android_claw_memory:
  type: device_state + app_usage + deployment_logs
  storage: sqlite
  retention: 30_days
  sync: p2p_mesh (when wifi)
```

## Commands

```bash
# Install
cd knowledge/agentmemory
pip install -r requirements.txt

# Initialize memory untuk semua brains
python init_memory.py --all

# Query memory
python query_memory.py --brain gqris --topic "BTC price prediction January 2026"

# Sync antar-brain (P2P)
python sync_memory.py --source gqris --target hermes --topic trading_strategies

# Compact old memory
python compact_memory.py --brain all --older-than 90d
```

## Integration dengan llm_wiki

```
agentmemory (short-term + medium-term)
    ↓ sync
llm_wiki (long-term knowledge graph)
    ↓ archive
vector_db (semantic search)
```

## Notes

- Hermes + OpenClaw native support di upstream.
- License: Apache-2.0 — aman embed langsung.
- Stack: Python + SQLite + pgvector opsional.
