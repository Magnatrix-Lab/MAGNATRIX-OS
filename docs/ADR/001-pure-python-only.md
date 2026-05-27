# ADR-001: Pure Python Standard Library Only

## Status
Accepted

## Context
MAGNATRIX-OS targets users who want complete control over their AI stack without external dependencies that may introduce supply chain attacks, licensing issues, or forced updates.

## Decision
All native modules (`*_native.py`) use Python standard library only. No numpy, no pandas, no requests, no LangChain, no LlamaIndex.

## Consequences

**Positive:**
- Zero dependency hell. Clone and run immediately.
- No supply chain attack surface from PyPI packages.
- Deterministic behavior — no version conflicts.
- Portable across Python 3.11+ environments.

**Negative:**
- Must reimplement algorithms that exist in libraries (vector search, graph traversal, crypto primitives).
- Performance may be slower than optimized C/C++ libraries for hot paths.
- Mitigated by: C++ and Rust native extensions for hot paths (HFT, crypto) with pure-Python fallbacks.

## Alternatives Considered
- Use numpy + scipy → Rejected: introduces 50MB+ dependency tree.
- Use LangChain framework → Rejected: too opinionated, vendor lock-in.
- Use existing vector DBs → Rejected: requires external processes (Redis, FAISS, Milvus).
