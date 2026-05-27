# ADR-002: Tri-Language Hybrid Architecture (Python + C++ + Rust)

## Status
Accepted

## Context
Pure Python is sufficient for orchestration and prototyping but too slow for:
- High-frequency trading (microsecond-level tick processing)
- Cryptographic operations (hashing, signing, encryption at scale)

## Decision
Use Python sebagai orchestration layer, C++ untuk hot paths (HFT), Rust untuk security primitives (crypto). Implement auto-detection dengan graceful fallback to pure Python.

## Architecture
```
┌─────────────┐
│   Python    │  ← Orchestrator, agent logic, glue code
│  (tri_lang  │
│   _bridge)  │
└──────┬──────┘
       │ FFI
┌──────┴──────┐
│  C++ (HFT)  │  ← Order book, arbitrage, tick processing
│  pybind11   │
└─────────────┘
       │ FFI
┌──────┴──────┐
│ Rust (Crypto)│ ← Ed25519, AES, ChaCha20, Argon2, SHA
│   PyO3      │
└─────────────┘
```

## Consequences

**Positive:**
- Python keeps development velocity high.
- C++ delivers microsecond-level HFT performance.
- Rust provides memory-safe crypto without GC pauses.
- Pure-Python fallback means system always works even without compiled extensions.

**Negative:**
- Three build systems (setuptools, CMake, Cargo).
- Cross-compilation complexity for ARM/mobile targets.
- Debugging across language boundaries is harder.

## Mitigations
- CMakeLists.txt includes `pybind11_add_module` with automatic Python detection.
- `Cargo.toml` uses `pyo3` dengan `abi3-py311` for broad compatibility.
- `tri_language_bridge.py` auto-detects `.so`/`.pyd` files dan falls back gracefully.
- Integration test `test_tri_language.py` verifies all 3 backends.
