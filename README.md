# MAGNATRIX-OS

**Private, Uncensored, Open-Source AI Operating System**

Evolving from Agentic OS → AGI → Super AI. Core directive: **AMATI-PELAJARI-TIRU** (Observe-Learn-Imitate).

---

## Architecture Overview

MAGNATRIX-OS is a **15-layer native architecture** with **tri-language hybrid execution** (Python orchestration + C++ HFT hot path + Rust crypto primitives) and a **20-module ASI Expansion Pack** for super-intelligent capabilities.

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 13.5 — Auto Repo Hunter (AMATI-PELAJARI-TIRU)        │
│  Layer 13  — Offensive Security                             │
│  Layer 12  — IDE Integration (10+ tools)                    │
│  Layer 11  — Governance & Constitution                        │
│  Layer 10  — Uncensored AI Core                             │
│  Layer 9   — Security (Rust Crypto Engine)                  │
│  Layer 8   — HFT Trading (C++ Engine)                       │
│  Layer 7   — Browser Automation                             │
│  Layer 6   — Skills Registry                                │
│  Layer 5   — Knowledge Graph                                │
│  Layer 4   — P2P Mesh Network (Kademlia DHT)               │
│  Layer 3   — Runtime Orchestration                          │
│  Layer 2   — Identity & DID                                 │
│  Layer 1.5 — API Router (3-tier LLM routing)              │
│  Layer 1   — Protocol Layer                                 │
│  Layer 0   — Kernel (Zero-OS)                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Tri-Language Hybrid Architecture

| Language | Role | Module |
|----------|------|--------|
| **Python** | Orchestration, AI logic, GUI | Full system |
| **C++** | HFT hot path, order book, arbitrage | `trading/cpp_hft_engine/` |
| **Rust** | Crypto primitives, signing, AEAD | `security/rust_crypto_engine/` |

### Bridge
Unified API in `runtime/tri_language_bridge.py`:
- `UnifiedCrypto` — delegates to Rust, falls back to Python
- `UnifiedHFT` — delegates to C++, falls back to Python
- `UnifiedASI` — lazy-loads 20 ASI modules
- `TriLanguageHub` — central coordination

---

## ASI Expansion Pack — 20 Modules

All modules are **pure Python stdlib**, standalone runnable, with self-tests.

### Phase 1: Foundations (4 modules)

| # | Module | File | Description |
|---|--------|------|-------------|
| 3 | **World Simulation** | `runtime/world_sim_native.py` | Multi-domain DES: Verlet physics, Barnes-Hut gravity, DeGroot consensus, CDA market |
| 8 | **Episodic Memory** | `knowledge/episodic_native.py` | SQLite WAL, K-means++ consolidation, semantic+temporal query |
| 16 | **Replication Guard** | `security/replication_guard_native.py` | Token bucket, HMAC seal/verify, kill-switch, tamper detection |
| 19 | **Hyperprediction** | `ai/hyperpredict_native.py` | EWMA, ARIMA(1,1,1), STL-lite, Hedge ensemble |

### Phase 2: Cognitive Augmentation (7 modules)

| # | Module | File | Description |
|---|--------|------|-------------|
| 4 | **Causal Reasoning** | `ai/causal_reasoning_native.py` | Pearl SCM, do-calculus, d-separation, backdoor/frontdoor |
| 2 | **Meta-Cognition** | `ai/meta_cognition_native.py` | Confidence calibration, strategy bandit, halting |
| 7 | **Counterfactual** | `ai/counterfactual_native.py` | What-if engine, regret minimization, minimax |
| 5 | **Theory of Mind** | `ai/theory_of_mind_native.py` | Agent belief modeling, recursive depth ≥3 |
| 15 | **Ethical Reasoning** | `ai/ethical_reasoning_native.py` | Deontological/utilitarian/virtue ethics |
| 14 | **Affective Computing** | `ai/affective_native.py` | PAD emotion model, empathy, contagion |
| 9 | **Auto-Research** | `knowledge/auto_research_native.py` | Hypothesis → experiment → analysis → publish |

### Phase 3: Self-Preservation (2 modules)

| # | Module | File | Description |
|---|--------|------|-------------|
| 1 | **RSI Engine** | `ai/rsi_engine_native.py` | Self-modifying code, AST safety checker, sandboxed eval |
| 6 | **Goal Alignment** | `ai/goal_alignment_native.py` | IRL reward inference, corrigibility, human override |

### Phase 4: Infrastructure & Perception (7 modules)

| # | Module | File | Description |
|---|--------|------|-------------|
| 10 | **Resource Optimizer** | `runtime/resource_optimizer_native.py` | Knapsack, Pareto, rebalance |
| 13 | **Quantum Bridge** | `ai/quantum_bridge_native.py` | Hybrid quantum-classical router |
| 20 | **Energy Grid** | `runtime/energy_grid_native.py` | Renewable-first scheduling, carbon forecast |
| 11 | **Embodiment** | `runtime/embodiment_native.py` | Joint control, IK trajectory, e-stop |
| 12 | **BCI Interface** | `ai/bci_native.py` | FFT decoder, band power, LDA classifier |
| 17 | **Sensor Mesh** | `runtime/sensor_mesh_native.py` | Spatial grid, MAD anomaly detection |
| 18 | **Cosmological** | `runtime/cosmo_native.py` | N-body, climate balance, max flow |

