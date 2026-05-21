# CCL Integration — MAGNATRIX Agentic OS

> **Repo**: https://github.com/luongnv89/ccl | 27 stars | Model Router (Cloud ↔ Local)

## Status: ADOPTED

---

## Integration Strategy: Embed

CCL menjadi **core engine Layer 1.5 — API Router & Cost Optimizer** di MAGNATRIX. Semua inference request melewati CCL sebelum di-route ke model (cloud atau local).

## Directory

```
api-router/ccl/
├── README.md              # This file
├── config.yaml            # Model registry + routing rules
├── adapters/              # Per-model adapter
│   ├── local/
│   │   ├── ollama.py      # Ollama bridge
│   │   ├── llamacpp.py    # llama.cpp bridge
│   │   ├── vllm.py        # vLLM bridge (AEON-7)
│   │   └── lmstudio.py    # LM Studio bridge
│   └── cloud/
│       ├── openai.py      # OpenAI GPT
│       ├── anthropic.py   # Claude
│       ├── openrouter.py  # OpenRouter (free/cheap models)
│       └── gemini.py      # Google Gemini
├── cache/                 # Response cache
└── logs/                  # Token usage logs
```

## Routing Rules (config.yaml)

```yaml
routing:
  default: local-ollama
  uncensored_mode: true  # Block all cloud when true

  # Task → Model mapping
  tasks:
    chat: local-llama3
    code: local-codellama
    reason: local-wizardlm
    research: local-qwen3-27b
    predict: local-gemma4-31b
    uncensored: local-uncensored-only
    emergency_cloud: openrouter-claude-haiku  # Fallback only

  # Cost optimization
  cost:
    max_tokens_per_request: 4096
    cache_enabled: true
    batch_similar_requests: true
    cloud_budget_daily_usd: 5.00

  # Privacy
  privacy:
    sensitive_data: local-only
    pii_detection: true
    telemetry: false
```

## CCL + context-stats Integration

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   Brain     │───▶│     CCL      │───▶│   Model     │
│  Request    │    │  (Router)    │    │ (Local/Cloud)│
└─────────────┘    └──────────────┘    └─────────────┘
                          │
                          ▼
                   ┌──────────────┐
                   │ context-stats │
                   │ (Monitor)    │
                   └──────────────┘
```

CCL route request → context-stats track token/cost → report ke dashboard.

## Commands

```bash
# Install CCL
cd api-router/ccl
npm install

# Add local models
npx ccl add-model --name ollama-llama3 --provider ollama --endpoint http://localhost:11434
npx ccl add-model --name aeon7-qwen3.6 --provider vllm --endpoint http://localhost:8000

# Add cloud fallback
npx ccl add-model --name openrouter-haiku --provider openrouter --api-key $OPENROUTER_KEY

# Test routing
npx ccl test "Explain quantum computing" --task reason
# → routes to local-wizardlm (uncensored mode)

# Switch model
npx ccl switch openrouter-haiku
# → routes to cloud (only if uncensored_mode: false)
```

## AEON-7 Integration

AEON-7 models (NVFP4) di-deploy sebagai vLLM servers:

```bash
# Qwen 3.6 27B Ultimate Uncensored
docker run -d --gpus all \
  -p 8000:8000 \
  -v ./models:/models \
  aeon7/vllm-dflash:qwen3.6-27b

# CCL config
npx ccl add-model \
  --name aeon7-qwen3.6-27b \
  --provider vllm \
  --endpoint http://localhost:8000 \
  --tags [uncensored, local, high-performance]
```

## Cost Savings

| Metric | Before CCL | After CCL |
|--------|-----------|-----------|
| Avg cost/query | $0.05 (cloud) | $0.00 (local) |
| Cache hit rate | 0% | ~40% |
| Token waste | High (repeated context) | Low (dedup) |
| Monthly cost | $150+ | <$5 (cloud fallback only) |

## Notes

- CCL = model router. context-stats = monitor. Kombinasi = Layer 1.5 complete.
- License: MIT — aman embed.
- Update: Track upstream untuk model provider baru.
