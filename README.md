# MAGNATRIX-OS

A private, uncensored, open-source agentic operating system.
Pure Python. Zero external dependencies. Ships with 135+ native modules.

---

## Quickstart (30 seconds)

```bash
# Clone
git clone https://github.com/Magnatrix-Lab/MAGNATRIX-OS.git
cd MAGNATRIX-OS

# No pip install needed — pure Python stdlib
python runtime/multi_agent_swarm_native.py
python runtime/agent_collaboration_native.py
python ai/meta_agent_native.py
python ai/theorem_prover_native.py
```

Every `*_native.py` has a self-test suite in `__main__`. Run any file directly.

---

## What You Get

| Component | File | Lines | What It Does |
|---|---|---|---|
| **Swarm Engine** | `runtime/multi_agent_swarm_native.py` | 1,177 | Multi-agent orchestration: registry, message bus, task delegation, consensus, auctions, MCP protocol |
| **Collaboration** | `runtime/agent_collaboration_native.py` | 519 | 5 patterns: CrewAI, AutoGen, LangGraph, MCP, Hierarchical |
| **State Backend** | `runtime/state_management_native.py` | 780 | Redis-like KV, Vector DB, Graph DB, Temporal Store |
| **Meta Agent** | `ai/meta_agent_native.py` | 643 | Prompt-driven agent framework with XML tools |
| **Theorem Prover** | `ai/theorem_prover_native.py` | 2,373 | Neuro-symbolic Draft/Sketch/Prove, 18 tactics, BFS search |
| **Agentic RAG** | `knowledge/agentic_rag_native.py` | 629 | LangGraph+FAISS+MCP hybrid, hash embeddings |
| **JIT Compiler** | `runtime/jit_compiler_native.py` | 1,056 | 4-tier V8-style: Ignition→Sparkplug→Maglev→TurboFan |
| **HFT Engine** | `trading/cpp_hft_engine/` | 450 | C++ lock-based order book + pybind11 |
| **Crypto Engine** | `security/rust_crypto_engine/` | 346 | Rust Ed25519/AES/ChaCha20 via PyO3 |
| **Tri-Language Bridge** | `runtime/tri_language_bridge.py` | 588 | Auto-detect C++/Rust, fallback to Python |
| **GUI Dashboard** | `website/dashboard.html` | 1,200 | 20-panel SPA, all iframe standalone |

**Total:** 135+ native files, ~163K lines Python, 169 commits.

---

## Architecture (C4 Model — Level 1: System Context)

```
┌─────────────────────────────────────────────────────────────┐
│                         YOU (User)                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   MAGNATRIX-OS (System)                     │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│  │  AI Layer  │  │  Runtime   │  │  Security  │           │
│  │  (Agents)  │  │  (Swarm)   │  │  (Crypto)  │           │
│  └────────────┘  └────────────┘  └────────────┘           │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│  │  Trading   │  │   P2P      │  │   GUI      │           │
│  │  (HFT)     │  │   (DHT)    │  │ Dashboard  │           │
│  └────────────┘  └────────────┘  └────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

See [docs/architecture.md](docs/architecture.md) for C4 Level 2-4, flowcharts, sequence diagrams.

---

## Installation

### Requirements

| Tier | Hardware | Use Case |
|---|---|---|
| Minimal | 2 CPU, 4GB RAM | Single agent, local LLM Q4_K_M |
| Recommended | 4 CPU, 16GB RAM, GPU 8GB+ | Multi-agent swarm, 7B models |
| HFT Node | 4 CPU, 8GB RAM, low-latency NIC | C++ hot-path trading |

### No Dependencies (Default)

Every `_native.py` runs with Python 3.11+ stdlib only. No `pip install`.

### Optional: C++ HFT Engine

```bash
cd trading/cpp_hft_engine
mkdir build && cd build
cmake .. && make -j$(nproc)
python -c "import _hft_engine; print('C++ engine loaded')"
```

Requires: `cmake`, `g++`, `pybind11`.

### Optional: Rust Crypto Engine

```bash
cd security/rust_crypto_engine
pip install maturin  # only optional dep
maturin develop
python -c "import _crypto_engine; print('Rust engine loaded')"
```

Requires: `rust`, `cargo`.

### Troubleshooting

| Problem | Solution |
|---|---|
| `ImportError: _hft_engine` | C++ not compiled — bridge auto-falls back to Python |
| `ImportError: _crypto_engine` | Rust not compiled — bridge auto-falls back to Python |
| `git push TLS timeout` | `git config --local http.version HTTP/1.1` |
| Git safe.directory error | `git config --global --add safe.directory $(pwd)` |

See [docs/installation.md](docs/installation.md) for full guide.

---

## Working End-to-End Example

```python
# 1. Create a swarm
from runtime.multi_agent_swarm_native import SwarmOrchestrator, AgentCapabilities

orch = SwarmOrchestrator()

# 2. Register agents with roles (CrewAI pattern)
orch.register_agent("r1", "Alice", "researcher",
    AgentCapabilities(specialties=["research"]))
orch.register_agent("w1", "Bob", "writer",
    AgentCapabilities(specialties=["write"]))
orch.register_agent("c1", "Carol", "critic",
    AgentCapabilities(specialties=["review"]))

# 3. Submit a task — auto-decomposed and delegated
task = orch.submit_task("Research Python asyncio best practices")

# 4. Check results
print(f"Task: {task.description}")
print(f"Subtasks: {len(task.subtasks)}")
for st_id in task.subtasks:
    st = orch.delegator.get_task(st_id)
    print(f"  [{st.status}] {st.description[:50]}...")

orch.stop()
```

Save as `demo.py`, run: `python demo.py`

See [docs/quickstart.md](docs/quickstart.md) for 10 more working examples.

---

## Project Structure

```
MAGNATRIX-OS/
├── ai/                     # AI agents (7 native implementations)
├── knowledge/              # RAG, document agents
├── runtime/                # Swarm, state, JIT compiler, bridge
├── security/               # Rust crypto + Python fallback
├── trading/                # C++ HFT + Python fallback
├── website/                # 20-panel GUI dashboard
│   ├── dashboard.html      # Main shell
│   └── panels/             # 20 standalone panels
├── docs/                   # Documentation
│   ├── quickstart.md       # Working examples
│   ├── installation.md     # Hardware, deps, troubleshooting
│   ├── architecture.md     # C4 model, diagrams
│   ├── api_reference.md    # All modules
│   └── ADR/                # Architecture Decision Records
├── tests/                  # Integration tests
│   └── integration/
│       └── test_tri_language.py  # 22 tests
```

---

## Every Module Self-Tests

Run any `*_native.py` directly — it has a `__main__` demo + test suite:

```bash
python ai/meta_agent_native.py           # 11 tests
python ai/theorem_prover_native.py        # 11 tests
python ai/autonomous_agent_native.py      # 8 tests
python ai/local_agent_native.py           # 8 tests
python knowledge/agentic_rag_native.py     # Vector + graph tests
python knowledge/document_agent_native.py # Multi-doc routing tests
python runtime/jit_compiler_native.py     # 12 compiler tests
python runtime/multi_agent_swarm_native.py  # 9 swarm tests
python runtime/agent_collaboration_native.py # 5 pattern tests
python runtime/state_management_native.py   # 5 backend tests
```

---

## License

AGPL-3.0. See LICENSE.

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md). TL;DR: AMATI-PELAJARI-TIRU — observe external repos, learn patterns, reimplement natively.
