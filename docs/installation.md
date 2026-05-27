# Installation Guide

## Hardware Requirements

| Tier | CPU | RAM | GPU | Storage | Use Case |
|---|---|---|---|---|---|
| **Minimal** | 2 cores | 4 GB | None | 5 GB | Single agent, local Q4_K_M models |
| **Recommended** | 4-8 cores | 16 GB | 8GB VRAM (RTX 3060+) | 20 GB | Multi-agent swarm, 7B models |
| **HFT Node** | 4 cores | 8 GB | None | 5 GB | C++ hot-path trading, low-latency NIC |
| **Full Stack** | 8+ cores | 32 GB | 24GB VRAM (RTX 4090) | 50 GB | All layers + 70B models |

## Software Requirements

| Component | Required Version | Notes |
|---|---|---|
| Python | 3.11+ | Core runtime |
| Git | 2.30+ | For AMATI repo cloning |
| OS | Linux / macOS / Windows WSL | Primary dev on Linux |

Optional:
| Component | Required Version | For |
|---|---|---|
| CMake | 3.20+ | C++ HFT engine build |
| g++ / clang++ | 11+ | C++ compilation |
| pybind11 | 2.12+ | Python-C++ bindings |
| Rust / Cargo | 1.75+ | Rust crypto engine |
| Maturin | 1.5+ | Rust-Python build |

## Installation Steps

### Step 1: Clone Repository

```bash
git clone https://github.com/Magnatrix-Lab/MAGNATRIX-OS.git
cd MAGNATRIX-OS
```

### Step 2: Verify Python

```bash
python --version  # Must be 3.11+
```

No `pip install` required for core system. Every `_native.py` uses stdlib only.

### Step 3: Run Self-Tests (Verify Installation)

```bash
# Quick sanity check — run 3 key modules
python ai/meta_agent_native.py
python runtime/multi_agent_swarm_native.py
python runtime/state_management_native.py
```

Each should print `All tests passed. Demo complete.`

### Step 4: Optional — C++ HFT Engine

```bash
cd trading/cpp_hft_engine
mkdir -p build && cd build
cmake .. -DPYTHON_EXECUTABLE=$(which python)
make -j$(nproc)
cd ../..
```

Verify:
```bash
python -c "from trading.cpp_hft_engine import hft_engine; print('C++ HFT OK')"
```

### Step 5: Optional — Rust Crypto Engine

```bash
cd security/rust_crypto_engine
pip install maturin
maturin develop --release
cd ../..
```

Verify:
```bash
python -c "from security.rust_crypto_engine import crypto_engine; print('Rust Crypto OK')"
```

### Step 6: Optional — Tri-Language Integration Test

```bash
python tests/integration/test_tri_language.py
```

Expected output: 22 tests, 0 failures, ~0.3s.

### Step 7: Launch GUI Dashboard

```bash
cd website
python -m http.server 8080
# Open http://localhost:8080/dashboard.html
```

Or simply open `dashboard.html` directly in any browser (no server required).

---

## Troubleshooting

### Git Push TLS Timeout (Recurring)

**Symptom:**
```
fatal: unable to access 'https://github.com/...': SSL_ERROR_SYSCALL
```

**Fix:**
```bash
git config --local http.version HTTP/1.1
git config --local http.postBuffer 524288000
git config --local http.lowSpeedLimit 1000
git config --local http.lowSpeedTime 120
```

Retry after 10 seconds.

### Git Safe Directory Error

**Symptom:**
```
fatal: detected dubious ownership in repository
```

**Fix:**
```bash
git config --global --add safe.directory $(pwd)
```

### C++ Engine Import Error

**Symptom:**
```
ImportError: No module named '_hft_engine'
```

**Fix:** Tri-language bridge auto-detects and falls back to pure Python. No action needed. To enable C++:
```bash
cd trading/cpp_hft_engine/build
make
```

### Rust Engine Import Error

**Symptom:**
```
ImportError: No module named '_crypto_engine'
```

**Fix:** Bridge auto-falls back to Python. To enable Rust:
```bash
cd security/rust_crypto_engine
maturin develop
```

### Permission Denied on .so Files

**Symptom:**
```
PermissionError: [Errno 13] Permission denied: '*.so'
```

**Fix:**
```bash
chmod +x security/rust_crypto_engine/*.so
dos2unix trading/cpp_hft_engine/build/*.so  # if on WSL
```

### Dashboard Not Loading Panels

**Symptom:** Blank iframe or "file not found" in panel.

**Fix:** Dashboard uses relative paths (`panels/panel_*.html`). Ensure you serve from `website/` directory or use a local server:
```bash
cd website && python -m http.server 8080
```

### Python Version Too Old

**Symptom:** Syntax errors on `match` statements or type hints.

**Fix:** Requires Python 3.11+. Check with `python --version`. Use `pyenv` if needed:
```bash
pyenv install 3.11.9
pyenv local 3.11.9
```

---

## Dependency Map

```
Core (Python 3.11+ stdlib)
    ├── ai/                          # No deps
    ├── knowledge/                   # No deps
    ├── runtime/                     # No deps
    ├── website/                     # No deps (pure HTML/CSS/JS)
    └── tests/integration/           # No deps

Optional: C++ HFT (trading/cpp_hft_engine/)
    ├── CMake >= 3.20
    ├── g++ >= 11
    └── pybind11 >= 2.12

Optional: Rust Crypto (security/rust_crypto_engine/)
    ├── Rust >= 1.75
    ├── Cargo
    └── Maturin >= 1.5
```

## Docker (Optional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
CMD ["python", "runtime/multi_agent_swarm_native.py"]
```

Build and run:
```bash
docker build -t magnatrix .
docker run magnatrix
```
