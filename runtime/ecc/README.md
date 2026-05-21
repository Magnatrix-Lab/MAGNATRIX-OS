# ECC Integration — MAGNATRIX Agentic OS

> **Repo**: https://github.com/affaan-m/ECC | 188k stars | Agent Harness Framework

## Status: ADOPTED

---

## Integration Strategy: Embed

ECC menjadi **runtime harness** untuk semua brain agents di MAGNATRIX. Setiap brain (HERMES, KIMI_CLAW, GQRIS, ANDROID_CLAW, OPENCLAW) berjalan sebagai agent instance dalam ECC framework.

## Directory

```
runtime/ecc/
├── README.md              # This file
├── AGENTS.md             # Brain agent definitions
├── skills/               # Shared skill marketplace
│   ├── trading/
│   ├── security/
│   ├── browser/
│   └── coding/
├── instincts/            # Behavioral patterns per brain
├── memory/               # Persistent memory config
└── mcp-configs/          # MCP server configs
```

## Agent Definitions (AGENTS.md)

```yaml
agents:
  hermes:
    role: ORACLE
    capabilities: [prediction, analysis, planning, meta-cognition]
    model: local-llama3-uncensored
    memory: persistent
    instincts: [think-before-act, recursive-improvement]

  kimi_claw:
    role: COORDINATOR
    capabilities: [desktop-control, browser-automation, file-system]
    model: local-codellama
    memory: persistent
    instincts: [surgical-change, ui-first]

  gqris:
    role: RESEARCHER
    capabilities: [data-mining, trading-signals, deep-research]
    model: local-wizardlm-uncensored
    memory: persistent
    instincts: [research-first, evidence-based]

  android_claw:
    role: MOBILE
    capabilities: [mobile-automation, apk-building, device-bridge]
    model: local-qwen3
    memory: persistent
    instincts: [edge-first, resource-aware]

  openclaw:
    role: INFRASTRUCTURE
    capabilities: [gateway, api-routing, message-broker]
    model: local-mistral
    memory: persistent
    instincts: [security-first, zero-telemetry]
```

## MCP Bridge

ECC exposes 5 brain agents sebagai MCP servers:

| Brain | MCP Tool | Port |
|-------|----------|------|
| HERMES | `hermes_predict`, `hermes_plan` | 50051 |
| KIMI_CLAW | `kimi_desktop`, `kimi_browser` | 50052 |
| GQRIS | `gqris_research`, `gqris_trade` | 50054 |
| ANDROID_CLAW | `android_device`, `android_build` | 50055 |
| OPENCLAW | `openclaw_route`, `openclaw_monitor` | 50053 |

## Commands

```bash
# Install ECC harness
cd runtime/ecc
npm install

# Register brain agents
npx ecc register --agent hermes --config agents/hermes.yaml
npx ecc register --agent kimi_claw --config agents/kimi_claw.yaml
npx ecc register --agent gqris --config agents/gqris.yaml
npx ecc register --agent android_claw --config agents/android_claw.yaml
npx ecc register --agent openclaw --config agents/openclaw.yaml

# Start all brains
npx ecc start --all

# Check status
npx ecc status
```

## Security Integration

agentshield (repo ke-2 Affaan) di-integrate sebagai security scanner:

```bash
npx agentshield scan --mcp-servers runtime/ecc/mcp-configs/
```

## Notes

- ECC = harness. claude-swarm = orchestrator. JARVIS = OSINT. Kombinasi = complete agent ecosystem.
- License: MIT — aman embed langsung.
- Update: Track upstream ECC releases untuk skill/plugin baru.