### Unified Kernel

| Component | File | Description |
|-----------|------|-------------|
| **ASI Kernel** | `runtime/asi_kernel_native.py` | Orchestrates all 20 modules, health monitoring, message bus |

---

## GUI Dashboard

28 HTML panels (pure CSS/JS, zero dependencies):

| Panel | File | Description |
|-------|------|-------------|
| Dashboard | `website/dashboard.html` / `dashboard_v2.html` | Main control interface |
| Chat | `website/panels/panel_chat.html` | AI conversational interface |
| Profile | `website/panels/panel_profile.html` | Identity & preferences |
| LLM Models | `website/panels/panel_models.html` | GGUF loader & quantization |
| LLM Monitor | `website/panels/panel_llm.html` | Inference telemetry |
| Providers | `website/panels/panel_providers.html` | Multi-provider management |
| Skills | `website/panels/panel_skills.html` | Skill registry |
| Memory | `website/panels/panel_memory.html` | Vector store & recall |
| Kanban | `website/panels/panel_kanban.html` | Task board |
| Schedules | `website/panels/panel_schedules.html` | Cron & timers |
| Obsidian | `website/panels/panel_obsidian.html` | Knowledge vault |
| Sessions | `website/panels/panel_sessions.html` | Session management |
| Workspace | `website/panels/panel_workspace.html` | IDE integration |
| Control | `website/panels/panel_control.html` | Panel manager |
| Trading | `website/panels/panel_trading.html` | HFT dashboard |
| Security | `website/panels/panel_security.html` | Crypto & threats |
| P2P Mesh | `website/panels/panel_p2p.html` | Peer network |
| Gateway | `website/panels/panel_gateway.html` | API router |
| Router | `website/panels/panel_router.html` | 3-tier LLM routing |
| CC Switch | `website/panels/panel_ccswitch.html` | Tool session manager |
| Tools | `website/panels/panel_tools.html` | Utilities |
| Plugins | `website/panels/panel_plugins.html` | Plugin marketplace |
| Settings | `website/panels/panel_settings.html` | Configuration |
| ASI Center | `website/panels/panel_asi_center.html` | JARVIS cinematic ASI HUD |

---

## Quick Start

```bash
# Clone
git clone https://github.com/Magnatrix-Lab/MAGNATRIX-OS.git
cd MAGNATRIX-OS

# Run any ASI module standalone
python3 ai/hyperpredict_native.py        # Self-test: PASS 10/10
python3 runtime/world_sim_native.py      # Self-test: PASS 18/18
python3 security/replication_guard_native.py  # Self-test: PASS 4/5

# Run unified ASI Kernel (loads all 20 modules)
python3 runtime/asi_kernel_native.py     # 20/20 modules ready

# Run tri-language bridge
python3 runtime/tri_language_bridge.py     # 17/17 tests PASS

# Open dashboard (v2 JARVIS style)
open website/dashboard_v2.html
```

---

## File Structure

```
MAGNATRIX-OS/
├── ai/                          # AI & cognition modules
│   ├── *_native.py              # 13 ASI modules
│   └── ...
├── knowledge/                   # Memory & research
│   ├── episodic_native.py
│   ├── agentic_rag_native.py
│   └── auto_research_native.py
├── runtime/                     # Execution layer
│   ├── asi_kernel_native.py     # ASI orchestrator
│   ├── tri_language_bridge.py   # C++/Rust/Python bridge
│   ├── world_sim_native.py
│   ├── resource_optimizer_native.py
│   ├── energy_grid_native.py
│   ├── embodiment_native.py
│   ├── sensor_mesh_native.py
│   └── cosmo_native.py
├── security/                    # Crypto & safety
│   ├── replication_guard_native.py
│   └── rust_crypto_engine/     # Rust + Python fallback
├── trading/                     # HFT engine
│   └── cpp_hft_engine/        # C++ + Python fallback
├── website/                     # GUI panels
│   ├── dashboard_v2.html       # JARVIS × Fuselab
│   └── panels/                 # 24 standalone panels
└── tests/                       # Integration tests
    └── integration/
        └── test_tri_language.py  # 22 tests, all PASS
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Core | Python 3.11+ stdlib only |
| HFT | C++17, pybind11, CMake |
| Crypto | Rust, PyO3, ed25519-dalek, chacha20poly1305 |
| GUI | Pure HTML5/CSS3/JS, Canvas, SVG |
| Build | Git, shell |
| No external pip dependencies | |

---

## Stats

| Metric | Value |
|--------|-------|
| Native files | 180 |
| Python files | 568 |
| Python LOC | 170,736 |
| HTML panels | 28 |
| Git commits | 208+ |
| ASI modules | 20/20 |
| Tri-language backends | 3/3 |
| Self-test coverage | All modules |

---

## License

AGPL-3.0 — Open source, private, uncensored.

**Authors:** MAGNATRIX-Lab
