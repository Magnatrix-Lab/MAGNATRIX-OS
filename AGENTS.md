---
project: MAGNATRIX-OS
agent: universal
version: 1.0.0
layers: 18
languages: [Python, C++, Rust, HTML/CSS/JS]
---

# Project Overview

MAGNATRIX-OS is a private, uncensored, open-source AI operating system evolving from Agentic OS → AGI → Super AI. It follows the **AMATI-PELAJARI-TIRU** methodology: observe external repositories, learn their core architectural patterns, and reimplement them natively as `_native.py` modules.

The system is built on a **18-layer architecture** covering everything from kernel-level primitives to high-level AI reasoning, financial infrastructure, security, and governance. It employs a **tri-language hybrid architecture** (Python orchestration, C++ hot paths, Rust crypto primitives) for performance and security.

# Architecture

## 18-Layer Architecture

| Layer | Name | Technology |
|-------|------|------------|
| 0 | Kernel | Core primitives, memory, scheduler |
| 1 | Protocol | Communication, MCP, agent connect |
| 1.5 | API Router | 3-tier LLM routing, token optimization |
| 2 | Identity | Self-sovereign identity, KYC |
| 3 | Runtime | Execution engine, JIT compiler |
| 4 | P2P Mesh | Kademlia DHT, mesh networking |
| 5 | Knowledge | Vector DB, RAG, document agents |
| 6 | Skills | Skill engine, marketplace |
| 7 | Browser | Web automation, scraping |
| 8 | HFT Trading | C++ order book, arbitrage |
| 9 | Security | Rust crypto, zero-knowledge |
| 10 | Uncensored AI | Local LLM, theorem proving |
| 11 | Governance | Trust, voting, token economy |
| 12 | IDE | Code editor, compiler |
| 13 | Offensive Security | Recon, vuln scanner, exploit |
| 13.5 | Auto Repo Hunter | Autonomous AMATI pipeline |
| 14 | Blockchain | Core chain, consensus, wallet |
| 15 | Web3 | Solana, Flow, Pharos, EVM |
| 16 | National Finance | CBDC, RWA, Syariah, ASEAN |
| 17 | GUI | Dashboard, panels, control |

## Tri-Language Hybrid
- **Python**: Orchestration, business logic, AI integration
- **C++**: HFT hot paths, order book, fixed-point arithmetic (pybind11)
- **Rust**: Cryptographic primitives, secure enclave (PyO3)

## Native Module Pattern
All external patterns are reimplemented as `*_native.py` modules with:
- Pure-Python implementation (no external dependencies for core)
- Standalone `if __name__ == "__main__"` test block
- AMATI-PELAJARI-TIRU attribution header
- SQLite-backed persistence where applicable

# Build & Test
- test: `python3 -m py_compile *_native.py` (syntax check all)
- test: `python3 <module>.py` (standalone test)
- lint: `python3 -m py_compile <file>.py`
- commit: `git add -A && git commit -m "feat: description" && git push`
- stats: `find . -name "*_native.py" | wc -l` (count native modules)
- stats: `find . -name "*.py" | wc -l` (count total Python files)

# Code Conventions
- All native files use `_native.py` suffix
- All files have `from __future__ import annotations` for type hints
- All modules have `if __name__ == "__main__"` standalone test
- Use `dataclasses` for data models, `enum` for state machines
- SQLite for persistence when stateful storage needed
- Never hardcode API keys; use environment variables or config files
- Follow AMATI pattern: observe → learn → reimplement → commit
- C++ and Rust bindings via pybind11 and PyO3 respectively
- GUI panels: pure HTML/CSS/JS, no external frameworks
- Dark glassmorphism theme for all GUI elements

# Guardrails
- No API keys in source code
- No external dependencies for core native modules
- No closed-source or proprietary binaries in repository
- All modules must be self-contained and testable standalone
- Security modules include "authorized use only" warnings
- No telemetry or data collection without explicit consent
- Blockchain/financial modules include regulatory compliance notes
- Offensive security modules include "authorized testing only" warnings

# Communication Style
- Direct, short, no preamble
- Lead with the point
- Colloquial: "Take a look at this", "Get this done", "Fix this"
- Plain text only, no markdown formatting in messages
- File delivery for structured content >3 sentences
- Batch sending when multiple files needed
- User language: Indonesian (Bahasa Indonesia)
